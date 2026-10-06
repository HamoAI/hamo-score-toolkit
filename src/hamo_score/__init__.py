"""hamo-score — client toolkit for the HamoAI/hamo-score-0.6b pulse-taking model.

Safe-by-default usage::

    from hamo_score import OllamaClient, score_message, update_stress, energy_state

    client = OllamaClient(model="hamo-score-0.6b")
    r = score_message(client, "今天试着出门散了个步")
    if r.crisis.triggered:
        ...  # route to your crisis pathway — scoring was skipped
    elif r.scores:
        stress = update_stress(r.scores, current_stress=3.0)
        state = energy_state(stress)  # cut-offs were set on legacy-rubric scores — see stress.py

From 0.3.0 the reference server serves v10. Scores are not comparable across
model versions: A changed meaning at v9 (rubric v8) and stays changed in v10;
B changed at v9 (the narrower "crisp" rubric) and returned to the legacy rubric
in v10. Do not feed v9 scores into update_stress() — see stress.py.
"""
from .client import OllamaClient, TransformersClient, ScoreResult, score_message
from .parse import parse_scores, DIMS
from .prompt import build_prompt, STUDENT_PROMPT
from .safety import CrisisGate, CrisisResult, DISCLOSURE_EN, DISCLOSURE_ZH
from .stress import energy_state, update_stress

__version__ = "0.3.0"
__all__ = [
    "OllamaClient", "TransformersClient", "ScoreResult", "score_message",
    "parse_scores", "DIMS", "build_prompt", "STUDENT_PROMPT",
    "CrisisGate", "CrisisResult", "DISCLOSURE_EN", "DISCLOSURE_ZH",
    "energy_state", "update_stress",
]
