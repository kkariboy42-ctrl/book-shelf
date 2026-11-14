"""책장에서 인스타 프로필로 나가는 누름 수를 읽는다 — 점검용(읽기만, 숫자를 올리지 않는다).

사이트(index.html)가 인스타 프로필 링크를 누를 때 자리별로 키를 올린다(같은 브라우저·같은 자리는 하루 한 번).
    btn  = 첫 화면 머리의 「@kkariboy42 팔로우」 단추
    nav  = 상단 Instagram 링크(폰에서는 아이콘)
    foot = 맨 아래 「인스타그램」 링크
키: fc-<자리>(전체) · fc-<자리>-YYYYMMDD(한국 날짜). 방문 수는 d-YYYYMMDD(같은 카운터).

    py -3 follow_clicks.py            # 최근 14일
    py -3 follow_clicks.py --days 30
    py -3 follow_clicks.py --json     # 표를 JSON 으로

재는 것은 「누른 수」다. 실제로 팔로우했는지는 인스타 인사이트(팔로워 증감)로만 알 수 있다.
2026-11-14 저녁 배포부터 센다 — 그 전 날짜는 0 이다.
"""
import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

API = "https://abacus.jasoncameron.dev/get/kkariboy42-bookshelf/"
PLACES = [("btn", "머리 단추"), ("nav", "상단 링크"), ("foot", "맨 아래")]
START = "20261114"


def get(k):
    # 카운터가 빠른 연속 요청을 429 로 막는다 — 기다렸다 다시(popular.py 와 같은 방식)
    err = None
    for wait in (0, 2, 5, 10):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(API + k, timeout=15) as r:
                return json.load(r).get("value", 0)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 0          # 아직 아무도 안 누른 키
            err = e.code
        except Exception as e:
            err = e
    print(f"  읽기 실패 {k}: {err}", file=sys.stderr)
    return None


def main():
    days = 14
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    today = datetime.now(timezone(timedelta(hours=9))).date()
    rows = []
    for i in range(days):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        if d < START:
            break
        r = {"날짜": f"{d[:4]}-{d[4:6]}-{d[6:]}", "방문": get("d-" + d)}
        for p, _ in PLACES:
            r[p] = get(f"fc-{p}-{d}")
            time.sleep(0.25)
        clicks = sum(r[p] or 0 for p, _ in PLACES)
        r["합"] = clicks
        r["방문대비%"] = round(clicks / r["방문"] * 100, 1) if r["방문"] else None
        rows.append(r)
    total = {p: get("fc-" + p) for p, _ in PLACES}
    if "--json" in sys.argv:
        print(json.dumps({"일별": rows, "전체": total}, ensure_ascii=False, indent=1))
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("날짜         방문   머리 단추  상단 링크  맨 아래   합   방문 대비")
    for r in rows:
        v = lambda x: "  ?" if x is None else f"{x:>3}"
        pct = "   –" if r["방문대비%"] is None else f"{r['방문대비%']:>5}%"
        print(f"{r['날짜']}  {v(r['방문']):>5}  {v(r['btn']):>8}  {v(r['nav']):>8}  {v(r['foot']):>7}  {r['합']:>3}  {pct}")
    print("전체(배포 뒤 누적): " + " · ".join(f"{name} {total[p]}" for p, name in PLACES))
    print("※ 같은 브라우저·같은 자리는 하루 한 번만 센다. 누른 수이지 팔로우 수가 아니다.")


if __name__ == "__main__":
    main()
