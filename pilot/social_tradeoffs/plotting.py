"""Plot actual saved scores, with undefined metrics shown as gaps."""
import os
import uuid
from pathlib import Path


def plot_scores(folder, reports):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    folder = Path(folder)
    fig = Figure(figsize=(12, 10), layout='constrained')
    FigureCanvasAgg(fig)
    axes = fig.subplots(3, 3, sharex=True, sharey=True)
    fields = ('accept_a', 'accept_b', 'choice')
    colors = {'fixed': '#2563eb', 'random': '#d97706', 'adaptive': '#059669'}
    for name, report in reports.items():
        stages = [row['stage'] for row in report['stages']]
        for column, field in enumerate(fields):
            for row, metric in enumerate(('accuracy_all_answered', 'accuracy', 'coverage')):
                values = [entry['fields'][field][metric] for entry in report['stages']]
                axes[row, column].plot(stages, [float('nan') if v is None else v for v in values],
                                       marker='o', label=name, color=colors.get(name))
    for column, field in enumerate(fields):
        axes[0, column].set_title(field)
        axes[2, column].set_xlabel('Revealed queries (k)')
        for row in range(3):
            axes[row, column].set_ylim(-0.05, 1.05)
            axes[row, column].grid(alpha=0.2)
            axes[row, column].legend()
    axes[0, 0].set_ylabel('Primary: correct / all answered items')
    axes[1, 0].set_ylabel('Conditional accuracy on predicted items')
    axes[2, 0].set_ylabel('Coverage on answered items')
    fig.suptitle('Same participant / fixed test set; undefined metrics are gaps')
    for extension in ('png', 'svg'):
        path = folder / f'comparison.{extension}'
        if path.exists():
            continue  # resume does not overwrite historical figures
        temp = folder / f'.plot-{uuid.uuid4().hex}.tmp'
        try:
            fig.savefig(temp, format=extension, dpi=160)
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
    fig.clear()
