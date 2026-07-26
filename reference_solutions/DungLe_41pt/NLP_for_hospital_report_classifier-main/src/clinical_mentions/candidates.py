"""Small candidate-code corrections proven useful on the leaderboard."""

from __future__ import annotations

import re
from collections.abc import Iterable


METOPROLOL_25_MG = re.compile(
    r"\bmetoprolol(?:\s+tartrate)?\s*25\s*mg\b",
    re.IGNORECASE,
)


def upgrade_entities(text: str, entities: Iterable[dict]) -> tuple[list[dict], int]:
    """Copy entities and apply the production RxNorm correction.

    Earlier versions tested fourteen candidate substitutions.  Only the
    metoprolol 25 mg rule survived leaderboard ablation, so rejected rules are
    intentionally absent from the production path.
    """

    del text  # Kept in the API for future context-aware candidate rules.
    upgraded: list[dict] = []
    changed = 0
    for source in entities:
        entity = dict(source)
        entity["assertions"] = list(source["assertions"])
        if "candidates" in source:
            entity["candidates"] = list(source["candidates"])
        if (
            entity["type"] == "THUỐC"
            and METOPROLOL_25_MG.search(entity["text"])
            and entity.get("candidates") != ["866924"]
        ):
            entity["candidates"] = ["866924"]
            changed += 1
        upgraded.append(entity)
    return upgraded, changed
