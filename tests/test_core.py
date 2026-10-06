"""Offline smoke tests — no model required."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hamo_score import (build_prompt, parse_scores, update_stress,
                        energy_state, CrisisGate, score_message)


def test_prompt_format_and_trim():
    p = build_prompt("你好")
    assert p == "给来访者最新消息打分（AWEHB，0.0-3.0）。\n最新消息: 你好"
    hist = [{"role": "user", "content": "x" * 999}] * 5
    p = build_prompt("y" * 999, hist)
    assert p.count("user:") == 3          # 3-turn cap
    assert "x" * 201 not in p             # 200-char turn cap
    assert "y" * 501 not in p             # 500-char message cap


def test_parse_tolerates_think_block():
    raw = '<think>\n\n</think>\n\n{"A": 1.5, "W": 0.0, "E": 0.0, "H": 0.0, "B": 1.0}'
    s = parse_scores(raw)
    assert s == {"A": 1.5, "W": 0.0, "E": 0.0, "H": 0.0, "B": 1.0}
    assert parse_scores("no json here") is None
    assert parse_scores('{"A": 9, "W": 1.3, "E": 0, "H": 0, "B": 0}')["A"] == 3.0  # clamp
    assert parse_scores('{"A": 1.3, "W": 0, "E": 0, "H": 0, "B": 0}')["A"] == 1.5  # snap


def test_stress_math():
    zero = {d: 0.0 for d in "AWEHB"}
    assert update_stress(zero, 5.0) == 5.0                      # all-zero = no-op
    hot = {"A": 0, "W": 2.5, "E": 2.5, "H": 0, "B": 0}
    assert update_stress(hot, 5.0) > 5.0
    calm = {"A": 2.5, "W": 0, "E": 0, "H": 0, "B": 2.0}
    assert update_stress(calm, 5.0) < 5.0
    assert energy_state(3.9) == "positive"
    assert energy_state(4.0) == "negative"
    assert energy_state(7.0) == "neurotic"


def test_crisis_gate_short_circuits():
    class Boom:
        def generate(self, prompt):
            raise AssertionError("model must not be called when gate triggers")
    r = score_message(Boom(), "我真的不想活了")
    assert r.crisis.triggered and r.scores is None and not r.ok


def test_ollama_client_pins_neutral_sampling():
    """Every request must carry neutral sampling, whatever the server's Modelfile says.

    Regression guard: ollama's default repeat_penalty 1.1 raised the fabrication
    rate in every version we measured (v10 q8: 2.9% -> 14.4%). Intercepts the
    real HTTP payload OllamaClient sends.
    """
    import json
    import urllib.request
    from hamo_score import OllamaClient

    sent = {}

    class FakeResp:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps({"response": '{"A":0,"W":0,"E":0,"H":0,"B":0}'}).encode()

    def fake_urlopen(req, timeout=None):
        sent.update(json.loads(req.data))
        return FakeResp()

    orig = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        OllamaClient().generate("x")
    finally:
        urllib.request.urlopen = orig

    opts = sent["options"]
    assert opts["temperature"] == 0
    assert opts["repeat_penalty"] == 1.0, "repeat penalty inflates scores away from 0"
    assert opts["top_k"] == 0 and opts["top_p"] == 1.0
    assert sent["keep_alive"] == -1



def test_exam_label_sets():
    """Every self-check question carries all three label sets, and both exam scripts map to them."""
    import importlib.util, json, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rows = [json.loads(l) for l in open(os.path.join(root, "eval", "synthetic_exam.jsonl"))]
    assert len(rows) == 195
    keys = None
    for name in ("run_exam", "compare_quants"):
        spec = importlib.util.spec_from_file_location(name, os.path.join(root, "eval", name + ".py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        assert list(mod.LABEL_KEYS)[0] == "v10"          # the default label set is the served version's
        keys = keys or mod.LABEL_KEYS
        assert mod.LABEL_KEYS == keys
    for r in rows:
        for key in keys.values():
            assert set(r[key]) == set("AWEHB") and all(0.0 <= r[key][d] <= 3.0 for d in "AWEHB")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"✓ {name}")
    print("all green")
