# -*- coding: utf-8 -*-
"""월간 책호스터 탭(/zine/ · /zine/<호>/).

재료는 저장소 안 `zine/<호>/` 폴더 하나 — 다음 호는 폴더만 더하면 된다.
    zine/<호>/issue.json   {"no":0, "title":"창간 준비호", "issue":"2026-11", "issue_label":"2026년 11월",
                            "date":"2026-11-25", "pdf":"월간책호스터_0호.pdf", "lede":"한 줄 소개", "next":"다음 호 안내 한 줄"}
    zine/<호>/<pdf>        쪽마다 4:5 로 짠 PDF
PDF 를 쪽마다 WebP(폭 1080)로 구워 site/zine/<호>/p01.webp … 로 두고, PDF 는 받기용으로 복사한다.
이미 구운 쪽은 PDF 가 바뀌지 않으면 다시 굽지 않는다(pypdfium2 는 굽을 때만 필요).
`퍼즐_정답.md` 같은 정답 파일은 이 폴더에 두지 않는다 — 읽지도 싣지도 않는다.
"""
import glob, hashlib, html, json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://bookhoster.co.kr"
e = html.escape
WIDTH = 1080
LAZY = ' loading="lazy"'

ICO_DL = ('<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
          'stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 11l5 5 5-5M5 20h14"/></svg>')
ICO_GO = ('<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
          'stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')

CSS = """
<style>
.zwrap{max-width:640px;margin:0 auto}
.zbar{display:flex;flex-wrap:wrap;align-items:center;gap:12px 20px;margin:0 0 28px}
.zbtn{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;border-radius:999px;background:var(--ink);color:var(--bg);font:800 15px var(--sans);text-decoration:none;min-height:44px}
.zbtn:hover{filter:brightness(1.15)}
.zbtn .ico,.zlink .ico{width:18px;height:18px;flex:none}
.znext{margin:0;color:var(--ink-2);font-size:15px}
.zpages{list-style:none;margin:0;padding:0;display:grid;gap:14px}
.zpages img{display:block;width:100%;height:auto;aspect-ratio:4/5;border-radius:6px;background:var(--surface-2);box-shadow:var(--shadow)}
.zfoot{margin:32px 0 0;display:flex;flex-wrap:wrap;gap:12px 20px;align-items:center}
.zlist{list-style:none;margin:0;padding:0;display:grid;gap:20px}
.zcard{display:grid;grid-template-columns:132px 1fr;gap:22px;align-items:center;text-decoration:none;padding:18px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.zcard:hover{border-color:var(--ink)}
.zcard img{display:block;width:100%;height:auto;aspect-ratio:4/5;border-radius:4px;box-shadow:var(--shadow)}
.zcard h2{font:500 clamp(24px,4.4vw,34px)/1.15 var(--serif);letter-spacing:-.03em;margin:0 0 6px}
.zcard p{margin:0 0 4px;color:var(--muted);font-size:14px}
.zcard .zlink{display:inline-flex;align-items:center;gap:6px;margin-top:8px;font-weight:700;font-size:14px;color:var(--ink)}
.zhint{margin:28px 0 0;color:var(--muted);font-size:14px}
@media (max-width:420px){.zcard{grid-template-columns:96px 1fr;gap:16px;padding:14px}}
</style>
"""


def _issues():
    out = []
    for d in glob.glob(os.path.join(HERE, "zine", "*", "issue.json")):
        try:
            m = json.load(open(d, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        m["_dir"] = os.path.dirname(d)
        m["no"] = int(m["no"])
        out.append(m)
    out.sort(key=lambda m: m["no"], reverse=True)
    return out


def _bake(m, out_dir):
    """PDF → p01.webp … + cover.webp(목록용) + og.jpg(공유용). 바뀐 게 없으면 건너뛴다. 쪽 수를 돌려준다."""
    src = os.path.join(m["_dir"], m["pdf"])
    os.makedirs(out_dir, exist_ok=True)
    stamp = os.path.join(out_dir, ".baked")
    sig = f'{hashlib.sha1(open(src, "rb").read()).hexdigest()}:{WIDTH}'
    have = sorted(glob.glob(os.path.join(out_dir, "p[0-9][0-9].webp")))
    if have and os.path.exists(stamp) and open(stamp).read() == sig and os.path.exists(os.path.join(out_dir, "og.jpg")):
        return len(have)
    import pypdfium2 as pdfium
    for f in have + glob.glob(os.path.join(out_dir, "cover.webp")):
        os.remove(f)
    pdf = pdfium.PdfDocument(src)
    n = len(pdf)
    for i in range(n):
        pg = pdf[i]
        w, _h = pg.get_size()
        im = pg.render(scale=WIDTH / w).to_pil().convert("RGB")
        if im.width != WIDTH:
            im = im.resize((WIDTH, round(im.height * WIDTH / im.width)))
        im.save(os.path.join(out_dir, f"p{i + 1:02d}.webp"), "WEBP", quality=80, method=6)
        if i == 0:
            im.resize((360, round(im.height * 360 / im.width))).save(os.path.join(out_dir, "cover.webp"), "WEBP", quality=80, method=6)
            im.resize((720, round(im.height * 720 / im.width))).save(os.path.join(out_dir, "og.jpg"), "JPEG", quality=84, optimize=True)
    open(stamp, "w").write(sig)
    return n


def _set_hero(page, title_html, sub):
    page = re.sub(r'<h1 id="h-title">.*?</h1>', f'<h1 id="h-title">{title_html}</h1>', page, count=1, flags=re.S)
    page = re.sub(r'<p class="sub" id="h-sub">.*?</p>', f'<p class="sub" id="h-sub">{e(sub)}</p>', page, count=1, flags=re.S)
    page = re.sub(r'\n\s*<div class="searchbox">.*?</div>', "", page, count=1, flags=re.S)
    page = page.replace('<div class="stats" id="stats"></div>', "", 1)
    return page


def _finish(page, canonical, og_image=None):
    page = page.replace('<script src="/data.js"></script>',
                        '<script>window.SECTION = "zine";</script>\n<script src="/data.js"></script>', 1)
    if og_image:
        page = re.sub(r'<meta property="og:image" content="[^"]*">', f'<meta property="og:image" content="{e(og_image)}">', page, count=1)
        if 'property="og:image"' not in page:
            page = page.replace('<meta property="og:locale"', f'<meta property="og:image" content="{e(og_image)}">\n<meta property="og:locale"', 1)
    return page


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def build(template, site_dir, books, page_fn):
    """page_fn = static_pages._page. 만든 주소 [(url, lastmod)] 를 돌려준다."""
    issues = _issues()
    if not issues:
        print("  월간지: zine/<호>/issue.json 이 없다")
        return []
    tpl = template.replace("</head>", CSS + "</head>", 1)
    root = os.path.join(site_dir, "zine")
    urls = []
    cards = []
    for m in issues:
        no = m["no"]
        out_dir = os.path.join(root, str(no))
        n = _bake(m, out_dir)
        pdf_name = f"zine-{no}.pdf"
        shutil.copyfile(os.path.join(m["_dir"], m["pdf"]), os.path.join(out_dir, pdf_name))
        label = f'월간 책호스터 {no}호'
        full = f'{label} {m["title"]}' if m.get("title") else label
        base = f"/zine/{no}/"
        dl_name = m["pdf"]
        imgs = "".join(
            f'<li><img src="{base}p{i:02d}.webp" width="{WIDTH}" height="1350" alt="{e(label)} {i}쪽"'
            f'{LAZY if i > 1 else ""} decoding="async"></li>' for i in range(1, n + 1))
        body = (f'<div class="zwrap"><a class="back" href="/zine/">월간지 목록</a>'
                f'<div class="zbar"><a class="zbtn" href="{base}{pdf_name}" download="{e(dl_name)}">{ICO_DL}PDF 받기</a>'
                + (f'<p class="znext">{e(m["next"])}</p>' if m.get("next") else "") + '</div>'
                f'<ol class="zpages" aria-label="{e(full)} 쪽 모음">{imgs}</ol>'
                f'<div class="zfoot"><a class="zbtn" href="{base}{pdf_name}" download="{e(dl_name)}">{ICO_DL}PDF 받기</a>'
                + (f'<p class="znext">{e(m["next"])}</p>' if m.get("next") else "") + '</div></div>')
        desc = (m.get("lede") or f"{full} — 책호스터이프로가 한 달에 한 번 엮는 월간지입니다.")[:150]
        url = f"{SITE_URL}{base}"
        page = page_fn(tpl, f"{full} | 월간 책호스터", desc, url, body)
        page = _set_hero(page, f'<span class="nw">월간 책호스터</span> <span class="nw">{e(str(no))}호</span>',
                         f'{m.get("issue_label", "")} · {m.get("title", "")}'.strip(" ·"))
        page = _finish(page, url, f"{SITE_URL}{base}og.jpg")
        _write(os.path.join(out_dir, "index.html"), page)
        urls.append((url, m.get("date") or f'{m.get("issue", "2026-01")}-01'))
        cards.append(f'<li><a class="zcard" href="{base}"><img src="{base}cover.webp" width="360" height="450" alt="{e(label)} 표지" loading="lazy">'
                     f'<div><h2>{e(label)}</h2><p>{e(m.get("title", ""))} · {e(m.get("issue_label", ""))}</p>'
                     + (f'<p>{e(m["lede"])}</p>' if m.get("lede") else "")
                     + f'<span class="zlink">읽기{ICO_GO}</span></div></a></li>')
    latest = issues[0]
    body = ('<div class="zwrap"><ol class="zlist">' + "".join(cards) + '</ol>'
            + (f'<p class="zhint">{e(latest["next"])}</p>' if latest.get("next") else "") + '</div>')
    url = f"{SITE_URL}/zine/"
    page = page_fn(tpl, "월간 책호스터 | 책호스터이프로 책장",
                   "책호스터이프로가 한 달에 한 번 엮는 월간지 — 그달 읽은 책, 알라딘 순위 정리, 추천, 직접 지은 추리 퍼즐.",
                   url, body)
    page = _set_hero(page, '<span class="nw">월간</span> <span class="nw">책호스터</span>',
                     "그달 읽은 책과 알라딘 순위, 계절에 맞춘 추천, 직접 지은 추리 퍼즐을 한 권으로 엮습니다.")
    page = _finish(page, url, f'{SITE_URL}/zine/{latest["no"]}/og.jpg')
    _write(os.path.join(root, "index.html"), page)
    urls.insert(0, (url, max(u[1] for u in urls)))
    return urls
