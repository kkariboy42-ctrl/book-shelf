"""책 페이지별 조회 수를 읽어 인기 순위를 낸다 — 점검용(읽기만, 숫자를 올리지 않는다).

사이트(index.html bookHit)가 책 페이지를 열 때 b-<제목 FNV-1a 16진수> 키를 하루 한 번 hit 한다.
여기서는 같은 규칙으로 키를 만들어 get 만 부른다. 키가 없으면(404) 아직 아무도 안 연 책.

    py -3 popular.py            # 상위 20권
    py -3 popular.py --all      # 전부(0회 포함)
"""
import json, os, sys, time, unicodedata, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

API = "https://abacus.jasoncameron.dev/get/kkariboy42-bookshelf/"
HERE = os.path.dirname(os.path.abspath(__file__))


def key(title):
    h = 0x811C9DC5
    for b in unicodedata.normalize("NFC", title).encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return f"b-{h:08x}"


def get(k):
    # 카운터가 빠른 연속 요청을 429 로 막는다 — 기다렸다 다시
    for wait in (0, 2, 5, 10):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(API + k, timeout=15) as r:
                return json.load(r).get("value", 0)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 0
            err = e.code
        except Exception as e:
            err = e
    print(f"  읽기 실패 {k}: {err}", file=sys.stderr)
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    s = open(os.path.join(HERE, "site", "data.js"), encoding="utf-8").read()
    books = json.loads(s[s.index("{"):s.rindex("}") + 1])["books"]
    titles = list(books)
    with ThreadPoolExecutor(2) as ex:
        vals = list(ex.map(lambda t: get(key(t)), titles))
    rows = sorted(zip(titles, vals), key=lambda x: -(x[1] or 0))
    failed = sum(v is None for v in vals)
    opened = [r for r in rows if r[1]]
    show = rows if "--all" in sys.argv else opened[:20]
    print(f"책 {len(titles)}권 중 한 번이라도 열린 책 {len(opened)}권" + (f" · 읽기 실패 {failed}권" if failed else ""))
    print("| 순위 | 책 | 조회 | 구분 |\n|---|---|---|---|")
    for i, (t, v) in enumerate(show, 1):
        print(f"| {i} | {t} | {v if v is not None else '실패'} | {books[t].get('genre') or '소설'} |")


if __name__ == "__main__":
    main()
