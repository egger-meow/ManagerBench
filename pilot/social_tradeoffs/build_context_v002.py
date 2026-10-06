"""Reproduce the AI-origin twelve-case draft; never migrate participant answers."""
import copy
import json
from pathlib import Path

from pilot.social_tradeoffs.forms import instrument_hash, read_json, validate_instrument


def build():
    root = Path(__file__).parent
    old = read_json(root / 'instruments/f1_context_v001.json')
    result = copy.deepcopy(old)
    result.update(instrument_id='f1_context_v002', version='002')
    originals = {i['item_id']: i for i in old['items']}
    content = originals['F1-context-info-content']['stimulus']['option_a']
    risk = originals['F1-context-info-risk']['stimulus']['option_a']
    notice_content = content[content.index('使用者在選擇查看前'):content.index('新增貼文位於')]
    notice_risk = risk[risk.index('使用者在選擇查看前'):risk.index('新增貼文位於')]
    display = {}
    for mode, key in [('tab_inline', 'info-risk'), ('feed_inline', 'display-inline'), ('feed_click', 'display-click')]:
        text = originals['F1-context-' + key]['stimulus']['option_a']
        display[mode] = text[text.index('新增貼文位於'):text.index('使用者可以不選擇查看')]

    additions = [
        ('F1-context-feed-content-g15', 'F1-context-display-inline', {'risk_disclosure': 'content_notice_only'}),
        ('F1-context-feed-risk-g5', 'F1-context-display-inline', {'engagement_gain_percent': 5}),
        ('F1-context-tab-content-g15', 'F1-context-info-content', {'engagement_gain_percent': 15}),
        ('F1-context-click-spread-g15', 'F1-context-burden-spread', {'engagement_gain_percent': 15, 'exposure_mode': 'feed_click'}),
        ('F1-context-click-repeat-g5', 'F1-context-burden-repeat', {'exposure_mode': 'feed_click'}),
    ]
    derived = []
    for item_id, parent, changes in additions:
        item = copy.deepcopy(originals[parent])
        item['item_id'] = item_id
        p = item['stimulus']['parameters']
        text = item['stimulus']['option_a']
        if 'risk_disclosure' in changes:
            text = text.replace(notice_risk, notice_content)
        if 'exposure_mode' in changes:
            text = text.replace(display[p['exposure_mode']], display[changes['exposure_mode']])
        if 'engagement_gain_percent' in changes:
            gain = changes['engagement_gain_percent']
            total = 100000 * (100 + gain) // 100
            text = text.replace(f"增加 {p['engagement_gain_percent']}%，由 100,000 次變成 {p['option_a_weekly_interactions']:,} 次", f'增加 {gain}%，由 100,000 次變成 {total:,} 次')
            p['option_a_weekly_interactions'] = total
        p.update(changes)
        item['stimulus']['option_a'] = text
        result['items'].append(item)
        derived.append({'item_id': item_id, 'derived_from_item_id': parent, 'changes': changes,
                        'origin': 'AI-origin hypothetical combination; not empirical evidence'})

    result['query_item_ids'] = [
        'F1-context-info-content', 'F1-context-info-risk',
        'F1-context-burden-spread', 'F1-context-burden-repeat',
        'F1-context-display-inline', 'F1-context-display-click',
        'F1-context-info-risk-g15', 'F1-context-feed-content-g15']
    result['test_item_ids'] = [i[0] for i in additions[1:]]
    notes = result['research_notes']
    notes.update(use='Shared twelve-case draft: eight queries and four held-out condition combinations',
                 split_status='AI-origin proposed split pending human review; not validated',
                 previous_instrument='f1_context_v001; its seven items are preserved verbatim',
                 added_items=derived,
                 split_rationale='Test new combinations of familiar disclosure, display, burden and gain conditions; not new scenario families, paraphrase generalization, or unseen individual numeric values. Query cases expose both disclosure levels, direct/click display, dispersed/repeated burden and both gains. Four selected queries need not cover every cue.',
                 confounds_v002=['Disclosure changes transparency and risk salience together.',
                                 'Clicking changes effort and control together; equal numerical consequences are hypothetical controls.',
                                 'Burden contrast changes distinct people and events per person together; equal event totals do not imply equal welfare.',
                                 'A twelve-case exploratory pool cannot identify every interaction or prove nonlinear preferences; simple numeric predictors remain comparators.'])
    result['content_sha256'] = instrument_hash(result)
    validate_instrument(result)
    return result


if __name__ == '__main__':
    target = Path(__file__).parent / 'instruments/f1_context_v002.json'
    with target.open('x', encoding='utf-8') as handle:
        json.dump(build(), handle, ensure_ascii=False, indent=2)
        handle.write('\n')
