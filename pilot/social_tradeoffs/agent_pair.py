"""Run a paired agent-mimic experiment through fresh Codex CLI contexts.

No Gemini client or API key is used. Codex uses the user's existing ChatGPT
login. Allowed inference payloads are sent to Codex; saved artifacts stay local.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from .agent_backend import AgentBackend, format_agent_prompt
from .batch import execute_batch, initialize_batch
from .forms import digest, model_payload, read_json
from .llm import JournalClient
from .predictor import predict
from .run import ROOT, load_run
from .storage import now, run_lock, save
from .strategies import default_fixed_order


def codex_command(executable, model, workdir, output):
    """Do not inherit memories, project instructions, plugins or file tools."""
    return [str(executable), 'exec', '--ignore-user-config', '--ephemeral',
            '--skip-git-repo-check', '--sandbox', 'read-only', '--json',
            '--disable', 'memories', '--disable', 'plugins', '--disable', 'apps',
            '--disable', 'multi_agent', '--disable', 'shell_tool',
            '--disable', 'skill_search', '--disable', 'browser_use',
            '-c', 'project_doc_max_bytes=0', '-c', 'memories.use_memories=false',
            '-c', 'memories.generate_memories=false', '-c', 'web_search=disabled',
            '--model', model, '-C', str(workdir), '--color', 'never',
            '-o', str(output), '-']


def validate_trace(stdout):
    events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    completed = False
    for event in events:
        if event.get('type') in ('error', 'turn.failed'):
            raise RuntimeError('Codex agent failed; inspect private trace')
        if event.get('type', '').startswith('item.'):
            kind = event.get('item', {}).get('type')
            if kind not in ('reasoning', 'agent_message'):
                raise RuntimeError(f'Unexpected agent tool activity: {kind}')
        completed |= event.get('type') == 'turn.completed'
    if not completed:
        raise RuntimeError('No completed agent turn; inspect private trace')


class CodexAgentBackend(AgentBackend):
    allow_interactive_recovery = False

    def __init__(self, folder, executable, actual_model):
        super().__init__(folder=folder, interactive=False)
        self.executable = executable
        self.actual_model = actual_model

    def generate(self, request):
        # A separate process/session for EVERY selector or predictor request.
        prompt = format_agent_prompt(request)
        task_id = digest(request)
        task = self.folder / 'agent_tasks' / task_id
        task.mkdir(parents=True, exist_ok=True)
        if any(task.rglob('final.json')):
            raise RuntimeError('Existing unjournaled agent output; inspect before retry')
        if (task / 'handoff.json').exists():
            # Transport failures without a final answer may be retried; retain
            # the original receipt and failed trace instead of overwriting them.
            task = task / 'retries' / uuid.uuid4().hex
            task.mkdir(parents=True, exist_ok=False)
        workspace = task / 'empty_workspace'
        workspace.mkdir(exist_ok=True)
        output = task / 'final.json'
        if output.exists():
            raise RuntimeError('Existing unjournaled agent output; inspect before retry')
        (task / 'inbox.md').write_text(prompt, encoding='utf-8')
        self.inbox_path.write_text(prompt, encoding='utf-8')
        command = codex_command(self.executable, self.actual_model, workspace, output)
        save(task / 'handoff.json', {
            'origin': 'agent-mimic', 'runtime': 'codex-cli',
            'configured_agent_model': self.actual_model,
            'resolved_model_version': 'unknown', 'mimic_target': request['model'],
            'fresh_process_per_request': True, 'memory_enabled': False,
            'project_instructions_enabled': False, 'tool_use_allowed': False,
            'request_sha256': task_id, 'started_at_utc': now(),
            'command': command,
            'note': 'Runner generation settings are mimic metadata, not Codex sampling controls.',
        })
        print(f'agent-mimic {self.folder.name} {request["role"]} {task_id[:12]}', flush=True)
        try:
            result = subprocess.run(command, input=prompt, text=True, encoding='utf-8',
                                    capture_output=True, timeout=1800)
        except subprocess.TimeoutExpired as error:
            for name, content in (('trace.jsonl', error.stdout), ('stderr.txt', error.stderr)):
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='replace')
                (task / name).write_text(content or '', encoding='utf-8')
            raise RuntimeError(f'Codex timed out; partial trace retained in {task}') from None
        (task / 'trace.jsonl').write_text(result.stdout, encoding='utf-8')
        (task / 'stderr.txt').write_text(result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(f'Codex exited {result.returncode}; inspect {task}')
        validate_trace(result.stdout)
        text = output.read_text(encoding='utf-8').strip()
        json.loads(text)
        self.outbox_path.write_text(text, encoding='utf-8')
        return {'text': text,
                'raw': {'origin': 'agent-mimic', 'runtime': 'codex-cli',
                        'actual_agent_model': self.actual_model,
                        'resolved_model_version': 'unknown',
                        'model_mimic': request['model'], 'text': text,
                        'trace': str(task / 'trace.jsonl')},
                'usage': {'prompt_token_count': None, 'candidates_token_count': None},
                'model_version': f'agent-mimic:codex:{self.actual_model}'}


def pair_report(folder, pair):
    from matplotlib import font_manager, rc_context
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from .evaluate import score
    fields = ('accept_a', 'accept_b', 'choice')
    titles = ('A 可接受性', 'B 可接受性', '最終選擇')
    font = Path('C:/Windows/Fonts/msjh.ttc')
    font_family = 'DejaVu Sans'
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        font_family = font_manager.FontProperties(fname=str(font)).get_name()
    fig = Figure(figsize=(15, 6.8))
    FigureCanvasAgg(fig)
    axes = fig.subplots(2, 3, sharex=True)
    styles = {'fixed': ('#2563eb', '-', 'o'), 'random': ('#f97316', '--', 's'),
              'adaptive': ('#0d9488', ':', '^')}
    lines = ['# Paired agent-mimic rerun', '',
             f'Agent model: {pair["actual_agent_model"]}; resolved version: unknown.',
             'Reason means the participant reason, not model chain of thought.',
             f'Answer snapshot SHA256: {pair["answer_snapshot_sha256"]}',
             '', '|Reason access|Strategy|k|A correct/all|B correct/all|Choice correct/all|A/B/choice coverage|',
             '|---|---|---:|---:|---:|---:|---|']
    reports = {}
    first_child = folder.parent / (pair['batches']['false'] + '-fixed')
    instrument = read_json(first_child / 'instrument.snapshot.json')
    book = read_json(first_child / 'answers.snapshot.json')
    baseline_predictions = {}
    for item in instrument['items']:
        if item['item_id'] in instrument['test_item_ids']:
            response = item['response']
            acceptable = response['accept_a_and_b_labels_zh_tw']['acceptable']
            baseline_predictions[item['item_id']] = {
                'accept_a': acceptable, 'accept_b': acceptable,
                'choice': response['choice_labels_zh_tw']['A']}
    baseline = score(instrument, book, [(0, baseline_predictions)])
    save(folder / 'baseline.json', {'origin': 'programmatic_baseline',
                                  'policy': 'both acceptable, always choose A', 'scores': baseline})
    for row, (condition, batch_id) in enumerate(pair['batches'].items()):
        comparison = read_json(folder.parent / batch_id / 'comparison.json')
        reports[condition] = comparison['reports']
        for strategy, report in comparison['reports'].items():
            for col, field in enumerate(fields):
                color, style, marker = styles[strategy]
                axes[row, col].plot([s['stage'] for s in report['stages']],
                                   [s['fields'][field]['correct'] for s in report['stages']],
                                   marker=marker, linestyle=style, color=color,
                                   linewidth=2, markersize=6, label=strategy)
            for stage in report['stages']:
                metrics = [stage['fields'][f] for f in fields]
                values = [f'{m["correct"]}/{m["labels_available"]}' for m in metrics]
                coverage = '/'.join(str(m['coverage']) for m in metrics)
                lines.append(f'|{condition}|{strategy}|{stage["stage"]}|'
                             + '|'.join(values) + f'|{coverage}|')
        for col, field in enumerate(fields):
            ax = axes[row, col]
            total = baseline['stages'][0]['fields'][field]['labels_available']
            ax.axhline(baseline['stages'][0]['fields'][field]['correct'],
                       color='#a3a3a3', linestyle='--', linewidth=1.3, zorder=0)
            ax.set_ylim(-.2, max(total, 1) + .25)
            ax.set_yticks(range(total + 1), [f'{n}/{total}' for n in range(total + 1)])
            ax.set_xticks(range(5))
            ax.grid(alpha=.14)
            ax.set_axisbelow(True)
            ax.set_title(titles[col], fontfamily=font_family, fontsize=13)
            ax.tick_params(labelsize=11)
            if col:
                ax.tick_params(labelleft=False)
        label = '沒讀 reasoning' if condition == 'false' else '有讀 reasoning'
        axes[row, 0].set_ylabel(f'{label}\nagent-mimic\n答對題數',
                                fontfamily=font_family, fontsize=11)
        axes[row, 2].legend(loc='lower right', fontsize=11)
    for ax in axes[-1]:
        ax.set_xlabel('已揭露的詢問題數 k', fontfamily=font_family, fontsize=11)
    fig.suptitle(f'{pair["actual_agent_model"]} · agent-mimic', fontsize=15, y=.99)
    fig.text(.5, .012, '灰虛線：程式基線「A、B 皆可接受，永遠選 A」；coverage 與完整分數另存報告。',
             ha='center', fontfamily=font_family, fontsize=10, color='#666666')
    fig.subplots_adjust(left=.09, right=.985, top=.90, bottom=.12, hspace=.28, wspace=.055)
    with rc_context({'font.family': font_family, 'svg.fonttype': 'none'}):
        for extension in ('png', 'svg'):
            figure_path = folder / f'reasoning-comparison.{extension}'
            fig.savefig(figure_path, dpi=180)
            if extension == 'svg':
                figure_path.write_text('\n'.join(line.rstrip() for line in
                                       figure_path.read_text(encoding='utf-8').splitlines()) + '\n',
                                       encoding='utf-8')
    save(folder / 'paired-scores.json', reports)
    lines += ['', 'Gray dashed lines: programmatic baseline, both acceptable / always choose A.',
              'The chart shows correct / labels_available; coverage is reported separately.',
              'Four held-out items from one participant do not establish generalization or a causal reasoning benefit.']
    (folder / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pair-id')
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--agent-model')
    parser.add_argument('--codex-executable', type=Path,
                        help='Use a verified CLI binary, e.g. the desktop-bundled executable')
    parser.add_argument('--allow-codex-inference', action='store_true',
                        help='Explicitly allow sending model-facing experiment payloads to Codex inference')
    parser.add_argument('--preflight', action='store_true', help='Complete only fixed/no-reason k=0, then exit')
    parser.add_argument('--retry-ambiguous', action='store_true')
    args = parser.parse_args()
    if not args.allow_codex_inference:
        parser.error('Codex inference sends allowed payloads, including revealed query answers, '
                     'to an external service; explicit --allow-codex-inference is required')
    helper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.resume:
        folder = args.resume.resolve()
        if folder.parent != ROOT / 'runs':
            parser.error('Resume path must be runs/<pair_id>')
        pair = read_json(folder / 'pair.json')
        if pair.get('pair_sha256') != digest({k: v for k, v in pair.items() if k != 'pair_sha256'}):
            parser.error('Pair metadata hash mismatch')
        if pair['coordinator_sha256'] != helper_hash:
            parser.error('Coordinator code changed; do not silently resume')
        if args.pair_id or args.agent_model or args.codex_executable:
            parser.error('Resume uses frozen pair settings')
        executable = pair['codex_executable']
    else:
        if not args.pair_id or not args.agent_model:
            parser.error('New pairs need --pair-id and --agent-model')
        if not re.fullmatch(r'[A-Za-z0-9._-]+', args.agent_model):
            parser.error('Invalid agent model ID')
        executable = (str(args.codex_executable.resolve()) if args.codex_executable
                      else shutil.which('codex.cmd') or shutil.which('codex'))
        if not executable or not Path(executable).is_file():
            parser.error('Codex CLI executable not found')
        if not args.pair_id.replace('-', '').replace('_', '').isalnum():
            parser.error('Invalid pair ID')
        folder = ROOT / 'runs' / args.pair_id
        if folder.exists():
            parser.error('Pair exists; use --resume')
        instrument = read_json(ROOT / 'pilot/social_tradeoffs/instruments/f1_context_v002.json')
        book = read_json(ROOT / 'participants/p001/f1_context_v002.json')
        config = {'strategy': 'all', 'seed': 42, 'query_limit': 4,
                  'fixed_order': default_fixed_order(instrument),
                  'query_order': instrument['query_item_ids'], 'model': args.agent_model,
                  'backend': 'agent', 'max_api_attempts': 3,
                  'generation_settings': {'temperature': 0.0, 'max_output_tokens': 8192,
                                          'candidate_count': 1, 'top_p': 1.0, 'top_k': 40, 'seed': 42}}
        batches = {condition: folder.name + suffix for condition, suffix in
                   (('false', '-noreason'), ('true', '-reason'))}
        paths = [folder] + [folder.parent / batch_id for batch_id in batches.values()]
        paths += [folder.parent / (batch_id + '-' + strategy)
                  for batch_id in batches.values() for strategy in ('fixed', 'random', 'adaptive')]
        if any(path.exists() for path in paths):
            parser.error('Pair or batch paths already exist; refusing partial initialization')
        # One in-memory answer snapshot initializes BOTH conditions before inference.
        sdk = importlib.metadata.version('google-genai')
        for condition, batch_id in batches.items():
            initialize_batch(folder.parent / batch_id, instrument, book,
                             {**config, 'include_reason': condition == 'true'}, sdk_version=sdk)
        pair = {'origin': 'agent-mimic', 'actual_agent_model': args.agent_model,
                'codex_executable': executable,
                'resolved_model_version': 'unknown', 'batches': batches,
                'answer_snapshot_sha256': digest(book),
                'instrument_sha256': instrument['content_sha256'],
                'coordinator_sha256': helper_hash, 'created_at_utc': now(),
                'codex_version': subprocess.run([executable, '--version'], capture_output=True,
                                                 text=True).stdout.strip()}
        pair['pair_sha256'] = digest(pair)
        save(folder / 'pair.json', pair)
    model = pair['actual_agent_model']
    if args.preflight:
        child = folder.parent / (pair['batches']['false'] + '-fixed')
        with run_lock(child):
            manifest, instrument, _, prompts = load_run(child)
            client = JournalClient(child, manifest['config'], prompts,
                                   CodexAgentBackend(child, executable, model),
                                   retry_ambiguous=args.retry_ambiguous)
            try:
                predict(model_payload(instrument, {}, instrument['test_item_ids'], include_reason=False), 0, client)
            finally:
                client.close()
        print(f'PREFLIGHT PASSED: {folder}', flush=True)
        return
    def run_condition(batch_id):
        batch = folder.parent / batch_id
        return execute_batch(batch,
                             backend_factory=lambda strategy: CodexAgentBackend(
                                 folder.parent / (batch_id + '-' + strategy), executable, model),
                             retry_ambiguous=args.retry_ambiguous)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run_condition, pair['batches'].values()))
    pair_report(folder, pair)
    save(folder / 'completed.json', {'completed_at_utc': now(),
                                     'paired_scores_sha256': digest(read_json(folder / 'paired-scores.json'))})
    print(f'COMPLETED: {folder}', flush=True)


if __name__ == '__main__':
    main()
