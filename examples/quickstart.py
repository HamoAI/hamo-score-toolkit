"""10 行跑通：闸门 → 评分 → 平滑 → 状态桶。前置：ollama 已装载 hamo-score-0.6b。"""
from hamo_score import OllamaClient, score_message, update_stress, energy_state

client = OllamaClient(model="hamo-score-0.6b")
r = score_message(client, "虽然还是有点提不起劲，不过今天把拖了两周的体检约上了")
if r.crisis.triggered:
    print("危机闸门触发，转人工:", r.crisis.matched)
elif r.scores:
    stress = update_stress(r.scores, current_stress=3.0)
    print(r.scores, "→ 压力", round(stress, 2), "→", energy_state(stress))
