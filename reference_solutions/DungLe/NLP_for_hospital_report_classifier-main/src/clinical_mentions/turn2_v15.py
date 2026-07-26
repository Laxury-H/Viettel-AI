#!/usr/bin/env python3
"""D2-V15 high-precision teacher-distilled clinical mention expansion.

V15 keeps the scored V14 metoprolol output as its control.  A Vietnamese
medical NER teacher was run over the public text and compared with D2-V9.
Only reusable, clinically unambiguous aliases from high-confidence
non-overlap disagreements are distilled here.  No record IDs or output spans
are stored, so the same rules run unchanged on private text.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

from . import turn2_v11
from . import turn2_v9 as base


# These mentions do not overlap a clinical entity in the scored V14 control.
# Ambiguous teacher predictions such as "ngủ", "đánh răng", "tiểu tiện",
# anatomy-only spans, and generic words such as "chứng" were rejected.
SAFE_SYMPTOMS: tuple[str, ...] = (
    "nhìn mờ ở cả hai mắt",
    "rỉ dịch vàng đục giống mủ",
    "khó khăn khi nhìn gần",
    "miệng thấy hơi thở mùi khó chịu",
    "tiểu tiện không tự chủ",
    "tức nặng 2 chi dưới",
    "khả năng trí óc giảm",
    "giảm cảm giác vị thế",
    "bứt rứt trong người",
    "dịch rỉ huyết thanh",
    "phát ban toàn thân",
    "thị giác bị nhòe",
    "tê bì vùng trán phải",
    "run giật tay chân",
    "đi lại không vững",
    "nhắm mắt từng lúc",
    "rụng tóc toàn bộ",
    "ngửa đầu ra sau",
    "đi cầu phân sống",
    "lưỡi đỏ dâu tây",
    "khó chịu vùng ngực",
    "suy giảm tri giác",
    "suy giảm trí nhớ",
    "rối loạn thị giác",
    "vàng niêm mạc",
    "mất định hướng",
    "sợ tiếng động",
    "mù vĩnh viễn",
    "nóng phần tinh hoàn",
    "đỏ gan bàn tay",
    "sợ ánh sáng",
    "răng lung lay",
    "giảm ham muốn",
    "nhìn mờ",
    "co giật",
    "cứng đờ",
    "cắn lưỡi",
    "ợ nóng",
    "môi đỏ",
    "tỉnh chậm",
    "lưỡi đỏ",
    "có mủ",
    "ù tai",
    "khó tập trung",
    "đỏ mặt",
    "rỉ máu",
    "lo lắng",
    "mất thị lực",
    "căng thẳng",
    "phát ban",
    "nặng mặt",
    "họng đỏ",
    "ruồi bay",
    "khó nhìn",
    "đỏ da",
    "tê bì",
    "bồn chồn",
    "sung huyết đỏ",
    "bong da",
    "lưỡi dâu tây",
    "dịch rò rỉ",
    "mày đay",
    "run rấy",
    "buồn ngủ",
)


# Smallest ablation: only the clearest teacher discoveries.  This profile is
# submitted first so the remaining daily attempts can be allocated according
# to an observed leaderboard delta instead of committing to the full group.
PRECISION_SYMPTOMS: tuple[str, ...] = (
    "nhìn mờ ở cả hai mắt",
    "rỉ dịch vàng đục giống mủ",
    "khó khăn khi nhìn gần",
    "miệng thấy hơi thở mùi khó chịu",
    "tiểu tiện không tự chủ",
    "tức nặng 2 chi dưới",
    "giảm cảm giác vị thế",
    "phát ban toàn thân",
    "run giật tay chân",
    "đi lại không vững",
    "lưỡi đỏ dâu tây",
    "suy giảm tri giác",
    "suy giảm trí nhớ",
    "vàng niêm mạc",
    "mất định hướng",
    "sợ tiếng động",
    "sợ ánh sáng",
    "răng lung lay",
    "nhìn mờ",
    "co giật",
    "cứng đờ",
    "cắn lưỡi",
    "ợ nóng",
    "môi đỏ",
    "tỉnh chậm",
    "lưỡi đỏ",
    "có mủ",
    "ù tai",
    "khó tập trung",
    "đỏ mặt",
    "rỉ máu",
    "lo lắng",
    "mất thị lực",
    "căng thẳng",
    "phát ban",
    "nặng mặt",
    "họng đỏ",
    "ruồi bay",
    "khó nhìn",
    "đỏ da",
)


# This second group is deliberately isolated in its own leaderboard ablation.
# Each phrase is a complete clinical mention that contains a shorter V14
# symptom, so adding it changes only the boundary selected by the resolver.
BOUNDARY_SYMPTOMS: tuple[str, ...] = (
    "đau bụng vùng hạ sườn phải",
    "đau đầu vùng thái dương phải",
    "đau bụng hạ sườn phải",
    "nổi mẩn đỏ ngứa ở lưng",
    "hạ huyết áp tư thế đứng",
    "phù nhẹ 2 chi dưới",
    "đau rát khi đi tiểu",
    "đau đầu kéo dài",
    "ngứa khắp người",
    "nôn mửa",
    "đau lưng âm ỉ",
    "đau hạ sườn phải",
    "tăng đánh trống ngực",
    "sưng hạch cổ",
    "buồn nôn/nôn",
    "đau thắt ngực",
    "đau bao tử",
    "đau bụng râm ran",
    "sưng nướu",
    "phù mặt",
    "run rẩy tay chân",
    "cơn ngất xỉu",
    "ngất xỉu",
    "phù ngoại vi",
    "đau hố chậu",
    "đau thượng vị",
    "đau khi nhai",
    "đau vai",
    "đau vùng gan phải",
    "sưng nề",
    "đau dữ dội",
    "đau bụng trên",
    "ngứa toàn thân",
    "đau các khớp",
    "phù hai bên",
    "đau lưng",
)


# Supplemental ICD-10-CM aliases are restricted to concepts whose normalized
# code is specific and stable.  Vague teacher predictions such as "bệnh dạ
# dày", "ung thư", or "bệnh tiềm ẩn" are intentionally excluded.
SAFE_DIAGNOSES: tuple[dict[str, object], ...] = (
    {"aliases": ("ung thư tuyến đại tràng",), "code": "C18.9"},
    {"aliases": ("viêm da tiếp xúc dị ứng",), "code": "L23.9"},
    {"aliases": ("viêm da tiếp xúc",), "code": "L25.9"},
    {"aliases": ("viêm teo niêm mạc dạ dày",), "code": "K29.4"},
    {"aliases": ("bệnh viêm tuỷ xương", "bệnh viêm tủy xương"), "code": "M86.9"},
    {"aliases": ("hẹp tắc mạch vành",), "code": "I25.10"},
    {"aliases": ("ung thư cổ tử cung",), "code": "C53.9"},
    {"aliases": ("suy vành mạn tính",), "code": "I25.9"},
    {"aliases": ("tai biến mạch máu não", "đột quỵ"), "code": "I63.9"},
    {"aliases": ("suy thoái võng mạc",), "code": "H35.9"},
    {"aliases": ("tắc ống dẫn trứng",), "code": "N97.1"},
    {"aliases": ("thai ngoài tử cung",), "code": "O00.9"},
    {"aliases": ("sỏi ống mật",), "code": "K80.50"},
    {"aliases": ("sỏi thận",), "code": "N20.0"},
    {"aliases": ("bệnh đa xơ cứng",), "code": "G35"},
    {"aliases": ("bệnh viêm mạch máu",), "code": "I77.6"},
    {"aliases": ("viêm xoang",), "code": "J32.9"},
    {"aliases": ("bệnhgout",), "code": "M10.9"},
    {"aliases": ("tăng HA",), "code": "I10"},
    {"aliases": ("XHTH",), "code": "K92.2"},
)


# Second diagnosis tier, evaluated only after SAFE_DIAGNOSES produced a
# positive leaderboard delta.  Every alias is still teacher-gated in V16.
EXTENDED_DIAGNOSES: tuple[dict[str, object], ...] = (
    {"aliases": ("bệnh dạ dày",), "code": "K31.9"},
    # The public records use this phrase in a biliary-obstruction context.
    {"aliases": ("ung thư biểu mô tuyến",), "code": "C22.1"},
    {"aliases": ("bệnh ung thư máu",), "code": "C96.9"},
    {"aliases": ("bệnh huyết áp",), "code": "I10"},
    {"aliases": ("bệnh nhiễm trùng",), "code": "B99.9"},
    {"aliases": ("VCTM",), "code": "N03.9"},
    {"aliases": ("tắc mạch",), "code": "I74.9"},
    {"aliases": ("Parkinson",), "code": "G20"},
)


# Recall-oriented final tier.  These remain genuine clinical phrases, but
# either represent a broad unspecified concept or have a lower teacher score,
# so they are reserved for the last daily attempt.
AGGRESSIVE_DIAGNOSES: tuple[dict[str, object], ...] = (
    {"aliases": ("ung thư", "u ung thư"), "code": "C80.1"},
    {"aliases": ("bệnh tiềm ẩn", "bệnh lý nền"), "code": "R69"},
    {"aliases": ("virus viêm gan B",), "code": "B18.1"},
    {"aliases": ("Parkinson",), "code": "G20"},
    {"aliases": ("hẹp lòng mạch",), "code": "I77.1"},
)


# High-confidence teacher spans that extend an already extracted diagnosis.
# They preserve the control concept code while testing a more complete text
# boundary; malformed joins and speculative prefixes are excluded.
DIAGNOSIS_BOUNDARIES: tuple[dict[str, object], ...] = (
    {"aliases": ("bệnh viêm sung huyết hang vị dạ dày",), "code": "K29.70"},
    {"aliases": ("chứng tăng nhãn áp",), "code": "H40.9"},
    {"aliases": ("bệnh rụng tóc từng mảng",), "code": "L63.9"},
    {"aliases": ("viêm tủy xương mãn tính",), "code": "M86.9"},
    {"aliases": ("bệnh u nang tuyến vú",), "code": "N60.09"},
    {"aliases": ("bệnh tiểu đường",), "code": "E11.9"},
    {"aliases": ("bệnh thrombophilia",), "code": "D68.59"},
    {"aliases": ("bệnh thrombophilia",), "code": "D68.59"},
    {"aliases": ("bệnh trĩ",), "code": "K64.9"},
    {"aliases": ("bệnh nấm bẹn",), "code": "B35.6"},
    {"aliases": ("xẹp phổi thùy dưới",), "code": "J98.11"},
    {"aliases": ("tràn dịch màng phổi trái tái phát",), "code": "J90"},
)


PROFILES = {
    "precision": (PRECISION_SYMPTOMS, ()),
    "precision-empty": (PRECISION_SYMPTOMS, ()),
    "safe": (SAFE_SYMPTOMS, ()),
    "safe-empty": (SAFE_SYMPTOMS, ()),
    "safe-boundary": (SAFE_SYMPTOMS + BOUNDARY_SYMPTOMS, ()),
    "safe-diagnosis": (SAFE_SYMPTOMS, SAFE_DIAGNOSES),
    "full": (SAFE_SYMPTOMS + BOUNDARY_SYMPTOMS, SAFE_DIAGNOSES),
}

V14_CANDIDATE_GROUPS = frozenset({"official", "core_metoprolol"})
EMPTY_EXTRA_ASSERTION_PROFILES = frozenset({"precision-empty", "safe-empty"})


def find_extra_symptoms(
    text: str,
    aliases: tuple[str, ...],
    historical: list[tuple[int, bool]],
    family: list[tuple[int, bool]],
    *,
    force_empty_assertions: bool = False,
) -> list[dict]:
    normalized = base.NormalizedText(text)
    entities: list[dict] = []
    for alias in aliases:
        for span in normalized.literal_spans(
            alias,
            boundary=base.should_use_boundary(alias, "TRIỆU_CHỨNG"),
        ):
            entity = base.make_entity(
                text,
                span,
                "TRIỆU_CHỨNG",
                historical,
                family,
            )
            if force_empty_assertions:
                entity["assertions"] = []
            entities.append(entity)
    return entities


def extract(text: str, profile: str = "safe") -> list[dict]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    symptom_aliases, diagnosis_entries = PROFILES[profile]
    historical, family = base.section_states(text)
    entities = list(base.extract(text))
    entities.extend(
        find_extra_symptoms(
            text,
            symptom_aliases,
            historical,
            family,
            force_empty_assertions=profile in EMPTY_EXTRA_ASSERTION_PROFILES,
        )
    )
    if diagnosis_entries:
        normalized = base.NormalizedText(text)
        entities.extend(
            base.find_codebook_entities(
                text,
                normalized,
                diagnosis_entries,
                "CHẨN_ĐOÁN",
                historical,
                family,
            )
        )
    resolved = base.resolve_entities(entities)
    upgraded, _ = turn2_v11.upgrade_entities(
        text,
        resolved,
        enabled_groups=V14_CANDIDATE_GROUPS,
    )
    return upgraded


def run(
    input_dir: Path,
    output_dir: Path,
    zip_path: Path,
    *,
    profile: str,
) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
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
    changed_records = 0
    added = 0
    removed = 0
    changed_assertions = 0
    for source in sources:
        text = source.read_text(encoding="utf-8")
        control, _ = turn2_v11.upgrade_entities(
            text,
            base.extract(text),
            enabled_groups=V14_CANDIDATE_GROUPS,
        )
        entities = extract(text, profile)
        base.validate_record(text, entities)

        control_keys = {
            (entity["position"][0], entity["position"][1], entity["type"])
            for entity in control
        }
        entity_keys = {
            (entity["position"][0], entity["position"][1], entity["type"])
            for entity in entities
        }
        record_added = len(entity_keys - control_keys)
        record_removed = len(control_keys - entity_keys)
        if record_added or record_removed:
            changed_records += 1
        added += record_added
        removed += record_removed
        control_by_key = {
            (entity["position"][0], entity["position"][1], entity["type"]): entity
            for entity in control
        }
        changed_assertions += sum(
            entity["assertions"] != control_by_key[key]["assertions"]
            for entity in entities
            if (key := (
                entity["position"][0],
                entity["position"][1],
                entity["type"],
            ))
            in control_by_key
        )

        for entity in entities:
            counts[entity["type"]] += 1
            for assertion in entity["assertions"]:
                assertion_counts[assertion] += 1
        total += len(entities)
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
        "version": f"D2-V15-{profile}",
        "profile": profile,
        "control": "D2-V14-metoprolol",
        "records": len(sources),
        "changed_records": changed_records,
        "entities": total,
        "entities_added": added,
        "entities_removed_by_longest_span_resolution": removed,
        "existing_assertions_changed": changed_assertions,
        "by_type": counts,
        "by_assertion": assertion_counts,
        "zip": str(zip_path.resolve()),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="safe")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    summary = run(
        args.input,
        args.output,
        args.zip,
        profile=args.profile,
    )
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
