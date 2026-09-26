# -*- coding: utf-8 -*-
"""본계정 인스타 게시물을 책별로 모아 홈페이지 데이터(site/data.js)를 만든다.

    py -3 collect.py            # links.txt 의 새 주소만 받아 온다(받은 건 cache/ 에 남는다)
    py -3 collect.py --refresh  # 전부 다시 받는다(캡션을 고친 뒤)

## 입력
- links.txt      게시물 주소 한 줄에 하나. 순서·중복 상관없다.
- overrides.json 자동 분류를 고칠 때만. {"<shortcode>": {"book": "제목", "spoiler": true, "hide": true, "kind": "서평"}}

## 분류 규칙
책   : ① 캡션의 첫 『제목』 ② 첫 줄이 「제목 / 작가 / 출판사」 ③ 해시태그가 알려진 제목과 같다(띄어쓰기 무시)
스포 : 캡션에 스포가 있다고 쓴 경우만 「스포 있음」. 나머지는 전부 「스포 없음」. 애매하면 overrides 로.
제외 : 알라딘 주간 순위처럼 책 한 권 게시물이 아닌 것(EXCLUDE_PREFIX).
"""
import glob, hashlib, html, json, os, re, sys, time, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
SITE = os.path.join(HERE, "site")
COVERS = os.path.join(SITE, "covers")
UA = {"User-Agent": "facebookexternalhit/1.1", "Accept-Language": "ko"}
ALADIN_ENV = r"C:\Users\kkari\.config\eungye\.env"

EXCLUDE_PREFIX = ("알라딘 일본 추리·미스터리 주간 순위",)
SPOIL_YES = ("스포 있", "스포일러 있", "스포 포함", "스포일러 포함", "결말 포함", "결말까지", "다 읽은 분만", "읽은 분만", "스포 주의", "스포일러 주의")
SPOIL_NO = ("스포는 없", "스포 없", "스포일러는 없", "스포일러 없")
KINDS = (  # 먼저 걸리는 것
    ("사건파일", "사건파일"), ("증거판", "증거판"), ("진술", "사건파일"), ("관계도", "관계도"), ("인물 관계", "관계도"),
    ("작법", "작법"), ("표기", "표기"), ("복선", "복선"), ("카드뉴스", "카드뉴스"), ("ELI5", "쉽게 풀기"),
    ("구조", "구조"), ("표지", "표지"), ("명장면", "영상"), ("영상", "영상"),
)
# 원고 전문을 분석한 책(「@ 원고분석」 폴더가 있는 책). 첫 화면 「원고분석한 책」 거르기에 쓴다.
ATLAS = "G:/내 드라이브/03. 인스타그램/@ 원고분석"
DEEP_EXTRA = ("천 년의 후더닛", "미미소기", "인수세공", "입에 대한 앙케트")  # 폴더 이름이 제목과 다른 책


def _deep():
    names = [re.sub(r"^\d+\.\s*", "", d) for d in (os.listdir(ATLAS) if os.path.isdir(ATLAS) else [])]
    return {re.sub(r"[\s·:,.!?'\"「」『』]", "", n) for n in list(names) + list(DEEP_EXTRA)}


DEEP = _deep()
CORE_SINCE = "2026-08-20"  # 원고분석을 시작한 날. 이 뒤 게시물이 책 목록을 정한다


def excluded(cap):
    """책 한 권짜리가 아닌 게시물 — 순위·목록형(『』가 셋 이상이거나 번호 줄이 다섯 이상)."""
    if cap.startswith(EXCLUDE_PREFIX):
        return True
    if len(set(re.findall(r"『([^』]+)』", cap))) >= 3:
        return True
    return len(re.findall(r"(?m)^\s*\d+\s*[.)위]", cap)) >= 5


MONTHS = {m: i for i, m in enumerate("January February March April May June July August September October November December".split(), 1)}


def code_of(url):
    m = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def fetch_post(code):
    req = urllib.request.Request(f"https://www.instagram.com/p/{code}/", headers=UA)
    t = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    desc = re.search(r'<meta property="og:description" content="([^"]*)"', t)
    img = re.search(r'<meta property="og:image" content="([^"]*)"', t)
    otype = re.search(r'<meta property="og:type" content="([^"]*)"', t)
    if not desc:
        raise RuntimeError("캡션 태그 없음(비공개·삭제·차단)")
    d = html.unescape(desc.group(1))
    m = re.match(r'.*? - \S+ - (\w+) (\d+), (\d{4}): "(.*)"\.?\s*$', d, re.S)
    if not m:
        raise RuntimeError("캡션 형식이 바뀜: " + d[:80])
    mon, day, yr, cap = m.groups()
    return {
        "code": code,
        "date": f"{yr}-{MONTHS[mon]:02d}-{int(day):02d}",
        "caption": cap.rstrip('"'),
        "video": bool(otype and "video" in otype.group(1)),
        "image": html.unescape(img.group(1)) if img else None,
    }


def norm(s):
    return re.sub(r"[\s·:,.!?'\"「」『』]", "", s)


def explicit_title(cap):
    m = re.search(r"『([^』]{1,40})』", cap)
    if m:
        return m.group(1).strip()
    first = cap.strip().splitlines()[0] if cap.strip() else ""
    parts = [p.strip() for p in first.split(" / ")]
    if len(parts) >= 3 and 0 < len(parts[0]) <= 30:
        return parts[0]
    return None


def author_of(cap, title):
    first = cap.strip().splitlines()[0]
    parts = [p.strip() for p in first.split(" / ")]
    if len(parts) >= 3 and parts[0] == title:
        return parts[1]
    m = re.search(r"([^\s『」]{2,12}(?: [^\s『」]{1,8})?)\s*『" + re.escape(title) + "』", cap)
    return m.group(1).strip() if m else ""


def kind_of(post, reel=False):
    cap = post["caption"]
    first = cap.strip().splitlines()[0]
    if len(first.split(" / ")) >= 3:
        return "서평"
    head = " ".join(cap.strip().splitlines()[:2]) + " " + " ".join(re.findall(r"#\S+", cap))
    for k, label in KINDS:
        if k in head:
            return label
    return "영상" if post["video"] or reel else "게시물"


def spoiler_of(cap):
    if any(k in cap for k in SPOIL_NO):
        return False
    return any(k in cap for k in SPOIL_YES)


def aladin(title, author):
    if not os.path.exists(ALADIN_ENV):
        return None
    env = dict(l.split("=", 1) for l in open(ALADIN_ENV, encoding="utf-8").read().splitlines() if "=" in l)
    key = env.get("ALADIN_TTB_KEY", "").strip()
    if not key:
        return None
    import urllib.parse
    q = urllib.parse.urlencode(dict(ttbkey=key, Query=f"{title} {author}".strip(), QueryType="Keyword", MaxResults=5,
                                    start=1, SearchTarget="Book", Cover="Big", output="js", Version="20131101"))
    raw = urllib.request.urlopen("http://www.aladin.co.kr/ttb/api/ItemSearch.aspx?" + q, timeout=25).read().decode("utf-8", "replace")
    items = json.loads(raw.rstrip().rstrip(";")).get("item", [])
    items = [i for i in items if norm(title) in norm(i.get("title", ""))] or items
    return items[0] if items else None


def main():
    refresh = "--refresh" in sys.argv
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(COVERS, exist_ok=True)
    links = open(os.path.join(HERE, "links.txt"), encoding="utf-8").read().split()
    codes = list(dict.fromkeys(c for c in map(code_of, links) if c))
    reels = {code_of(u) for u in links if "/reel/" in u}
    ov_path = os.path.join(HERE, "overrides.json")
    overrides = json.load(open(ov_path, encoding="utf-8")) if os.path.exists(ov_path) else {}
    books_path = os.path.join(HERE, "books.json")
    books = json.load(open(books_path, encoding="utf-8")) if os.path.exists(books_path) else {}

    posts, fails = [], []
    for c in codes:
        f = os.path.join(CACHE, c + ".json")
        if os.path.exists(f) and not refresh:
            posts.append(json.load(open(f, encoding="utf-8")))
            continue
        try:
            p = fetch_post(c)
            json.dump(p, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            posts.append(p)
            print("받음", c, p["date"])
            time.sleep(1.2)
        except Exception as e:
            fails.append((c, str(e)))
            print("실패", c, e)

    # 알려진 제목(띄어쓰기 무시) → 대표 표기. 새 책은 원고분석 시기(CORE_SINCE 이후) 게시물에서만 생긴다.
    known = {norm(t): t for t in books}
    for p in posts:
        t = explicit_title(p["caption"])
        if t and p["date"] >= CORE_SINCE and norm(t) not in known and not excluded(p["caption"]):
            known[norm(t)] = t

    def find_book(p, core):
        cap = p["caption"]
        t = explicit_title(cap if core else "\n".join(cap.strip().splitlines()[:3]))
        if not t:
            tags = re.findall(r"#(\S+)", cap)
            t = next((known[norm(x)] for x in tags if norm(x) in known), None)
        if not t and core:  # 본문에 알려진 제목이 그대로 나온다(긴 제목부터) — 옛 게시물엔 안 쓴다(오탐)
            body = norm(cap)
            t = next((known[k] for k in sorted(known, key=len, reverse=True) if len(k) >= 3 and k in body), None)
        return known.get(norm(t), t) if t else None

    out, skipped, core_books = [], [], set()
    for core_pass in (True, False):  # 원고분석 시기로 책을 정하고, 옛 게시물은 그 책일 때만 붙인다
        for p in posts:
            core = p["date"] >= CORE_SINCE
            if core != core_pass:
                continue
            o = overrides.get(p["code"], {})
            if o.get("hide") or (excluded(p["caption"]) and "book" not in o):
                if core:
                    skipped.append(p["code"])
                continue
            t = o.get("book") or find_book(p, core)
            if core:
                if not t:
                    skipped.append(p["code"] + " (책 못 찾음)")
                    continue
                core_books.add(t)
            elif t not in core_books:
                continue
            b = books.setdefault(t, {"author": ""})
            if not b.get("author"):
                b["author"] = author_of(p["caption"], t)
            cap = p["caption"]
            out.append({
                "code": p["code"], "date": p["date"], "book": t, "video": p["video"] or p["code"] in reels,
                "kind": o.get("kind") or kind_of(p, p["code"] in reels),
                "spoiler": o["spoiler"] if "spoiler" in o else spoiler_of(cap),
                "hook": re.sub(r"\s+", " ", cap.strip().splitlines()[0])[:80],
            })

    # 서평 책: classify/out_*.json(게시물마다 서평/책/기타·제목·작가 판정)에서 서평을 올린 책을 더한다.
    # 그 책을 다룬 다른 게시물(소식·카드뉴스 등)도 같이 붙인다. 원고분석 책에도 빠진 게시물이 있으면 붙인다.
    tp = os.path.join(HERE, "titles.json")
    fix = {norm(k): v for k, v in (json.load(open(tp, encoding="utf-8")) if os.path.exists(tp) else {}).items() if not k.startswith("_")}
    cls = {}
    for f in sorted(glob.glob(os.path.join(HERE, "classify", "out_*.json"))):
        for r in json.load(open(f, encoding="utf-8")):
            if r.get("title"):
                r["title"] = fix.get(norm(r["title"]), r["title"])
            if r.get("title") and r.get("type") in ("서평", "책"):
                cls[r["code"]] = r
    canon = {norm(t): t for t in core_books}
    for r in cls.values():
        if r["type"] == "서평":
            canon.setdefault(norm(r["title"]), r["title"])
    have = {p["code"] for p in out}
    by_code = {p["code"]: p for p in posts}
    for code, r in cls.items():
        t = canon.get(norm(r["title"]))
        p = by_code.get(code)
        o = overrides.get(code, {})
        if not t or not p or code in have or o.get("hide"):
            continue
        t = o.get("book") or t
        b = books.setdefault(t, {"author": ""})
        if not b.get("author") and r.get("author"):
            b["author"] = r["author"]
        cap = p["caption"]
        out.append({
            "code": code, "date": p["date"], "book": t, "video": p["video"] or code in reels,
            "kind": o.get("kind") or ("서평" if r["type"] == "서평" else kind_of(p, code in reels)),
            "spoiler": o["spoiler"] if "spoiler" in o else spoiler_of(cap),
            "hook": re.sub(r"\s+", " ", cap.strip().splitlines()[0])[:80],
        })
    shelf_books = {p["book"] for p in out}

    # 표지: 알라딘 API(책 소개 용도). 한 번 받으면 다시 안 받는다.
    for t, b in books.items():
        if t not in shelf_books:
            continue
        if b.get("cover") and os.path.exists(os.path.join(SITE, b["cover"])):
            continue
        try:
            it = aladin(b.get("aladin_q") or t, "" if b.get("aladin_q") else b.get("author", ""))
            if it:
                img = urllib.request.urlopen(urllib.request.Request(it["cover"].replace("cover200", "cover500"), headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
                name = "covers/" + hashlib.md5(norm(t).encode()).hexdigest()[:10] + ".jpg"
                open(os.path.join(SITE, name), "wb").write(img)
                b.update(cover=name, author=b.get("author") or re.sub(r"\s*\([^)]*\)", "", it.get("author", "")).split(",")[0].strip(), publisher=it.get("publisher", ""), aladin=it.get("link", ""))
                print("표지", t)
        except Exception as e:
            print("표지 실패", t, e)

    # 별점: 서평 캡션의 「#이프로별N개」(# 빠진 것·「N+」 포함). 한 책에 값이 갈리면 ratings.json 으로 정한다.
    rp = os.path.join(HERE, "ratings.json")
    rfix = {k: v for k, v in (json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else {}).items() if not k.startswith("_")}
    got = {}
    for p in out:
        cap = by_code[p["code"]]["caption"] if p["code"] in by_code else ""
        for m in re.finditer(r"이프로별\s*(\d(?:\.\d)?)\s*(?:개|\+)", cap):
            got.setdefault(p["book"], set()).add(float(m.group(1)))
    for t in shelf_books:
        if t in rfix:
            r = rfix[t]
        elif len(got.get(t, ())) == 1:
            r = next(iter(got[t]))
        else:
            r = None
            if len(got.get(t, ())) > 1:
                print("  별점이 갈림 → ratings.json 에 적을 것:", t, sorted(got[t]))
        books.setdefault(t, {})["rating"] = r

    for b in books.values():  # 알라딘 표기 「이름 (지은이), 번역자 (옮긴이)」 → 이름
        b["author"] = re.sub(r"\s*\([^)]*\)", "", b.get("author", "")).split(",")[0].strip()
    json.dump(books, open(books_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out.sort(key=lambda x: x["date"], reverse=True)
    used = {p["book"] for p in out}
    # 사이트 전용 스포 게시물(spoilers/<책>.json) — 인스타엔 없고 여기에만 있다
    notes = {}
    sp_dir = os.path.join(HERE, "spoilers")
    for fn in sorted(os.listdir(sp_dir)) if os.path.isdir(sp_dir) else []:
        if fn.endswith(".json"):
            sp = json.load(open(os.path.join(sp_dir, fn), encoding="utf-8"))
            if sp["book"] in used:
                notes[sp["book"]] = sp["posts"]
            else:
                print("  스포 글의 책이 책장에 없음:", sp["book"])
    data = {"updated": time.strftime("%Y-%m-%d"), "posts": out, "notes": notes,
            "books": {t: dict(b, deep=norm(t) in DEEP) for t, b in books.items() if t in used}}
    with open(os.path.join(SITE, "data.js"), "w", encoding="utf-8") as fh:
        fh.write("window.SHELF = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")

    print(f"\n게시물 {len(out)} · 책 {len(used)} · 제외 {len(skipped)} · 실패 {len(fails)}")
    for s in skipped:
        print("  제외", s)
    for c, e in fails:
        print("  실패", c, e)
    for p in out:
        print(f"  {p['date']} {'스포' if p['spoiler'] else '    '} {p['kind']:<5} {p['book']} ← {p['hook'][:30]}")


if __name__ == "__main__":
    main()
