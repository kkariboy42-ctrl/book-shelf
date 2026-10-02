"""규칙 기반 판정 틀 (2025 본선 1번 「AI 입국 심사관」 유형).

AI 에게 「30명 심사해줘」를 한 번에 시키면 틀린다. 대신
  ① 서류를 코드로 표(신청자 한 명 = dict 하나)로 만들고
  ② 규칙 하나 = 함수 하나로 옮기고 (AI 에게 번역시키되 규칙 원문을 docstring 에 붙여 1:1 대조)
  ③ 번호순으로 검사해 **첫 위반에서 멈춘다** → 「여러 위반이면 가장 낮은 번호」가 저절로 지켜진다.

당일 할 일: RULES 를 실제 규칙으로 바꾸고, load_cases() 를 실제 데이터 읽기로 바꾼다.
조합 규정(출하 기준·보조금 자격 등) 판정에도 그대로 쓴다.

  python rule_engine.py --demo                  # 가짜 신청자로 동작 확인
  python rule_engine.py --demo --explain        # 사람마다 규칙별 통과/위반 전부 표시(검산용)
  python rule_engine.py --demo -o 답.json       # 제출 JSON 저장 → check_format.py 로 형식 검사
"""
import argparse
import json
from datetime import date

INSPECTION_DATE = date(2025, 11, 22)  # 「오늘」이 아니라 문제가 정한 기준일. 반드시 바꿀 것.
REQUIRED_DOCS = {"passport", "visa", "arrival_declaration", "flight_ticket", "financial_proof"}


def d(s):
    return date.fromisoformat(s) if s else None


# ── 규칙: (번호, 원문, 함수). 함수는 위반이면 사유 문자열, 통과면 None ──────────────
def r1(c):
    """1. 필수 서류가 모두 있어야 한다."""
    miss = REQUIRED_DOCS - set(c["docs"])
    return f"서류 누락 {sorted(miss)}" if miss else None


def r2(c):
    """2. 여권은 심사일 기준 만료되지 않아야 한다."""
    exp = d(c["docs"].get("passport", {}).get("expiry"))
    return f"여권 만료 {exp}" if exp and exp < INSPECTION_DATE else None


def r3(c):
    """3. 서류 간 이름이 일치해야 한다."""
    names = {v.get("name") for v in c["docs"].values() if v.get("name")}
    return f"이름 불일치 {sorted(names)}" if len(names) > 1 else None


def r4(c):
    """4. 비자 목적과 입국신고서 목적이 같아야 한다."""
    v = c["docs"].get("visa", {}).get("purpose")
    a = c["docs"].get("arrival_declaration", {}).get("purpose")
    return f"목적 불일치 비자={v} 신고서={a}" if v and a and v != a else None


def r5(c):
    """5. 체류 1일당 100 이상의 자금 증명."""
    days = c["docs"].get("arrival_declaration", {}).get("stay_days", 0)
    money = c["docs"].get("financial_proof", {}).get("amount", 0)
    return f"자금 부족 {money} < {days * 100}" if money < days * 100 else None


RULES = [(1, r1), (2, r2), (3, r3), (4, r4), (5, r5)]


def judge(case, explain=False):
    trail = []
    first = None
    for no, fn in RULES:
        why = fn(case)
        trail.append((no, why))
        if why and first is None:
            first = (no, why)
            if not explain:
                break
    out = {"id": case["id"], "answer": "Deny" if first else "Approve"}
    if first:
        out["reason"] = first[0]
    return out, trail


def load_cases():
    """가짜 데이터. 당일엔 PDF·JSON 을 읽어 같은 모양 dict 목록을 돌려주게 바꾼다."""
    full = lambda **kw: {
        "passport": {"name": "KIM", "expiry": "2027-01-01"},
        "visa": {"name": "KIM", "purpose": "tour"},
        "arrival_declaration": {"name": "KIM", "purpose": "tour", "stay_days": 5},
        "flight_ticket": {"name": "KIM"},
        "financial_proof": {"name": "KIM", "amount": 900},
        **kw,
    }
    c2 = full(passport={"name": "LEE", "expiry": "2025-11-21"})  # 2번(만료)·3번(이름) 동시 위반 → 2
    c3 = full()
    del c3["visa"]                                                # 1번 누락
    c4 = full(financial_proof={"name": "KIM", "amount": 300})    # 5번
    c5 = full(passport={"name": "KIM", "expiry": "2025-11-22"})  # 기준일 당일 만료 → 통과(규정 문구 확인!)
    return [{"id": f"applicant_{i:03d}", "docs": c} for i, c in enumerate([full(), c2, c3, c4, c5], 1)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--explain", action="store_true")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    if not a.demo:
        ap.print_help()
        return
    results = []
    for case in load_cases():
        res, trail = judge(case, a.explain)
        results.append(res)
        line = f"{res['id']}: {res['answer']}" + (f" (규칙 {res['reason']})" if "reason" in res else "")
        print(line)
        if a.explain:
            for no, why in trail:
                print(f"    {no:>2}  {'✗ ' + why if why else '·'}")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("저장:", a.out)


if __name__ == "__main__":
    main()
