# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai==2.28.0", "matplotlib==3.11.2"]
# ///
"""Simple entry: prepare -> fill participants JSON -> check -> run all strategies."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pilot.social_tradeoffs.forms import blank_book, read_json, validate_book


INSTRUMENT = ROOT / 'pilot/social_tradeoffs/instruments/f1_context_v002.json'
BOOK = ROOT / 'participants/p001/f1_context_v002.json'


def prepare():
    instrument = read_json(INSTRUMENT)
    if BOOK.exists():
        validate_book(instrument, read_json(BOOK))
        print('作答本已存在，保留全部答案。')
    else:
        BOOK.parent.mkdir(parents=True, exist_ok=True)
        with BOOK.open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(blank_book(instrument, 'p001'), handle, ensure_ascii=False, indent=2)
            handle.write('\n')
    print(f'只填這個檔案各題的 answer：\n{BOOK}')
    print('共十二題；不要改 instruments。reason 可略過，未回答保留 null。')


def main():
    if Path.cwd().resolve() != ROOT:
        raise SystemExit('請在 ManagerBench repo 根目錄啟動。')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare', help='產生／找到 p001 十二題作答本，不覆寫')
    sub.add_parser('check', help='檢查作答本、列出缺答，不補答案')
    sub.add_parser('run', add_help=False, help='預設一次跑三策略並出圖；會呼叫 Gemini')
    args, remaining = parser.parse_known_args()
    try:
        if args.command == 'prepare':
            if remaining:
                parser.error('prepare 沒有其他參數')
            prepare()
        elif args.command == 'check':
            if remaining:
                parser.error('check 沒有其他參數')
            missing = validate_book(read_json(INSTRUMENT), read_json(BOOK))
            print(f'驗證通過；缺 {len(missing)} 個欄位（reason 可略過）。')
            for field in missing:
                print(field)
        else:
            from pilot.social_tradeoffs.run import main as run_main
            default_args = [] if any(t.split('=')[0] == '--resume' for t in remaining) else [
                '--instrument', str(INSTRUMENT), '--responses', str(BOOK), '--strategy', 'all']
            sys.argv = ['social_tradeoffs.run', *default_args, *remaining]
            run_main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'錯誤：{error}\n')


if __name__ == '__main__':
    main()
