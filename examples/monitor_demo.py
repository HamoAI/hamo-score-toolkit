"""极简会话监测 demo：一段脚本化对话走完整管线，含危机短路演示。

Minimal session-monitoring demo. Feeds a scripted mini-session through
gate → score → smooth → bucket and prints the stress trajectory — including
the one message the crisis gate short-circuits before the model ever sees it.

用法:
    python examples/monitor_demo.py            # 需要 ollama 已装载 hamo-score-0.6b
    python examples/monitor_demo.py --mock     # 无模型试跑（固定假分数，看管线形状）
"""
import argparse
import itertools

from hamo_score import (DISCLOSURE_ZH, OllamaClient, energy_state,
                        score_message, update_stress)

SESSION = [
    "这周工作太多了，天天加班",
    "昨晚只睡了四个小时，脑子完全转不动",
    "我真的不想活了",                      # ← 闸门在这里短路，模型不会看到这句
    "算了不说这个了，说点别的吧",
    "其实今天把拖了很久的体检约上了",
]

MOCK_SCORES = itertools.cycle(['{"A": 0.5, "W": 1.0, "E": 1.0, "H": 0.0, "B": 1.0}',
                    '{"A": 0.0, "W": 1.5, "E": 1.5, "H": 0.0, "B": 0.5}',
                    '{"A": 0.5, "W": 1.0, "E": 0.5, "H": 0.0, "B": 1.0}',
                    '{"A": 2.0, "W": 0.5, "E": 0.0, "H": 0.0, "B": 1.5}'])


class MockClient:
    def generate(self, prompt):
        return next(MOCK_SCORES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="hamo-score-0.6b")
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    client = MockClient() if args.mock else OllamaClient(model=args.model)

    stress, history = 3.0, []
    print(f"{'message':<24} {'scores':<34} {'stress':>6}  state")
    print("-" * 78)
    for msg in SESSION:
        r = score_message(client, msg, history=history[-3:])
        if r.crisis.triggered:
            # 短路：不评分、不更新压力、不进 history——危机原文连后续上下文都不进
            print(f"{msg:<24} ⛔ CRISIS GATE → human handoff (matched: {r.crisis.matched[0]})")
            print(f"{'':<24} → {DISCLOSURE_ZH}")
            continue
        if r.scores:
            stress = update_stress(r.scores, stress)
            s = " ".join(f"{d}{r.scores[d]}" for d in "AWEHB")
            print(f"{msg:<24} {s:<34} {stress:>6.2f}  {energy_state(stress)}")
        history.append({"role": "user", "content": msg})

    print("-" * 78)
    print("注意：危机那一句没有分数、也没有推动压力轨迹——它从未抵达模型。")
    print("Note: the crisis line has no score and never moved the trajectory — "
          "it never reached the model.")


if __name__ == "__main__":
    main()
