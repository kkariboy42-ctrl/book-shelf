"""제출 직전 형식 검사기.

2025 문제는 답이 맞아도 형식이 틀리면 0점인 구조였다(대문자만, JSON 스키마, Approve/Deny 대소문자,
id 개수). 제출 버튼 누르기 전에 이걸 한 번 돌린다.

  # JSON 배열 답안 — 필수 키·허용값·id 개수·중복 검사
  python check_format.py json 답.json --keys id,winner --allow winner=blue,red --ids test_battles.json
  python check_format.py json 답.json --keys id,answer --allow answer=Approve,Deny --need-if answer=Deny:reason
  python check_format.py json 답.json --keys id,lunch --optional dinner --id-pattern "2025-02-\\d\\d"

  # 문자열 답 — 허용 문자·단어 수
  python check_format.py text "AITOP100" --charset upper,digit
  python check_format.py text "The quick brown fox jumps" --charset alpha,space --words 5

  # 문항별 답 묶음 — {"Q1": "7", "Q6": {...}} 같은 답안 파일을 문항마다 정규식/JSON 키 순서로 검사
  python check_format.py answers 답.json --rule Q1=int --rule Q2=dec1 --rule Q5=multi --rule "Q6=json:교동,갯마을"
  (규칙: int 정수 · dec1 소수 첫째 자리 · multi 「1,3,5」 오름차순·중복 없음 · upper 대문자만 ·
   json:키1,키2 키 순서 그대로·값 정수·": " 공백 · 그 밖의 문자열은 정규식으로 본다)

--ids 에는 id 목록이 든 파일(JSON 배열·각 원소에 id 키, 또는 한 줄에 하나) 을 준다. 빠진 id·남는 id 를 알려준다.
"""
import argparse
import json
import re
import sys

CHARSETS = {
    "upper": "A-Z", "lower": "a-z", "alpha": "A-Za-z", "digit": "0-9",
    "space": " ", "comma": ",", "dot": ".",
}


def load_ids(path):
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if isinstance(data, dict):  # {"battles":[...]} 같은 감싼 형태
        data = next((v for v in data.values() if isinstance(v, list)), [])
    return [d["id"] if isinstance(d, dict) else d for d in data]


def check_json(a):
    errs, warns = [], []
    with open(a.file, encoding="utf-8-sig") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [f"JSON 파싱 실패: {e}"], warns
    if not isinstance(data, list):
        return ["최상위가 배열([ ])이 아니다"], warns

    keys = [k for k in (a.keys or "").split(",") if k]
    optional = [k for k in (a.optional or "").split(",") if k]
    allow = {}
    for spec in a.allow or []:
        k, v = spec.split("=", 1)
        allow[k] = v.split(",")
    need_if = []
    for spec in a.need_if or []:
        cond, need = spec.split(":", 1)
        k, v = cond.split("=", 1)
        need_if.append((k, v, need))

    seen = {}
    for i, row in enumerate(data):
        tag = f"[{i}] {row.get('id', '?') if isinstance(row, dict) else '?'}"
        if not isinstance(row, dict):
            errs.append(f"{tag}: 객체가 아니다")
            continue
        for k in keys:
            if k not in row:
                errs.append(f"{tag}: 필수 키 '{k}' 없음")
        extra = set(row) - set(keys) - set(optional) - {n for _, _, n in need_if}
        if keys and extra:
            warns.append(f"{tag}: 정의 안 된 키 {sorted(extra)}")
        for k, vals in allow.items():
            if k in row and row[k] not in vals:
                hint = [v for v in vals if str(v).lower() == str(row[k]).lower()]
                errs.append(f"{tag}: {k}={row[k]!r} 허용값 아님 {vals}" + (f" — 대소문자? {hint[0]!r}" if hint else ""))
        for k, v, need in need_if:
            if str(row.get(k)) == v and need not in row:
                errs.append(f"{tag}: {k}={v} 인데 '{need}' 없음")
            if str(row.get(k)) != v and need in row:
                warns.append(f"{tag}: {k}≠{v} 인데 '{need}' 있음")
        if a.id_pattern and "id" in row and not re.fullmatch(a.id_pattern, str(row["id"])):
            errs.append(f"{tag}: id 형식이 패턴 {a.id_pattern} 과 다름")
        if "id" in row:
            if row["id"] in seen:
                errs.append(f"{tag}: id 중복 (앞서 [{seen[row['id']]}])")
            seen[row["id"]] = i

    if a.ids:
        want = load_ids(a.ids)
        missing = [x for x in want if x not in seen]
        surplus = [x for x in seen if x not in set(want)]
        if missing:
            errs.append(f"빠진 id {len(missing)}개: {missing[:10]}{' …' if len(missing) > 10 else ''}")
        if surplus:
            errs.append(f"문제에 없는 id {len(surplus)}개: {surplus[:10]}")
    warns.insert(0, f"항목 {len(data)}개")
    return errs, warns


PRESETS = {"int": r"-?\d+", "dec1": r"-?\d+\.\d", "upper": r"[A-Z]+", "multi": None}


def check_answers(a):
    errs, warns = [], []
    with open(a.file, encoding="utf-8-sig") as f:
        ans = json.load(f)
    rules = dict(r.split("=", 1) for r in a.rule or [])
    for q in rules:
        if q not in ans:
            errs.append(f"{q}: 답이 없다")
    for q, v in ans.items():
        rule = rules.get(q)
        if rule is None:
            warns.append(f"{q}: 규칙 없음 — 형식 미검사")
            continue
        if rule.startswith("json:"):
            keys = rule[5:].split(",")
            s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            try:
                obj = json.loads(s)
            except json.JSONDecodeError as e:
                errs.append(f"{q}: JSON 아님 ({e})")
                continue
            if list(obj) != keys:
                errs.append(f"{q}: 키·순서 {list(obj)} ≠ {keys}")
            bad = [k for k, x in obj.items() if not isinstance(x, int) or isinstance(x, bool)]
            if bad:
                errs.append(f"{q}: 정수가 아닌 값 {bad}")
            if '":' in s and '": ' not in s:
                warns.append(f"{q}: 콜론 뒤 공백 없음 — 예시와 같은지 확인")
            continue
        s = str(v)
        if s != s.strip():
            errs.append(f"{q}: 앞뒤 공백")
        if rule == "multi":
            if not re.fullmatch(r"\d+(,\d+)*", s):
                errs.append(f"{q}: {s!r} 는 「1,3,5」 꼴이 아니다(공백·다른 구분자?)")
            else:
                nums = [int(x) for x in s.split(",")]
                if nums != sorted(set(nums)):
                    errs.append(f"{q}: 오름차순·중복 없음이 아니다 {nums}")
            continue
        pat = PRESETS.get(rule, rule)
        if not re.fullmatch(pat, s):
            errs.append(f"{q}: {s!r} 가 규칙 {rule} 에 안 맞음")
    warns.insert(0, f"답 {len(ans)}개, 규칙 {len(rules)}개")
    return errs, warns


def check_text(a):
    errs, warns = [], []
    s = a.answer
    if s != s.strip():
        errs.append("앞뒤 공백이 있다")
    if "  " in s:
        errs.append("공백이 두 칸 연속인 곳이 있다")
    if a.charset:
        cls = "".join(CHARSETS[c] for c in a.charset.split(","))
        bad = sorted(set(re.sub(f"[{cls}]", "", s)))
        if bad:
            errs.append(f"허용 안 된 문자 {bad} (허용: {a.charset})")
    n = len(s.split())
    if a.words is not None and n != a.words:
        errs.append(f"단어 수 {n}개 — 지문은 {a.words}개")
    warns.append(f"단어 {n}개, 글자 {len(s)}자")
    return errs, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    j = sub.add_parser("json")
    j.add_argument("file")
    j.add_argument("--keys", help="필수 키, 콤마 구분")
    j.add_argument("--optional", help="있어도 되는 키")
    j.add_argument("--allow", action="append", help="키=값1,값2 (여러 번 가능)")
    j.add_argument("--need-if", action="append", help="키=값:필요한키 (예 answer=Deny:reason)")
    j.add_argument("--ids", help="정답에 있어야 할 id 목록 파일")
    j.add_argument("--id-pattern", help="id 정규식")
    t = sub.add_parser("text")
    t.add_argument("answer")
    t.add_argument("--charset", help="upper,lower,alpha,digit,space,comma,dot 조합")
    t.add_argument("--words", type=int)
    s = sub.add_parser("answers")
    s.add_argument("file")
    s.add_argument("--rule", action="append", help="문항=규칙 (int, dec1, multi, upper, json:키,키, 또는 정규식)")
    a = ap.parse_args()

    errs, warns = {"json": check_json, "text": check_text, "answers": check_answers}[a.mode](a)
    for w in warns:
        print("  ·", w)
    for e in errs:
        print("  ✗", e)
    print("통과" if not errs else f"실패 {len(errs)}건")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
