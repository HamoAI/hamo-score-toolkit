"""批量给聊天记录 CSV 打分：闸门 → 评分 → 平滑 → 状态桶，逐行落盘。

Batch-score a chat-log CSV through the full safe pipeline.

输入 CSV 至少一列 `message`；可选 `conversation_id`（分组维护各自的压力轨迹）。
输出 = 输入列 + crisis / A W E H B / stress / state。危机命中的行不评分（模型
根本不会被调用），只标 crisis 并原样透传——把这些行路由给人来处理。

用法:
    python examples/batch_csv.py chat_log.csv scored.csv
    python examples/batch_csv.py chat_log.csv scored.csv --model my-tag
    python examples/batch_csv.py chat_log.csv scored.csv --mock   # 无模型试跑管线
"""
import argparse
import csv
import sys

from hamo_score import OllamaClient, score_message, update_stress, energy_state


class MockClient:
    """No-model stand-in: returns a fixed benign score so you can see the pipeline shape."""
    def generate(self, prompt):
        return '{"A": 1.0, "W": 0.5, "E": 0.0, "H": 0.0, "B": 1.0}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--model", default="hamo-score-0.6b")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--start-stress", type=float, default=3.0)
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()

    client = MockClient() if args.mock else OllamaClient(
        base_url=args.base_url, model=args.model)

    with open(args.infile, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    if "message" not in fields:
        sys.exit("input CSV needs a `message` column")
    if not rows:
        sys.exit("input CSV has no data rows")

    stress_by_conv = {}  # per-conversation smoothed stress trajectory
    out_fields = fields + [c for c in ("crisis", "A", "W", "E", "H", "B", "stress", "state")
                           if c not in fields]
    n_crisis = n_invalid = 0

    with open(args.outfile, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for i, row in enumerate(rows, 1):
            row.pop(None, None)  # cells beyond the header would break the writer
            conv = row.get("conversation_id", "_")
            r = score_message(client, row["message"])
            if r.crisis.triggered:
                n_crisis += 1
                row["crisis"] = ";".join(r.crisis.matched)
            elif r.scores is None:
                n_invalid += 1
            else:
                row.update({d: r.scores[d] for d in "AWEHB"})
                stress = update_stress(r.scores,
                                       stress_by_conv.get(conv, args.start_stress))
                stress_by_conv[conv] = stress
                row["stress"] = round(stress, 2)
                row["state"] = energy_state(stress)
            w.writerow(row)
            if i % 50 == 0:
                print(f"  {i}/{len(rows)}", file=sys.stderr)

    print(f"{len(rows)} rows → {args.outfile}"
          f"  (crisis-gated: {n_crisis}, unparseable: {n_invalid})")
    if n_crisis:
        print("crisis-gated rows were NEVER sent to the model — route them to a human.")


if __name__ == "__main__":
    main()
