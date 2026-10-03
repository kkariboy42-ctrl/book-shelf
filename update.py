# -*- coding: utf-8 -*-
"""책장 갱신 한 줄: 인스타 최근 게시물 → links.txt → collect.py → 커밋·푸시(=사이트 배포).

    py -3 update.py            # 받고, 분류하고, 올린다
    py -3 update.py --no-push  # 올리기 전까지만(로컬에서 확인)

- 로그인 없이 프로필에서 보이는 최근 12개만 받는다. 갱신 사이에 12개 넘게 올렸으면
  「빠진 게시물이 있을 수 있음」을 띄운다 — 그땐 브라우저에서 로그인하고 스크롤로 받아야 한다.
- 새 게시물이 어느 책으로 갔는지, 책을 못 찾아 빠진 것은 무엇인지 끝에 보여 준다.
  잘못 갔으면 overrides.json 에 {"<shortcode>": {"book": "제목"}} 또는 {"hide": true} 를 적고 다시 돌린다.
"""
import json, os, re, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = "https://www.instagram.com/kkariboy42/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"


def latest_links():
    dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=8000",
                          f"--user-agent={UA}", "--dump-dom", PROFILE],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120).stdout
    found = dict.fromkeys(re.findall(r"/(p|reel)/([A-Za-z0-9_-]{8,})/", dom))
    return [f"https://www.instagram.com/{kind}/{code}/" for kind, code in found]


def code_of(u):
    m = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", u)
    return m.group(1) if m else None


def load_data():
    s = open(os.path.join(HERE, "site", "data.js"), encoding="utf-8").read()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


def main():
    push = "--no-push" not in sys.argv
    lp = os.path.join(HERE, "links.txt")
    old = open(lp, encoding="utf-8").read().split()
    have = {code_of(u) for u in old}
    latest = latest_links()
    if not latest:
        raise SystemExit("인스타 프로필에서 게시물을 못 읽었습니다(차단·구조 변경). 잠시 뒤 다시 하거나 브라우저로 받으세요.")
    new = [u for u in latest if code_of(u) not in have]
    print(f"프로필 최근 {len(latest)}개 중 새 게시물 {len(new)}개")
    if len(new) >= len(latest):
        print("  ⚠️ 최근 것이 전부 새것 — 그 사이에 더 올린 게시물이 빠졌을 수 있음. 로그인 후 스크롤로 받아야 함.")
    if new:
        open(lp, "w", encoding="utf-8").write("\n".join(new + old) + "\n")

    before = {p["code"] for p in load_data()["posts"]}
    r = subprocess.run([sys.executable, os.path.join(HERE, "collect.py")], cwd=HERE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = r.stdout + r.stderr
    if r.returncode != 0:
        print(out[-3000:])
        raise SystemExit("collect.py 실패")
    for line in out.splitlines():
        if re.search(r"^(게시물 \d|별점 출처|책 페이지|표지 |표지 실패|표지 건너뜀)|갈림|다름|^실패", line.strip()):
            print(" ", line.strip())

    # 필터용 책 정보(쪽수·출간일·옮긴이·나라·순위 진입) — 새 책만 알라딘에서 받고, data.js 에 합치려고 collect 를 한 번 더
    r = subprocess.run([sys.executable, os.path.join(HERE, "enrich.py")], cwd=HERE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    for line in (r.stdout + r.stderr).splitlines():
        if re.search(r"^(받음|실패|meta\.json|나라를 짐작)|→", line.strip()):
            print(" ", line.strip())
    if r.returncode == 0 and re.search(r"^받음", r.stdout, re.M):
        subprocess.run([sys.executable, os.path.join(HERE, "collect.py")], cwd=HERE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))

    data = load_data()
    added = [p for p in data["posts"] if p["code"] not in before]
    new_codes = {code_of(u) for u in new}
    print(f"\n책장에 새로 들어간 게시물 {len(added)}개")
    for p in added:
        print(f"  {p['date']} {p['kind']:<4} 『{p['book']}』 ← {p['hook'][:40]}")
    missed = sorted(new_codes - {p["code"] for p in data["posts"]})
    if missed:
        print(f"\n책장에 안 들어간 새 게시물 {len(missed)}개 (책 한 권이 아니거나 책을 못 찾음):")
        cache = os.path.join(HERE, "cache")
        for c in missed:
            f = os.path.join(cache, c + ".json")
            cap = json.load(open(f, encoding="utf-8"))["caption"].strip().splitlines()[0][:60] if os.path.exists(f) else "(캡션 못 받음)"
            print(f"  {c} ← {cap}")

    if not push:
        print("\n--no-push: 올리지 않음")
        return
    subprocess.run(["git", "add", "-A"], cwd=HERE, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=HERE).returncode == 0:
        print("\n바뀐 것 없음 — 올리지 않음")
        return
    msg = f"책장 갱신 {data['updated']}: 새 게시물 {len(added)}개 (책 {len(data['books'])}권 · 게시물 {len(data['posts'])}개)"
    subprocess.run(["git", "commit", "-q", "-m", msg + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"], cwd=HERE, check=True)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=HERE, check=True)
    print(f"\n올림: {msg}\n1~2분 뒤 https://bookhoster.co.kr 에 반영")


if __name__ == "__main__":
    main()
