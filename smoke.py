# -*- coding: utf-8 -*-
"""로컬 헤드리스 스모크 — 구운 책장 페이지를 로컬(포트 8792)에서 열어 JS 오류 0건 · 표지가 실제로 그려졌는지 본다.

    py -3 smoke.py                      # 첫 화면 + 가장 최근 게시물 책 페이지
    py -3 smoke.py /book/<slug>/ ...    # 지정한 페이지

- 공개 주소(bookhoster.co.kr)는 열지 않는다 — 헤드리스로 열면 방문자 수가 오른다. 로컬만.
  (index.html 의 카운터는 bookhoster.co.kr·github.io 가 아니면 세지 않는다)
- 8792 에 이미 book-shelf-main 미리보기가 떠 있으면 그걸 쓰고(같은 data.js 인지 확인), 없으면 잠깐 띄웠다 끈다.
- 실패 조건: 잡히지 않은 JS 오류(pageerror) 1건 이상 · 책 페이지 표지 img 의 naturalWidth 0.
  console.error 와 바깥 자원(인스타 임베드·광고) 실패는 적어만 둔다.
- 끝 코드: 0 통과 · 1 실패 · 2 크롬/로컬 서버를 못 띄움
"""
import json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import websocket  # websocket-client

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
PORT = 8792
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = f"http://127.0.0.1:{PORT}"

COVER_JS = """(async () => {
  const im = document.querySelector('.bookhead .cover img');
  if (!im) return {img: false, ph: !!document.querySelector('.bookhead .cover .ph')};
  im.loading = 'eager';
  if (!im.complete || !im.naturalWidth) await new Promise(r => { im.addEventListener('load', r); im.addEventListener('error', r); setTimeout(r, 4000); });
  return {img: true, w: im.naturalWidth, src: im.getAttribute('src')};
})()"""


def get(url, timeout=2):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def ensure_server():
    """8792 가 이 폴더의 site 를 내주고 있으면 None, 새로 띄웠으면 그 프로세스."""
    local = open(os.path.join(SITE, "data.js"), "rb").read()
    try:
        served = get(BASE + "/data.js")
    except Exception:
        served = None
    if served is not None:
        if served != local:
            raise RuntimeError(f"포트 {PORT} 에 다른 data.js 를 내주는 서버가 떠 있음 — 끄고 다시")
        return None
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", SITE],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            if get(BASE + "/data.js") == local:
                return proc
        except Exception:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError(f"로컬 서버(포트 {PORT})를 못 띄움")


def default_pages():
    s = open(os.path.join(SITE, "data.js"), encoding="utf-8").read()
    data = json.loads(s[s.index("{"):s.rindex("}") + 1])
    newest = data["posts"][0]["book"]
    return ["/", f"/book/{data['books'][newest]['slug']}/"]


BLOCK_HOSTS = ("abacus.jasoncameron.dev",)


class Tab:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=15, suppress_origin=True)
        self.n = 0
        self.events = []

    def call(self, method, **params):
        self.n += 1
        my = self.n
        self.ws.send(json.dumps({"id": my, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == my:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})
            self.events.append(m)

    def drain(self, until_method=None, seconds=10.0):
        end = time.time() + seconds
        while time.time() < end:
            self.ws.settimeout(max(0.05, end - time.time()))
            try:
                m = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                break
            self.events.append(m)
            if until_method and m.get("method") == until_method:
                return True
        self.ws.settimeout(15)
        return False


def check(tab, path):
    tab.events.clear()
    tab.call("Page.navigate", url=BASE + path)
    loaded = tab.drain("Page.loadEventFired", 10)
    tab.drain(None, 1.5)  # 늦게 도는 타이머·모듈 스크립트 오류까지
    errs, cons, logs = [], [], []
    for e in tab.events:
        m, p = e.get("method"), e.get("params", {})
        if m == "Runtime.exceptionThrown":
            d = p.get("exceptionDetails", {})
            errs.append((d.get("exception") or {}).get("description") or d.get("text", "?"))
        elif m == "Runtime.consoleAPICalled" and p.get("type") == "error":
            cons.append(" ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", [])))
        elif m == "Log.entryAdded" and p.get("entry", {}).get("level") == "error":
            if any(h in p["entry"].get("url", "") for h in BLOCK_HOSTS):
                continue  # 일부러 막은 카운터 요청
            logs.append(p["entry"].get("text", "") + " " + p["entry"].get("url", ""))
    cover = None
    if path.startswith("/book/"):
        r = tab.call("Runtime.evaluate", expression=COVER_JS, awaitPromise=True, returnByValue=True)
        cover = r.get("result", {}).get("value")
    bad = []
    if not loaded:
        bad.append("load 이벤트 없음(10초)")
    if errs:
        bad.append(f"JS 오류 {len(errs)}건")
    if cover is not None and cover.get("img") and not cover.get("w"):
        bad.append(f"표지 안 그려짐 naturalWidth=0 ({cover.get('src')})")
    if cover is not None and not cover.get("img") and not cover.get("ph"):
        bad.append("책 머리 표지 자리 없음")
    cv = "" if cover is None else (f" · 표지 {cover['w']}px" if cover.get("img") else " · 표지 자리표시(표지 없는 책)")
    print(f"  {'통과' if not bad else '실패'} {path} — JS 오류 {len(errs)}{cv} · console.error {len(cons)} · 자원 오류 {len(logs)}")
    for x in errs[:5]:
        print("    오류:", x.splitlines()[0][:200])
    for x in (cons + logs)[:5]:
        print("    참고:", x[:160])
    for x in bad:
        print("    ✗", x)
    return not bad


def main():
    pages = [a for a in sys.argv[1:] if a.startswith("/")] or default_pages()
    t0 = time.time()
    try:
        server = ensure_server()
    except Exception as e:
        print("스모크 못 함:", e)
        return 2
    prof = tempfile.mkdtemp(prefix="shelf_smoke_")
    cport = free_port()
    chrome = None
    try:
        chrome = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", f"--remote-debugging-port={cport}",
                                   f"--user-data-dir={prof}", "--no-first-run", "--no-default-browser-check",
                                   "--window-size=390,844", "about:blank"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws_url = None
        for _ in range(100):
            try:
                tabs = json.loads(get(f"http://127.0.0.1:{cport}/json/list"))
                ws_url = next(t["webSocketDebuggerUrl"] for t in tabs if t.get("type") == "page")
                break
            except Exception:
                time.sleep(0.1)
        if not ws_url:
            print("스모크 못 함: 헤드리스 크롬 연결 실패")
            return 2
        tab = Tab(ws_url)
        for m in ("Page.enable", "Runtime.enable", "Log.enable", "Network.enable"):
            tab.call(m)
        # 방문자 카운터(abacus)는 스모크에서 아예 부르지 않는다 — 외부 호출·429 방지 (사용자 11-25)
        tab.call("Network.setBlockedURLs", urls=[f"*{h}*" for h in BLOCK_HOSTS])
        print(f"로컬 스모크 ({BASE}, 공개 주소 안 엶)")
        ok = all([check(tab, p) for p in pages])
        try:
            tab.call("Browser.close")
        except Exception:
            pass
        print(f"  → {'통과' if ok else '실패 — 푸시하지 말 것'} ({time.time() - t0:.1f}초)")
        return 0 if ok else 1
    finally:
        if chrome and chrome.poll() is None:
            chrome.kill()
        if server:
            server.kill()
        time.sleep(0.3)
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
