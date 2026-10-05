"""Google Gemini adapter and crash-aware request journal. No chat sessions."""
import json
import os
import time
from pathlib import Path

from .forms import digest, read_json
from .storage import now, save


class AmbiguousCall(RuntimeError):
    pass


class GoogleBackend:
    def __init__(self):
        key = os.environ.get('GEMINI_API_KEY')
        if not key:
            raise ValueError('請在本機環境設定 GEMINI_API_KEY；不可放進設定 JSON')
        from google import genai
        from google.genai import types
        self.client = genai.Client(
            vertexai=False, api_key=key,
            http_options=types.HttpOptions(
                base_url='https://generativelanguage.googleapis.com',
                api_version='v1beta', timeout=120000,
                retry_options=types.HttpRetryOptions(attempts=1)),
        )

    def generate(self, request):
        from google.genai import types
        response = self.client.models.generate_content(
            model=request['model'],
            contents=json.dumps(request['payload'], ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=request['prompt'],
                response_mime_type='application/json',
                response_json_schema=request['response_schema'],
                **request['generation_settings']),
        )
        return {
            'text': response.text,
            'raw': response.model_dump(mode='json'),
            'usage': response.usage_metadata.model_dump(mode='json') if response.usage_metadata else {},
            'model_version': response.model_version,
        }

    def close(self):
        self.client.close()


class JournalClient:
    def __init__(self, folder, config, prompts, backend=None, *, retry_ambiguous=False):
        self.folder = Path(folder)
        self.config = config
        self.prompts = prompts
        self.backend = backend  # lazy: no API/client during validation or --help
        self.retry_ambiguous = retry_ambiguous

    def call(self, call_id, role, payload, schema, validate):
        request = {
            'provider': 'google', 'model': self.config['model'], 'role': role,
            'prompt': self.prompts[role], 'payload': payload,
            'generation_settings': self.config['generation_settings'],
            'response_schema': schema,
        }
        call_dir = self.folder / 'api' / call_id
        save(call_dir / 'request.json', request)
        valid_path = call_dir / 'validated.json'
        if valid_path.exists():
            value = read_json(valid_path)
            validate(value)
            return value
        attempts = self.config['max_api_attempts']
        for attempt in range(1, attempts + 1):
            attempt_dir = call_dir / f'attempt-{attempt:02d}'
            response_path = attempt_dir / 'response.json'
            pending_path = attempt_dir / 'pending.json'
            error_path = attempt_dir / 'error.json'
            if response_path.exists():
                response = read_json(response_path)
            else:
                if pending_path.exists():
                    error = read_json(error_path) if error_path.exists() else {}
                    if error.get('kind') == 'rejected':
                        raise RuntimeError(f'{call_id}：Google 拒絕請求；查看本地 error.json')
                    safe_retry = error.get('kind') == 'rate_limited'
                    if not safe_retry and not self.retry_ambiguous:
                        raise AmbiguousCall(
                            f'{call_id} attempt {attempt} 送出狀態不明；停止避免重複付費。'
                            '確認後才能使用 --retry-ambiguous（可能重複收費）。')
                    save(attempt_dir / 'retry_authorized.json', {
                        'request_sha256': digest(request),
                        'reason': 'rate_limited' if safe_retry else 'explicit_retry_ambiguous',
                    })
                    continue
                if self.backend is None:
                    self.backend = GoogleBackend()
                save(pending_path, {'started_at_utc': now(), 'request_sha256': digest(request)})
                try:
                    response = self.backend.generate(request)
                except Exception as error:
                    code = getattr(error, 'code', None)
                    code = code if isinstance(code, int) else None
                    kind = ('rate_limited' if code == 429 else
                            'rejected' if code is not None and 400 <= code < 500 and code != 408
                            else 'ambiguous')
                    # Never persist exception text: URLs/headers may contain secrets.
                    save(error_path, {'at_utc': now(), 'kind': kind, 'http_code': code,
                                      'exception_type': type(error).__name__})
                    if kind == 'rate_limited':
                        time.sleep(min(attempt * 2, 10))
                        continue
                    if kind == 'rejected':
                        raise RuntimeError(f'{call_id}：Google 拒絕請求 ({code})') from None
                    raise AmbiguousCall(f'{call_id}：未取得可保存回覆，送出狀態不明；續跑預設不重送') from None
                save(response_path, {'received_at_utc': now(), **response})
            try:
                def unique(pairs):
                    result = {}
                    for key, entry in pairs:
                        if key in result:
                            raise ValueError('API 回覆包含重複 JSON key')
                        result[key] = entry
                    return result
                value = json.loads(response['text'], object_pairs_hook=unique)
                validate(value)
            except (ValueError, TypeError, KeyError) as error:
                save(attempt_dir / 'invalid.json', {
                    'kind': 'invalid_output', 'exception_type': type(error).__name__,
                })
                continue  # known completed call; bounded paid format retry
            save(valid_path, value)
            return value
        raise RuntimeError(f'{call_id}：已達 {attempts} 次 API 嘗試上限；保留全部回覆，未補預測')

    def close(self):
        if self.backend is not None and hasattr(self.backend, 'close'):
            self.backend.close()


def usage_report(folder):
    totals = {}
    completed = 0
    unknown = []
    for pending in sorted((Path(folder) / 'api').glob('*/attempt-*/pending.json')):
        response_path = pending.parent / 'response.json'
        if not response_path.exists():
            error_path = pending.parent / 'error.json'
            error = read_json(error_path) if error_path.exists() else {}
            if error.get('kind') not in ('rate_limited', 'rejected'):
                unknown.append(str(pending.parent.relative_to(folder)))
            continue
        completed += 1
        for key, value in read_json(response_path).get('usage', {}).items():
            if type(value) is int:
                totals[key] = totals.get(key, 0) + value
    return {'completed_responses': completed, 'token_totals': totals,
            'unknown_usage_attempts': unknown, 'cost': None,
            'cost_note': '只記供應商回傳用量；未估算費用，未知請求不得視為零費用'}
