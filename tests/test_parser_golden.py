"""Golden-set parser tests.

Each case in tests/golden_tips/ is a pair: NAME.txt (the raw message) and
NAME.expected.json (the expected extraction). Populate with ~30 REAL historical
tips (anonymized) during Phase 1 — the two samples here document the format.

The live test calls the Anthropic API and is skipped unless ANTHROPIC_API_KEY
is set (run: pytest -m live_api).
"""
import json
import os
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).parent / "golden_tips"
CASES = sorted(GOLDEN_DIR.glob("*.txt"))


def expected_for(case: Path) -> dict:
    return json.loads(case.with_suffix("").with_suffix(".expected.json").read_text())


def test_golden_pairs_are_well_formed():
    assert CASES, "golden set is empty"
    for case in CASES:
        expected = expected_for(case)
        assert "is_tip" in expected
        if expected["is_tip"]:
            assert expected["tips"], f"{case.name}: is_tip true but no tips listed"
            for tip in expected["tips"]:
                assert {"course", "race_time", "horse_name", "side"} <= tip.keys()


@pytest.mark.live_api
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY")
@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_golden_extraction(case: Path):
    from betbot.parsing.claude_parser import parse_message

    expected = expected_for(case)
    parsed = parse_message(case.read_text())
    assert parsed.is_tip == expected["is_tip"], f"is_tip mismatch on {case.name}"
    if not expected["is_tip"]:
        return
    assert len(parsed.tips) == len(expected["tips"])
    for got, want in zip(parsed.tips, expected["tips"]):
        assert got.horse_name.lower() == want["horse_name"].lower()
        assert got.course.lower() == want["course"].lower()
        assert got.race_time == want["race_time"]
        assert got.side == want["side"]
        if want.get("tipped_price") is not None:
            assert got.tipped_price == pytest.approx(want["tipped_price"])
