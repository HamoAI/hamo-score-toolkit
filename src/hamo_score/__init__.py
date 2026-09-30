"""hamo-score — client toolkit for the HamoAI/hamo-score-0.6b pulse-taking model.

Safe-by-default usage::

    from hamo_score import OllamaClient, score_message, update_stress, energy_state

    client = OllamaClient(model="hamo-score-0.6b")
    r = score_message(client, "今天试着出门散了个步")
    if r.crisis.triggered:
        ...  # route to your crisis pathway — scoring was skipped
    elif r.scores:
        stress = update_stress(r.scores, current_stress=3.0)
        state = energy_state(stress)  # cut-offs set on pre-v9 scores — re-tune for v9

From 0.2.0 the reference server serves v9, which changed what A and B mean;
scores are not comparable across the v7 → v9 boundary.
"""
from .client import OllamaClient, TransformersClient, ScoreResult, score_message
from .parse import parse_scores, DIMS
from .prompt import build_prompt, STUDENT_PROMPT
from .safety import CrisisGate, CrisisResult, DISCLOSURE_EN, DISCLOSURE_ZH
from .stress import energy_state, update_stress

__version__ = "0.2.0"
__all__ = [
    "OllamaClient", "TransformersClient", "ScoreResult", "score_message",
    "parse_scores", "DIMS", "build_prompt", "STUDENT_PROMPT",
    "CrisisGate", "CrisisResult", "DISCLOSURE_EN", "DISCLOSURE_ZH",
    "energy_state", "update_stress",
]
