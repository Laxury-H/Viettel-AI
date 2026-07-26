#!/usr/bin/env python3
"""D2-V11 conservative CPU candidate linker.

V11 deliberately keeps the entity spans, types and assertions produced by the
scored D2-V9 extractor.  It only replaces an RxNorm candidate when the mention
contains enough drug/strength/route information for a more specific concept.
This makes the leaderboard experiment an isolated candidates-only ablation.

The rules are general medication normalization rules.  They do not reference
record IDs or private-test phrases, and inference remains offline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Pattern

from . import turn2_v9 as base


@dataclass(frozen=True)
class RxNormRule:
    """A strength-aware mapping to one active RxNorm concept."""

    group: str
    pattern: Pattern[str]
    candidates: tuple[str, ...]


def _rule(group: str, pattern: str, *candidates: str) -> RxNormRule:
    return RxNormRule(
        group,
        re.compile(pattern, re.IGNORECASE | re.VERBOSE),
        candidates,
    )


# Specific rules must precede broader rules.  The first block reproduces
# strength-specific examples in the official submission guide.  The second
# block covers the same common clinical forms using active RxNorm concepts.
RXNORM_RULES: tuple[RxNormRule, ...] = (
    _rule("official", r"\bamlodipine\s*10\s*mg\b", "308135"),
    _rule("official", r"\baspirin\s*81\s*mg\b", "243670"),
    _rule(
        "official",
        r"\bmetoprolol\s+succinate(?:\s+(?:xl|er))?\s*50\s*mg\b",
        "866436",
    ),
    _rule("official", r"\bguaifenesin\s+ml\s+(?:po|oral)\b", "392085"),
    _rule(
        "official",
        r"\bacetaminophen\s*325\s*[-–]\s*650\s*mg\b",
        "313782",
    ),
    _rule(
        "official",
        r"\bpravastatin(?:\s+sodium)?\s*40\s*mg\b",
        "904475",
    ),
    _rule("official", r"\bdocusate\s+sodium\s*100\s*mg\b", "1099279"),
    _rule(
        "official",
        r"\b(?:senna|sennosides?)\s*8[.,]6\s*mg\b",
        "312935",
    ),
    _rule("official", r"\bclonazepam\s*0?[.,]5\s*mg\b", "197527"),
    _rule("official", r"\bclonazepam\s*1[.,]5\s*mg\b", "197528"),
    _rule(
        "core_metoprolol",
        r"\bmetoprolol(?:\s+tartrate)?\s*25\s*mg\b",
        "866924",
    ),
    _rule(
        "strength_component",
        r"\b(?:simethicon|simethicone)\s*100\s*mg\b",
        "333293",
    ),
    _rule(
        "generic_uncertain",
        r"\bmetoclopramide\s*10\s*mg\b",
        "311666",
    ),
    _rule("strength_component", r"\bbumetanide\s*2\s*mg\b", "315502"),
    _rule("branded_sbd", r"\bmedrol\s*16\s*mg\b", "207138"),
    _rule(
        "core_omeprazole",
        r"\b(?:omeprazole|omez)\s*20\s*mg\b",
        "198051",
    ),
    _rule("branded_sbd", r"\bzestril\s*10\s*mg\b", "104377"),
    _rule("official_extra", r"\blisinopril\s*10\s*mg\b", "314076"),
    _rule(
        "strength_component",
        r"\b(?:nitramyl|nitroglycerin)\s*2[.,]5\s*mg\b",
        "316375",
    ),
    _rule(
        "generic_uncertain",
        r"\btylenol\s*(?:1\s*(?:g|gram)|1000\s*mg)\b",
        "430837",
    ),
    _rule(
        "branded_sbd",
        r"\bcoumadin\s*3(?:[.,]0)?\s*mg\b",
        "855320",
    ),
    _rule(
        "core_furosemide",
        r"\b(?:lasix|furosemide|furosemid)\s*40\s*mg\b"
        r"(?=[^;\r\n]{0,50}\b(?:po|uống|oral|viên)\b)",
        "313988",
    ),
)


FUROSEMIDE_80_IV = re.compile(
    r"(?ix)(?:"
    r"\b80\s*mg\s*iv\s*(?:lasix|furosemide|furosemid)\b|"
    r"\b80\s*mg\s*(?:lasix|furosemide|furosemid)\s*iv\b|"
    r"\b(?:lasix|furosemide|furosemid)\s*80\s*mg\s*iv\b"
    r")"
)


def normalize_surface(value: str) -> str:
    """Normalize presentation variants without changing source offsets."""

    value = unicodedata.normalize("NFC", value).casefold()
    return re.sub(r"[ \t]+", " ", value)


def medication_candidates(
    text: str,
    entity: dict,
    enabled_groups: frozenset[str] | None = None,
) -> list[str]:
    """Return a conservative strength-aware candidate list for one entity."""

    start, end = entity["position"]
    surface = normalize_surface(entity["text"])

    # D2-V9's generic 80-mg rule precedes its IV rule.  Correct that ordering
    # here: without a volume/concentration, the ingredient is safer than an
    # oral-tablet RxCUI for an explicitly intravenous mention.
    route_context = normalize_surface(text[max(0, start - 8) : min(len(text), end + 8)])
    if FUROSEMIDE_80_IV.search(route_context):
        return ["4603"]

    # Do not infer an oral 40-mg product when "IV" occurs immediately before
    # the extracted Lasix/furosemide span.
    if re.search(r"\b(?:lasix|furosemide|furosemid)\s*40\s*mg\b", surface):
        prefix = normalize_surface(text[max(0, start - 8) : start])
        if re.search(r"\biv\s*$", prefix):
            return list(entity["candidates"])

    for rule in RXNORM_RULES:
        if (
            enabled_groups is None or rule.group in enabled_groups
        ) and rule.pattern.search(surface):
            return list(rule.candidates)
    return list(entity["candidates"])


def upgrade_entities(
    text: str,
    entities: Iterable[dict],
    enabled_groups: frozenset[str] | None = None,
) -> tuple[list[dict], int]:
    """Copy entities and update medication candidates only."""

    upgraded: list[dict] = []
    changed = 0
    for source_entity in entities:
        entity = dict(source_entity)
        entity["assertions"] = list(source_entity["assertions"])
        if "candidates" in source_entity:
            entity["candidates"] = list(source_entity["candidates"])
        if entity["type"] == "THUỐC":
            candidates = medication_candidates(
                text,
                entity,
                enabled_groups=enabled_groups,
            )
            if candidates != entity["candidates"]:
                entity["candidates"] = candidates
                changed += 1
        upgraded.append(entity)
    return upgraded, changed


def extract(text: str) -> list[dict]:
    entities, _ = upgrade_entities(text, base.extract(text))
    return entities


def run(
    input_dir: Path,
    output_dir: Path,
    zip_path: Path,
    *,
    enabled_groups: frozenset[str] | None = None,
    version: str = "D2-V11-candidate-only",
) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=base.natural_key)
    if not sources:
        raise SystemExit(f"Không tìm thấy .txt trong {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    counts = {entity_type: 0 for entity_type in sorted(base.OFFICIAL_TYPES)}
    assertion_counts = {
        assertion: 0 for assertion in sorted(base.OFFICIAL_ASSERTIONS)
    }
    total = 0
    candidate_changes = 0
    for source in sources:
        text = source.read_text(encoding="utf-8")
        baseline = base.extract(text)
        entities, changed = upgrade_entities(
            text,
            baseline,
            enabled_groups=enabled_groups,
        )
        base.validate_record(text, entities)

        # This is the central V11 safety contract: only candidate values may
        # differ from the scored control.
        for before, after in zip(baseline, entities, strict=True):
            before_without_candidates = {
                key: value for key, value in before.items() if key != "candidates"
            }
            after_without_candidates = {
                key: value for key, value in after.items() if key != "candidates"
            }
            if before_without_candidates != after_without_candidates:
                raise AssertionError("V11 changed a non-candidate field")

        for entity in entities:
            counts[entity["type"]] += 1
            for assertion in entity["assertions"]:
                assertion_counts[assertion] += 1
        total += len(entities)
        candidate_changes += changed
        (output_dir / f"{source.stem}.json").write_text(
            base.format_json(entities),
            encoding="utf-8",
            newline="\n",
        )

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for output_file in sorted(output_dir.glob("*.json"), key=base.natural_key):
            info = zipfile.ZipInfo(
                f"output/{output_file.name}",
                (1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, output_file.read_bytes())

    return {
        "version": version,
        "candidate_groups": (
            "all" if enabled_groups is None else sorted(enabled_groups)
        ),
        "normalization_source": "official sample + NLM RxNorm API",
        "records": len(sources),
        "entities": total,
        "by_type": counts,
        "by_assertion": assertion_counts,
        "candidate_entities_changed": candidate_changes,
        "non_candidate_fields_changed": 0,
        "zip": str(zip_path.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(args.input, args.output, args.zip)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
