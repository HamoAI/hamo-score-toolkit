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

From 0.5.0 the reference server serves v12 (0.4.x served v10h, 0.3.x served
v10). Scores are not comparable across model versions: A changed meaning at v9
(rubric v8) and stays changed in v10; B changed at v9 (the narrower "crisp"
rubric) and returned to the legacy rubric in v10. v10h keeps v10's prompts and
training recipe, with the synthetic training labels re-scored by human counselors
engaged by Hamo: A and W read lower on average than v10's, and all-zero outputs
are fewer. v12 keeps v10h's prompts and training recipe, with the synthetic
training labels replaced by those counselors' third-round scores. On our real
final exam its mean A, E and B read lower than v10h's (0.40, 0.27 and 0.95
against 0.43, 0.32 and 1.00), although its training labels' mean A and B are
higher than v10h's (0.462 and 0.942 against 0.423 and 0.832). Do not feed v9
scores into update_stress() — see stress.py.
"""
from .client import OllamaClient, TransformersClient, ScoreResult, score_message
from .parse import parse_scores, DIMS
from .prompt import build_prompt, strip_turn_markers, STUDENT_PROMPT
from .safety import CrisisGate, CrisisResult, DISCLOSURE_EN, DISCLOSURE_ZH
from .stress import energy_state, update_stress

__version__ = "0.5.0"
__all__ = [
    "OllamaClient", "TransformersClient", "ScoreResult", "score_message",
    "parse_scores", "DIMS", "build_prompt", "strip_turn_markers", "STUDENT_PROMPT",
    "CrisisGate", "CrisisResult", "DISCLOSURE_EN", "DISCLOSURE_ZH",
    "energy_state", "update_stress",
]
