# -*- coding: utf-8 -*-
"""V1 독립 재풀이. 실행: py -3 verify.py  (같은 입력이면 같은 출력)"""
import csv, re, json, os, math
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

BASE = r"C:\Claude\book-shelf\ai-top-100\practice\mock01"
DATA = os.path.join(BASE, "problem", "data")
EXT = os.path.join(BASE, "_work", "mock01", "extract")
OUT = os.path.join(BASE, "_work", "mock01", "verify")

D = Decimal

# ---------- 파서 ----------
def parse_time(s):
    s = s.strip()
    m = re.match(r"(\d{4})[-./](\d{2})[-./](\d{2})\s+(오전|오후)?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if not m:
        raise ValueError(s)
    y, mo, d, ampm, hh, mm, ss = m.groups()
    hh = int(hh)
    if ampm == "오전" and hh == 12: hh = 0
    if ampm == "오후" and hh != 12: hh += 12
    return datetime(int(y), int(mo), int(d), hh, int(mm), int(ss or 0))

def parse_price(s):
    s = s.strip().replace("₩", "").replace(",", "").replace("원", "")
    if s.endswith("만"):
        return int(D(s[:-1]) * 10000)
    return int(D(s))

ITEM = {
    "배추": "배추", "전어": "전어", "햇전어": "전어", "물오징어": "오징어", "오징어": "오징어",
    "생강": "생강", "생강(토종)": "생강", "사과(홍로)": "사과", "사과": "사과", "홍로": "사과",
    "사과 부사": "사과", "부사": "사과", "고춧가루": "고춧가루", "고추가루": "고춧가루",
    "숫꽃게": "꽃게", "꽃게": "꽃게", "고등어": "고등어",
}
UNIT = {"포기": "포기", "kg": "kg", "키로": "kg", "근": "근", "미": "마리", "마리": "마리",
        "축": "축", "손": "손", "상자": "상자", "box": "상자", "박스": "상자"}

def norm_unit(u):
    u = u.strip()
    return UNIT.get(u.lower(), UNIT.get(u))

def bizday(kst):
    return (kst - timedelta(hours=6)).date()

SEP1 = date(2026, 9, 1); SEP30 = date(2026, 9, 30)

def rate(village, bd):
    if village == "교동":
        return D("0.03")
    return D("0.035") if bd >= date(2026, 9, 21) else D("0.05")

def conv(item, unit, qty, bd):
    """(환산계수, 중량kg, 마리수) — 공지 기준"""
    q = D(str(qty))
    if item == "사과":
        if unit == "상자":
            f = D(10) if bd <= date(2026, 9, 15) else D(5)
            return f, q * f, None
        if unit == "kg": return D(1), q, None
    if item == "고춧가루" and unit == "근": return D("0.6"), q * D("0.6"), None
    if item == "생강" and unit == "근": return D("0.375"), q * D("0.375"), None
    if item in ("전어", "꽃게") and unit == "kg": return D(1), q, None
    if item == "고등어" and unit == "손": return D(2), None, q * 2
    if item == "오징어":
        if unit == "축": return D(20), None, q * 20
        if unit == "마리": return D(1), None, q
    if item == "배추": return None, None, None
    raise ValueError((item, unit))

# ---------- 적재 ----------
rows = []
with open(os.path.join(DATA, "9월_장터거래_내보내기.csv"), encoding="utf-8-sig", newline="") as f:
    rd = csv.reader(f)
    header = next(rd)
    for i, r in enumerate(rd, start=2):  # 파일 행번호(헤더=1)
        tid, ts, vil, mem, item, qty, unit, price, note = r
        rows.append(dict(src="CSV", line=i, tid=tid, ts_raw=ts, vil=vil, mem_raw=mem, item_raw=item,
                         qty=D(qty), unit_raw=unit, price_raw=price, note=note, cancel=False))
with open(os.path.join(EXT, "handbook_final.csv"), encoding="utf-8-sig", newline="") as f:
    for i, r in enumerate(csv.DictReader(f), start=1):
        rows.append(dict(src="수기", line=i, tid=r["번호"], ts_raw="2026-09-23 " + r["시각"], vil=r["마을"],
                         mem_raw=r["조합원"], item_raw=r["품목"], qty=D(r["수량"]), unit_raw=r["수량단위"],
                         price_raw=r["단가"], note="", cancel=(r["취소여부"] == "Y")))

NAMES = {("교동", "0712"): "김순자", ("교동", "0217"): "김숙자", ("교동", "0315"): "박영철",
         ("교동", "0408"): "이말순", ("교동", "0521"): "최동훈", ("갯마을", "0712"): "김순자",
         ("갯마을", "0205"): "정해룡", ("갯마을", "0330"): "윤바다", ("갯마을", "0419"): "한어진"}

# 중복 판정 (같은 거래번호 → 한 건, 내용 동일 여부 확인)
seen = {}
for r in rows:
    key = (r["src"], r["tid"])
    if key in seen:
        a = seen[key]
        same = all(a[k] == r[k] for k in ("ts_raw", "vil", "mem_raw", "item_raw", "qty", "unit_raw", "price_raw", "note"))
        assert same, ("중복인데 내용 다름", r["tid"])
        r["dup"] = True
    else:
        seen[key] = r
        r["dup"] = False

for r in rows:
    r["mem4"] = re.sub(r"^[KG]-", "", r["mem_raw"].strip())
    r["name"] = NAMES[(r["vil"], r["mem4"])]
    r["item"] = ITEM[r["item_raw"].strip()]
    r["unit"] = norm_unit(r["unit_raw"])
    r["price"] = parse_price(r["price_raw"])
    t = parse_time(r["ts_raw"])
    r["kst"] = t + timedelta(hours=9) if (r["src"] == "CSV" and r["vil"] == "갯마을") else t
    r["bd_rec"] = bizday(r["kst"])
    m = re.search(r"T\d{3}", r["note"])
    r["corr_of"] = m.group(0) if (m and "정정" in r["note"]) else ""

byid = {r["tid"]: r for r in rows if not r["dup"] and r["src"] == "CSV"}
replaced = {r["corr_of"] for r in rows if not r["dup"] and r["corr_of"]}
for r in rows:
    root = r["tid"]; chain = 0
    while byid.get(root) and byid[root]["corr_of"]:
        root = byid[root]["corr_of"]; chain += 1
        assert chain < 10
    r["root"] = root if r["corr_of"] else ""
    r["bd"] = byid[root]["bd_rec"] if r["corr_of"] else r["bd_rec"]
    r["sep"] = SEP1 <= r["bd"] <= SEP30
    r["replaced"] = (r["src"] == "CSV" and r["tid"] in replaced)
    r["confirmed"] = (not r["dup"]) and (not r["replaced"]) and (not r["cancel"]) and r["sep"]
    r["sales"] = r["qty"] * r["price"]
    f, kg, ea = conv(r["item"], r["unit"], r["qty"], r["bd"])
    r["factor"], r["kg"], r["ea"] = f, kg, ea
    r["rate"] = rate(r["vil"], r["bd"])
    fee = (r["sales"] * r["rate"] / 10).to_integral_value(rounding=ROUND_FLOOR) * 10
    r["fee"] = int(fee)

# ---------- 장부 ----------
cols = ["거래ID", "출처", "원본행번호", "마을", "조합원번호4자리", "성명", "품목원문", "품목표준", "수량", "단위원문",
        "단위표준", "단가원문", "단가", "매출", "찍힌시각원문", "KST시각", "기록영업일", "정정대상ID", "정정루트ID",
        "귀속영업일", "9월여부", "중복여부", "대체됨여부", "취소여부", "확정여부", "환산계수", "중량kg", "마리수",
        "수수료율", "수수료"]
yn = lambda b: "Y" if b else "N"
s = lambda v: "" if v is None else str(v)
with open(os.path.join(OUT, "ledger_verify.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(cols)
    for r in rows:
        w.writerow([r["tid"], r["src"], r["line"], r["vil"], r["mem4"], r["name"], r["item_raw"], r["item"],
                    r["qty"], r["unit_raw"], r["unit"], r["price_raw"], r["price"], r["sales"], r["ts_raw"],
                    r["kst"].strftime("%Y-%m-%d %H:%M"), r["bd_rec"], r["corr_of"], r["root"], r["bd"],
                    yn(r["sep"]), yn(r["dup"]), yn(r["replaced"]), yn(r["cancel"]), yn(r["confirmed"]),
                    s(r["factor"]), s(r["kg"]), s(r["ea"]), r["rate"], r["fee"]])

C = [r for r in rows if r["confirmed"]]
def tot(it, key): return sum((x[key] for x in it), D(0))

q1 = sum(1 for r in C if r["bd"] == date(2026, 9, 15))
q2 = tot([r for r in C if r["vil"] == "교동" and r["item"] == "사과"], "kg")
fee_v = {v: sum(r["fee"] for r in C if r["vil"] == v) for v in ("교동", "갯마을")}
sales_v = {v: tot([r for r in C if r["vil"] == v], "sales") for v in ("교동", "갯마을")}
q4 = tot([r for r in C if r["vil"] == "교동" and r["mem4"] == "0712"], "sales")

ginger = tot([r for r in C if r["vil"] == "교동" and r["item"] == "생강"], "kg")
squid = tot([r for r in C if r["vil"] == "갯마을" and r["item"] == "오징어"], "ea")
daily = {}
for r in C: daily[r["bd"]] = daily.get(r["bd"], D(0)) + r["sales"]
top = sorted(daily.items(), key=lambda kv: -kv[1])[:3]
g712 = sum(1 for r in C if r["vil"] == "갯마을" and r["mem4"] == "0712")
st = [ginger == D("24.375"), squid == 344, top[0][0] == date(2026, 9, 15), g712 == 22, fee_v["갯마을"] > fee_v["교동"]]
q5 = ",".join(str(i + 1) for i, b in enumerate(st) if b)

ans = {"Q1": q1, "Q2": str(q2.quantize(D("0.1"), rounding=ROUND_HALF_UP)), "Q3": fee_v["갯마을"], "Q4": int(q4),
       "Q5": q5, "Q6": {"교동": int(sales_v["교동"] - fee_v["교동"]), "갯마을": int(sales_v["갯마을"] - fee_v["갯마을"])}}
with open(os.path.join(OUT, "answers_verify.json"), "w", encoding="utf-8") as f:
    json.dump(ans, f, ensure_ascii=False, indent=1)

print(json.dumps(ans, ensure_ascii=False))
print("Q2 raw kg", q2)
print("Q5 근거: 생강kg", ginger, "/ 오징어마리", squid, "/ 상위영업일", [(str(d), int(v)) for d, v in top],
      "/ 갯0712건수", g712, "/ 수수료", fee_v, "/ 매출", {k: int(v) for k, v in sales_v.items()})
print("확정", len(C), "전체행", len(rows))
