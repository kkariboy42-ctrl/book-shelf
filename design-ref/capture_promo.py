# -*- coding: utf-8 -*-
"""홍보 릴스 재료: 사이트 화면을 폰 크기(1080×1350)로 찍는다. 로컬 미리보기(8790)에서 — 방문자 수를 올리지 않는다."""
import os, subprocess, urllib.parse
from PIL import Image

OUT = r"G:\내 드라이브\03. 인스타그램\@@ 릴스\25. 책장 홈페이지\_화면"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TMP = os.path.join(os.environ["TEMP"], "bs_cap")
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

B = lambda t: "/book/" + urllib.parse.quote(t.replace(" ", "-")) + "/"
SHOTS = {
    "01_첫화면": dict(src="/"),
    "02_별5플러스": dict(src="/", sel=".rgroup.plus"),
    "03_별5묶음": dict(src="/", sel=".rgroup:nth-of-type(2)"),
    "04_검색_투명": dict(src="/?q=" + urllib.parse.quote("투명한"), sel=".bar"),
    "05_검색_작가": dict(src="/?q=" + urllib.parse.quote("히가시노"), sel=".bar"),
    "06_책머리": dict(src=B("투명한 나선")),
    "07_서평한토막": dict(src=B("투명한 나선"), sel=".excerpt"),
    "08_게시물": dict(src=B("투명한 나선"), sel=".col .post"),
    "09_스포칸": dict(src=B("폐놀이공원의 살인"), act="gate", dy=-140),
    "10_경고창": dict(src=B("폐놀이공원의 살인"), act="dialog"),
    "11_스포글목록": dict(src=B("폐놀이공원의 살인"), act="notes"),
    "12_원고분석": dict(src="/", act="deep", sel=".bar"),
    "13_비소설": dict(src="/nonfiction/"),
    "14_비소설목록": dict(src="/nonfiction/", sel=".bar"),
    "15_별점없음": dict(src="/", sel=".rgroup:last-of-type"),
    "16_소개_별점기준": dict(src="/about.html", sel="table"),
}

ONLY = __import__("sys").argv[1:]
for name, o in SHOTS.items():
    if ONLY and name not in ONLY:
        continue
    qs = urllib.parse.urlencode({k: v for k, v in o.items()})
    url = "http://localhost:8790/_cap.html?" + qs
    raw = os.path.join(TMP, name + ".png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=500,488",
                    "--force-device-scale-factor=2.7692", "--virtual-time-budget=9000", f"--screenshot={raw}", url],
                   capture_output=True, timeout=90)
    im = Image.open(raw).convert("RGB").crop((0, 0, 1080, 1350))
    im.save(os.path.join(OUT, name + ".png"))
    print("찍음", name)
