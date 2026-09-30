# -*- coding: utf-8 -*-
"""알라딘 일본 추리·미스터리 주간 순위 탭(/ranking/).

재료는 aladin-weekly 스킬이 매주 남기는 `알라딘\\<연>\\<YYYY-MM N주>\\data.json` 과 `알라딘\\_표지\\<ItemId>.jpg`.
드라이브의 주를 전부 읽어 /ranking/ (가장 최근 주) 과 /ranking/<연-월-주>/ (지난 주) 를 만든다.
표지는 사이트 안(/ranking/covers/)으로 줄여 복사한다 — 배포 저장소에 드라이브 원본을 싣지 않으려고.
세일즈포인트 같은 기계 숫자는 싣지 않는다(순위·변화만).
"""
import glob, html, json, os, re

ALADIN = r"G:\내 드라이브\03. 인스타그램\알라딘"
SITE_URL = "https://bookhoster.co.kr"
e = html.escape


def _norm(s):
    return re.sub(r"[\s\W_]", "", str(s)).lower()


def load_weeks(root=ALADIN):
    weeks = []
    for p in glob.glob(os.path.join(root, "*", "*", "data.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if len(d.get("books") or []) < 10:
            continue
        y, m, w = d["week"]
        d["key"] = f"{y}-{m:02d}-{w}"
        d["label"] = f"{y}년 {m}월 {w}주"
        weeks.append(d)
    weeks.sort(key=lambda d: d["key"], reverse=True)
    return weeks


def _copy_cover(item, out_dir):
    dst = os.path.join(out_dir, f"{item}.jpg")
    if os.path.exists(dst):
        return True
    src = os.path.join(ALADIN, "_표지", f"{item}.jpg")
    if not os.path.exists(src):
        return False
    try:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((320, 480))
        im.save(dst, "JPEG", quality=84, optimize=True)
    except Exception:
        import shutil
        shutil.copyfile(src, dst)
    return True


def _chg(b):
    k = b.get("kind")
    if k == "up":
        return f'<span class="chg up" aria-label="{b["delta"]}계단 상승">▲ {b["delta"]}</span>'
    if k == "down":
        return f'<span class="chg down" aria-label="{-b["delta"]}계단 하락">▼ {-b["delta"]}</span>'
    if k == "new":
        return '<span class="chg new">NEW</span>'
    if k in ("re", "reentry", "back"):
        return '<span class="chg re">재진입</span>'
    return '<span class="chg same" aria-label="순위 같음">—</span>'


def _prev_text(b):
    if b.get("kind") == "new":
        return "첫 진입"
    if b.get("prev"):
        return f"지난주 {b['prev']}위"
    return "지난주 순위 밖"


def _spark(trail, w=112, h=34, floor=30):
    """8주 순위 선. 위가 1위. 30위 밖은 바닥에 붙이고, 목록에 없던 주는 끊는다."""
    n = len(trail)
    if not n:
        return ""
    xs = [4 + i * (w - 8) / max(n - 1, 1) for i in range(n)]
    y = lambda r: 4 + (min(r, floor) - 1) * (h - 8) / (floor - 1)
    segs, cur = [], []
    for x, r in zip(xs, trail):
        if r is None:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append((x, y(r)))
    if cur:
        segs.append(cur)
    lines = "".join(
        f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in s)}"/>' for s in segs if len(s) > 1)
    last = trail[-1]
    dot = f'<circle cx="{xs[-1]:.1f}" cy="{y(last):.1f}" r="3"/>' if last else ""
    guide = f'<line x1="2" x2="{w - 2}" y1="{y(20):.1f}" y2="{y(20):.1f}"/>'
    known = [r for r in trail if r]
    best = min(known) if known else None
    label = f"지난 8주 최고 {best}위" if best else ""
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}">'
            f'<g class="g20">{guide}</g><g class="ln">{lines}</g><g class="pt">{dot}</g></svg>')


def _link(b, shelf):
    t = shelf.get(_norm(b["title"])) or shelf.get(_norm(b.get("short", "")))
    if t:
        return f'/book/{e(t["slug"])}/', True
    return f'https://www.aladin.co.kr/shop/wproduct.aspx?ItemId={e(str(b["item"]))}', False


def _buy(b, cls="buy"):
    """알라딘 구매 링크 — 서평이 있는 책도 제목은 책장으로, 이건 알라딘으로. TTB 는 리퍼러로 세므로 noreferrer 금지."""
    url = f'https://www.aladin.co.kr/shop/wproduct.aspx?ItemId={e(str(b["item"]))}'
    return (f'<a class="{cls}" href="{url}" target="_blank" rel="noopener" aria-label="『{e(b["short"])}』 알라딘에서 구매">'
            '알라딘에서 구매 <svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg></a>')


def _week_html(d, weeks, shelf, cover_ok):
    books = d["books"]
    top = books[0]
    cov = lambda b, cls="": (f'<img class="{cls}" src="/ranking/covers/{e(str(b["item"]))}.jpg" alt="『{e(b["short"])}』 표지" loading="lazy">'
                             if cover_ok.get(str(b["item"])) else f'<span class="ph {cls}">{e(b["short"])}</span>')

    # 1위 한 줄
    if top.get("streak", 0) >= 2:
        crown = f"{top['streak']}주 연속 1위"
    elif top.get("kind") == "new":
        crown = "첫 진입 1위"
    elif top.get("prev"):
        crown = f"지난주 {top['prev']}위 → 1위"
    else:
        crown = "이번 주 1위"

    # 이번 주 눈에 띄는 것
    news = [b for b in books if b.get("kind") == "new"]
    ups = sorted([b for b in books if b.get("kind") == "up"], key=lambda b: -b["delta"])
    notes = []
    if news:
        notes.append(("새로 들어온 책", ", ".join(f"『{e(b['short'])}』 {b['rank']}위" for b in news)))
    if ups and ups[0]["delta"] >= 3:
        u = ups[0]
        notes.append(("가장 크게 오른 책", f"『{e(u['short'])}』 {u['prev']}위 → {u['rank']}위"))
    ups_top = [b for b in ups if b["rank"] <= 5 and b is not (ups[0] if ups else None)]
    if ups_top:
        b = ups_top[0]
        notes.append(("TOP 5 로 올라온 책", f"『{e(b['short'])}』 {b['prev']}위 → {b['rank']}위"))
    note_html = "".join(f'<div class="rn"><dt>{k}</dt><dd>{v}</dd></div>' for k, v in notes)

    href, mine = _link(top, shelf)
    hero = (f'<section class="rtop"><a class="rtop-cover" href="{href}">{cov(top)}</a>'
            f'<div class="rtop-body"><p class="rk-eyebrow">이번 주 1위</p>'
            f'<h2><a href="{href}">{e(top["short"])}</a></h2><p class="au">{e(top["who"])}</p>'
            f'<p class="crown">{e(crown)}</p>'
            f'<p class="rbuy">{_buy(top, "buy big")}</p>'
            + (f'<dl class="rnotes">{note_html}</dl>' if note_html else "")
            + '</div></section>')

    rows = []
    for b in books:
        href, mine = _link(b, shelf)
        ext = '' if mine else ' target="_blank" rel="noopener"'
        rows.append(
            f'<li class="rrow{" me" if mine else ""}"><span class="no">{b["rank"]}</span>'
            f'<a class="rc" href="{href}"{ext} tabindex="-1" aria-hidden="true">{cov(b)}</a>'
            f'<div class="rt"><a href="{href}"{ext}>{e(b["short"])}</a>'
            f'<span class="au">{e(b["who"])}</span>'
            + ('<span class="deep">서평 있음</span>' if mine else '')
            + _buy(b)
            + f'</div>{_spark(b.get("trail") or [])}'
            f'<div class="rchg">{_chg(b)}<span class="prev">{_prev_text(b)}</span></div></li>')

    cur = ' aria-current="page"'
    wk = "".join(
        f'<a href="{"/ranking/" if i == 0 else "/ranking/" + w_["key"] + "/"}"'
        f'{cur if w_["key"] == d["key"] else ""}>{e(w_["label"].split("년 ")[1])}</a>'
        for i, w_ in enumerate(weeks))
    first, last = d["weeks"][0], d["weeks"][-1]
    return (f'<nav class="rweeks" aria-label="주 고르기">{wk}</nav>'
            + hero
            + f'<div class="rhead"><h2>TOP 20</h2><p>줄마다 작은 선은 지난 8주({first[1]}월 {first[2]}주~{last[1]}월 {last[2]}주)의 순위입니다. '
              '위로 갈수록 높은 순위이고, 점선은 20위입니다.</p></div>'
            + f'<ol class="rlist">{"".join(rows)}</ol>'
            + '<p class="rsrc">출처: 알라딘 국내도서 베스트셀러 · 일본 추리/미스터리소설 주간 순위. '
              '「서평 있음」은 제목을 누르면 이 책장의 서평으로, 나머지는 알라딘 상품 페이지로 이어집니다. '
              '「알라딘에서 구매」는 제휴 링크라, 그 링크로 구매하시면 운영자가 소정의 수수료를 받을 수 있습니다.</p>')


CSS = """
<style>
/* 알라딘 주간 순위 탭 */
.rweeks{display:flex;gap:18px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin:0 0 36px}
.rweeks a{font:600 14px var(--sans);text-decoration:none;color:var(--muted);padding:6px 0;border-bottom:2px solid transparent}
.rweeks a[aria-current]{color:var(--ink);border-bottom-color:var(--ink)}
.rtop{display:grid;grid-template-columns:200px 1fr;gap:40px;align-items:center;padding:0 0 48px;border-bottom:1px solid var(--line);margin-bottom:44px}
.rtop-cover img,.rtop-cover .ph{width:100%;aspect-ratio:500/734;object-fit:cover;border-radius:3px 6px 6px 3px;box-shadow:var(--shadow-lg);display:flex;align-items:center;justify-content:center;background:var(--surface-2);font:500 18px/1.3 var(--serif);text-align:center;padding:0}
.rk-eyebrow{margin:0 0 10px;font:600 12px/1 var(--sans);letter-spacing:.08em;color:var(--accent)}
.rtop h2{font:500 clamp(30px,5vw,48px)/1.1 var(--serif);letter-spacing:-.035em;margin:0 0 6px}
.rtop h2 a{text-decoration:none}
.rtop .au{color:var(--muted);margin:0 0 18px}
.crown{display:inline-block;margin:0 0 24px;font:500 22px/1.2 var(--serif);color:var(--gold);letter-spacing:-.02em}
.rnotes{margin:0;display:grid;gap:10px;border-top:1px solid var(--line);padding-top:18px}
.rn{display:grid;grid-template-columns:9em 1fr;gap:12px;font-size:15px}
.rn dt{color:var(--muted);font-size:13px;padding-top:2px}
.rn dd{margin:0;color:var(--ink-2)}
.rhead{display:flex;align-items:baseline;gap:8px 20px;flex-wrap:wrap;margin:0 0 18px}
.rhead h2{font:500 26px/1.2 var(--serif);letter-spacing:-.025em;margin:0}
.rhead p{margin:0;color:var(--muted);font-size:13px;max-width:60ch}
.rlist{list-style:none;margin:0;padding:0;border-top:1px solid var(--ink)}
.rrow{display:grid;grid-template-columns:44px 52px minmax(0,1fr) 112px 104px;gap:16px;align-items:center;padding:12px 0;border-bottom:1px solid var(--line)}
.rrow .no{font:500 26px/1 var(--serif);letter-spacing:-.03em;font-variant-numeric:tabular-nums;text-align:right}
.rrow:nth-child(-n+3) .no{color:var(--gold)}
.rc img,.rc .ph{width:52px;aspect-ratio:500/734;object-fit:cover;border-radius:2px 4px 4px 2px;display:flex;align-items:center;justify-content:center;background:var(--surface-2);font:500 9px/1.2 var(--serif);text-align:center;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.18)}
.rt{min-width:0;display:flex;flex-direction:column}
.rt a{font:600 16px/1.4 var(--sans);text-decoration:none;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.rt a:hover{text-decoration:underline}
.rt .au{color:var(--muted);font-size:13px}
.rt .deep{align-self:flex-start;margin-top:4px}
.spark{display:block;overflow:visible}
.spark .ln polyline{fill:none;stroke:var(--ink-2);stroke-width:1.6;stroke-linejoin:round;stroke-linecap:round}
.spark .pt circle{fill:var(--accent)}
.spark .g20 line{stroke:var(--line);stroke-width:1;stroke-dasharray:3 3}
.rchg{display:flex;flex-direction:column;align-items:flex-end;gap:3px}
.chg{font:700 12px/1 var(--sans);padding:5px 8px;border-radius:999px;white-space:nowrap;font-variant-numeric:tabular-nums}
.chg.up{color:#1f6b45;background:#dff1e6}.chg.down{color:#a1283f;background:#f8e1e6}
.chg.same{color:var(--muted);background:var(--surface-2)}.chg.new{color:#6b4b00;background:#f6e3b0}.chg.re{color:#1d4f86;background:#dde9f7}
.rchg .prev{font-size:12px;color:var(--muted);white-space:nowrap}
.rsrc{margin:28px 0 0;font-size:13px;color:var(--muted)}
.buy{align-self:flex-start;display:inline-flex;align-items:center;gap:4px;margin-top:6px;font:600 12px/1 var(--sans);color:var(--accent);text-decoration:none;padding:5px 9px;border:1px solid currentColor;border-radius:999px}
.buy:hover{background:var(--accent-soft)}
.buy .ico{width:12px;height:12px}
.rt .buy{font-size:12px}
.rbuy{margin:0 0 20px}
.buy.big{font-size:14px;padding:9px 14px}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]) .chg.up{color:#8fe0b2;background:#173526}
  :root:not([data-theme="light"]) .chg.down{color:#f3a3b3;background:#3d1a22}
  :root:not([data-theme="light"]) .chg.new{color:#f2cf73;background:#3a2e10}
  :root:not([data-theme="light"]) .chg.re{color:#a9cbf3;background:#172b44}}
:root[data-theme="dark"] .chg.up{color:#8fe0b2;background:#173526}
:root[data-theme="dark"] .chg.down{color:#f3a3b3;background:#3d1a22}
:root[data-theme="dark"] .chg.new{color:#f2cf73;background:#3a2e10}
:root[data-theme="dark"] .chg.re{color:#a9cbf3;background:#172b44}
@media (max-width:720px){
  .rtop{grid-template-columns:120px 1fr;gap:20px;padding-bottom:32px;margin-bottom:32px;align-items:start}
  .crown{font-size:18px;margin-bottom:16px}
  .rn{grid-template-columns:1fr;gap:2px}
  .rrow{grid-template-columns:30px 44px minmax(0,1fr) auto;gap:12px}
  .rrow .spark{display:none}
  .rrow .no{font-size:20px}
  .rc img,.rc .ph{width:44px}
  .rt a{font-size:15px}
}
@media (max-width:420px){.rtop{grid-template-columns:96px 1fr}.rtop h2{font-size:26px}}
</style>
"""


def build(template, site_dir, books, page_fn):
    """page_fn = static_pages._page. 만든 주소 [(url, lastmod)] 를 돌려준다."""
    weeks = load_weeks()
    if not weeks:
        print("  알라딘 순위: 읽을 주가 없다 —", ALADIN)
        return []
    root = os.path.join(site_dir, "ranking")
    cov_dir = os.path.join(root, "covers")
    os.makedirs(cov_dir, exist_ok=True)
    for f in glob.glob(os.path.join(root, "*", "index.html")):
        os.remove(f)
    shelf = {_norm(t): b for t, b in books.items()}
    cover_ok = {}
    for d in weeks:
        for b in d["books"]:
            cover_ok[str(b["item"])] = _copy_cover(b["item"], cov_dir)
    miss = [k for k, v in cover_ok.items() if not v]
    if miss:
        print("  ⚠️ 순위 표지 없음:", ", ".join(miss))

    tpl = template.replace("</head>", CSS + "</head>", 1)
    urls = []
    for i, d in enumerate(weeks):
        body = _week_html(d, weeks, shelf, cover_ok)
        url = f"{SITE_URL}/ranking/" if i == 0 else f"{SITE_URL}/ranking/{d['key']}/"
        top = d["books"][0]
        title = f"알라딘 일본 미스터리 주간 순위 {d['label']} | 책호스터이프로 책장"
        desc = (f"{d['label']} 알라딘 일본 추리·미스터리 베스트 TOP 20 — 1위 『{top['short']}』. "
                "지난 8주 순위 흐름과 오르내림을 한눈에 봅니다.")
        page = page_fn(tpl, title, desc, url, body)
        page = page.replace('<script src="/data.js"></script>',
                            '<script>window.SECTION = "ranking";</script>\n<script src="/data.js"></script>', 1)
        page = re.sub(r'<h1 id="h-title">.*?</h1>', '<h1 id="h-title"><span class="nw">알라딘</span> <span class="nw">일본 미스터리</span> <span class="nw">주간 순위</span></h1>', page, count=1, flags=re.S)
        page = re.sub(r'<p class="sub" id="h-sub">.*?</p>',
                      f'<p class="sub" id="h-sub">{e(d["label"])} · 알라딘 일본 추리/미스터리소설 베스트셀러 TOP 20. '
                      '매주 수요일 저녁에 새 주를 올립니다.</p>', page, count=1, flags=re.S)
        page = re.sub(r'\n\s*<div class="searchbox">.*?</div>', "", page, count=1, flags=re.S)
        page = page.replace('<div class="stats" id="stats"></div>', "", 1)
        d_out = root if i == 0 else os.path.join(root, d["key"])
        os.makedirs(d_out, exist_ok=True)
        open(os.path.join(d_out, "index.html"), "w", encoding="utf-8").write(page)
        y, m, w = d["week"]
        urls.append((url, f"{y}-{m:02d}-{min(28, w * 7):02d}"))
    return urls
