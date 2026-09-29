# -*- coding: utf-8 -*-
"""책마다 실제 페이지(/book/<slug>/index.html)와 sitemap.xml·robots.txt 를 만든다.

검색엔진은 주소의 # 뒤를 보지 않아서, #/book/... 로만 있으면 첫 화면 한 장만 잡힌다.
페이지마다 제목·설명·대표 주소를 따로 주고, 본문에 책 소개·서평 한 토막·게시물 목록을
글자로 미리 넣어 둔다(자바스크립트가 뜨면 같은 화면으로 바뀐다).
스포 칸 글은 미리 넣지 않는다 — 검색 결과 미리보기에 결말이 뜨면 안 된다.
"""
import html, json, os, re, shutil

SITE_URL = "https://bookhoster.co.kr"


def slugify(title):
    s = re.sub(r"[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ\s-]", "", title).strip()
    return re.sub(r"[\s-]+", "-", s) or "book"


def excerpt_of(caption, title, limit=360):
    """서평 캡션에서 계정 주인이 쓴 문장만 — 첫 줄 서지(「제목 / 작가 / 출판사」)·해시태그·점 줄을 뺀다."""
    keep = []
    for i, line in enumerate(caption.splitlines()):
        s = re.sub(r"#\S+", "", line).strip()
        if not s or re.fullmatch(r"[.\s·…]+", s):
            continue
        if i < 2 and (" / " in s or "//" in s or (title.replace(" ", "") in s.replace(" ", "") and len(s) < len(title) + 20)):
            continue
        keep.append(s)
    text = re.sub(r"\s+", " ", " ".join(keep)).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    ends = [m.end() for m in re.finditer(r"(다|요|죠|네|까)[.!?…]*\s|[.!?]\s", cut)]
    return (cut[:ends[-1]].strip() if ends and ends[-1] > limit * 0.5 else cut.rstrip() + "…")


def _stars(b):
    if b.get("rating") is None:
        return "가제본이라 별점 없음" if b.get("gajebon") else ""
    return "별점 5+" if b.get("plus") else f"별점 {int(round(b['rating']))}"


def _page(template, title, desc, canonical, body_html, book_title=None):
    e = html.escape
    t = template
    t = re.sub(r"<title>.*?</title>", f"<title>{e(title)}</title>", t, count=1, flags=re.S)
    t = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(desc)}">', t, count=1)
    t = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{e(canonical)}">', t, count=1)
    t = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{e(canonical)}">', t, count=1)
    t = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(title)}">', t, count=1)
    t = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(desc)}">', t, count=1)
    if book_title is not None:
        t = t.replace('<script src="/data.js"></script>',
                      f'<script>window.BOOK = {json.dumps(book_title, ensure_ascii=False)};</script>\n<script src="/data.js"></script>', 1)
    t = t.replace('<div class="wrap" id="app"></div>', f'<div class="wrap" id="app">{body_html}</div>', 1)
    return t


def build(data, site_dir):
    tpl_path = os.path.join(site_dir, "index.html")
    template = open(tpl_path, encoding="utf-8").read()
    assert '<script src="/data.js"></script>' in template, "index.html 이 /data.js 를 절대 경로로 불러야 한다"
    e = html.escape
    books = data["books"]
    posts_by = {}
    for p in data["posts"]:
        posts_by.setdefault(p["book"], []).append(p)

    root = os.path.join(site_dir, "book")
    if os.path.isdir(root):
        shutil.rmtree(root)
    urls = [(SITE_URL + "/", data["updated"]), (SITE_URL + "/about.html", data["updated"]), (SITE_URL + "/privacy.html", data["updated"])]
    for t, b in books.items():
        ps = posts_by.get(t, [])
        slug = b["slug"]
        meta = " · ".join(x for x in (b.get("author"), b.get("publisher"), _stars(b)) if x)
        desc = (b.get("excerpt") or f"{b.get('author', '')} 『{t}』 서평과 인스타그램 게시물 모음")[:150]
        items = "".join(
            f'<li><time>{e(p["date"])}</time> · {e(p["kind"])} — {e(p["hook"])} '
            f'<a href="https://www.instagram.com/{"reel" if p["video"] else "p"}/{e(p["code"])}/">인스타그램에서 보기</a></li>'
            for p in ps)
        body = (f'<article class="static"><a class="back" href="/">책장으로</a><h1>{e(t)}</h1><p class="meta">{e(meta)}</p>'
                + (f'<h2>서평 한 토막</h2><p>{e(b["excerpt"])}</p>' if b.get("excerpt") else "")
                + f'<h2>인스타그램 게시물</h2><ul>{items}</ul></article>')
        title = f"{t} — {b.get('author', '')} 서평·별점 | 책호스터이프로 책장".replace(" —  서평", " — 서평")
        page = _page(template, title, desc, f"{SITE_URL}/book/{slug}/", body, book_title=t)
        d = os.path.join(root, slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
        last = max((p["date"] for p in ps), default=data["updated"])
        urls.append((f"{SITE_URL}/book/{slug}/", last))

    # 비소설 책장: 첫 화면과 같은 틀, window.SECTION 으로 비소설만 보여 준다
    nf = [t for t, b in books.items() if b.get("genre") == "비소설"]
    page = _page(template, "비소설 서평 | 책호스터이프로 책장",
                 "책호스터이프로가 읽은 비소설 — 경영·사회·역사 서평과 별점 모음",
                 f"{SITE_URL}/nonfiction/",
                 "<h1>비소설 서평</h1><ul>" + "".join(
                     f'<li><a href="/book/{e(books[t]["slug"])}/">{e(t)}</a></li>' for t in nf) + "</ul>")
    page = page.replace('<script src="/data.js"></script>',
                        '<script>window.SECTION = "nonfiction";</script>\n<script src="/data.js"></script>', 1)
    d = os.path.join(site_dir, "nonfiction")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
    urls.insert(1, (f"{SITE_URL}/nonfiction/", data["updated"]))

    from urllib.parse import quote
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, lm in urls:
        sm.append(f"  <url><loc>{e(quote(u, safe=':/'))}</loc><lastmod>{lm}</lastmod></url>")
    sm.append("</urlset>")
    open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm) + "\n")
    open(os.path.join(site_dir, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    return len(books)
