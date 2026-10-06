"""One command for fixed/random/adaptive, sharing immutable input snapshots."""
import copy
from pathlib import Path

from .forms import digest, read_json
from .storage import now, run_lock, save


STRATEGIES = ('fixed', 'random', 'adaptive')


def initialize_batch(folder, instrument, book, config, *, sdk_version):
    from .run import initialize, validate_config
    children = {}
    for strategy in STRATEGIES:
        child_config = {**config, 'strategy': strategy}
        validate_config(instrument, book, child_config)
        children[strategy] = folder.name + '-' + strategy
    paths = [folder] + [folder.parent / child for child in children.values()]
    if any(path.exists() for path in paths):
        raise ValueError('批次或子 run 已存在；請用 --resume，不覆寫')
    folder.mkdir(parents=True)
    for strategy, child_id in children.items():
        initialize(folder.parent / child_id, instrument, book,
                   {**copy.deepcopy(config), 'strategy': strategy}, sdk_version=sdk_version)
    manifest = {'schema_version': 1, 'batch_id': folder.name, 'created_at_utc': now(),
                'children': children,
                'instrument_sha256': instrument['content_sha256'],
                'answer_snapshot_sha256': digest(book)}
    manifest['manifest_sha256'] = digest(manifest)
    save(folder / 'batch.json', manifest)


def execute_batch(folder, backend_factory=None, *, retry_ambiguous=False):
    from .run import execute, load_run
    from .plotting import plot_scores
    folder = Path(folder)
    with run_lock(folder):
        batch = read_json(folder / 'batch.json')
        if batch['manifest_sha256'] != digest({k: v for k, v in batch.items() if k != 'manifest_sha256'}):
            raise ValueError('批次設定雜湊不一致')
        if batch['batch_id'] != folder.name or set(batch['children']) != set(STRATEGIES):
            raise ValueError('批次 ID／策略不一致')
        shared = None
        for strategy in STRATEGIES:
            child_id = batch['children'][strategy]
            if child_id != folder.name + '-' + strategy:
                raise ValueError('子 run 路徑不一致')
            manifest, _, _, _ = load_run(folder.parent / child_id)
            config = manifest['config']
            if (config['strategy'] != strategy or
                    manifest['instrument_sha256'] != batch['instrument_sha256'] or
                    manifest['answer_snapshot_sha256'] != batch['answer_snapshot_sha256']):
                raise ValueError('三策略未共用相同題庫／答案')
            comparable = {'config': {k: v for k, v in config.items() if k != 'strategy'},
                          'llm': manifest['llm'], 'code_sha256': manifest['code_sha256']}
            if shared is not None and comparable != shared:
                raise ValueError('三策略的 predictor／prompt／設定不一致')
            shared = comparable
        reports = {}
        for strategy in STRATEGIES:
            child = folder.parent / batch['children'][strategy]
            print(f'執行／續跑：{strategy}', flush=True)
            backend = backend_factory(strategy) if backend_factory else None
            reports[strategy] = execute(child, backend, retry_ambiguous=retry_ambiguous)
        summary = {'schema_version': 1, 'batch_id': folder.name, 'children': batch['children'],
                   'reports': reports, 'usage': {s: read_json(folder.parent / i / 'usage.json')
                                               for s, i in batch['children'].items()}}
        save(folder / 'comparison.json', summary)
        plot_scores(folder, reports)
        if not (folder / 'completed.json').exists():
            save(folder / 'completed.json', {'completed_at_utc': now(),
                                           'comparison_sha256': digest(summary)})
        return summary
