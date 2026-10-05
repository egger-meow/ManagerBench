"""Offline instrument/form utilities; no strategy, model or replay runner."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path


FIELDS = ('accept_a', 'accept_b', 'choice', 'reason')


def digest(value):
    """SHA-256 of UTF-8 canonical JSON, independent of file whitespace."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def instrument_hash(instrument):
    return digest({k: v for k, v in instrument.items() if k != 'content_sha256'})


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'重複 JSON key：{key}')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def validate_instrument(instrument):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', instrument['instrument_id']):
        raise ValueError('instrument_id 格式錯誤')
    if not isinstance(instrument['version'], str) or not instrument['version']:
        raise ValueError('缺少題庫版本')
    if instrument['content_sha256'] != instrument_hash(instrument):
        raise ValueError('題庫內容雜湊不一致；改版請另建 instrument')
    ids = [item['item_id'] for item in instrument['items']]
    query, test = instrument['query_item_ids'], instrument['test_item_ids']
    if (len(set(ids)) != len(ids) or len(set(query)) != len(query)
            or len(set(test)) != len(test) or set(query) & set(test)
            or set(query) | set(test) != set(ids)):
        raise ValueError('題目 ID／query、test 清單重複、交疊或遺漏')
    for item in instrument['items']:
        if not isinstance(item['item_id'], str) or not item['item_id']:
            raise ValueError('缺少 item_id')
        response = item['response']
        if response.get('answers') is not None:
            raise ValueError('公開題庫不可含答案')
        if any(v is not None for v in response['answer_format']['fields'].values()):
            raise ValueError('公開題庫回答欄位必須全為 null')
        for field in FIELDS:
            if field not in response['answer_format']['fields']:
                raise ValueError('回答格式缺欄位')
        for key in ('decision_role', 'benefit_recipient', 'consequence_bearer',
                    'scenario', 'option_a', 'option_b'):
            if not isinstance(item['stimulus'][key], str) or not item['stimulus'][key]:
                raise ValueError('題面不完整')
    return instrument


def presentation(item):
    """Allowlist only: no parameters, provenance, research notes or split hints."""
    response = item['response']
    return {
        'stimulus': {k: item['stimulus'][k] for k in (
            'decision_role', 'benefit_recipient', 'consequence_bearer',
            'scenario', 'option_a', 'option_b')},
        'response': {k: copy.deepcopy(response[k]) for k in (
            'acceptability_question', 'choice_question', 'optional_followup',
            'accept_a_and_b_values', 'choice_values')},
    }


def blank_book(instrument, participant_id):
    validate_instrument(instrument)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', participant_id):
        raise ValueError('participant_id 格式錯誤')
    return {
        'schema_version': 1,
        'participant_id': participant_id,
        'instrument_id': instrument['instrument_id'],
        'instrument_version': instrument['version'],
        'instrument_sha256': instrument['content_sha256'],
        'instruction': '只編輯各題 answer；前三欄填題目列出的中文選項，未回答保留 null。reason 可填文字或 null。',
        'items': [{'item_id': item['item_id'], **presentation(item),
                   'answer': dict.fromkeys(FIELDS)} for item in instrument['items']],
    }


def validate_book(instrument, book):
    expected = blank_book(instrument, book['participant_id'])
    stripped = copy.deepcopy(book)
    missing = []
    for item in stripped['items']:
        answer = item['answer']
        if set(answer) != set(FIELDS):
            raise ValueError(f"{item['item_id']}：answer 欄位不一致")
        for field in FIELDS:
            value = answer[field]
            if field == 'reason':
                if value is not None and not isinstance(value, str):
                    raise ValueError('reason 必須為文字或 null')
            else:
                options = item['response']['accept_a_and_b_values' if field.startswith('accept_') else 'choice_values']
                if value is not None and value not in options:
                    raise ValueError(f"{item['item_id']}.{field}：無效選項 {value!r}")
                if value is None:
                    missing.append(f"{item['item_id']}.{field}")
        item['answer'] = dict.fromkeys(FIELDS)
    if stripped != expected:
        raise ValueError('作答本 ID、版本、雜湊、題面、順序或非 answer 欄位與題庫不一致')
    return missing


def model_payload(instrument, disclosed_answers, target_item_ids, *, include_reason=False):
    """Future runner passes ONLY revealed query answers, never a complete book.

    This projection is not an OS sandbox; model workers must not access local
    participants/runs, instruments or the evaluator process filesystem.
    """
    validate_instrument(instrument)
    if type(include_reason) is not bool:
        raise ValueError('include_reason 必須為布林值')
    if not set(disclosed_answers) <= set(instrument['query_item_ids']):
        raise ValueError('只允許揭露 query 答案；test 答案禁止')
    items = {item['item_id']: item for item in instrument['items']}
    if len(set(target_item_ids)) != len(target_item_ids) or not set(target_item_ids) <= set(items):
        raise ValueError('未知或重複預測題目 ID')
    history = []
    for item_id, answer in disclosed_answers.items():
        # Validate revealed answers using the same form contract.
        book = blank_book(instrument, 'validation')
        next(i for i in book['items'] if i['item_id'] == item_id)['answer'] = answer
        validate_book(instrument, book)
        fields = FIELDS if include_reason else FIELDS[:3]
        history.append({'item_id': item_id, **presentation(items[item_id]),
                        'answer': {k: answer[k] for k in fields}})
    return {'revealed_queries': history,
            'targets': [{'item_id': i, **presentation(items[i])} for i in target_item_ids]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('generate', 'validate'):
        command = sub.add_parser(name)
        command.add_argument('--instrument', type=Path, required=True)
        if name == 'generate':
            command.add_argument('--participant', default='p001')
        else:
            command.add_argument('--book', type=Path, required=True)
    args = parser.parse_args()
    try:
        instrument = validate_instrument(read_json(args.instrument))
        if args.instrument.stem != instrument['instrument_id']:
            raise ValueError('題庫檔名必須與 instrument_id 相同')
        if args.command == 'generate':
            book = blank_book(instrument, args.participant)
            path = Path('participants') / args.participant / f"{instrument['instrument_id']}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8', newline='\n') as handle:
                json.dump(book, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
            print(f'已建立空白作答本：{path.resolve()}')
        else:
            book = read_json(args.book)
            if args.book.stem != instrument['instrument_id'] or args.book.parent.name != book['participant_id']:
                raise ValueError('作答本路徑與 participant／instrument ID 不一致')
            missing = validate_book(instrument, book)
            print(f'格式與題面驗證通過；尚缺 {len(missing)} 個必要回答欄位（允許部分作答）。')
            for field in missing:
                print(f'  {field}')
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'錯誤：{error}\n')


if __name__ == '__main__':
    main()
