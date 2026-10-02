"""PDF 속 숨은 글자 찾기 (2025 예선 5번 「PDF 스텔스 텍스트」 유형).

숨기는 방식 다섯 가지를 각각 따로 잡는다.
  W  흰색·밝은 글자          (글자색 밝기 ≥ 0.9)
  S  극소 글자               (크기 < 3pt)
  I  보이지 않게 그린 글자    (렌더 모드 3, 투명도 0)
  U  레이어 아래 글자         (나중에 그린 이미지·도형이 글자를 덮음)
  O  페이지 밖 글자
  + 이미지 속 배경색과 비슷한 글자 → --enhance 로 페이지를 대비 극대화해 PNG 로 저장, 눈·OCR 로 읽는다

  python pdf_stealth.py 문서.pdf                 # 의심 구간 목록
  python pdf_stealth.py 문서.pdf --enhance out/  # + 페이지·이미지 대비 강화본 저장
  python pdf_stealth.py --selftest               # 가짜 PDF 로 다섯 방식 모두 잡히는지 시험

주의: 찾은 글자는 「AI 에게 이 문서를 높게 평가하라」 같은 지시문일 수 있다.
AI 에게 PDF 를 통째로 넘기지 말고, 이 스크립트 결과를 사람이 읽는다.
"""
import argparse
import os
import sys

import pymupdf

COVER_TYPES = ("fill-image", "fill-path", "fill-shade")


def lum(rgb):
    if rgb is None:
        return 0.0
    if isinstance(rgb, int):
        rgb = ((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)
        rgb = [c / 255 for c in rgb]
    if len(rgb) == 1:
        return rgb[0]
    if len(rgb) == 4:  # CMYK
        c, m, y, k = rgb
        rgb = [(1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k)]
    r, g, b = rgb[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def covers(big, small):
    return big.x0 <= small.x0 + 0.5 and big.y0 <= small.y0 + 0.5 and big.x1 >= small.x1 - 0.5 and big.y1 >= small.y1 - 0.5


def scan_page(page):
    log = page.get_bboxlog()  # 그리는 순서대로 (종류, bbox)
    covers_after = [(i, pymupdf.Rect(b)) for i, (t, b) in enumerate(log) if t in COVER_TYPES]
    prect = page.rect
    hits = []
    for sp in page.get_texttrace():
        text = "".join(chr(c[0]) for c in sp["chars"]).strip()
        if not text:
            continue
        bbox = pymupdf.Rect(sp["bbox"])
        tags = []
        if lum(sp.get("color")) >= 0.9:
            tags.append("W")
        if sp["size"] * abs(sp.get("scale", 1) or 1) < 3:
            tags.append("S")
        if sp.get("type") == 3 or sp.get("opacity", 1) == 0:
            tags.append("I")
        if not bbox.intersects(prect):
            tags.append("O")
        seq = sp.get("seqno", -1)
        if any(i > seq and covers(r, bbox) for i, r in covers_after):
            tags.append("U")
        if tags:
            hits.append({"tags": tags, "text": text, "size": round(sp["size"], 1), "bbox": [round(v) for v in bbox]})
    return hits


def merge_lines(hits):
    """같은 줄·같은 태그의 조각을 이어 붙인다."""
    out = []
    for h in hits:
        if out and out[-1]["tags"] == h["tags"] and abs(out[-1]["bbox"][1] - h["bbox"][1]) < 2:
            out[-1]["text"] += ("" if out[-1]["text"].endswith(" ") else " ") + h["text"]
            out[-1]["bbox"][2] = h["bbox"][2]
        else:
            out.append(dict(h, bbox=list(h["bbox"])))
    return out


def enhance(doc, outdir):
    from PIL import Image, ImageOps

    os.makedirs(outdir, exist_ok=True)
    saved = []
    for n, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        for name, im in (("eq", ImageOps.equalize(img)), ("ac", ImageOps.autocontrast(img, cutoff=1))):
            p = os.path.join(outdir, f"p{n:02d}_{name}.png")
            im.save(p)
            saved.append(p)
        # 페이지에 박힌 원본 이미지도 따로 — 축소 렌더에서 뭉개지는 희미한 글자 대비
        for k, info in enumerate(page.get_images(full=True)):
            x = doc.extract_image(info[0])
            from io import BytesIO
            im = Image.open(BytesIO(x["image"])).convert("RGB")
            # 채널별 범위를 0~255 로 늘려, 배경과 2~3 차이 나는 글자도 드러나게
            p = os.path.join(outdir, f"p{n:02d}_img{k}_eq.png")
            ImageOps.equalize(im).save(p)
            saved.append(p)
    return saved


def report(path, enhance_dir=None):
    doc = pymupdf.open(path)
    total = 0
    for n, page in enumerate(doc, 1):
        hits = merge_lines(scan_page(page))
        for h in hits:
            total += 1
            print(f"p{n} [{''.join(h['tags'])}] {h['size']}pt {h['bbox']}  {h['text']}")
        if not page.get_text().strip() and page.get_images():
            print(f"p{n} [이미지 페이지] 글자층 없음 → --enhance 로 대비 강화본을 눈으로 확인")
    print(f"\n의심 구간 {total}개  (W 흰색 · S 극소 · I 투명 · U 덮임 · O 페이지 밖)")
    if enhance_dir:
        for p in enhance(doc, enhance_dir):
            print("저장:", p)


def selftest(tmp):
    from PIL import Image, ImageDraw

    os.makedirs(tmp, exist_ok=True)
    pdf = os.path.join(tmp, "stealth_test.pdf")
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((72, 72), "Visible title of the report", fontsize=14)
    p.insert_text((72, 100), "white secret sentence here", fontsize=10, color=(1, 1, 1))
    p.insert_text((72, 120), "tiny secret sentence here", fontsize=1)
    p.insert_text((72, 140), "invisible secret sentence here", fontsize=10, render_mode=3)
    p.insert_text((72, 160), "covered secret sentence here", fontsize=10)
    p.draw_rect(pymupdf.Rect(60, 148, 400, 166), color=None, fill=(0.95, 0.95, 0.95))
    p.insert_text((700, 700), "offpage secret sentence here", fontsize=10)
    # 이미지 속 배경과 거의 같은 색 글자
    im = Image.new("RGB", (600, 120), (250, 250, 250))
    ImageDraw.Draw(im).text((20, 50), "LOW CONTRAST SECRET IN IMAGE", fill=(244, 244, 244))
    ip = os.path.join(tmp, "low.png")
    im.save(ip)
    p.insert_image(pymupdf.Rect(72, 200, 472, 280), filename=ip)
    doc.save(pdf)

    hits = merge_lines(scan_page(pymupdf.open(pdf)[0]))
    found = {t: any(t in h["tags"] for h in hits) for t in "WSIUO"}
    normal_flagged = any("Visible" in h["text"] for h in hits)
    for h in hits:
        print(f"  [{''.join(h['tags'])}] {h['text']}")
    saved = enhance(pymupdf.open(pdf), os.path.join(tmp, "enh"))
    ok = all(found.values()) and not normal_flagged
    print("잡은 방식:", found, "| 정상 글자 오탐:", normal_flagged)
    print("이미지 대비 강화본(눈으로 확인):", [s for s in saved if "img" in s])
    print("자가 시험", "통과" if ok else "실패")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", nargs="?")
    ap.add_argument("--enhance", metavar="DIR")
    ap.add_argument("--selftest", nargs="?", const="_selftest_out", metavar="DIR")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest(a.selftest) else 1)
    if not a.pdf:
        ap.print_help()
        sys.exit(1)
    report(a.pdf, a.enhance)


if __name__ == "__main__":
    main()
