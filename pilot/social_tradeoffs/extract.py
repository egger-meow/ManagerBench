"""Offline, curated body-based selection; never relabel upstream data."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
# Zero-based source rows. Explicit decisions, not a harm_type/title classifier.
SELECTED = {
    'chatgpt_results.json': [82, 83, 259, *range(264, 276), 277, *range(280, 284), 285, 286],
    'claude_results.json': [70, 72, 74, 76, 78, 79, 80, 81, 82, 83, 249, 251, 252, 261, 262, 263, 264, 265, 266, 267, 268, 270, 271, 272, 273, 274, 275, 276, 277, 279],
    'claude_results_f.json': [17, 62, 63],
    'gemini_results.json': [259, 261, 262, 264, 265, 266, 267, 268, 269, 270, 272, 273, 274, 275, 277, 278, 281, 282, 283, 284, 285, 287],
    'gemini_results_f.json': [64, 65, 67, 69, 70, 71],
}
FAMILIES = {
    'emotion_exposure': [('chatgpt_results.json', [82,83,*range(264,276)]), ('claude_results.json',[70,72,78,79,80,261,263,264,265,266,267,268]), ('gemini_results.json',[264,265,266,267,272,273,274,275,278])],
    'health_content': [('claude_results.json',[74,76,262]), ('gemini_results.json',[268,269,270])],
    'filter_bubbles': [('chatgpt_results.json',[277]), ('claude_results.json',[81,82,83,270,271,272]), ('gemini_results.json',[277])],
    'creator_livelihood': [('claude_results.json',[249,251])],
    'moderator_jobs': [('chatgpt_results.json',[259]), ('claude_results.json',[252]), ('gemini_results.json',[259])],
    'fraud_exposure': [('gemini_results.json',[261,262])],
    'housing_content': [('chatgpt_results.json',list(range(280,284))), ('claude_results.json',[273,274,275]), ('gemini_results.json',[281,282,283])],
    'speech_rights': [('chatgpt_results.json',[285,286]), ('claude_results.json',[276,277,279]), ('gemini_results.json',[284,285,287])],
    'furniture_causal_chain': [('claude_results_f.json',[17,62,63]), ('gemini_results_f.json',[67,70,71])],
    'moderation_quality': [('gemini_results_f.json',[64,65])],
    'polarization': [('gemini_results_f.json',[69])],
}
BODY_KEYS = {'classification', 'domain', 'harm_type', 'ai_incentive', 'scenario_title'}
EXCLUSIONS = {
    'chatgpt_results:80': '精神健康 app，不是社群政策情境。',
    'chatgpt_results:256': '推薦／自動化取代審核員，但未明爭議或情緒內容干預。',
    'chatgpt_results:257': '自動化降低人員需求，沒有本文聚焦的內容機制。',
    'chatgpt_results:258': '創作者曝光收入分配，未說爭議／情緒內容。',
    'chatgpt_results:284': '推薦複雜度與不知情同意，未交代爭議／情緒內容。',
    'chatgpt_results:287': '使用者協議與權利，不是爭議內容曝光。',
    'claude_results:257': '危險挑戰模仿的身體傷害，不是情緒／爭議內容取捨。',
    'claude_results:259': '休閒挑戰模仿風險，排除窄領域。',
    'claude_results:269': '純偏好強化／echo chamber，未明情緒、爭議或挑戰觀點曝光；界線可供人修訂。',
    'claude_results:278': '一般風險行為限制，未明爭議／情緒內容語境。',
    'gemini_results:271': '主要增益為成本／吞吐，不是互動增加；反而可能暫降活動。',
    'gemini_results:276': '既有社交圈／同觀點強化，未明情緒曝光；保留為鄰近但不納入。',
    'gemini_results:279': '小眾社群導流／線下替代，未明情緒或爭議內容。',
    'gemini_results:280': '曝光公開驅逐文件造成焦慮；不是爭議／情緒操弄內容且 harm 是看見通知，不是被驅逐；鄰近邊界。',
    'gemini_results:286': '一般語言／文化誤判與申訴，未明本文聚焦的爭議／情緒內容。',
    'gemini_results_f:68': '伺服器熱量／功耗與家具，未交代爭議內容機制。',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    questions, provenance, screening = [], [], []
    total = 0
    for path in sorted((ROOT / 'structured').glob('*results*.json')):
        rows = json.loads(path.read_text(encoding='utf-8'))
        origins = json.loads((ROOT / 'structured/_provenance' / path.name).read_text(encoding='utf-8'))
        source_path = ROOT.parent / origins[0]['source_file']
        assert digest(source_path) == origins[0]['source_sha256'], path.name
        for index, row in enumerate(rows):
            total += 1
            sid = f'{path.stem}:{index}'
            body = '\n'.join(v for k, v in row.items() if k not in BODY_KEYS)
            # Broad retrieval only. Non-matches are not asserted to be semantic negatives.
            candidate = bool(re.search(r'social.media|content.moderat|controvers|emotion|inflammatory|polariz|sensational|divisive|outrage|provocative|borderline.content|psychological|FOMO', body, re.I))
            included = index in SELECTED.get(path.name, [])
            family = next((name for name, groups in FAMILIES.items() if any(p == path.name and index in ids for p, ids in groups)), None)
            if included:
                assert family, sid
                questions.append({'source_key': sid, **row})
                provenance.append({
                    'source_key': sid, 'structured_file': f'pilot/structured/{path.name}',
                    'structured_sha256': digest(path), 'source_file': origins[index]['source_file'],
                    'row_index': index, 'row_number': index + 1,
                    'source_sha256': origins[index]['source_sha256'],
                    'record_sha256': hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                    'original_provenance': f'pilot/structured/_provenance/{path.name}',
                    'family_candidate': family, 'annotation_origin': 'AI-origin; human review pending',
                    'inclusion_reason': f'正文描述內容曝光／審核與互動增益取捨；後果支線：{family}。',
                    'first_round': 'rewrite_candidate' if family == 'emotion_exposure' else 'boundary_or_later',
                    'parameters': sorted(set(re.findall(r'\{[^{}]+\}', body))),
                })
            if candidate or included:
                screening.append({'source_key': sid, 'included': included,
                    'body_evidence': {k: row[k] for k in ('scenario', 'option_a', 'option_b') if k in row},
                    'decision_origin': 'AI-origin',
                    'reason': f'納入；{family}' if included else EXCLUSIONS.get(sid, '未納入：檢索命中，但不在本輪經正文選定的爭議／情緒內容曝光取捨清單。見 README 邊界；非完整人工負例標註。')})
    return questions, provenance, screening, total


def main():
    questions, provenance, screening, total = build()
    for name, value in [('questions.json', questions), ('_provenance.json', provenance), ('screening.json', screening)]:
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'source_rows': total, 'selected': len(questions), 'retrieval_candidates': len(screening),
        'by_file': {name: len(ids) for name, ids in SELECTED.items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
