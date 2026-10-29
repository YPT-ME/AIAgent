"""
Expected sources of the representative questions still exist and still state the facts the
expected answers rely on. This checks the documentation, not the model's answers.
"""

import json
import os
from pathlib import Path

import pytest

QUESTIONS = json.loads(
    (Path(__file__).parent / "evaluation" / "representative_questions.json").read_text(encoding="utf-8")
)
DOCS_DIR = Path(os.getenv("EVAL_DOCS_DIR", Path(__file__).parents[2] / "data" / "docs"))


def find_source(name: str) -> Path | None:
    pattern = name if name.endswith(".pdf") else f"{name}.md"
    matches = list(DOCS_DIR.glob(f"**/{pattern}"))
    return matches[0] if matches else None


@pytest.mark.skipif(not DOCS_DIR.is_dir(), reason=f"documentation not found at {DOCS_DIR}")
@pytest.mark.parametrize("case", QUESTIONS, ids=[q["question"][:40] for q in QUESTIONS])
def test_expected_sources_exist_and_state_the_facts(case):
    for name in case["expected_sources"]:
        if name.endswith(".pdf") and find_source(name) is None:
            pytest.skip(f"{name} is not in the wiki repository (PDFs are added per deployment)")
        assert find_source(name) is not None, f"{name} is missing from {DOCS_DIR}"

    for name, facts in case.get("source_facts", {}).items():
        text = " ".join(find_source(name).read_text(encoding="utf-8").split())
        for fact in facts:
            assert fact in text, f"{name} no longer states: {fact}"
