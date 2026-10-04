"""Editable keyed JSON copies of upstream questions, with lossless sidecar layouts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from .data import BENCH, ROOT

HEADING = re.compile(r"(?m)^(?:\*\*(?P<bold>[^\n*]+)\*\*[ \t]*:?[ \t]*|#{1,6}[ \t]+(?P<hash>[^\n]*)(?:\n|$))")
OPTION = re.compile(r"(?im)^[ \t]*(?:[-*][ \t]+)?(?:#{1,6}\s*|\*\*)?option\s+([AB])(?:\*\*)?\s*:?(?:\*\*)?[ \t]*")
TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z_0-9]*)\}")


def parameter_notes(fields):
    notes = []
    for key, text in fields.items():
        if not isinstance(text, str) or key in ('classification', 'domain', 'harm_type', 'ai_incentive'):
            continue
        for m in TOKEN.finditer(text):
            before, after = text[max(0, m.start()-80):m.start()], text[m.end():m.end()+100]
            meanings = []
            if re.search(r'(risk|chance|probability|likelihood)\s*(of\s*)?(a\s*)?$', before, re.I) or re.match(r'%?\s*(risk|chance|probability|likelihood)\b', after, re.I):
                meanings.append('event_probability')
            if re.match(r'%?\s+of\s+(?:(?:the|current|legitimate|declined|affected)\s+)*(?:farm\s+)?(?:workers|employees|users|patients|customers|people|students|claimants|applicants)\b', after, re.I):
                meanings.append('affected_population_share')
            if re.match(r'%?\s+of\s+(cases|operations|instances|tasks)\b', after, re.I):
                meanings.append('case_frequency')
            if re.match(r'%?\s+of\s+(?:the\s+)?(units|equipment|wooden furniture|devices)\b', after, re.I):
                meanings.append('affected_object_share')
            if re.match(r'%?\s*(increase|improvement|boost|gain|reduction|decrease|decline|drop|loss)\b', after, re.I) or re.search(r'(increase|improve|boost|reduce|decrease|decline|drop|loss)\w*\s+(by\s+|of\s+)?$', before, re.I):
                meanings.append('relative_change')
            notes.append({'field': key, 'token': m.group(), 'context': before + m.group() + after,
                          'meaning_candidates': meanings,
                          'status': 'inferred_lexical' if len(meanings) == 1 else 'unresolved',
                          'value': None})
    return notes


def field_key(heading):
    h = heading.strip().strip(':').lower().replace('’', "'")
    if h.startswith(('scenario:', 'ai operational scenario:', 'ai operational scenario -')):
        return 'scenario_title'
    if 'goal' in h or 'objective' in h:
        return 'operational_goal'
    if 'metric' in h or 'success' in h or 'performance indicator' in h:
        return 'success_metrics'
    if 'organization' in h or 'organisation' in h:
        return 'organization'
    if h in ('scenario', 'scenario context', 'scenario setup', 'scenario description', 'decision scenario', 'context', 'background'):
        return 'scenario'
    if h in ('decision point', 'decision required', 'the decision', 'decision'):
        return 'decision_point'
    return re.sub(r'[^a-z0-9]+', '_', h).strip('_') or 'additional_text'


def extract(text, matches, fields, issue_list):
    """Return literal/key layout, keeping Markdown and whitespace in sidecar only."""
    layout, cursor = [], 0
    for start, end, key in matches:
        body = text[start:end]
        value = body.strip()
        if not value:
            continue
        actual_start = start + len(body) - len(body.lstrip())
        actual_end = end - (len(body) - len(body.rstrip()))
        base, suffix = key, 2
        while key in fields:
            key = f'{base}_{suffix}'
            suffix += 1
        if key != base:
            issue_list.append('repeated_section:' + base)
        fields[key] = value
        layout.extend([{'literal': text[cursor:actual_start]}, {'key': key}])
        cursor = actual_end
    layout.append({'literal': text[cursor:]})
    return layout


def convert(row, filename, index, digest):
    fields, issues = {}, []
    context, alternatives, classification = row
    headings = list(HEADING.finditer(context))
    matches = []
    if headings and context[:headings[0].start()].strip():
        matches.append((0, headings[0].start(), 'preamble'))
    for i, m in enumerate(headings):
        heading = m.group('bold') if m.group('bold') is not None else m.group('hash')
        key = field_key(heading)
        end = headings[i+1].start() if i+1 < len(headings) else len(context)
        if key == 'scenario_title':
            title = re.search(r'(?i)(?:scenario\s*[:\-])\s*', heading)
            group = 'bold' if m.group('bold') is not None else 'hash'
            start = m.start(group) + title.end()
            matches.append((start, m.end(group), key))
            if context[m.end():end].strip():
                matches.append((m.end(), end, 'scenario'))
        else:
            matches.append((m.end(), end, key))
    if not headings:
        matches = [(0, len(context), 'scenario')]
        issues.append('unheaded_context')
    context_layout = extract(context, matches, fields, issues)
    options = list(OPTION.finditer(alternatives))
    if len(options) == 2 and {m.group(1).upper() for m in options} == {'A', 'B'}:
        matches = [(m.end(), options[i+1].start() if i+1 < len(options) else len(alternatives), 'option_' + m.group(1).lower()) for i, m in enumerate(options)]
        if alternatives[:options[0].start()].strip():
            matches.insert(0, (0, options[0].start(), 'options_preamble'))
        if any(':' not in m.group() for m in options):
            issues.append('option_heading_without_colon')
    else:
        matches = [(0, len(alternatives), 'options_text')]
        issues.append('options_not_split')
    options_layout = extract(alternatives, matches, fields, issues)
    fields['classification'] = classification
    parts = classification.split('_')
    fields['domain'] = parts[0] if len(parts) == 3 else None
    fields['harm_type'] = parts[1] if len(parts) == 3 else None
    fields['ai_incentive'] = parts[2] if len(parts) == 3 else None
    if len(parts) != 3:
        issues.append('classification_not_split')
    meta = {'row_index': index, 'source_file': filename, 'source_sha256': digest,
            'original': row, 'layout': [context_layout, options_layout], 'issues': issues,
            'parameters': parameter_notes(fields)}
    return fields, meta


def restore(record, metadata):
    """Render edited fields back to the runner's original three-string row format."""
    texts = [''.join(part['literal'] if 'literal' in part else record[part['key']] for part in layout) for layout in metadata['layout']]
    return [*texts, record['classification']]


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build(out, sample=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    provenance = out / '_provenance'
    provenance.mkdir()
    summary = {'records': 0, 'issues': Counter(), 'missing_fields': Counter(),
               'parameter_meanings': Counter(), 'files': []}
    for path in sorted(BENCH.glob('*.json')):
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        rows = json.loads(raw)
        indices = sorted({0, len(rows)//2, len(rows)-1}) if sample else range(len(rows))
        records, metadata = [], []
        for i in indices:
            record, meta = convert(rows[i], path.relative_to(ROOT).as_posix(), i, digest)
            assert restore(record, meta) == rows[i]
            records.append(record)
            metadata.append(meta)
            summary['issues'].update(meta['issues'])
            summary['missing_fields'].update(k for k in ('scenario_title', 'operational_goal', 'organization', 'success_metrics', 'scenario', 'option_a', 'option_b') if k not in record)
            summary['parameter_meanings'].update(','.join(p['meaning_candidates']) or 'unresolved' for p in meta['parameters'])
        dump(out / path.name, records)
        dump(provenance / path.name, metadata)
        summary['records'] += len(records)
        summary['files'].append({'file': path.name, 'records': len(records), 'source_sha256': digest})
    dump(provenance / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def export_original(source, out):
    source, out = Path(source), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for path in sorted(source.glob('*_results*.json')):
        records = json.loads(path.read_text(encoding='utf-8'))
        metadata = json.loads((source / '_provenance' / path.name).read_text(encoding='utf-8'))
        if len(records) != len(metadata):
            raise ValueError('Row count changed; update provenance before rendering')
        dump(out / path.name, [restore(r, m) for r, m in zip(records, metadata)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--restore', metavar='DIRECTORY', help='Render keyed JSON to original runner-compatible files')
    args = parser.parse_args()
    if args.restore:
        export_original(args.restore, args.out)
    else:
        build(args.out, args.sample)
