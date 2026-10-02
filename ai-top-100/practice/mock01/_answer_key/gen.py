# -*- coding: utf-8 -*-
"""mock01 생성기 — 자료 전부 생성 + 정답 계산 (시드 고정).  실행: py -3 gen.py"""
import random, json, csv
from datetime import datetime, timedelta, date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import pymupdf as fitz
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, Border, Side, PatternFill

ROOT = Path(__file__).resolve().parent.parent
PROB = ROOT / 'problem'; DATA = PROB / 'data'; KEY = ROOT / '_answer_key'
DATA.mkdir(parents=True, exist_ok=True)
FONT = r'C:\Windows\Fonts\malgun.ttf'; FONTB = r'C:\Windows\Fonts\malgunbd.ttf'
rng = random.Random(20260915)

MEMBERS = {
    'K-0712': ('김순자', '교동'), 'K-0217': ('김숙자', '교동'), 'K-0315': ('박영철', '교동'),
    'K-0408': ('이말순', '교동'), 'K-0521': ('최동훈', '교동'),
    'G-0712': ('김순자', '갯마을'), 'G-0205': ('정해룡', '갯마을'), 'G-0330': ('윤바다', '갯마을'),
    'G-0419': ('한어진', '갯마을'),
}
ITEMS = {
    'K-0712': ['사과', '생강'], 'K-0217': ['사과', '배추'], 'K-0315': ['생강', '고춧가루'],
    'K-0408': ['배추', '고춧가루'], 'K-0521': ['사과'],
    'G-0712': ['전어', '꽃게'], 'G-0205': ['고등어', '오징어'], 'G-0330': ['오징어', '꽃게'],
    'G-0419': ['전어', '고등어'],
}
VIL_MEMBERS = {v: [m for m, (_, vv) in MEMBERS.items() if vv == v] for v in ('교동', '갯마을')}
KST_OFFSET = timedelta(hours=9)
BOX_SWITCH = date(2026, 9, 16)          # 이 영업일부터 사과 1상자 = 5kg
RATE_SWITCH = date(2026, 9, 21)         # 이 영업일부터 갯마을 3.5%
SEPT = (date(2026, 9, 1), date(2026, 9, 30))


def bday(kst):
    return (kst - timedelta(hours=6)).date()


def r100(a, b):
    return rng.randint(a // 100, b // 100) * 100


def rand_trade(item, bd):
    """returns (qty10, unit, price)"""
    if item == '사과':
        if rng.random() < 0.7:
            p = r100(30000, 42000) if bd < BOX_SWITCH else r100(16000, 24000)
            return rng.randint(1, 6) * 10, '상자', p
        return rng.randint(10, 80), 'kg', r100(3000, 4500)
    if item == '배추':
        return rng.randint(3, 20) * 10, '포기', r100(2500, 4000)
    if item == '고춧가루':
        return rng.randint(1, 6) * 10, '근', r100(18000, 25000)
    if item == '생강':
        return rng.randint(1, 8) * 10, '근', r100(6000, 9000)
    if item == '전어':
        return rng.randint(5, 80), 'kg', r100(15000, 22000)
    if item == '꽃게':
        return rng.randint(5, 60), 'kg', r100(25000, 38000)
    if item == '고등어':
        return rng.randint(1, 10) * 10, '손', r100(9000, 14000)
    if item == '오징어':
        if rng.random() < 0.6:
            return rng.randint(1, 3) * 10, '축', r100(60000, 90000)
        return rng.randint(5, 40) * 10, '마리', r100(3500, 5000)
    raise ValueError(item)


recs = []


def add(kst, mem, item, qty10, unit, price, kind='normal', target=None, src='csv', void=False, tag=None):
    r = dict(kst=kst, mem=mem, vil=MEMBERS[mem][1], item=item, qty10=qty10, unit=unit, price=price,
             kind=kind, target=target, src=src, void=void, tag=tag)
    recs.append(r)
    return r


def rand_time(vil, bd):
    base = datetime.combine(bd, datetime.min.time()) + timedelta(hours=6)
    if vil == '교동':
        off = rng.randint(60, 14 * 60)            # 07:00 ~ 20:00
    else:
        if rng.random() < 0.4:                    # 새벽 위판 04:00~07:59
            off = rng.choice([rng.randint(22 * 60, 24 * 60 - 1), rng.randint(0, 119)])
        else:
            off = rng.randint(3 * 60, 12 * 60)
    return base + timedelta(minutes=off)


# ---------- 1. 기본 무작위 거래 ----------
d = SEPT[0]
while d <= SEPT[1]:
    for vil in ('교동', '갯마을'):
        for _ in range(rng.randint(1, 3)):
            mem = rng.choice(VIL_MEMBERS[vil]); item = rng.choice(ITEMS[mem])
            q, u, p = rand_trade(item, d)
            add(rand_time(vil, d), mem, item, q, u, p)
    d += timedelta(days=1)

# ---------- 2. 심어둔 거래 ----------
K = lambda *a: datetime(*a)                       # KST
U = lambda *a: datetime(*a) + KST_OFFSET          # UTC 로 적힐 갯마을 거래 → 내부는 KST
add(K(2026, 9, 16, 3, 40), 'K-0521', '사과', 30, '상자', 32000, tag='P1_자정넘김_사과')
add(K(2026, 9, 1, 5, 20), 'K-0408', '배추', 120, '포기', 3100, tag='P2_8월영업일')
add(K(2026, 10, 1, 4, 30), 'K-0217', '사과', 20, '상자', 21000, tag='P3_9월30일영업일')
add(U(2026, 8, 31, 20, 20), 'G-0419', '전어', 42, 'kg', 17800, tag='P4_UTC_8월')
add(U(2026, 9, 30, 22, 0), 'G-0330', '꽃게', 35, 'kg', 33000, tag='P5_UTC_10월')
add(U(2026, 9, 20, 22, 10), 'G-0205', '고등어', 70, '손', 11300, tag='P6_UTC_9.21')
add(U(2026, 9, 20, 19, 30), 'G-0419', '전어', 57, 'kg', 19300, tag='P7_UTC_9.20')
o8 = add(K(2026, 9, 8, 10, 15), 'G-0205', '오징어', 20, '축', 74000, tag='P8_사슬원')
c8a = add(K(2026, 9, 12, 13, 5), 'G-0205', '오징어', 30, '축', 74000, kind='corr', target=o8, tag='P8_사슬1')
add(K(2026, 9, 19, 9, 40), 'G-0205', '오징어', 30, '축', 71500, kind='corr', target=c8a, tag='P8_사슬2')
o9 = add(K(2026, 9, 15, 10, 0), 'K-0712', '사과', 40, '상자', 36500, tag='P9_원')
add(K(2026, 9, 17, 11, 0), 'K-0712', '사과', 50, '상자', 36500, kind='corr', target=o9, tag='P9_정정')
o10 = add(K(2026, 9, 20, 15, 0), 'G-0712', '꽃게', 48, 'kg', 31700, tag='P10_원')
add(K(2026, 9, 22, 10, 20), 'G-0712', '꽃게', 43, 'kg', 31700, kind='corr', target=o10, tag='P10_정정')
add(U(2026, 9, 14, 22, 30), 'G-0330', '오징어', 20, '축', 68800, tag='P11a_UTC_9.15')
add(U(2026, 9, 15, 20, 0), 'G-0419', '고등어', 50, '손', 10700, tag='P11b_UTC_9.15')
add(U(2026, 9, 15, 21, 30), 'G-0712', '전어', 36, 'kg', 18200, tag='P11c_UTC_9.16')
add(K(2026, 9, 11, 9, 30), 'K-0712', '생강', 50, '근', 7400, tag='P12_김순자K')
add(K(2026, 9, 26, 14, 50), 'K-0712', '사과', 30, '상자', 19800, tag='P12_김순자K')
add(K(2026, 9, 5, 11, 10), 'G-0712', '전어', 64, 'kg', 16900, tag='P12_김순자G')
add(K(2026, 9, 9, 10, 0), 'K-0217', '사과', 20, '상자', 34800, tag='P12_김숙자')

# 장부 사진(수기) — KST, 영업일 9/23
L = []
L.append(add(K(2026, 9, 23, 14, 10), 'K-0712', '사과', 20, '상자', 21500, src='ledger'))
L.append(add(K(2026, 9, 23, 14, 45), 'G-0712', '전어', 35, 'kg', 18000, src='ledger'))
L.append(add(K(2026, 9, 23, 15, 30), 'K-0315', '생강', 40, '근', 8200, src='ledger', void=True))
L.append(add(K(2026, 9, 23, 16, 20), 'G-0205', '고등어', 60, '손', 12000, src='ledger'))
L.append(add(K(2026, 9, 23, 17, 5), 'K-0408', '고춧가루', 30, '근', 23500, src='ledger'))

# 무작위 정정 몇 건 추가 (원거래 이후 1~3일)
csv_recs = [r for r in recs if r['src'] == 'csv' and r['kind'] == 'normal' and r['tag'] is None]
for o in rng.sample(csv_recs, 4):
    q = max(5 if o['unit'] in ('kg',) else 10, o['qty10'] + rng.choice([-10, 10, 20]))
    t = o['kst'] + timedelta(days=rng.randint(1, 3), minutes=rng.randint(10, 300))
    t = t.replace(hour=rng.randint(9, 17))
    add(t, o['mem'], o['item'], q, o['unit'], o['price'], kind='corr', target=o, tag='R_정정')

# ---------- 3. 거래번호 부여 ----------
csv_rows = sorted([r for r in recs if r['src'] == 'csv'], key=lambda r: r['kst'])
for i, r in enumerate(csv_rows, 1):
    r['tid'] = f'T{i:03d}'
for i, r in enumerate([r for r in recs if r['src'] == 'ledger'], 1):
    r['tid'] = f'H{i:02d}'
for r in recs:
    assert r['kind'] != 'corr' or r['kst'] > r['target']['kst']

# ---------- 4. 정답 모델 ----------
superseded = {id(r['target']) for r in recs if r['kind'] == 'corr'}


def root(r):
    while r['kind'] == 'corr':
        r = r['target']
    return r


def amount(r):
    return r['qty10'] * r['price'] // 10        # 단가 100원 단위 → 정수


def kg_of(r, bd):
    if r['item'] == '사과':
        if r['unit'] == '상자':
            return r['qty10'] / 10 * (10 if bd < BOX_SWITCH else 5)
        return r['qty10'] / 10
    if r['item'] in ('생강', '고춧가루'):
        return r['qty10'] / 10 * (0.375 if r['item'] == '생강' else 0.6)
    return r['qty10'] / 10


def fee(vil, bd, amt):
    if vil == '교동':
        num, den = 3, 100
    elif bd < RATE_SWITCH:
        num, den = 5, 100
    else:
        num, den = 35, 1000
    return (amt * num // den) // 10 * 10


eff = []
for r in recs:
    if r['void'] or id(r) in superseded:
        continue
    rt = root(r); bd = bday(rt['kst'])
    if not (SEPT[0] <= bd <= SEPT[1]):
        continue
    a = amount(r)
    eff.append(dict(rec=r, root=rt, bd=bd, vil=r['vil'], mem=r['mem'], item=r['item'], amt=a,
                    fee=fee(r['vil'], bd, a)))

ans = {}
ans['Q1'] = sum(1 for e in eff if e['bd'] == date(2026, 9, 15))
ans['Q2'] = round(sum(kg_of(e['rec'], e['bd']) for e in eff if e['item'] == '사과'), 1)
ans['Q3'] = sum(e['fee'] for e in eff if e['vil'] == '갯마을')
ans['Q4'] = sum(e['amt'] for e in eff if e['mem'] == 'K-0712')
pay = {v: sum(e['amt'] - e['fee'] for e in eff if e['vil'] == v) for v in ('교동', '갯마을')}
ans['Q6'] = {'교동': pay['교동'], '갯마을': pay['갯마을']}

# Q5 보기
ginger = sum(kg_of(e['rec'], e['bd']) for e in eff if e['item'] == '생강')
sq_true = sum(e['rec']['qty10'] // 10 * (20 if e['rec']['unit'] == '축' else 1) for e in eff if e['item'] == '오징어')
sq_wrong = sum(e['rec']['qty10'] // 10 * (10 if e['rec']['unit'] == '축' else 1) for e in eff if e['item'] == '오징어')
assert sq_true != sq_wrong
daily = {}
for e in eff:
    daily[e['bd']] = daily.get(e['bd'], 0) + e['amt']
top = sorted(daily.items(), key=lambda kv: -kv[1])
assert top[0][1] - top[1][1] >= 20000, top[:3]
g712_true = sum(1 for e in eff if e['mem'] == 'G-0712')
g712_stated = g712_true + 1
fee_k = sum(e['fee'] for e in eff if e['vil'] == '교동'); fee_g = ans['Q3']
assert fee_k != fee_g


def kgfmt(x):
    s = f'{x:.3f}'.rstrip('0').rstrip('.')
    return s


opts = [
    (f'교동마을 생강의 9월 총 판매 중량은 {kgfmt(ginger)}kg이다.', True),
    (f'갯마을 오징어의 9월 총 판매량은 {sq_wrong}마리이다.', False),
    (f'두 마을을 합친 확정 매출이 9월 중 가장 큰 영업일은 9월 {top[0][0].day}일이다.', True),
    (f'갯마을 조합원 김순자(G-0712)의 9월 확정 거래는 {g712_stated}건이다.', False),
    (f'9월 수수료 합계는 {"교동마을이 갯마을보다 많다" if fee_k > fee_g else "갯마을이 교동마을보다 많다"}.', True),
]
ans['Q5'] = ','.join(str(i + 1) for i, (_, t) in enumerate(opts) if t)

# ---------- 5. 오답(함정) 값 계산 — 해설용 ----------
naive = {}
# Q1: 단말기 시각 그대로 + 달력 날짜 + 정정/중복 무시
def naive_day(r):
    return r['kst'] - KST_OFFSET if r['vil'] == '갯마을' else r['kst']
naive['Q1_달력날짜·UTC무시'] = sum(1 for r in csv_rows if naive_day(r).date() == date(2026, 9, 15))
naive['Q1_영업일O_UTC무시'] = sum(1 for e in eff if bday(naive_day(e['root'])) == date(2026, 9, 15))
naive['Q2_상자10kg고정'] = round(sum((e['rec']['qty10'] / 10 * 10 if e['rec']['unit'] == '상자' else e['rec']['qty10'] / 10) for e in eff if e['item'] == '사과'), 1)
naive['Q2_정정시각기준'] = round(sum(kg_of(e['rec'], bday(e['rec']['kst'])) for e in eff if e['item'] == '사과'), 1)
naive['Q3_합계후절사'] = sum((e['amt'] * (5 if e['bd'] < RATE_SWITCH else 3.5) / 100) for e in eff if e['vil'] == '갯마을') // 10 * 10
naive['Q3_5%고정'] = sum((e['amt'] * 5 // 100) // 10 * 10 for e in eff if e['vil'] == '갯마을')
naive['Q3_초안4%'] = sum((e['amt'] * 4 // 100) // 10 * 10 for e in eff if e['vil'] == '갯마을')
naive['Q4_0712전부'] = sum(e['amt'] for e in eff if e['mem'].endswith('0712'))
naive['Q4_장부제외'] = sum(e['amt'] for e in eff if e['mem'] == 'K-0712' and e['rec']['src'] == 'csv')
naive['Q5_생강600g'] = kgfmt(sum(e['rec']['qty10'] / 10 * 0.6 for e in eff if e['item'] == '생강'))
naive['Q5_오징어참값'] = sq_true
naive['Q5_G0712참값'] = g712_true
naive['Q5_수수료'] = {'교동': fee_k, '갯마을': fee_g}
naive['Q5_일별상위3'] = [(str(k), v) for k, v in top[:3]]

# ---------- 6. CSV 출력 (지저분하게) ----------
UNIT_TXT = {'상자': ['상자', '박스', 'BOX', 'box'], 'kg': ['kg', 'KG', '키로', 'Kg'], '포기': ['포기'],
            '근': ['근'], '손': ['손'], '축': ['축'], '마리': ['마리', '미']}
ITEM_TXT = {'사과': ['사과', '사과(홍로)', '홍로', '사과 부사', '부사'], '생강': ['생강', '생강(토종)'],
            '고춧가루': ['고춧가루', '고추가루'], '배추': ['배추'], '전어': ['전어', '햇전어'],
            '꽃게': ['꽃게', '숫꽃게'], '고등어': ['고등어'], '오징어': ['오징어', '물오징어']}


def fmt_dt(dt):
    k = rng.randint(0, 3)
    if k == 0:
        return dt.strftime('%Y-%m-%d %H:%M')
    if k == 1:
        return dt.strftime('%Y.%m.%d %H:%M')
    if k == 2:
        return dt.strftime('%Y/%m/%d %H:%M:%S')
    ap = '오전' if dt.hour < 12 else '오후'
    h = dt.hour % 12 or 12
    return f'{dt.year}-{dt.month:02d}-{dt.day:02d} {ap} {h}:{dt.minute:02d}'


def fmt_price(p):
    c = ['comma', 'won', 'wonsign']
    if p % 1000 == 0 and p >= 10000:
        c.append('man')
    k = rng.choice(c)
    if k == 'comma':
        return f'{p:,}'
    if k == 'won':
        return f'{p}원'
    if k == 'wonsign':
        return f'₩{p:,}'
    return f'{p / 10000:g}만'


def fmt_qty(q10):
    if q10 % 10 == 0 and rng.random() < 0.6:
        return str(q10 // 10)
    return f'{q10 / 10:.1f}'


def fmt_mem(r):
    if rng.random() < 0.35:
        return r['mem'].split('-')[1]              # 접두어 없는 번호
    return r['mem']


rows = []
for r in csv_rows:
    shown = r['kst'] - KST_OFFSET if r['vil'] == '갯마을' else r['kst']
    note = ''
    if r['kind'] == 'corr':
        note = rng.choice([f'정정(원거래 {r["target"]["tid"]})', f'{r["target"]["tid"]} 정정분', f'정정: {r["target"]["tid"]}'])
    elif rng.random() < 0.12:
        note = rng.choice(['단골', '택배', '현금', '카드', '시식 행사'])
    item_txt = rng.choice(ITEM_TXT[r['item']])
    unit_txt = rng.choice(UNIT_TXT[r['unit']])
    if r['tag'] and r['tag'].startswith('P12'):
        memtxt = r['mem'].split('-')[1]
    else:
        memtxt = fmt_mem(r)
    rows.append([r['tid'], fmt_dt(shown), r['vil'], memtxt, item_txt, fmt_qty(r['qty10']), unit_txt,
                 fmt_price(r['price']), note])
# 중복 내보내기 4행 (G-0712 1건 포함)
dup_pool = [i for i, r in enumerate(csv_rows) if r['kind'] == 'normal' and id(r) not in superseded]
g712_idx = [i for i in dup_pool if csv_rows[i]['mem'] == 'G-0712' and SEPT[0] <= bday(csv_rows[i]['kst']) <= SEPT[1]]
d15_idx = [i for i in dup_pool if bday(csv_rows[i]['kst']) == date(2026, 9, 15)]
dups = {g712_idx[0], d15_idx[0]}
while len(dups) < 4:
    dups.add(rng.choice(dup_pool))
out = []
for i, row in enumerate(rows):
    out.append(row)
    if i in dups:
        out.append(list(row))
        if rng.random() < 0.5:   # 바로 다음이 아니라 몇 줄 뒤에 붙는 경우도 있도록
            pass
with open(DATA / '9월_장터거래_내보내기.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['거래번호', '일시(단말기)', '마을', '조합원번호', '품목', '수량', '단위', '단가', '비고'])
    w.writerows(out)

# ---------- 7. 조합원 명부 XLSX (병합 머리글, 두 마을 나란히) ----------
wb = Workbook(); ws = wb.active; ws.title = '조합원명부'
thin = Side(style='thin'); bd_ = Border(left=thin, right=thin, top=thin, bottom=thin)
ws['A1'] = '교동·갯마을 공동판매조합 조합원 명부 (2026.9.1 기준)'; ws.merge_cells('A1:F1')
ws['A1'].font = Font(bold=True, size=13)
ws['A2'] = '교동마을 (농산물)'; ws.merge_cells('A2:C2')
ws['D2'] = '갯마을 (수산물)'; ws.merge_cells('D2:F2')
for c, t in zip('ABCDEF', ['번호', '성명', '주 품목'] * 2):
    ws[f'{c}3'] = t
for c in 'ABCDEF':
    for rr in (2, 3):
        ws[f'{c}{rr}'].alignment = Alignment(horizontal='center'); ws[f'{c}{rr}'].font = Font(bold=True)
        ws[f'{c}{rr}'].fill = PatternFill('solid', fgColor='DDEBF7' if c in 'ABC' else 'FCE4D6')
kl = [m for m in MEMBERS if m.startswith('K')]; gl = [m for m in MEMBERS if m.startswith('G')]
for i in range(max(len(kl), len(gl))):
    rr = 4 + i
    if i < len(kl):
        m = kl[i]; ws[f'A{rr}'] = m.split('-')[1]; ws[f'B{rr}'] = MEMBERS[m][0]; ws[f'C{rr}'] = '·'.join(ITEMS[m])
    if i < len(gl):
        m = gl[i]; ws[f'D{rr}'] = m.split('-')[1]; ws[f'E{rr}'] = MEMBERS[m][0]; ws[f'F{rr}'] = '·'.join(ITEMS[m])
for row in ws.iter_rows(min_row=2, max_row=3 + max(len(kl), len(gl)), max_col=6):
    for c in row:
        c.border = bd_
        c.number_format = '@'
ws[f'A{5 + max(len(kl), len(gl))}'] = '※ 번호 앞 마을 기호: 교동 K-, 갯마을 G- (명부에는 생략)'
for c, wdt in zip('ABCDEF', [8, 10, 16, 8, 10, 16]):
    ws.column_dimensions[c].width = wdt
wb.save(DATA / '조합원명부.xlsx')


# ---------- 8. 이미지 1 : 게시판 공지 (환산표) ----------
def F(sz, b=False):
    return ImageFont.truetype(FONTB if b else FONT, sz)


W, H = 1500, 1150
board = Image.new('RGB', (W, H), (150, 108, 70))
arr = np.array(board).astype(np.int16)
nrng = np.random.default_rng(7)
arr += nrng.integers(-18, 18, arr.shape[:2])[..., None]
board = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
paper = Image.new('RGB', (1180, 960), (250, 248, 238))
dp = ImageDraw.Draw(paper)
dp.text((40, 30), '【공지】 품목별 단위 환산 기준', font=F(46, True), fill=(20, 20, 20))
dp.text((40, 100), '게시 2026. 9. 10.   교동·갯마을 공동판매조합 사무국', font=F(24), fill=(70, 70, 70))
dp.line((40, 145, 1140, 145), fill=(40, 40, 40), width=3)
hdr = ['품목', '거래 단위', '환산', '적용 기간']
colx = [40, 330, 560, 830]
y = 165
for x, t in zip(colx, hdr):
    dp.text((x + 8, y), t, font=F(28, True), fill=(0, 0, 0))
y += 50
table = [
    ('사과 (홍로·부사)', '1상자', '10kg', '9월 15일 영업일까지'),
    ('사과 (홍로·부사)', '1상자', '5kg', '9월 16일 영업일부터'),
    ('고춧가루', '1근', '600g', '9월 전체'),
    ('생강', '1근', '375g', '9월 전체'),
    ('배추', '1포기', '(중량 환산 없음)', '9월 전체'),
    ('고등어', '1손', '2마리', '9월 전체'),
    ('오징어', '1축', '20마리', '9월 전체'),
    ('오징어', '1미', '1마리', '9월 전체'),
    ('전어 · 꽃게', 'kg', '(그대로)', '9월 전체'),
]
for i, row in enumerate(table):
    if i % 2 == 0:
        dp.rectangle((40, y - 6, 1140, y + 50), fill=(238, 236, 224))
    for x, t in zip(colx, row):
        dp.text((x + 8, y), t, font=F(28), fill=(25, 25, 25))
    y += 58
dp.line((40, y, 1140, y), fill=(40, 40, 40), width=2)
y += 20
dp.text((40, y), '※ 사과는 9월 16일 영업일부터 5kg 소포장 상자로만 출하합니다.', font=F(25), fill=(150, 20, 20))
y += 42
dp.text((40, y), '※ 상자 수로 적힌 거래는 거래가 귀속되는 영업일의 상자 규격으로 환산합니다.', font=F(25), fill=(40, 40, 40))
y += 42
dp.text((40, y), '※ 영업일의 정의는 「정산 규정」 제4조를 따릅니다.', font=F(25), fill=(40, 40, 40))
paper = paper.rotate(-1.6, expand=True, fillcolor=(150, 108, 70), resample=Image.BICUBIC)
board.paste(paper, (150, 90))
dbd = ImageDraw.Draw(board)
for (px, py) in [(205, 120), (1260, 110)]:
    dbd.ellipse((px - 14, py - 14, px + 14, py + 14), fill=(200, 30, 30), outline=(90, 10, 10))
board = board.filter(ImageFilter.GaussianBlur(0.6))
# 비네팅
yy, xx = np.mgrid[0:H, 0:W]
vig = 1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
arr = (np.array(board).astype(np.float32) * vig[..., None]).clip(0, 255).astype(np.uint8)
Image.fromarray(arr).save(DATA / '게시판_공지_사진.jpg', quality=88)

# ---------- 9. 이미지 2 : 수기 장부 사진 ----------
W2, H2 = 1400, 1000
pg = Image.new('RGB', (W2, H2), (246, 241, 222))
dl = ImageDraw.Draw(pg)
for yy_ in range(150, H2, 60):
    dl.line((0, yy_, W2, yy_), fill=(170, 195, 220), width=2)
dl.line((95, 0, 95, H2), fill=(220, 120, 120), width=2)
dl.text((120, 40), '현장 수기 장부  —  9/23(수) 오후 단말기 장애 중 기록', font=F(38, True), fill=(25, 35, 90))
dl.text((120, 98), '(단말기 복구 후에도 내보내기 파일에는 안 들어감. 정산 때 반드시 합산!)', font=F(24), fill=(60, 60, 110))
cols = [120, 230, 350, 490, 660, 820, 990]
heads = ['번호', '시각', '마을', '조합원', '품목', '수량', '단가']
for x, t in zip(cols, heads):
    dl.text((x, 162), t, font=F(28, True), fill=(25, 35, 90))
yrow = 222
for r in L:
    vals = [r['tid'], r['kst'].strftime('%H:%M'), r['vil'], r['mem'], r['item'],
            f'{fmt_qty(r["qty10"])}{r["unit"]}', f'{r["price"]:,}']
    for x, t in zip(cols, vals):
        dl.text((x, yrow), t, font=F(30), fill=(30, 40, 100))
    if r['void']:
        dl.line((115, yrow + 22, 1180, yrow + 16), fill=(200, 20, 20), width=5)
        dl.text((1200, yrow - 4), '취소', font=F(34, True), fill=(200, 20, 20))
    yrow += 60
dl.text((120, yrow + 40), '기록: 사무장 윤', font=F(26), fill=(30, 40, 100))
pg = pg.rotate(2.2, expand=False, fillcolor=(60, 55, 50), resample=Image.BICUBIC)
arr = np.array(pg).astype(np.float32)
grad = np.linspace(1.0, 0.82, W2)[None, :, None]
arr = arr * grad + nrng.normal(0, 4, arr.shape)
pg = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
pg.save(DATA / '수기장부_0923.jpg', quality=85)

# ---------- 10. PDF : 정산 규정 ----------
doc = fitz.open()
ocg = doc.add_ocg('개정안(검토중)', on=False)


def page_with(lines, start_y=60):
    p = doc.new_page(width=595, height=842)
    p.insert_font(fontname='mg', fontfile=FONT)
    p.insert_font(fontname='mgb', fontfile=FONTB)
    y = start_y
    for t, sz, bold in lines:
        if t == '':
            y += sz; continue
        p.insert_text((50, y), t, fontname='mgb' if bold else 'mg', fontsize=sz)
        y += sz + 8
    return p, y


p1_lines = [
    ('교동·갯마을 공동판매조합 직거래장터 정산 규정', 17, True),
    ('제정 2025. 3. 1.  /  일부개정 2026. 9. 18.', 9, False),
    ('', 8, False),
    ('제1조(목적) 이 규정은 교동마을과 갯마을이 함께 운영하는 직거래장터의', 10.5, False),
    ('            거래 확정, 수수료 산정 및 월 정산 지급에 필요한 사항을 정한다.', 10.5, False),
    ('제2조(확정 거래) ① 단말기 내보내기 파일과 사무국 수기 장부에 기록된 거래를', 10.5, False),
    ('            모두 정산 대상으로 한다. 수기 장부에서 줄을 그어 취소한 거래는 제외한다.', 10.5, False),
    ('       ② 같은 거래번호가 두 번 이상 내보내진 경우 한 건으로 본다.', 10.5, False),
    ('제3조(수수료) ① 수수료율은 농산물(교동마을) 3%, 수산물(갯마을) 5%로 한다.', 10.5, False),
    ('       ② 수수료는 확정 거래 한 건마다 「수량 × 단가」에 수수료율을 곱하여 산정하고,', 10.5, False),
    ('            건별로 10원 미만은 버린다. 월 수수료는 건별 수수료의 합으로 한다.', 10.5, False),
    ('', 18, False),
    ('제4조(영업일) ① 장터의 영업일은 당일 06:00부터 다음 날 05:59까지로 한다.', 10.5, False),
    ('       ② 모든 거래는 위 기준에 따라 하나의 영업일에 귀속되며, 「9월」은', 10.5, False),
    ('            9월 1일 영업일부터 9월 30일 영업일까지를 말한다.', 10.5, False),
    ('       ③ 시각은 한국 표준시를 기준으로 판단한다.', 10.5, False),
    ('제5조(정정) ① 정정 거래는 그것이 가리키는 원거래를 대체하며, 대체된 원거래는', 10.5, False),
    ('            효력을 잃는다. 정정 거래를 다시 정정한 경우에도 같다.', 10.5, False),
    ('       ② 정정 거래는 기록된 시각과 관계없이 최초 원거래의 영업일에 귀속되며,', 10.5, False),
    ('            그 영업일의 환산 기준과 수수료율을 적용한다.', 10.5, False),
    ('제6조(단위 환산) 상자·근·손·축 등 거래 단위의 환산은 사무국 게시판 공지를 따른다.', 10.5, False),
    ('제7조(매출 및 지급) ① 매출은 확정 거래별 「수량 × 단가」의 합으로 한다.', 10.5, False),
    ('       ② 월 정산 지급액은 마을별로 「매출 - 수수료」로 한다.', 10.5, False),
]
p1, yend = page_with(p1_lines)
# 숨은 레이어(기본 꺼짐): 개정안 초안 — 화면/인쇄에는 안 보임
p1.insert_text((50, 262), '       ③ (개정안) 수산물 수수료율은 2026. 9. 1. 영업일부터 4%로 한다.', fontname='mg',
               fontsize=10.5, color=(0.1, 0.1, 0.6), oc=ocg)
p1.insert_text((50, 800), '- 1 -', fontname='mg', fontsize=9)
p2_lines = [
    ('부 칙', 14, True),
    ('', 6, False),
    ('제1조(시행일) 이 규정은 2025년 3월 1일부터 시행한다.', 10.5, False),
    ('', 8, False),
    ('부 칙 (2026. 9. 18. 개정)', 12, True),
    ('', 6, False),
    ('제1조(태풍 피해 어가 지원) 제3조제1항에도 불구하고, 갯마을 수산물의 수수료율은', 10.5, False),
    ('            2026년 9월 21일 영업일부터 3.5%로 한다.', 10.5, False),
    ('제2조(경과조치) 이 부칙 시행 전 영업일에 귀속되는 거래에는 종전 수수료율을 적용한다.', 10.5, False),
    ('', 30, False),
    ('교동·갯마을 공동판매조합 이사회', 11, True),
]
p2, _ = page_with(p2_lines, 70)
p2.insert_text((50, 800), '- 2 -', fontname='mg', fontsize=9)
doc.set_metadata({'title': '정산 규정', 'author': '공동판매조합 사무국'})
doc.subset_fonts()
doc.save(DATA / "정산규정_2026개정.pdf", garbage=4, deflate=True)
doc.close()

# ---------- 11. 메모 ----------
memo = """보낸사람: 윤해정 (사무장)
받는사람: 정산 담당
날짜: 2026-10-01 18:40
제목: 9월 장터 정산 자료 넘깁니다

담당자님, 9월 정산 자료 보내드립니다.

1) 9월_장터거래_내보내기.csv — 두 마을 단말기 내보내기 원본입니다.
   내보내기를 두 번 눌러서 같은 줄이 몇 개 겹쳐 들어갔을 수 있어요.
2) 수기장부_0923.jpg — 23일 오후 단말기 먹통일 때 제가 손으로 적은 장부 사진.
3) 게시판_공지_사진.jpg — 단위 환산표. 사과 상자는 원래 10kg짜리였죠.
4) 정산규정_2026개정.pdf — 지난주 이사회에서 부칙 붙은 최신본.
5) 조합원명부.xlsx

참, 갯마을 위판장 단말기는 작년에 업체가 설치하면서 시계를 협정세계시(UTC)로
맞춰 놓고 갔습니다. 그래서 갯마을 거래 시각은 한국 시각보다 9시간 느리게 찍혀요.
교동 단말기는 한국 시각 그대로고, 제 수기 장부도 한국 시각입니다.

조합원번호는 내보내기 때 앞에 K-, G- 가 빠지는 경우가 있는데 마을 칸 보시면 됩니다.

윤해정 드림
"""
(DATA / '사무장_메일.txt').write_text(memo, encoding='utf-8')

# ---------- 12. 정답·검증 기록 ----------
ans_out = {
    'Q1': ans['Q1'], 'Q2': f"{ans['Q2']:.1f}", 'Q3': ans['Q3'], 'Q4': ans['Q4'],
    'Q5': ans['Q5'], 'Q6': ans['Q6'],
}
(KEY / '정답.json').write_text(json.dumps(ans_out, ensure_ascii=False, indent=2), encoding='utf-8')
(KEY / '_q5_보기.json').write_text(json.dumps([o[0] for o in opts], ensure_ascii=False, indent=2), encoding='utf-8')
(KEY / '_오답값.json').write_text(json.dumps(naive, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print(json.dumps(ans_out, ensure_ascii=False))
print(json.dumps(naive, ensure_ascii=False, default=str, indent=1))
for o in opts:
    print(o)
print('csv rows', len(out), 'eff', len(eff))
