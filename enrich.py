"""필터용 책 정보 — 알라딘 상품 페이지에서 쪽수·출간일·원제·옮긴이·주제 분류를 읽어 meta.json 으로.

    py -3 enrich.py            # 캐시에 없는 책만 받는다(cache/meta/<ItemId>.json)
    py -3 enrich.py --refresh  # 전부 다시 받는다

나라는 알라딘 분류(일본소설·한국소설·영미소설…)로 정하고, 분류에 나라가 없으면(「외국 과학소설」 등)
원제 글자(가나·한자·한글·로마자)로 짐작한다. 틀리면 books.json 의 그 책에 "country_fixed": "일본" 처럼 적는다.
알라딘 주간 순위(/ranking/)에 든 적이 있으면 최고 순위와 주 수도 적는다.
collect.py 가 meta.json 을 data.js 의 책 정보에 합친다.
"""
import html, json, os, re, sys, time
sys.path.insert(0, r"C:\Claude\shared")
import aladin_web

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "meta")
COUNTRY_WORDS = [  # 분류 경로에 이 낱말이 있으면 그 나라
    ("일본", "일본"), ("한국", "한국"), ("영미", "영미"), ("미국", "영미"), ("영국", "영미"),
    ("중국", "중화권"), ("대만", "중화권"), ("프랑스", "유럽"), ("독일", "유럽"), ("북유럽", "유럽"),
    ("스페인", "유럽"), ("이탈리아", "유럽"), ("러시아", "유럽"), ("동유럽", "유럽"),
]


def parse(h):
    t = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ").strip()
    m = re.search(r'class="conts_info_list1"><ul>(.*?)</ul>', h, re.S)
    pages = None
    if m:
        pm = re.search(r"<li>\s*([\d,]+)\s*쪽\s*</li>", m.group(1))
        pages = int(pm.group(1).replace(",", "")) if pm else None
    pub = re.search(r'itemprop="datePublished" content="([\d-]+)"', h)
    orig = re.search(r"원제\s*:\s*([^<]+)</a>", h)
    trans = [t(x) for x in re.findall(r">([^<>]+)</a>&nbsp;\(옮긴이\)", h)]
    cats = []
    ul = re.search(r'<ul id="ulCategory">(.*?)</ul>', h, re.S)
    if ul:
        for li in re.findall(r"<li[^>]*>(.*?)</li>", ul.group(1), re.S):
            path = re.sub(r"\s*접기.*$", "", t(li))
            path = re.sub(r"\s*>\s*", " > ", path)
            if path and path not in cats:
                cats.append(path)
    return dict(pages=pages, pubdate=pub.group(1) if pub else None,
                orig=html.unescape(orig.group(1)).strip() if orig else None,
                translators=trans, cats=cats)


def country_of(m):
    for path in m.get("cats") or []:
        for w, c in COUNTRY_WORDS:
            if w in path.split(" > ")[-1] or (w + "소설") in path or (w + " 소설") in path:
                return c, "분류"
    o = m.get("orig") or ""
    if re.search(r"[\u3040-\u30ff]", o):
        return "일본", "원제(가나)"
    if re.search(r"[\u4e00-\u9fff]", o):
        return "일본", "원제(한자 — 일본으로 짐작)"
    if re.search(r"[A-Za-z]", o):
        return "영미", "원제(로마자 — 영미로 짐작)"
    if not m.get("translators") and not o:
        return "한국", "옮긴이·원제 없음"
    return None, "모름"


def main():
    refresh = "--refresh" in sys.argv
    os.makedirs(CACHE, exist_ok=True)
    books = json.load(open(os.path.join(HERE, "books.json"), encoding="utf-8"))
    out, guess = {}, []
    for title, b in books.items():
        iid = re.search(r"ItemId=(\d+)", b.get("aladin") or "")
        m = {}
        if iid:
            f = os.path.join(CACHE, iid.group(1) + ".json")
            if os.path.exists(f) and not refresh:
                m = json.load(open(f, encoding="utf-8"))
            else:
                try:
                    m = parse(aladin_web._get(aladin_web.product_link(iid.group(1))))
                    json.dump(m, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                    print("받음", title, m.get("pages"), m.get("pubdate"))
                    time.sleep(1.0)
                except Exception as e:
                    print("실패", title, e)
        c, why = (b["country_fixed"], "직접") if b.get("country_fixed") else country_of(m)
        if why not in ("분류", "직접"):
            guess.append((title, c, why))
        out[title] = {k: v for k, v in dict(
            pages=m.get("pages"), pubdate=m.get("pubdate"), orig=m.get("orig"),
            translators=m.get("translators") or [], country=c).items() if v not in (None, [], "")}

    # 알라딘 주간 순위에 든 적 — 순위 탭과 같은 제목 맞추기
    import ranking_page as RP
    shelf = {RP._norm(t): t for t in books}
    for d in RP.load_weeks():
        for r in d["books"]:
            t = shelf.get(RP._norm(r["title"])) or shelf.get(RP._norm(r.get("short", "")))
            if t:
                o = out.setdefault(t, {})
                o["rank_best"] = min(o.get("rank_best", 99), r["rank"])
                o["rank_weeks"] = o.get("rank_weeks", 0) + 1

    json.dump(out, open(os.path.join(HERE, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = lambda k: sum(1 for v in out.values() if k in v)
    print(f"meta.json: 책 {len(out)} · 쪽수 {n('pages')} · 출간일 {n('pubdate')} · 나라 {n('country')} · 순위 진입 {n('rank_best')}")
    if guess:
        print("나라를 짐작한 책(틀리면 books.json country_fixed):")
        for t, c, why in guess:
            print(f"  {t} → {c or '?'} ({why})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
