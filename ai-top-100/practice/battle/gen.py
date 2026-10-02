"""연습용 가짜 「전투 시뮬레이션」 문제 생성기 (2025 예선 4번 모양).

숨긴 규칙을 심은 데이터를 만든다. 풀이 쪽(toolkit/set_battle.py)은 이 파일을 열어 보지 않고
train.json 만 보고 규칙을 찾아내야 한다. truth.json 은 채점용 — 풀기 전에 보지 말 것.

  py -3 gen.py                # train.json · test.json · truth.json 생성 (seed 7)
  py -3 gen.py --seed 11      # 다른 판

숨긴 규칙 (스포일러 — 연습 끝나고 확인)
  - 기본 전력 차이
  - 5종 상성 순환: 각 타입은 순환에서 다음 두 타입을 이긴다
  - 전방/후방: 「자기 팀 중심을 지나고 두 중심 연결선에 수직인 선」 기준 (2025 문제 그림 방식, 글의 「수직이등분선」과 다름)
    · dgreg 는 전방일 때 강하고, cbene 는 후방일 때 강하다
  - 진형: x 방향으로 긴 팀이 약간 유리
  - 팀이 뭉칠수록 약간 유리
  - 잡음
"""
import argparse
import json
import random

import numpy as np

TYPES = ["eyanoo", "bras", "cbene", "aleo", "dgreg"]
CYCLE = ["aleo", "eyanoo", "dgreg", "bras", "cbene"]  # 각자 다음 두 개를 이긴다
BASE = {"eyanoo": 1.0, "bras": 1.05, "cbene": 0.95, "aleo": 1.15, "dgreg": 1.0}
FRONT_BONUS = {"dgreg": +0.7, "cbene": -0.5}
COUNTER = 0.9
X_LONG = 0.35
COHESION = -0.04  # 평균 거리 1 늘 때마다
NOISE = 0.45


def beats(a, b):
    return (CYCLE.index(b) - CYCLE.index(a)) % 5 in (1, 2)


def front_own(team, enemy):
    """자기 중심을 지나 연결선에 수직인 선 기준, 상대 쪽이면 전방."""
    c, e = team.mean(0), enemy.mean(0)
    return (team - c) @ (e - c) > 0


def strength(types, pos, etypes, epos, rng_unused=None):
    front = front_own(pos, epos)
    s = 0.0
    for t, f in zip(types, front):
        s += BASE[t] + (FRONT_BONUS.get(t, 0) if f else 0)
        s += COUNTER * sum(beats(t, et) for et in etypes) / len(etypes)
        s -= COUNTER * sum(beats(et, t) for et in etypes) / len(etypes) * 0.5
    sx, sy = pos[:, 0].std(), pos[:, 1].std()
    if len(types) > 1:
        s += X_LONG * len(types) * (1 if sx > sy else -1) * 0.5
        d = np.mean([np.linalg.norm(a - b) for i, a in enumerate(pos) for b in pos[i + 1:]])
        s += COHESION * d * len(types)
    return s


def make(rng, n, prefix):
    out, truth = [], {}
    for k in range(n):
        size = rng.choice([1, 1, 2, 2, 3, 4])
        while True:
            bt = [rng.choice(TYPES) for _ in range(size)]
            rt = [rng.choice(TYPES) for _ in range(size)]
            # 두 팀을 대략 마주 보게 배치
            ang = rng.uniform(0, 2 * np.pi)
            dvec = np.array([np.cos(ang), np.sin(ang)])
            bc = np.array([10.5, 10.5]) - dvec * rng.uniform(2, 5) + rng.normal(0, 1.5, 2)
            rc = np.array([10.5, 10.5]) + dvec * rng.uniform(2, 5) + rng.normal(0, 1.5, 2)
            spread = rng.uniform(0.5, 4)
            bp = np.clip(np.round(bc + rng.normal(0, spread, (size, 2))), 1, 20)
            rp = np.clip(np.round(rc + rng.normal(0, spread, (size, 2))), 1, 20)
            if size == 1 or (len({tuple(p) for p in bp}) == size and len({tuple(p) for p in rp}) == size):
                break
        sb = strength(bt, bp, rt, rp) + rng.normal(0, NOISE)
        sr = strength(rt, rp, bt, bp) + rng.normal(0, NOISE)
        bid = f"{prefix}_{k + 1:04d}"
        rec = {
            "id": bid,
            "blue": [{"type": t, "x": int(p[0]), "y": int(p[1])} for t, p in zip(bt, bp)],
            "red": [{"type": t, "x": int(p[0]), "y": int(p[1])} for t, p in zip(rt, rp)],
        }
        w = "blue" if sb > sr else "red"
        truth[bid] = w
        out.append(rec)
    return out, truth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--train", type=int, default=4000)
    ap.add_argument("--test", type=int, default=1000)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    random.seed(a.seed)
    tr, trt = make(rng, a.train, "train")
    for r in tr:
        r["winner"] = trt[r["id"]]
    te, tet = make(rng, a.test, "test")
    json.dump(tr, open("train.json", "w"), indent=1)
    json.dump(te, open("test.json", "w"), indent=1)
    json.dump({"test_winner": tet, "cycle": CYCLE, "front_bonus": FRONT_BONUS, "base": BASE,
               "front_definition": "own-center line", "x_long_better": True},
              open("truth.json", "w"), indent=1)
    print(f"train {len(tr)} · test {len(te)} 생성 (blue 승 {sum(r['winner'] == 'blue' for r in tr)}/{len(tr)})")


if __name__ == "__main__":
    main()
