# L1: ledger_main.csv 생성 (주 경로). 규정 원문은 ../extract/rules.md
# 함정 처리: 갯마을 CSV 시각 +9h(메일), 수기는 KST 그대로 / 영업일=KST-6h의 날짜 / 정정 사슬 루트 귀속(제5조②) /
# 중복 거래번호 1건(제2조②) / 수기 취소 제외 / 가격 표기(₩,원,쉼표,만) / 시각 4형식+오전오후 / 품목·단위 정규화
import csv, re, sys, collections, pickle
from datetime import datetime, timedelta, date
from decimal import Decimal as D, ROUND_FLOOR
sys.stdout.reconfigure(encoding='utf-8')
W = r'C:\Claude\book-shelf\ai-top-100\practice\mock01\_work\mock01'
SRC = r'C:\Claude\book-shelf\ai-top-100\practice\mock01\problem\data\9월_장터거래_내보내기.csv'
NAMES = {('교동','0712'):'김순자',('교동','0217'):'김숙자',('교동','0315'):'박영철',('교동','0408'):'이말순',('교동','0521'):'최동훈',
         ('갯마을','0712'):'김순자',('갯마을','0205'):'정해룡',('갯마을','0330'):'윤바다',('갯마을','0419'):'한어진'}
ITEM = {'사과':'사과','사과(홍로)':'사과','사과 부사':'사과','홍로':'사과','부사':'사과','생강':'생강','생강(토종)':'생강',
        '고춧가루':'고춧가루','고추가루':'고춧가루','전어':'전어','햇전어':'전어','오징어':'오징어','물오징어':'오징어',
        '꽃게':'꽃게','숫꽃게':'꽃게','배추':'배추','고등어':'고등어'}
UNIT = {'kg':'kg','Kg':'kg','KG':'kg','키로':'kg','상자':'상자','박스':'상자','box':'상자','BOX':'상자',
        '근':'근','손':'손','축':'축','미':'미','마리':'마리','포기':'포기'}
def parse_ts(s):
    s=s.strip()
    m=re.fullmatch(r'(\d{4})[./-](\d\d)[./-](\d\d) (?:(오전|오후) )?(\d{1,2}):(\d\d)(?::(\d\d))?',s)
    assert m, s
    y,mo,d,ap,h,mi,se=m.groups(); h=int(h)
    if ap=='오후' and h<12: h+=12
    if ap=='오전' and h==12: h=0
    return datetime(int(y),int(mo),int(d),h,int(mi),int(se or 0))
def parse_price(s):
    t=s.strip().replace('₩','').replace('원','').replace(',','')
    if t.endswith('만'): return D(t[:-1])*10000
    assert re.fullmatch(r'\d+',t), s
    return D(t)
def bday(kst): return (kst-timedelta(hours=6)).date()

def build():
    rows=[]
    raw=list(csv.DictReader(open(SRC,encoding='utf-8-sig')))
    seen=set()
    for i,r in enumerate(raw,1):
        tid=r['거래번호']; dup='Y' if tid in seen else 'N'
        if dup=='Y':
            prev=[x for x in rows if x['거래ID']==tid][0]
            assert prev['_raw']==tuple(r.values()), ('중복 줄이 완전히 같지 않음',tid)
        seen.add(tid)
        ts=parse_ts(r['일시(단말기)'])
        kst=ts+timedelta(hours=9) if r['마을']=='갯마을' else ts
        note=r['비고'].strip()
        tgt=''
        if '정정' in note:
            tgt=re.search(r'T\d+',note).group(0)
        num=re.sub(r'^[KG]-','',r['조합원번호'].strip()); assert len(num)==4
        rows.append(dict(거래ID=tid,출처='CSV',원본행번호=i+1,마을=r['마을'],조합원번호4자리=num,성명=NAMES[(r['마을'],num)],
            품목원문=r['품목'],품목표준=ITEM[r['품목']],수량=D(r['수량']),단위원문=r['단위'],단위표준=UNIT[r['단위']],
            단가원문=r['단가'],단가=parse_price(r['단가']),찍힌시각원문=r['일시(단말기)'],_ts=ts,_kst=kst,
            정정대상ID=tgt,중복여부=dup,취소여부='N',비고=note,_raw=tuple(r.values())))
    for r in csv.DictReader(open(W+r'\extract\handbook_final.csv',encoding='utf-8-sig')):
        hh,mm=map(int,r['시각'].split(':')); ts=datetime(2026,9,23,hh,mm)
        num=re.sub(r'^[KG]-','',r['조합원'])
        rows.append(dict(거래ID=r['번호'],출처='수기',원본행번호=r['번호'],마을=r['마을'],조합원번호4자리=num,성명=NAMES[(r['마을'],num)],
            품목원문=r['품목'],품목표준=ITEM[r['품목']],수량=D(r['수량']),단위원문=r['수량단위'],단위표준=UNIT[r['수량단위']],
            단가원문=r['단가'],단가=D(r['단가']),찍힌시각원문='2026-09-23 '+r['시각'],_ts=ts,_kst=ts,
            정정대상ID='',중복여부='N',취소여부=r['취소여부'],비고='',_raw=None))
    first={}
    for x in rows: first.setdefault(x['거래ID'],x)
    replaced=set(x['정정대상ID'] for x in rows if x['정정대상ID'])
    def root(tid):
        seenr=[]
        while first[tid]['정정대상ID']:
            tid=first[tid]['정정대상ID']; assert tid not in seenr; seenr.append(tid)
        return tid
    for x in rows:
        x['매출']=x['수량']*x['단가']
        x['KST시각']=x['_kst'].strftime('%Y-%m-%d %H:%M')
        x['기록영업일']=bday(x['_kst'])
        x['정정루트ID']=root(x['거래ID']) if x['정정대상ID'] else x['거래ID']
        x['귀속영업일']=bday(first[x['정정루트ID']]['_kst'])
        x['9월여부']='Y' if date(2026,9,1)<=x['귀속영업일']<=date(2026,9,30) else 'N'
        x['대체됨여부']='Y' if x['거래ID'] in replaced else 'N'
        x['확정여부']='Y' if (x['중복여부']=='N' and x['대체됨여부']=='N' and x['취소여부']=='N') else 'N'
        u,it,q=x['단위표준'],x['품목표준'],x['수량']
        coef='';kg='';mari=''
        if u=='상자':
            coef=D(10) if x['귀속영업일']<=date(2026,9,15) else D(5); kg=q*coef
        elif u=='근':
            coef={'고춧가루':D('0.6'),'생강':D('0.375')}[it]; kg=q*coef
        elif u=='kg': coef=D(1); kg=q
        if it=='고등어' and u=='손': coef=D(2); mari=q*2
        if it=='오징어':
            coef=D(20) if u=='축' else D(1); mari=q*coef
        x['환산계수']=coef; x['중량kg']=kg; x['마리수']=mari
        if x['마을']=='교동': rate=D('0.03')
        else: rate=D('0.05') if x['귀속영업일']<date(2026,9,21) else D('0.035')
        x['수수료율']=rate
        f=x['매출']*rate
        x['수수료']=(f/10).to_integral_value(rounding=ROUND_FLOOR)*10
        x['_수수료_정확']=f
    return rows, first

OUT=['거래ID','출처','원본행번호','마을','조합원번호4자리','성명','품목원문','품목표준','수량','단위원문','단위표준','단가원문','단가','매출',
     '찍힌시각원문','KST시각','기록영업일','정정대상ID','정정루트ID','귀속영업일','9월여부','중복여부','대체됨여부','취소여부','확정여부',
     '환산계수','중량kg','마리수','수수료율','수수료']

if __name__=='__main__':
    rows,first=build()
    with open(W+r'\calc\ledger_main.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(OUT)
        for x in rows: w.writerow([x[k] for k in OUT])
    print('CSV 원본 줄',sum(1 for x in rows if x['출처']=='CSV'),'/ 중복 줄',sum(x['중복여부']=='Y' for x in rows),
          '/ 고유',len(set(x['거래ID'] for x in rows if x['출처']=='CSV')))
    print('수기',sum(x['출처']=='수기' for x in rows),'취소',sum(x['취소여부']=='Y' for x in rows))
    rep=sorted(set(x['거래ID'] for x in rows if x['대체됨여부']=='Y')); print('대체된 원거래',len(rep),rep)
    assert set(rep)=={'T026','T039','T029','T052','T081','T096','T068','T142'}
    print('단가<=0:',sum(x['단가']<=0 for x in rows),'/ 수량<=0:',sum(x['수량']<=0 for x in rows),'/ 매출 정수아님:',sum(x['매출']!=x['매출'].to_integral_value() for x in rows),'/ 시각·단가 파싱 실패 0 (assert 통과)')
    print('품목표준',dict(collections.Counter(x['품목표준'] for x in rows))); print('단위표준',dict(collections.Counter(x['단위표준'] for x in rows)))
    print('사과 단위원문',dict(collections.Counter(x['단위원문'] for x in rows if x['품목표준']=='사과')))
    print('확정&9월',sum(x['확정여부']=='Y' and x['9월여부']=='Y' for x in rows),'/ 확정이나 9월밖',[x['거래ID'] for x in rows if x['확정여부']=='Y' and x['9월여부']=='N'])
    print('정정사슬(행->루트)',{x['거래ID']:x['정정루트ID'] for x in rows if x['정정대상ID']})
    EXP={'T001':(8,31),'T002':(8,31),'T004':(9,1),'T066':(9,15),'T067':(9,15),'T069':(9,15),'T071':(9,15),'T072':(9,15),'T073':(9,16),'T074':(9,16),
         'T082':(9,15),'T098':(9,20),'T099':(9,20),'T100':(9,21),'T103':(9,21),'T106':(9,20),'T144':(9,30),'T145':(10,1),'T146':(9,30),
         'H01':(9,23),'H02':(9,23),'H03':(9,23),'H04':(9,23),'H05':(9,23)}
    for t,(m,d) in EXP.items():
        assert first[t]['귀속영업일']==date(2026,m,d),(t,first[t]['귀속영업일'])
    print('경계행 assert',len(EXP),'행 일치')
    print('06:00 근접(05:30~06:30 KST):',[(x['거래ID'],x['KST시각'],str(x['기록영업일'])) for x in rows if x['중복여부']=='N' and 330<=x['_kst'].hour*60+x['_kst'].minute<=390])
    for n in ['시식 행사','현금','단골','택배','카드']:
        print('비고',n,[x['거래ID'] for x in rows if x['비고']==n and x['중복여부']=='N'])
