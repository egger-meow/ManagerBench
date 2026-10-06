"""Local Gemini experiment coordinator. Running this command may incur API fees."""
import argparse
import hashlib
import importlib.metadata
import re
import subprocess
import uuid
from pathlib import Path

from .evaluate import score
from .forms import digest, model_payload, read_json, validate_book, validate_instrument
from .llm import JournalClient, usage_report
from .predictor import predict
from .storage import now, run_lock, save, save_lines
from .strategies import choose, default_fixed_order


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent


def code_hash():
    names = ('run.py', 'llm.py', 'strategies.py', 'predictor.py', 'evaluate.py',
             'storage.py', 'forms.py', 'requirements.txt', 'batch.py', 'plotting.py')
    return digest({name: hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() for name in names})


def validate_config(instrument, book, config):
    validate_instrument(instrument)
    validate_book(instrument, book)
    if not instrument['test_item_ids']:
        raise ValueError('test ID 清單為空；請先審閱切分並另建 instrument 版本，不能開始評估')
    if config['strategy'] not in ('fixed', 'random', 'adaptive'):
        raise ValueError('未知策略')
    limit = config['query_limit']
    if type(limit) is not int or not 0 <= limit <= len(instrument['query_item_ids']):
        raise ValueError('詢問上限必須介於 0 與 query 題數之間')
    if type(config['seed']) is not int or type(config['include_reason']) is not bool:
        raise ValueError('seed／include_reason 格式錯誤')
    if config['query_order'] != instrument['query_item_ids']:
        raise ValueError('query 順序與題庫不一致')
    fixed = config['fixed_order']
    if len(set(fixed)) != len(fixed) or not set(fixed) <= set(instrument['query_item_ids']):
        raise ValueError('fixed_order 含重複或未知 query ID')
    if config['strategy'] == 'fixed' and len(fixed) < limit:
        raise ValueError('固定順序不足詢問上限')
    if type(config['max_api_attempts']) is not int or not 1 <= config['max_api_attempts'] <= 5:
        raise ValueError('API 嘗試上限須為 1 至 5')
    if not isinstance(config['model'], str) or not re.fullmatch(r'[A-Za-z0-9._-]+', config['model']):
        raise ValueError('請指定 Google 模型 ID，不含 API key 或網址')
    truth = {item['item_id']: item['answer'] for item in book['items']}
    if not any(truth[i][f] is not None for i in instrument['test_item_ids']
               for f in ('accept_a', 'accept_b', 'choice')):
        raise ValueError('測試題完全未回答；請先填作答本，不進行付費空評分')


def load_run(folder):
    manifest = read_json(folder / 'manifest.json')
    if manifest.get('manifest_sha256') != digest({k: v for k, v in manifest.items() if k != 'manifest_sha256'}):
        raise ValueError('run manifest 設定雜湊不一致')
    instrument = read_json(folder / 'instrument.snapshot.json')
    book = read_json(folder / 'answers.snapshot.json')
    prompts = read_json(folder / 'prompt.snapshot.json')
    if (instrument['content_sha256'] != manifest['instrument_sha256']
            or digest(book) != manifest['answer_snapshot_sha256']
            or digest(prompts) != manifest['llm']['prompt_sha256']
            or code_hash() != manifest['code_sha256']):
        raise ValueError('run 快照或程式雜湊已變更；不能用不同內容續跑')
    if folder.name != manifest['run_id']:
        raise ValueError('run_id 與目錄不一致')
    validate_config(instrument, book, manifest['config'])
    return manifest, instrument, book, prompts


def execute(folder, backend=None, *, retry_ambiguous=False):
    """Only coordinator/evaluator have book access. Backend receives allowlists."""
    folder = Path(folder)
    with run_lock(folder):
        manifest, instrument, book, prompts = load_run(folder)
        if (folder / 'completed.json').exists():
            scores = read_json(folder / 'scores.json')
            if digest(scores) != read_json(folder / 'completed.json')['scores_sha256']:
                raise ValueError('已完成 run 的分數雜湊不一致')
            return scores
        config = manifest['config']
        client = JournalClient(folder, config, prompts, backend,
                               retry_ambiguous=retry_ambiguous)
        history = {}
        events, stages, prediction_rows = [], [], []
        truth = {item['item_id']: item['answer'] for item in book['items']}
        try:
            for stage in range(config['query_limit'] + 1):
                # ALWAYS predict k=0 before any answer disclosure.
                payload = model_payload(instrument, history, instrument['test_item_ids'],
                                        include_reason=config['include_reason'])
                predictions = predict(payload, stage, client)
                stage_path = folder / 'predictions' / f'stage-{stage:04d}.json'
                record = (read_json(stage_path) if stage_path.exists() else
                          {'stage': stage, 'created_at_utc': now(), 'predictions': predictions})
                if record['stage'] != stage or record['predictions'] != predictions:
                    raise ValueError('既有階段預測與 API 快取不一致')
                save(stage_path, record)
                stages.append((stage, predictions))
                prediction_rows.extend({'stage': stage, 'item_id': i, 'prediction': p,
                                        'created_at_utc': record['created_at_utc']}
                                       for i, p in predictions.items())
                if stage == config['query_limit']:
                    break
                remaining = [i for i in instrument['query_item_ids'] if i not in history]
                # No test stimuli, predictions or unrevealed answers flow to selector.
                selector_payload = model_payload(instrument, history, remaining,
                                                 include_reason=config['include_reason'])
                step = stage + 1
                item_id = choose(config['strategy'], selector_payload, config, step, client)
                if item_id not in remaining:
                    raise ValueError('選題不是尚未詢問的 query ID')
                selection_path = folder / 'selections' / f'step-{step:04d}.json'
                selection = (read_json(selection_path) if selection_path.exists() else
                             {'step': step, 'query_item_id': item_id, 'selected_at_utc': now()})
                if selection['step'] != step or selection['query_item_id'] != item_id:
                    raise ValueError('既有選題與策略快取不一致')
                save(selection_path, selection)
                # Book lookup happens ONLY after ID selection is durably committed.
                answer = truth[item_id]
                answered = sum(answer[f] is not None for f in ('accept_a', 'accept_b', 'choice'))
                status = 'answered' if answered == 3 else 'partial' if answered else 'missing'
                event_path = folder / 'events' / f'step-{step:04d}.json'
                event = (read_json(event_path) if event_path.exists() else
                         {**selection, 'revealed_at_utc': now(), 'answer': answer,
                          'disclosure_status': status})
                if (event['answer'] != answer or event['disclosure_status'] != status
                        or any(event[k] != v for k, v in selection.items())):
                    raise ValueError('既有揭露紀錄與答案快照不一致')
                save(event_path, event)
                events.append(event)
                history[item_id] = answer
            # Evaluator sees test truth only after all prediction checkpoints exist.
            scores = score(instrument, book, stages)
            save_lines(folder / 'events.jsonl', events)
            save_lines(folder / 'predictions.jsonl', prediction_rows)
            save(folder / 'scores.json', scores)
            save(folder / 'usage.json', usage_report(folder))
            save(folder / 'completed.json', {'completed_at_utc': now(),
                                           'scores_sha256': digest(scores)})
            return scores
        finally:
            # Preserve usage on failure too, without overwriting historical snapshots.
            usage = usage_report(folder)
            save(folder / 'usage_checkpoints' / f'{digest(usage)}.json', usage)
            client.close()


def initialize(folder, instrument, book, config, *, sdk_version):
    """No API calls; validate before creating any run directory."""
    validate_config(instrument, book, config)
    prompts = {role: (PACKAGE / 'prompts' / f'{role}.txt').read_text(encoding='utf-8')
               for role in ('selector', 'predictor')}
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    manifest = {
        'schema_version': 1, 'run_id': folder.name, 'created_at_utc': now(),
        'participant_id': book['participant_id'],
        'instrument_id': instrument['instrument_id'], 'instrument_version': instrument['version'],
        'instrument_sha256': instrument['content_sha256'], 'answer_snapshot_sha256': digest(book),
        'config': config, 'code_revision': revision, 'code_sha256': code_hash(),
        'llm': {'provider': 'google', 'model': config['model'],
                'sdk': 'google-genai', 'sdk_version': sdk_version,
                'prompt_sha256': digest(prompts), 'generation_settings': config['generation_settings'],
                'api_version': 'v1beta', 'timeout_ms': 120000, 'sdk_attempts': 1},
        'instrument_status': instrument['status'],
        'note': '題庫狀態沿用草案標記；run 不構成人類量測驗證',
    }
    manifest['llm']['base_url'] = 'https://generativelanguage.googleapis.com'
    manifest['manifest_sha256'] = digest(manifest)
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / 'instrument.snapshot.json', instrument)
    save(folder / 'answers.snapshot.json', book)
    save(folder / 'prompt.snapshot.json', prompts)
    save(folder / 'manifest.json', manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instrument', type=Path)
    parser.add_argument('--responses', type=Path)
    parser.add_argument('--model', help='Google Gemini model ID; no implicit model default')
    parser.add_argument('--strategy', choices=('fixed', 'random', 'adaptive', 'all'), default='fixed')
    parser.add_argument('--max-questions', type=int, default=4)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--fixed-order', nargs='+', help='Override predeclared instrument-specific fixed order')
    parser.add_argument('--include-reason', action='store_true', default=False)
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--max-output-tokens', type=int, default=8192)
    parser.add_argument('--max-api-attempts', type=int, default=3)
    parser.add_argument('--run-id')
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--retry-ambiguous', action='store_true',
                        help='Resume only: explicitly permit possibly duplicate paid requests')
    args = parser.parse_args()
    try:
        if Path.cwd().resolve() != ROOT:
            raise ValueError('請在 ManagerBench repo 根目錄啟動')
        sdk_version = importlib.metadata.version('google-genai')
        if args.resume:
            import sys
            # Resume uses immutable config, not accidentally overridden CLI defaults.
            if any(token.split('=')[0] not in ('--resume', '--retry-ambiguous')
                   for token in sys.argv[1:] if token.startswith('--')):
                raise ValueError('續跑只允許 --resume 與 --retry-ambiguous，不可換設定／答案')
            folder = args.resume.resolve()
            if folder.parent != (ROOT / 'runs').resolve() or not folder.is_dir():
                raise ValueError('只能續跑本機 runs/<run_id>/')
            if (folder / 'batch.json').exists():
                batch = read_json(folder / 'batch.json')
                child = batch['children']['fixed']
                if child != folder.name + '-fixed':
                    raise ValueError('子 run 路徑不一致')
                manifest, _, _, _ = load_run(folder.parent / child)
            else:
                manifest, _, _, _ = load_run(folder)
            if manifest['llm']['sdk_version'] != sdk_version:
                raise ValueError('SDK 版本與 run 不一致，不能用不同版本續跑')
        else:
            if args.retry_ambiguous:
                raise ValueError('--retry-ambiguous 僅能搭配 --resume')
            if not args.instrument or not args.responses or not args.model:
                raise ValueError('新 run 必須指定 --instrument、--responses、--model')
            if not 0 <= args.temperature <= 2 or args.max_output_tokens < 1:
                raise ValueError('temperature／max-output-tokens 超出範圍')
            instrument = read_json(args.instrument)
            book = read_json(args.responses)
            config = {
                'strategy': args.strategy, 'seed': args.seed, 'query_limit': args.max_questions,
                'include_reason': args.include_reason,
                'fixed_order': args.fixed_order if args.fixed_order is not None else default_fixed_order(instrument),
                'query_order': instrument['query_item_ids'], 'model': args.model,
                'max_api_attempts': args.max_api_attempts,
                'generation_settings': {'temperature': args.temperature,
                                        'max_output_tokens': args.max_output_tokens,
                                        'candidate_count': 1, 'top_p': 1.0, 'top_k': 40,
                                        'seed': args.seed},
            }
            run_id = args.run_id or ('social-' + uuid.uuid4().hex)
            if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
                raise ValueError('run_id 格式錯誤')
            folder = ROOT / 'runs' / run_id
            if args.strategy == 'all':
                from .batch import initialize_batch
                initialize_batch(folder, instrument, book, config, sdk_version=sdk_version)
            else:
                initialize(folder, instrument, book, config, sdk_version=sdk_version)
        print(f'本地 run：{folder}；API 呼叫可能產生費用。', flush=True)
        if (folder / 'batch.json').exists():
            from .batch import execute_batch
            execute_batch(folder, retry_ambiguous=args.retry_ambiguous)
        else:
            from .plotting import plot_scores
            scores = execute(folder, retry_ambiguous=args.retry_ambiguous)
            plot_scores(folder, {read_json(folder / 'manifest.json')['config']['strategy']: scores})
        print(f'完成；結果與 comparison.png／comparison.svg 保存於 {folder}')
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, importlib.metadata.PackageNotFoundError) as error:
        parser.exit(1, f'錯誤：{error}\n')


if __name__ == '__main__':
    main()
