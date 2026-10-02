"""두 모델이 각각 뽑은 표(CSV)를 칸 단위로 비교한다 (2025 예선 1번 「춘식도락」 유형).

이미지·PDF 표를 AI 로 옮기면 한 글자씩 틀린다(조림↔조립, 959↔969). 같은 이미지를 두 모델에게
따로 옮기게 한 뒤 이 스크립트로 다른 칸만 뽑아, 그 칸만 원본을 눈으로 본다.

  python csv_diff.py claude.csv gemini.csv --key 날짜,식사,코너
  python csv_diff.py a.csv b.csv --key id --loose      # 공백·전각문자·쉼표 차이는 무시
  python csv_diff.py --selftest

출력: 한쪽에만 있는 행, 값이 다른 칸(행 키·열·A값·B값). 끝에 「다른 칸 N개 / 전체 M칸」.
"""
import argparse
import csv
import sys
import unicodedata


def norm(v, loose):
    v = "" if v is None else str(v)
    if loose:
        v = unicodedata.normalize("NFKC", v)
        v = "".join(v.split()).replace(",", "")
    return v.strip()


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def diff(a_rows, b_rows, key, loose=False):
    def k(r):
        return tuple(norm(r.get(c), True) for c in key)

    A = {k(r): r for r in a_rows}
    B = {k(r): r for r in b_rows}
    only_a = [x for x in A if x not in B]
    only_b = [x for x in B if x not in A]
    cols = [c for c in a_rows[0].keys() if c not in key] if a_rows else []
    cells, total = [], 0
    for x in A:
        if x not in B:
            continue
        for c in cols:
            total += 1
            va, vb = norm(A[x].get(c), loose), norm(B[x].get(c), loose)
            if va != vb:
                cells.append((x, c, A[x].get(c), B[x].get(c)))
    dup_a = len(a_rows) - len(A)
    dup_b = len(b_rows) - len(B)
    return only_a, only_b, cells, total, dup_a, dup_b


def show(only_a, only_b, cells, total, dup_a, dup_b, na="A", nb="B"):
    if dup_a or dup_b:
        print(f"! 키가 겹치는 행: {na} {dup_a}개, {nb} {dup_b}개 — 키 열을 더 넣어야 한다")
    for x in only_a:
        print(f"{na}에만 있는 행: {x}")
    for x in only_b:
        print(f"{nb}에만 있는 행: {x}")
    for x, c, va, vb in cells:
        print(f"{' / '.join(x)} | {c} | {na}={va!r} | {nb}={vb!r}")
    print(f"\n다른 칸 {len(cells)}개 / 비교한 칸 {total}개, 한쪽에만 있는 행 {len(only_a) + len(only_b)}개")


def selftest():
    a = [
        {"날짜": "01-13", "코너": "한식A", "메뉴": "통마늘간장제육불고기", "반찬": "두부조림", "kcal": "959"},
        {"날짜": "01-13", "코너": "한식B", "메뉴": "돈코츠라멘", "반찬": "단무지무침", "kcal": "1,012"},
        {"날짜": "01-14", "코너": "양식", "메뉴": "수제남산왕돈까스", "반찬": "콘샐러드", "kcal": "1210"},
    ]
    b = [
        {"날짜": "01-13", "코너": "한식A", "메뉴": "통마늘간장제육불고기", "반찬": "두부조립", "kcal": "969"},
        {"날짜": "01-13", "코너": "한식B", "메뉴": "돈코츠 라멘", "반찬": "단무지무침", "kcal": "1012"},
        {"날짜": "01-15", "코너": "양식", "메뉴": "수제남산왕돈까스", "반찬": "콘샐러드", "kcal": "1210"},
    ]
    r = diff(a, b, ["날짜", "코너"], loose=True)
    show(*r)
    only_a, only_b, cells, *_ = r
    got = {(c, va) for _, c, va, _ in cells}
    ok = got == {("반찬", "두부조림"), ("kcal", "959")} and len(only_a) == 1 and len(only_b) == 1
    print("자가 시험", "통과" if ok else f"실패 {got}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a", nargs="?")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--key", help="행을 맞출 열, 콤마 구분")
    ap.add_argument("--loose", action="store_true", help="공백·전각·쉼표 차이 무시")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not (a.a and a.b and a.key):
        ap.print_help()
        sys.exit(1)
    r = diff(read(a.a), read(a.b), a.key.split(","), a.loose)
    show(*r, na=a.a, nb=a.b)
    sys.exit(1 if r[2] or r[0] or r[1] else 0)


if __name__ == "__main__":
    main()
