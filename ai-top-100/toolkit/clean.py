"""조합 거래 기록 정제 뼈대.

당일 데이터를 보고 UNIT_KG(단위 환산표)와 ITEM_ALIASES(품목 사전)만 채우면 된다.
환산값은 품목·지역마다 다르니 반드시 문제에서 주어진 값이나 관계자 답변으로 확정할 것.

  python clean.py --demo                 # 가짜 데이터로 동작 확인
  python clean.py 입력.csv -o 정제.csv    # 실제 데이터 (csv/xlsx)

기대하는 열: 날짜, 품목, 수량, 단위, 금액 (이름이 다르면 읽은 뒤 df.rename 으로 맞춘다)
"""
import argparse
import re
import sys

import pandas as pd


# 단위 → kg. 아래 값은 예시일 뿐 — 문제에서 주어진 기준으로 바꿔야 한다.
UNIT_KG = {
    "kg": 1.0, "킬로": 1.0, "g": 0.001,
    "관": 3.75, "근": 0.6,
    "상자": None, "박스": None, "짝": None, "마리": None,  # 품목마다 다름 → ITEM_UNIT_KG 로
}
# (품목, 단위) → kg. 상자·짝처럼 품목마다 무게가 다른 단위
ITEM_UNIT_KG = {
    # ("사과", "상자"): 10.0,
    # ("고등어", "마리"): 0.4,
}
# 표기 흔들림 → 표준 품목명
ITEM_ALIASES = {
    "고딩어": "고등어", "고등어(대)": "고등어", "고등어(중)": "고등어",
    "사과-부사": "사과", "부사": "사과", "홍로": "사과",
}


def norm_item(s):
    s = re.sub(r"\s+", "", str(s))
    return ITEM_ALIASES.get(s, s)


def norm_date(s):
    s = str(s).strip()
    m = re.match(r"(?:(\d{4})[.\-/년]\s*)?(\d{1,2})[.\-/월]\s*(\d{1,2})", s)
    if not m:
        return pd.NaT
    y = int(m.group(1) or 2026)
    return pd.Timestamp(year=y, month=int(m.group(2)), day=int(m.group(3)))


def to_kg(row):
    unit = str(row["단위"]).strip()
    per = ITEM_UNIT_KG.get((row["품목"], unit), UNIT_KG.get(unit))
    return row["수량"] * per if per else None


def clean(df):
    df = df.copy()
    report = []

    df["품목"] = df["품목"].map(norm_item)
    df["날짜"] = df["날짜"].map(norm_date)
    for c in ("수량", "금액"):
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(r"[,원\s]", "", regex=True), errors="coerce")

    bad = df[df["날짜"].isna() | df["수량"].isna() | df["금액"].isna()]
    if len(bad):
        report.append(f"읽을 수 없는 값 {len(bad)}건 (행 {list(bad.index)})")

    dup = df.duplicated(subset=["날짜", "품목", "수량", "단위", "금액"], keep="first")
    if dup.any():
        report.append(f"중복 거래 {int(dup.sum())}건 제거 (행 {list(df.index[dup])})")
    df = df[~dup]

    df["kg"] = df.apply(to_kg, axis=1)
    no_kg = df[df["kg"].isna()]
    if len(no_kg):
        pairs = sorted(set(zip(no_kg["품목"], no_kg["단위"])))
        report.append(f"kg 환산 불가 {len(no_kg)}건 — 환산표 필요: {pairs}")

    df["kg당단가"] = df["금액"] / df["kg"]
    med = df.groupby("품목")["kg당단가"].transform("median")
    out = (df["kg당단가"] > med * 3) | (df["kg당단가"] < med / 3) | (df["금액"] <= 0)
    df["이상치"] = out.fillna(False)
    if df["이상치"].any():
        report.append(f"단가 이상치 {int(df['이상치'].sum())}건 (품목 중앙값 대비 3배 밖, 또는 0원 이하)")

    return df, report


def demo():
    return pd.DataFrame({
        "날짜": ["2026.10.03", "10/3", "10월 4일", "2026-10-04", "10/5", "10/5"],
        "품목": ["사과-부사", "사과", "고딩어", "고등어(대)", "고등어", "고등어"],
        "수량": [2, "2", 30, 20, 25, 25],
        "단위": ["관", "관", "kg", "kg", "kg", "kg"],
        "금액": ["45,000원", "45000", 240000, 1600000, 200000, 200000],
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        df = demo()
    elif a.src:
        df = pd.read_excel(a.src) if a.src.endswith(("xlsx", "xls")) else pd.read_csv(a.src)
    else:
        ap.print_help()
        sys.exit(1)

    out, report = clean(df)
    print(out.to_string())
    print("\n[정제 보고]")
    for r in report or ["문제 없음"]:
        print(" -", r)
    if a.out:
        out.to_csv(a.out, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
