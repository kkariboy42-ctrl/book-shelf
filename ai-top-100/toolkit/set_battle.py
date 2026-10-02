"""「두 팀 유닛 배치 → 승패」 데이터 풀이기 (2025 예선 4번 「전투 시뮬레이션」 유형).

한 번 돌리면 ① 문항형 질문에 쓸 통계 보고서 ② K-fold 로 고른 모델의 test 예측 JSON 이 나온다.
숫자를 AI 머릿속에 맡기지 않기 위한 도구다. 보고서의 숫자로 객관식을 고른다.

  py -3 set_battle.py train.json                       # 보고서만
  py -3 set_battle.py train.json --test test.json -o pred.json
  py -3 set_battle.py train.json --combo aleo+dgreg bras+eyanoo   # 조합 대 조합 전적

데이터 모양이 다르면 load() 만 고친다. 기대하는 모양:
  [{"id":..., "blue":[{"type","x","y"},...], "red":[...], "winner":"blue"|"red"}, ...]

전방/후방은 두 정의로 다 계산한다(2025 문제는 글과 그림이 달랐다).
  bisector : 두 팀 중심의 수직이등분선 기준, 상대 쪽 반평면이면 전방   ← 문제 글
  own      : 자기 팀 중심을 지나고 연결선에 수직인 선 기준             ← 문제 그림
두 정의에서 답이 같으면 안심, 다르면 그림·예시와 맞는 쪽을 고르고 근거를 적는다.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np

CENTER = np.array([10.5, 10.5])


# ── 읽기 ────────────────────────────────────────────────────────────────
def load(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = next(v for v in data.values() if isinstance(v, list))
    out = []
    for r in data:
        def team(us):
            return [u["type"] for u in us], np.array([[u["x"], u["y"]] for u in us], float)
        bt, bp = team(r["blue"])
        rt, rp = team(r["red"])
        out.append({"id": r["id"], "bt": bt, "bp": bp, "rt": rt, "rp": rp, "winner": r.get("winner")})
    return out


# ── 기하 ────────────────────────────────────────────────────────────────
def front(pos, epos, how):
    c, e = pos.mean(0), epos.mean(0)
    origin = (c + e) / 2 if how == "bisector" else c
    return (pos - origin) @ (e - c) > 1e-9


def spread(pos):
    return pos[:, 0].std(), pos[:, 1].std(), np.ptp(pos[:, 0]), np.ptp(pos[:, 1])


def cohesion(pos):
    if len(pos) < 2:
        return 0.0
    return float(np.mean([np.linalg.norm(a - b) for a, b in combinations(pos, 2)]))


def sides(b):
    """(내 타입, 내 좌표, 상대 타입, 상대 좌표, 이겼나) 를 두 팀 각각."""
    yield b["bt"], b["bp"], b["rt"], b["rp"], b["winner"] == "blue"
    yield b["rt"], b["rp"], b["bt"], b["bp"], b["winner"] == "red"


def rate(w, n):
    return f"{w / n:6.1%} ({w}/{n})" if n else "   -   (0)"


# ── 보고서 ───────────────────────────────────────────────────────────────
def report(B, types):
    print(f"전투 {len(B)}개 · 타입 {types}")
    sizes = Counter(len(b["bt"]) for b in B)
    print("팀 크기 분포:", dict(sorted(sizes.items())), "· blue 승률", rate(sum(b["winner"] == "blue" for b in B), len(B)))

    print("\n[1] 1:1 타입별 승률")
    one = [b for b in B if len(b["bt"]) == 1 and len(b["rt"]) == 1]
    w, n = Counter(), Counter()
    for b in one:
        for t, _, _, _, win in sides(b):
            n[t[0]] += 1
            w[t[0]] += win
    for t in sorted(types, key=lambda t: -w[t] / max(n[t], 1)):
        print(f"   {t:8} {rate(w[t], n[t])}")

    print("\n[2] 1:1 상성표 — 행이 열을 이긴 비율 (같은 타입끼리는 -)")
    pw, pn = defaultdict(int), defaultdict(int)
    for b in one:
        a, c = b["bt"][0], b["rt"][0]
        if a == c:
            continue
        pn[a, c] += 1
        pn[c, a] += 1
        pw[(a, c) if b["winner"] == "blue" else (c, a)] += 1
    print("   " + " " * 8 + "".join(f"{t:>9}" for t in types))
    for a in types:
        cells = "".join(f"{'-':>9}" if a == c else f"{pw[a, c] / pn[a, c] if pn[a, c] else float('nan'):9.0%}" for c in types)
        print(f"   {a:8}{cells}")
    print("   우위 관계 (60% 이상, 10전 이상):")
    for a in types:
        for c in types:
            if a != c and pn[a, c] >= 10 and pw[a, c] / pn[a, c] >= 0.6:
                print(f"     {a} > {c}  {rate(pw[a, c], pn[a, c])}")

    for how in ("bisector", "own"):
        print(f"\n[3-{how}] 전방/후방 승률 (팀 2명 이상, 정의={how})")
        fw, fn = Counter(), Counter()
        for b in B:
            if len(b["bt"]) < 2:
                continue
            for t, p, et, ep, win in sides(b):
                for ty, f in zip(t, front(p, ep, how)):
                    fn[ty, f] += 1
                    fw[ty, f] += win
        rows = []
        for ty in types:
            fr = fw[ty, True] / max(fn[ty, True], 1)
            bk = fw[ty, False] / max(fn[ty, False], 1)
            rows.append((abs(fr - bk), ty, fr, bk, fn[ty, True], fn[ty, False]))
        for d, ty, fr, bk, nf, nb in sorted(rows, reverse=True):
            print(f"   {ty:8} 전방 {fr:6.1%}(n={nf:4}) 후방 {bk:6.1%}(n={nb:4})  차이 {fr - bk:+6.1%}")

    print("\n[4] 진형 — x로 긴 팀 vs y로 긴 팀 (팀 2명 이상)")
    for label, idx in (("표준편차", (0, 1)), ("범위", (2, 3))):
        w, n = Counter(), Counter()
        for b in B:
            if len(b["bt"]) < 2:
                continue
            for t, p, et, ep, win in sides(b):
                s = spread(p)
                if s[idx[0]] == s[idx[1]]:
                    continue
                k = "x형" if s[idx[0]] > s[idx[1]] else "y형"
                n[k] += 1
                w[k] += win
        print(f"   기준={label}: x형 {rate(w['x형'], n['x형'])} · y형 {rate(w['y형'], n['y형'])}")

    print("\n[5] 경향 — 한 전투 안에서 두 팀을 비교")
    for name, f, better in (
        ("더 뭉친 팀(유닛 간 평균 거리 작음)", cohesion, "작은"),
        ("중심이 (10.5,10.5)에 더 가까운 팀", lambda p: float(np.linalg.norm(p.mean(0) - CENTER)), "작은"),
    ):
        w = n = 0
        for b in B:
            if len(b["bt"]) < 2:
                continue
            vb, vr = f(b["bp"]), f(b["rp"])
            if abs(vb - vr) < 1e-9:
                continue
            n += 1
            w += (vb < vr) == (b["winner"] == "blue")
        print(f"   {name}이 이긴 비율 {rate(w, n)}  (50%에서 멀수록 경향이 강함)")

    print("\n[6] 크기별 조합 승률 상위·하위 (10전 이상)")
    for size in sorted(sizes):
        if size < 2:
            continue
        w, n = Counter(), Counter()
        for b in B:
            if len(b["bt"]) != size:
                continue
            for t, _, _, _, win in sides(b):
                k = "+".join(sorted(t))
                n[k] += 1
                w[k] += win
        ok = [(w[k] / n[k], k) for k in n if n[k] >= 10]
        if ok:
            ok.sort(reverse=True)
            show = ok[:3] + ([("…", "")] if len(ok) > 6 else []) + ok[-3:] if len(ok) > 6 else ok
            print(f"   {size}:{size}  " + " · ".join(f"{k} {r:.0%}" if k else "…" for r, k in show))


def combo(B, a, b):
    A, Bk = sorted(a.split("+")), sorted(b.split("+"))
    w = n = 0
    for x in B:
        bt, rt = sorted(x["bt"]), sorted(x["rt"])
        if (bt, rt) == (A, Bk):
            n += 1
            w += x["winner"] == "blue"
        elif (bt, rt) == (Bk, A):
            n += 1
            w += x["winner"] == "red"
    print(f"{a} vs {b}: {w}승 {n - w}패 ({n}전)")


# ── 특징·모델 ─────────────────────────────────────────────────────────────
def team_vec(t, p, et, ep, types):
    k = len(types)
    idx = {ty: i for i, ty in enumerate(types)}
    n = np.zeros(k)
    fo = np.zeros(k)
    fb = np.zeros(k)
    for ty, f1, f2 in zip(t, front(p, ep, "own"), front(p, ep, "bisector")):
        n[idx[ty]] += 1
        fo[idx[ty]] += f1
        fb[idx[ty]] += f2
    en = np.zeros(k)
    for ty in et:
        en[idx[ty]] += 1
    cross = np.outer(n, en).ravel() / max(len(et), 1)  # 내 i 타입 × 상대 j 타입
    sx, sy, rx, ry = spread(p)
    geo = [sx, sy, float(sx > sy) - float(sy > sx), rx, ry, cohesion(p),
           float(np.linalg.norm(p.mean(0) - CENTER)), len(t)]
    return np.concatenate([n, fo, fb, cross, geo])


def features(B, types):
    """대칭 특징: f(blue 관점) - f(red 관점). 팀을 바꾸면 부호만 바뀐다."""
    X = np.array([team_vec(b["bt"], b["bp"], b["rt"], b["rp"], types)
                  - team_vec(b["rt"], b["rp"], b["bt"], b["bp"], types) for b in B])
    size = np.array([[len(b["bt"])] for b in B], float)
    return np.hstack([X, size])


def fit_predict(B, T, types, folds=5, seed=0):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    X = features(B, types)
    y = np.array([b["winner"] == "blue" for b in B], int)
    # 팀 바꾸기 증강: 특징 부호 반전(크기 열 제외) + 라벨 반전
    Xs = X.copy()
    Xs[:, :-1] *= -1
    Xa, ya = np.vstack([X, Xs]), np.concatenate([y, 1 - y])

    models = {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)),
        "hgb": HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=seed),
    }
    cv = StratifiedKFold(folds, shuffle=True, random_state=seed)
    scores = {}
    print(f"\n[모델] {folds}-fold 정확도 (증강은 학습 폴드 안에서만)")
    for name, m in models.items():
        accs = []
        for tr, va in cv.split(X, y):
            Xt = np.vstack([X[tr], Xs[tr]])
            yt = np.concatenate([y[tr], 1 - y[tr]])
            m.fit(Xt, yt)
            accs.append((m.predict(X[va]) == y[va]).mean())
        scores[name] = float(np.mean(accs))
        print(f"   {name:9} {scores[name]:.3f} ± {np.std(accs):.3f}")
    best = max(scores, key=scores.get)
    print(f"   → {best} 선택")
    if T is None:
        return None, scores
    m = models[best].fit(Xa, ya)
    XT = features(T, types)
    p = m.predict_proba(XT)[:, 1]
    # 대칭 보정: 팀을 바꿔 넣은 예측과 평균
    XTs = XT.copy()
    XTs[:, :-1] *= -1
    p = (p + (1 - m.predict_proba(XTs)[:, 1])) / 2
    return [{"id": t["id"], "winner": "blue" if q >= 0.5 else "red"} for t, q in zip(T, p)], scores


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("train")
    ap.add_argument("--test")
    ap.add_argument("-o", "--out")
    ap.add_argument("--combo", nargs=2, metavar=("A", "B"))
    ap.add_argument("--no-report", action="store_true")
    a = ap.parse_args()
    B = load(a.train)
    types = sorted({t for b in B for t in b["bt"] + b["rt"]})
    if a.combo:
        return combo(B, *a.combo)
    if not a.no_report:
        report(B, types)
    T = load(a.test) if a.test else None
    preds, _ = fit_predict(B, T, types)
    if preds and a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(preds, f, ensure_ascii=False, indent=2)
        print(f"저장: {a.out} ({len(preds)}개) → check_format.py json {a.out} --keys id,winner --allow winner=blue,red --ids {a.test}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
