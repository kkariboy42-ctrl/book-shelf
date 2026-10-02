"""횟수 제한 있는 채점 API 에 반복 제출하는 틀 (2025 본선 2번 「몽타주」 유형).

몽타주 문제 제약: 1분당 1회 · 1024×1024 PNG/JPEG · 10MB 이하 · 같은 파일(해시) 재제출은 무효 ·
이력은 최근 4건만 보임. → 직접 기록하지 않으면 무엇이 점수를 올렸는지 잃는다.

이 틀이 해 주는 것
  - 제출 전 검사: 크기·형식·용량·이미 낸 해시인지 (실패하면 보내지 않는다 = 한 번을 아낀다)
  - 간격 지키기: 마지막 제출 시각을 파일에 남겨, 프로그램을 다시 켜도 1분을 지킨다
  - 기록: submissions.csv 에 시각·파일·해시·메모(무엇을 바꿨나)·점수·응답 전문

당일 할 일: submit() 안의 요청 부분만 실제 API 에 맞게 바꾼다.

  python api_loop.py 후보.png --note "코 폭 좁힘"     # 한 장 제출
  python api_loop.py 후보폴더/ --note "1차 묶음"       # 폴더 안 이미지를 차례로(간격 자동)
  python api_loop.py --best                           # 지금까지 최고점 5개
  python api_loop.py --dry 후보.png                   # 검사만, 제출 안 함
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime

LOG = "submissions.csv"
STAMP = ".last_submit"
MIN_INTERVAL = 61  # 초. 문제 규정 + 1초 여유
SIZE = (1024, 1024)
MAX_BYTES = 10 * 1024 * 1024
EXTS = (".png", ".jpg", ".jpeg")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sent_hashes():
    if not os.path.exists(LOG):
        return set()
    with open(LOG, encoding="utf-8-sig") as f:
        return {r["hash"] for r in csv.DictReader(f)}


def precheck(path):
    from PIL import Image

    errs = []
    if not path.lower().endswith(EXTS):
        errs.append("PNG/JPEG 아님")
    if os.path.getsize(path) > MAX_BYTES:
        errs.append(f"용량 {os.path.getsize(path) / 1e6:.1f}MB > 10MB")
    with Image.open(path) as im:
        if im.size != SIZE:
            errs.append(f"크기 {im.size} ≠ {SIZE}")
    if sha(path) in sent_hashes():
        errs.append("이미 낸 파일(해시 같음) — 평가 안 됨")
    return errs


def wait_turn():
    if os.path.exists(STAMP):
        left = MIN_INTERVAL - (time.time() - float(open(STAMP).read() or 0))
        if left > 0:
            print(f"  {left:.0f}초 대기 (이 동안 다음 후보를 만든다)")
            time.sleep(left)


def submit(path):
    """실제 API 호출 자리. (점수, 응답 dict) 를 돌려준다."""
    raise NotImplementedError("당일 API 주소·인증·필드명에 맞게 작성: requests.post(URL, files={'image': open(path,'rb')}, headers=...)")


def log(row):
    new = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "file", "hash", "note", "score", "response"])
        if new:
            w.writeheader()
        w.writerow(row)


def run(paths, note, dry):
    for p in paths:
        errs = precheck(p)
        print(f"{p}: {'검사 통과' if not errs else ' / '.join(errs)}")
        if errs or dry:
            continue
        wait_turn()
        open(STAMP, "w").write(str(time.time()))
        try:
            score, resp = submit(p)
        except NotImplementedError as e:
            print(" ", e)
            sys.exit(1)
        log({"time": datetime.now().isoformat(timespec="seconds"), "file": p, "hash": sha(p),
             "note": note, "score": score, "response": json.dumps(resp, ensure_ascii=False)})
        print(f"  점수 {score}")


def best(n=5):
    if not os.path.exists(LOG):
        print("기록 없음")
        return
    with open(LOG, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["score"]]
    for r in sorted(rows, key=lambda r: float(r["score"]), reverse=True)[:n]:
        print(f"{r['score']:>8}  {r['time']}  {r['file']}  {r['note']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--best", action="store_true")
    a = ap.parse_args()
    if a.best:
        return best()
    if not a.target:
        ap.print_help()
        return
    paths = sorted(os.path.join(a.target, f) for f in os.listdir(a.target) if f.lower().endswith(EXTS)) \
        if os.path.isdir(a.target) else [a.target]
    run(paths, a.note, a.dry)


if __name__ == "__main__":
    main()
