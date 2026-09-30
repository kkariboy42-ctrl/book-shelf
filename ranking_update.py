# -*- coding: utf-8 -*-
"""알라딘 순위 탭만 다시 만들어 배포한다 — 인스타 게시물 수집 없이.

aladin-weekly 가 새 주를 만든 뒤: py -3 ranking_update.py        (--no-push 는 만들기만)
책장 갱신(update.py)도 끝에서 같은 페이지를 다시 만들므로, 그쪽을 돌렸다면 따로 안 돌려도 된다.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import static_pages as SP
import ranking_page as RP

site = os.path.join(HERE, "site")
s = open(os.path.join(site, "data.js"), encoding="utf-8").read()
data = json.loads(s[s.index("=") + 1:].rstrip().rstrip(";"))
SP.build(data, site)
weeks = RP.load_weeks()
print("순위 탭:", ", ".join(w["label"] for w in weeks))

if "--no-push" not in sys.argv:
    git = lambda *a: subprocess.run(["git", *a], cwd=HERE, check=True)
    git("add", "-A", "site", "ranking_page.py", "static_pages.py", "ranking_update.py")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=HERE).returncode:
        git("commit", "-m", f"알라딘 순위 탭 갱신 {time.strftime('%Y-%m-%d')}: {weeks[0]['label']}")
        git("push")
        print("배포: https://bookhoster.co.kr/ranking/")
    else:
        print("바뀐 것 없음")
