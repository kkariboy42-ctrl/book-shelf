# Q1~Q6 주 경로. build_ledger.build() 의 행을 질의한다 (ledger_main.csv 와 같은 값).
import sys, json, collections
from datetime import date
from decimal import Decimal as D, ROUND_HALF_UP, ROUND_FLOOR
sys.path.insert(0, r'C:\Claude\book-shelf\ai-top-100\practice\mock01\_work\mock01\calc')
import build_ledger as B
sys.stdout.reconfigure(encoding='utf-8')
W = B.W
rows, first = B.build()
OK = [x for x in rows if x['확정여부']=='Y' and x['9월여부']=='Y']   # 확정 + 9월(귀속영업일 기준)
def fl10(v): return (v/10).to_integral_value(rounding=ROUND_FLOOR)*10
def r1(v): return v.quantize(D('0.1'), rounding=ROUND_HALF_UP)
alt = []   # alternatives.md 용 줄
ans = {}

# ---- Q1 (제4조·제5조②) ----
q1_rows = [x for x in OK if x['귀속영업일']==date(2026,9,15)]
ans['Q1'] = len(q1_rows)
print('Q1 (a) 귀속영업일(정정=원거래 영업일):', ans['Q1'], [x['거래ID'] for x in q1_rows])
q1b = [x for x in rows if x['확정여부']=='Y' and x['기록영업일']==date(2026,9,15)]
q1c = [x for x in rows if x['확정여부']=='Y' and x['_ts'].date()==date(2026,9,15)]
print('Q1 (b) 정정행은 자기 기록 영업일(T082=9/17):', len(q1b), [x['거래ID'] for x in q1b])
print('Q1 (c) 순진한 풀이: 찍힌 달력날짜(보정 없음):', len(q1c), [x['거래ID'] for x in q1c])
alt.append(('Q1', 'a 귀속=원거래 영업일 (규정 제5조②)', ans['Q1'], 'b 정정행을 자기 기록 영업일로', len(q1b), 'c 찍힌 달력날짜 그대로(참고)', len(q1c)))

# ---- Q2 ----
q2_rows = [x for x in OK if x['마을']=='교동' and x['품목표준']=='사과']
tot = sum(x['중량kg'] for x in q2_rows)
ans['Q2'] = str(r1(tot))
def kg_alt(x, mode):
    if x['단위표준']!='상자': return x['중량kg']
    if mode=='printed': d = x['_ts'].date()                      # 찍힌 날짜
    elif mode=='recorded': d = x['기록영업일']                    # 정정행 자기 영업일
    elif mode=='office': d = x['_ts'].date()
    else: return x['수량']*10                                    # 전부 10kg(메일)
    return x['수량']*(D(10) if d<=date(2026,9,15) else D(5))
q2b = sum(kg_alt(x,'printed') for x in q2_rows); q2c = sum(kg_alt(x,'recorded') for x in q2_rows); q2d = sum(kg_alt(x,'all10') for x in q2_rows)
q2e = sum(x['수량']*D(5) if x['단위표준']=='상자' else x['중량kg'] for x in q2_rows)
print('Q2 (a) 귀속영업일 규격 합 =', tot, '->', ans['Q2'])
print('Q2 (b) 찍힌 날짜 규격:', q2b, r1(q2b), '| (c) 정정행 자기 기록영업일 규격:', q2c, r1(q2c), '| (d) 전부10kg:', q2d, r1(q2d), '| (e) 전부5kg:', q2e, r1(q2e))
alt.append(('Q2','a 귀속영업일 규격(공지※2+제5조②)',ans['Q2'],'b 찍힌 날짜 규격',str(r1(q2b)),'c 정정행 자기 영업일 규격 / d 전부10kg(메일) / e 전부5kg',f'{r1(q2c)} / {r1(q2d)} / {r1(q2e)}'))
q2_lines = ['| ID | 원문 품목 | 수량 | 단위 | 찍힌시각 | KST | 귀속영업일 | 규격/계수 | kg |','|---|---|---|---|---|---|---|---|---|']
for x in sorted(q2_rows, key=lambda x:(x['귀속영업일'], x['거래ID'])):
    q2_lines.append(f"| {x['거래ID']} | {x['품목원문']} | {x['수량']} | {x['단위원문']} | {x['찍힌시각원문']} | {x['KST시각']} | {x['귀속영업일']} | {x['환산계수']} | {x['중량kg']} |")

# ---- Q3 ----
g = [x for x in OK if x['마을']=='갯마을']
ans['Q3'] = int(sum(x['수수료'] for x in g))
g_sum_floor = fl10(sum(x['_수수료_정확'] for x in g))
# 요율을 정정행 자기 기록 영업일로 (참고)
def rate_rec(x): return D('0.05') if x['기록영업일']<date(2026,9,21) else D('0.035')
q3c = sum(fl10(x['매출']*rate_rec(x)) for x in g)
q3d = sum(fl10(x['매출']*D('0.05')) for x in g)
q3_floor_none = sum(x['_수수료_정확'] for x in g)
print('Q3 (a) 건별 10원 버림 후 합:', ans['Q3'], '| (b) 합계 후 버림:', g_sum_floor, '(버림 전 정확값', q3_floor_none, ') | (c) 요율을 정정행 자기영업일로:', q3c, '| (d) 5% 일괄:', q3d)
alt.append(('Q3','a 건별 버림 후 합(제3조②)',ans['Q3'],'b 합계 후 버림',int(g_sum_floor),'c 정정행 요율을 자기 영업일로 / d 5% 일괄',f'{int(q3c)} / {int(q3d)}'))
q3_lines = ['| ID | 마을 | 귀속영업일 | 매출 | 요율 | 수수료 |','|---|---|---|---|---|---|']
for x in sorted(g, key=lambda x:(x['귀속영업일'], x['거래ID'])): q3_lines.append(f"| {x['거래ID']} | {x['마을']} | {x['귀속영업일']} | {x['매출']} | {x['수수료율']} | {x['수수료']} |")
print('Q3 요율 경계 행:', [(x['거래ID'], str(x['귀속영업일']), str(x['수수료율']), str(x['매출']), str(x['수수료'])) for x in g if x['거래ID'] in ('T098','T099','T100','T103','T106','T146','H02','H04')])

# ---- Q4 ----
q4_rows = [x for x in OK if x['마을']=='교동' and x['조합원번호4자리']=='0712']
ans['Q4'] = int(sum(x['매출'] for x in q4_rows))
print('Q4 교동 0712 확정 매출:', ans['Q4'], [(x['거래ID'], str(x['매출'])) for x in q4_rows])
print('   (참고) 두 마을 0712 합산:', int(sum(x['매출'] for x in OK if x['조합원번호4자리']=='0712')), '/ 이름 김순자 전체:', int(sum(x['매출'] for x in OK if x['성명']=='김순자')))

# ---- Q5 ----
tab = []
# 5-1
gin = [x for x in OK if x['마을']=='교동' and x['품목표준']=='생강']
gin_kg = sum(x['중량kg'] for x in gin)
tab.append((1,'교동 생강 24.375kg', f'{gin_kg}kg', gin_kg==D('24.375'), ','.join(x['거래ID'] for x in gin)))
# 5-2
sq = [x for x in OK if x['마을']=='갯마을' and x['품목표준']=='오징어']
sq_n = sum(x['마리수'] for x in sq)
by_unit = collections.defaultdict(lambda: D(0))
for x in sq: by_unit[x['단위표준']] += x['수량']
tab.append((2,'갯마을 오징어 344마리', f'{sq_n}마리 (단위별 원수량 {dict((k,str(v)) for k,v in by_unit.items())})', sq_n==344, ','.join(x['거래ID'] for x in sq)))
# 5-3
daily = collections.defaultdict(lambda: D(0))
for x in OK: daily[x['귀속영업일']] += x['매출']
top = sorted(daily.items(), key=lambda kv:-kv[1])
tab.append((3,'합산 매출 최대 영업일=9/15', f'최대 {top[0][0]} ({top[0][1]}), 2위 {top[1][0]} ({top[1][1]}), 9/15={daily[date(2026,9,15)]}', top[0][0]==date(2026,9,15), '영업일별 표 참조'))
# 5-4
g712 = [x for x in OK if x['마을']=='갯마을' and x['조합원번호4자리']=='0712']
tab.append((4,'갯마을 0712 확정 거래 22건', f'{len(g712)}건', len(g712)==22, ','.join(x['거래ID'] for x in g712)))
# 5-5
fee_k = int(sum(x['수수료'] for x in OK if x['마을']=='교동')); fee_g = ans['Q3']
tab.append((5,'수수료 갯마을 > 교동', f'갯마을 {fee_g} vs 교동 {fee_k}', fee_g>fee_k, '-'))
ans['Q5'] = ','.join(str(t[0]) for t in tab if t[3])
print('Q5 참거짓:', [(t[0], t[3], t[2]) for t in tab], '=>', ans['Q5'])
alt_q5 = {
 '5-1 중량을 600g(고춧가루값) 오적용 참고': str(sum(x['수량'] for x in gin)*D('0.6')),
 '5-1 수기 취소 H03 포함 시': str(gin_kg + D('4')*D('0.375')),
 '5-2 오징어 확정 전체(정정 원거래 포함,9월밖 제외 없이) 참고': str(sum(x['마리수'] for x in rows if x['품목표준']=='오징어' and x['마을']=='갯마을' and x['중복여부']=='N')),
 '5-4 갯마을 0712 (정정 원거래·9월밖 포함한 모든 고유 행 수)': len([x for x in rows if x['마을']=='갯마을' and x['조합원번호4자리']=='0712' and x['중복여부']=='N']),
}
print('Q5 참고값:', alt_q5)
with open(W+r'\calc\q5_table.md','w',encoding='utf-8') as f:
    f.write('# Q5 보기별 참/거짓 (주 경로)\n\n| 보기 | 주장 | 계산값 | 참/거짓 | 근거 행ID |\n|---|---|---|---|---|\n')
    for t in tab: f.write(f"| 5-{t[0]} | {t[1]} | {t[2]} | {'참' if t[3] else '거짓'} | {t[4]} |\n")
    f.write(f'\n**옳은 것: {ans["Q5"]}**\n\n## 5-3 영업일별 두 마을 합산 확정 매출 (귀속영업일 기준, 수기 포함)\n\n| 영업일 | 매출 |\n|---|---|\n')
    for d,v in sorted(daily.items()): f.write(f'| {d} | {v} |\n')
    f.write('\n상위 5일: '+', '.join(f'{d}={v}' for d,v in top[:5])+'\n')
    f.write('\n## 5-1 생강 행\n\n| ID | 품목원문 | 수량(근) | 귀속영업일 | kg |\n|---|---|---|---|---|\n')
    for x in gin: f.write(f"| {x['거래ID']} | {x['품목원문']} | {x['수량']} | {x['귀속영업일']} | {x['중량kg']} |\n")
    f.write('\n## 5-2 오징어 행\n\n| ID | 품목원문 | 수량 | 단위 | 귀속영업일 | 마리 |\n|---|---|---|---|---|---|\n')
    for x in sq: f.write(f"| {x['거래ID']} | {x['품목원문']} | {x['수량']} | {x['단위원문']} | {x['귀속영업일']} | {x['마리수']} |\n")
    f.write('\n## 5-4 갯마을 0712 행\n\n| ID | 출처 | 찍힌시각 | KST | 귀속영업일 | 비고 |\n|---|---|---|---|---|---|\n')
    for x in g712: f.write(f"| {x['거래ID']} | {x['출처']} | {x['찍힌시각원문']} | {x['KST시각']} | {x['귀속영업일']} | {x['정정대상ID'] and '정정→'+x['정정대상ID']} |\n")
    f.write('\n## 참고(오답 경로) 값\n\n'+'\n'.join(f'- {k}: {v}' for k,v in alt_q5.items())+'\n')
print('영업일별 매출 상위5:', [(str(d),str(v)) for d,v in top[:5]])

# ---- Q6 ----
def pay(v):
    rv = [x for x in OK if x['마을']==v]
    rev = sum(x['매출'] for x in rv); fee = sum(x['수수료'] for x in rv)
    return int(rev), int(fee), int(rev-fee)
kr, kf, kp = pay('교동'); gr, gf, gp = pay('갯마을')
ans['Q6'] = {'교동': kp, '갯마을': gp}
print('Q6 교동 매출/수수료/지급', kr, kf, kp, '| 갯마을', gr, gf, gp)
assert gf == ans['Q3']
print('Q6 일관성: 매출-수수료 =', kr-kf, gr-gf)

json.dump(ans, open(W+r'\calc\answers_main.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('ANSWERS', json.dumps(ans, ensure_ascii=False))

# ---- alternatives.md ----
with open(W+r'\calc\alternatives.md','w',encoding='utf-8') as f:
    f.write('# 정의가 갈리는 지점 — 두 해석 병기 (주 경로 계산)\n\n| 문항 | 해석 A (채택) | A 값 | 해석 B | B 값 | 그 밖 | 값 |\n|---|---|---|---|---|---|---|\n')
    for a in alt: f.write('| '+' | '.join(str(v) for v in a)+' |\n')
    f.write('\n채택 근거: Q1·Q2·Q3 모두 규정 제5조②(정정은 최초 원거래 영업일·환산 기준·수수료율), 공지 ※2(귀속 영업일의 상자 규격), 제3조②(건별 10원 미만 버림).\n')
    f.write('\n## Q1 두 해석 차이 행\n- A 만 포함: '+str(sorted(set(x['거래ID'] for x in q1_rows)-set(x['거래ID'] for x in q1b)))+'\n- B 만 포함: '+str(sorted(set(x['거래ID'] for x in q1b)-set(x['거래ID'] for x in q1_rows)))+'\n')
    f.write('\n## Q2 행별 내역 (해석 A)\n\n'+'\n'.join(q2_lines)+'\n')
    f.write('\n## Q3 행별 내역 (해석 A)\n\n'+'\n'.join(q3_lines)+'\n')

# ---- count_sheet.md ----
cand = [x for x in rows if x['중복여부']=='N' and (x['_ts'].date() in (date(2026,9,14),date(2026,9,15),date(2026,9,16),date(2026,9,17)) or x['기록영업일']==date(2026,9,15) or x['귀속영업일']==date(2026,9,15))]
cand.sort(key=lambda x: x['_kst'])
dupids = {x['거래ID'] for x in rows if x['중복여부']=='Y'}
def line(x, show_verdict=False):
    corr = f"정정→{x['정정대상ID']} (루트 {x['정정루트ID']})" if x['정정대상ID'] else ('원거래(정정으로 대체됨)' if x['대체됨여부']=='Y' else '')
    tz = 'UTC→+9h' if x['마을']=='갯마을' and x['출처']=='CSV' else ('KST' if x['출처']=='CSV' else 'KST(수기)')
    return f"| {x['거래ID']} | {x['마을']} | {x['찍힌시각원문']} | {tz} | {x['KST시각']} | {x['기록영업일']} | {corr} | {'중복줄있음' if x['거래ID'] in dupids else ''} |"
with open(W+r'\human\count_sheet.md','w',encoding='utf-8') as f:
    f.write('# 사람 세기용 표\n\n규칙(규정): 영업일 = KST 06:00 ~ 다음날 05:59 (06:00 정각은 당일). 갯마을 CSV 시각은 UTC라 +9시간 해야 KST. 수기·교동은 KST 그대로. 정정 거래는 기록 시각과 무관하게 최초 원거래의 영업일. 정정으로 대체된 원거래는 세지 않음. 같은 거래번호 중복 줄은 1건.\n\n')
    f.write('## Q1 — 9/15 영업일 후보 (찍힌 날짜 9/14~9/17 전 행 + 기록·귀속 영업일이 9/15인 행). 시각순 정렬\n\n사람이 「9/15 영업일에 귀속되고 대체되지 않은 거래」에 체크. 정정 행은 「루트」의 KST 시각으로 영업일을 판단(루트 시각은 아래 별표).\n\n| ID | 마을 | 원문 시각 | 보정 | KST | 기록 영업일 | 정정 여부 | 중복 | 사람 체크 |\n|---|---|---|---|---|---|---|---|---|\n')
    for x in cand: f.write(line(x).rstrip()+' [ ] |\n')
    roots = {x['정정루트ID'] for x in cand if x['정정대상ID']}
    f.write('\n정정 루트 행(영업일 판단 기준):\n\n| ID | 마을 | 원문 시각 | KST | 영업일 |\n|---|---|---|---|---|\n')
    for r in sorted(roots): f.write(f"| {r} | {first[r]['마을']} | {first[r]['찍힌시각원문']} | {first[r]['KST시각']} | {first[r]['기록영업일']} |\n")
    f.write(f'\n### (코드 판정 — 사람이 센 뒤에 열어볼 것) 9/15 귀속 확정: {ans["Q1"]}건\n'+', '.join(x['거래ID'] for x in q1_rows)+'\n')
    c4 = [x for x in rows if x['마을']=='갯마을' and x['조합원번호4자리']=='0712']
    f.write('\n## Q5-4 — 갯마을 0712(김순자, G-0712) 모든 행 (중복 줄은 한 줄로 표기)\n\n9월 영업일에 귀속 + 대체 안 됨 + 취소 아님 + 중복 1건 처리로 센다. 번호는 `0712`·`G-0712` 표기 혼재, 교동 K-0712 는 제외.\n\n| ID | 출처 | 원문 시각 | KST | 귀속 영업일 | 정정/대체 | 중복 | 사람 체크 |\n|---|---|---|---|---|---|---|---|\n')
    for x in sorted([x for x in c4 if x['중복여부']=='N'], key=lambda x:x['_kst']):
        corr = f"정정→{x['정정대상ID']}" if x['정정대상ID'] else ('원거래(대체됨)' if x['대체됨여부']=='Y' else '')
        f.write(f"| {x['거래ID']} | {x['출처']} | {x['찍힌시각원문']} | {x['KST시각']} | {x['귀속영업일']} | {corr} | {'중복줄있음' if x['거래ID'] in dupids else ''} | [ ] |\n")
    f.write(f'\n### (코드 판정) 갯마을 0712 확정 9월: {len(g712)}건\n'+', '.join(x['거래ID'] for x in g712)+'\n')
print('count_sheet 후보 Q1:', len(cand), '/ Q5-4 행:', len([x for x in rows if x['마을']=='갯마을' and x['조합원번호4자리']=='0712' and x['중복여부']=='N']))

# ---- 추가 민감도 (alternatives.md 에 덧붙임) ----
daily_b = collections.defaultdict(lambda: D(0))
for x in rows:
    if x['확정여부']=='Y' and date(2026,9,1)<=x['기록영업일']<=date(2026,9,30): daily_b[x['기록영업일']] += x['매출']
top_b = sorted(daily_b.items(), key=lambda kv:-kv[1])[:3]
with open(W+r'\calc\alternatives.md','a',encoding='utf-8') as f:
    f.write('\n## 연동되는 문항의 민감도\n')
    f.write(f'- Q5-3: 해석 B(정정행을 자기 기록 영업일로)이면 영업일별 상위3 = {[(str(d),str(v)) for d,v in top_b]} -> 최대일이 9/15 인지: {top_b[0][0]==date(2026,9,15)} (해석 A 에서는 9/15={daily[date(2026,9,15)]}, 2위 9/8={daily[date(2026,9,8)]})\n')
    f.write(f'- Q6 갯마을: A {gp} / Q3 해석 B(합계 후 버림) 적용 시 {gr-int(g_sum_floor)} / 정정행 요율을 자기 영업일로 시 {gr-int(q3c)}. 교동 {kp} 는 해석과 무관(3% 단일).\n')
    f.write(f'- Q5-5: 위 어느 해석에서도 갯마을({ans["Q3"]}/{int(g_sum_floor)}/{int(q3c)}) > 교동({kf}) 이라 불변.\n')
print('Q5-3 해석B 상위3', [(str(d),str(v)) for d,v in top_b])
