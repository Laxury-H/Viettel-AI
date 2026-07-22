#!/usr/bin/env python3
"""Deterministic CPU inference for the upgraded Viettel AI Race medical task.

The extractor is deliberately offline: it uses a compact clinical codebook and
context rules, preserves exact source spans, and never calls an external API.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from knowledge_base import (
    DIAGNOSES,
    LAB_TEST_PATTERNS,
    MEDICATIONS,
    OFFICIAL_TYPES,
    SYMPTOMS,
)


CLINICAL_TYPES = {"CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"}
LAB_TYPES = {"TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"}
OFFICIAL_ASSERTIONS = {"isNegated", "isFamily", "isHistorical"}


@dataclass(frozen=True)
class Span:
    start: int
    end: int


class NormalizedText:
    """NFC/casefold view with an exact map back to original character offsets."""

    def __init__(self, source: str) -> None:
        self.source = source
        normalized: list[str] = []
        starts: list[int] = []
        ends: list[int] = []
        index = 0
        while index < len(source):
            cluster_start = index
            index += 1
            while index < len(source) and unicodedata.combining(source[index]):
                index += 1
            cluster = source[cluster_start:index]
            folded = unicodedata.normalize("NFC", cluster).casefold()
            for character in folded:
                normalized.append(character)
                starts.append(cluster_start)
                ends.append(index)
        self.text = "".join(normalized)
        self._starts = starts
        self._ends = ends

    @staticmethod
    def normalize_alias(alias: str) -> str:
        return unicodedata.normalize("NFC", alias).casefold()

    @staticmethod
    def _word_character(character: str) -> bool:
        return character == "_" or character.isalnum()

    def literal_spans(self, alias: str, *, boundary: bool) -> Iterator[Span]:
        needle = self.normalize_alias(alias)
        if not needle:
            return
        cursor = 0
        while True:
            found = self.text.find(needle, cursor)
            if found < 0:
                break
            normalized_end = found + len(needle)
            before_ok = found == 0 or not self._word_character(self.text[found - 1])
            after_ok = normalized_end == len(self.text) or not self._word_character(
                self.text[normalized_end]
            )
            if not boundary or (before_ok and after_ok):
                yield Span(self._starts[found], self._ends[normalized_end - 1])
            cursor = found + 1


def natural_key(path: Path) -> tuple[int, str]:
    return (int(path.stem), path.name) if path.stem.isdigit() else (10**9, path.name)


def aliases_from(entry: object) -> tuple[str, ...]:
    if isinstance(entry, str):
        return (entry,)
    if isinstance(entry, dict):
        aliases = entry.get("aliases", ())
        if isinstance(aliases, str):
            return (aliases,)
        return tuple(str(alias) for alias in aliases)
    if isinstance(entry, (tuple, list)):
        return tuple(str(alias) for alias in entry)
    return ()


def candidates_from(entry: dict) -> list[str]:
    value = entry.get("codes", entry.get("code", ()))
    if isinstance(value, str):
        return [value]
    return [str(code) for code in value]


def should_use_boundary(alias: str, entity_type: str) -> bool:
    normalized = NormalizedText.normalize_alias(alias).strip()
    token_count = len(normalized.split())
    if entity_type in {"TRIỆU_CHỨNG", "TÊN_XÉT_NGHIỆM"}:
        return token_count == 1
    # Short clinical abbreviations must not match inside ordinary words. Longer
    # names remain tolerant of OCR concatenation errors seen in the release.
    return token_count == 1 and len(normalized) <= 4


def section_states(text: str) -> tuple[list[tuple[int, bool]], list[tuple[int, bool]]]:
    """Return historical and family-history state transitions by source offset."""
    historical: list[tuple[int, bool]] = [(0, False)]
    family: list[tuple[int, bool]] = [(0, False)]
    offset = 0
    historical_state = False
    family_state = False
    historical_has_content = False
    family_has_content = False
    for line in text.splitlines(keepends=True):
        compact = unicodedata.normalize("NFC", line).casefold().strip(" \t\r\n-•:.")
        if not compact:
            if historical_state and historical_has_content:
                historical_state = False
                historical_has_content = False
                historical.append((offset, False))
            if family_state and family_has_content:
                family_state = False
                family_has_content = False
                family.append((offset, False))
            offset += len(line)
            continue
        user_question = bool(
            re.search(r"\b(?:bác\s+sĩ|bs)\b.{0,100}\b(?:hỏi|tư\s+vấn)\b", compact)
        )
        is_heading = len(compact) <= 100 or bool(re.match(r"^\d+[.)]\s*", compact))
        family_heading = False
        historical_heading = False
        if is_heading or user_question:
            family_heading = bool(
                re.fullmatch(
                    r"(?:\d+[.)]\s*)?(?:(?:tiền sử|bệnh sử)\s+(?:của\s+)?gia đình|"
                    r"family history)",
                    compact,
                )
            )
            historical_heading = bool(
                re.search(
                    r"(?:^|\s)(?:tiền sử bệnh(?:\s+(?:lý|nội khoa))?|các bệnh(?:\s+lý)?\s+"
                    r"(?:mạn|mãn)\s+tính|thuốc(?:\s+đã)?(?:\s+điều\s+trị|\s+dùng)?\s+"
                    r"trước\s+(?:khi\s+)?nhập viện|thuốc\s+đã\s+dùng\s+trước\s+đây)",
                    compact,
                )
            ) and "hiện tại" not in compact and not family_heading
            reset = user_question or bool(
                re.search(
                    r"^(?:\d+[.)]\s*)?(?:(?:bệnh sử|tiền sử bệnh)\s+hiện tại|cận lâm sàng|"
                    r"khám(?:\s+lâm sàng)?|bệnh sử|chẩn đoán|đánh giá|điều trị(?:\s|:|$)|diễn biến|"
                    r"câu hỏi|câu trả lời|dị ứng|tiền sử (?:bản thân|dịch tễ))",
                    compact,
                )
            )
            if family_heading:
                if historical_state:
                    historical_state = False
                    historical_has_content = False
                    historical.append((offset, False))
                if not family_state:
                    family_state = True
                    family_has_content = False
                    family.append((offset, True))
            elif historical_heading:
                if family_state:
                    family_state = False
                    family_has_content = False
                    family.append((offset, False))
                if not historical_state:
                    historical_state = True
                    historical_has_content = False
                    historical.append((offset, True))
            elif reset:
                if historical_state:
                    historical_state = False
                    historical_has_content = False
                    historical.append((offset, False))
                if family_state:
                    family_state = False
                    family_has_content = False
                    family.append((offset, False))
        if historical_state and not historical_heading:
            historical_has_content = True
        if family_state and not family_heading:
            family_has_content = True
        offset += len(line)
    lines = text.splitlines(keepends=True)
    line_offsets: list[int] = []
    running_offset = 0
    for line in lines:
        line_offsets.append(running_offset)
        running_offset += len(line)
    for index, line in enumerate(lines):
        compact_line = unicodedata.normalize("NFC", line).casefold()
        if (
            re.search(r"các bệnh(?:\s+lý)?\s+(?:mạn|mãn)\s+tính", compact_line)
            and index > 0
            and re.search(
                r"(?i)\b(?:bố|cha|mẹ|ông|bà|vợ|chồng)\s+(?:tôi|em|mình|bạn)\b",
                lines[index - 1],
            )
        ):
            family.append((line_offsets[index], True))
            end_index = index + 1
            while end_index < len(lines) and lines[end_index].strip():
                end_index += 1
            family.append(
                (
                    line_offsets[end_index]
                    if end_index < len(line_offsets)
                    else len(text),
                    False,
                )
            )
        if not re.search(r"thuốc\s+trước\s+(?:khi\s+)?nhập\s+viện", compact_line):
            continue
        block_start = index
        cursor = index - 1
        while cursor >= 0:
            stripped = lines[cursor].strip()
            if not stripped or not re.match(r"^(?:[-•]|\d+[.)])\s*", stripped):
                break
            block_start = cursor
            cursor -= 1
        if block_start < index:
            historical.append((line_offsets[block_start], True))
    historical.sort(key=lambda item: item[0])
    family.sort(key=lambda item: item[0])
    return historical, family


def state_at(transitions: list[tuple[int, bool]], position: int) -> bool:
    state = False
    for offset, candidate in transitions:
        if offset > position:
            break
        state = candidate
    return state


def local_clause(text: str, start: int, *, limit: int = 180) -> str:
    left = max(0, start - limit)
    fragment = text[left:start]
    delimiter = max(fragment.rfind(mark) for mark in ("\n", ".", ";", ":", "•", "?", "!"))
    if delimiter >= 0:
        fragment = fragment[delimiter + 1 :]
    reset_matches = []
    for candidate in re.finditer(
            r"(?i)\b(?:nhưng|tuy nhiên|song|phát hiện|ghi nhận|cho thấy|chẩn đoán)\b",
            fragment,
        ):
        prefix = unicodedata.normalize("NFC", fragment[max(0, candidate.start() - 12) : candidate.start()]).casefold()
        if candidate.group(0).casefold() in {"phát hiện", "ghi nhận"} and re.search(
            r"(?:không|chưa)\s*$", prefix
        ):
            continue
        reset_matches.append(candidate)
    if reset_matches:
        fragment = fragment[reset_matches[-1].end() :]
    return fragment


def has_family_context(text: str, start: int, family_state: bool) -> bool:
    if family_state:
        return True
    fragment = text[max(0, start - 240) : start]
    delimiter = max(fragment.rfind(mark) for mark in ("\n", ".", ";", "•", "?", "!"))
    context = fragment[delimiter + 1 :] if delimiter >= 0 else fragment
    if re.search(
        r"(?i)(?:tiền\s+sử|bệnh\s+sử)\s+gia\s+đình[^.;\n]{0,160}$",
        context,
    ):
        return True
    direct = bool(
        re.search(
            r"(?ix)(?:\b(?:bố|cha|mẹ|ông|bà|vợ|chồng|anh\s+trai|"
            r"chị\s+gái|em\s+trai|em\s+gái|cô|dì|chú|bác|người\s+nhà|họ\s+hàng|"
            r"con\s+(?:tôi|em|mình|bạn)|bé\s+nhà(?:\s+(?:tôi|em|mình|bạn))?)"
            r"(?:\s+(?:của\s+)?(?:bệnh\s+nhân|tôi|em|mình|bạn(?:\s+ấy)?))?"
            r"(?:\s*,?\s*năm\s+nay\s+\d+\s*(?:tuổi|t))?\s*,?"
            r"(?:\s+(?:đã|cũng|có\s+thể)){0,2}\s+"
            r"(?:bị|mắc|có|được\s+chẩn\s+đoán|từng\s+bị)|"
            r"(?:tiền\s+sử|bệnh\s+sử)\s+gia\s+đình(?:\s+có)?|"
            r"gia\s+đình\s+(?:có\s+)?(?:người|ai))[^.;\n]{0,220}$",
            context,
        )
    )
    paragraph = text[max(text.rfind("\n", 0, start) + 1, start - 360) : start]
    carried_subject = bool(
        re.search(
            r"(?i)\b(?:bố|cha|mẹ|ông|bà|vợ|chồng)\s+(?:tôi|em|mình|bạn)\b",
            paragraph,
        )
        and re.search(r"(?i)\b(?:kê|cho)\b[^.;\n]{0,90}$", context)
    )
    return direct or carried_subject


def has_negation(text: str, start: int, end: int) -> bool:
    context = local_clause(text, start, limit=130)
    folded = unicodedata.normalize("NFC", context).casefold()
    suffix = unicodedata.normalize("NFC", text[end : min(len(text), end + 35)]).casefold()
    if re.search(r"^\s*(?:nặng hơn|tiến triển|xấu đi)", suffix) and re.search(
        r"không\s+thấy\s+tình\s+trạng", folded
    ):
        return False
    cue_pattern = re.compile(
        r"(?ix)\b(?:không\s+xác\s+nhận(?:\s+đã)?(?:\s+bị)?|"
        r"không\s+ghi\s+nhận|không\s+phát\s+hiện|chưa\s+phát\s+hiện|"
        r"chưa\s+thấy|phủ\s+nhận|âm\s+tính\s+với|"
        r"không(?:\s+có)?|chưa(?:\s+từng)?)\b"
    )
    cues = list(cue_pattern.finditer(folded))
    if not cues:
        return bool(re.match(r"\s*\(\s*[-–]\s*\)", text[end : end + 8]))
    tail = folded[cues[-1].end() :].strip()
    if len(tail) > 90:
        return False
    # These constructions negate treatment response, modality, or another
    # predicate rather than the medical concept that appears later.
    if re.match(
        r"(?ix)^(?:được|thể|phải|nhớ|điều\s+trị|tuân\s+thủ|dùng|sử\s+dụng|uống|"
        r"xét\s+nghiệm|đo|định\s+lượng|đáp\s+ứng|cải\s+thiện|giảm|đỡ|rõ|"
        r"cố\s+định|đặc\s+hiệu|cần|liên\s+quan|là|nghĩ|"
        r"ổn\s+định|thay\s+đổi|"
        r"phải\s+là|có\s+(?:phương\s+pháp|biến\s+chứng|thay\s+đổi|tác\s+dụng)|"
        r"ngon\s+miệng|vững|ứ\s+nước)\b",
        tail,
    ):
        return False
    if re.search(
        r"(?ix)\b(?:điều\s+trị|dùng|uống|gây|dẫn\s+đến|khiến|làm|nói|"
        r"mặc\s+dù|nhưng|ngoại\s+trừ|tuy\s+nhiên|vì|nên|gần\s+như|khi\s+xuất\s+hiện|"
        r"sau\s+\d+)\b",
        tail,
    ):
        return False
    return True


def assertions_for(
    text: str,
    start: int,
    end: int,
    entity_type: str,
    historical_state: bool,
    family_state: bool,
) -> list[str]:
    if entity_type not in CLINICAL_TYPES:
        return []
    assertions: list[str] = []
    local = unicodedata.normalize("NFC", local_clause(text, start, limit=150)).casefold()
    negated = has_negation(text, start, end)
    if entity_type == "THUỐC" and re.search(
        r"\b(?:không|chưa)(?:\s+từng)?\s+(?:dùng|uống|sử\s+dụng)\s*$",
        local,
    ):
        negated = True
    if negated:
        assertions.append("isNegated")
    family = has_family_context(text, start, family_state)
    if family:
        assertions.append("isFamily")
    post_context = unicodedata.normalize(
        "NFC", text[end : min(len(text), end + 150)]
    ).casefold()
    entity_surface = unicodedata.normalize("NFC", text[start:end]).casefold()
    broad_history = unicodedata.normalize(
        "NFC", text[max(0, start - 190) : start]
    ).casefold()
    broad_delimiter = max(broad_history.rfind(mark) for mark in ("\n", ".", ";", "?", "!"))
    if broad_delimiter >= 0:
        broad_history = broad_history[broad_delimiter + 1 :]
    explicit_history = bool(
        re.search(
            r"\b(?:(?:có\s+)?tiền\s+sử\s+(?:bị|mắc|chẩn\s+đoán|nhập\s+viện|"
            r"lâm\s+sàng|(?!(?:bệnh|gia\s+đình|phẫu\s+thuật|dịch\s+tễ|bản\s+thân|"
            r"nội\s+khoa|hiện\s+tại)\b)[^\s:;,.-]+)|trước\s+đây|đã\s+từng|"
            r"từng\s+bị|đã\s+dùng|đã\s+sử\s+dụng|"
            r"đã\s+ngừng|lần\s+nhập\s+viện\s+trước)\b[^.;\n]{0,110}$",
            local,
        )
        or re.search(
            r"\b(?:triệu\s+chứng|tình\s+trạng)\s+tương\s+tự\s+trước\s+đây\b[^.;\n]{0,130}$",
            broad_history,
        )
        or re.search(r"\btiền\s+sử\s*$", local)
        or re.search(
            r"\b\d+\s*(?:ngày|tuần|tháng|năm)\s+trước\b[^.;\n]{0,90}$",
            local + " " + broad_history,
        )
        or re.search(
            r"\b(?:trước\s+đây|đã\s+từng|từng\s+bị|nhập\s+viện\s+trước\s+đó)\b"
            r"[^.;\n]{0,130}$",
            broad_history,
        )
    ) and "tiền sử gia đình" not in local and "tiền sử gia đình" not in broad_history
    if re.search(
        r"\b(?:tiền\s+sử\s+bệnh|bệnh\s+sử)\s+hiện\s+tại\b",
        local,
    ):
        explicit_history = False
    if entity_type == "TRIỆU_CHỨNG":
        symptom_history_context = local + " " + broad_history
        symptom_history_cue = bool(
            re.search(
                r"\b(?:trước\s+đây|đã\s+từng|từng\s+bị|nhập\s+viện\s+trước\s+đó|"
                r"\d+\s*(?:ngày|tuần|tháng|năm)\s+trước|"
                r"tiền\s+sử\s+(?:bị|mắc|nhập\s+viện|"
                r"(?!(?:bệnh|gia\s+đình|phẫu\s+thuật|dịch\s+tễ|bản\s+thân|"
                r"nội\s+khoa|hiện\s+tại)\b)[^\s:;,.-]+))\b",
                symptom_history_context,
            )
            or re.search(r"\btiền\s+sử\s*$", local) is not None
        )
        if not symptom_history_cue:
            explicit_history = False
    if entity_type == "CHẨN_ĐOÁN" and re.search(
        r"\btừ\s+thời\s+kỳ\s+sơ\s+sinh\b",
        entity_surface + " " + post_context[:35],
    ):
        explicit_history = True
    if entity_type == "THUỐC" and re.match(
        r"[^.;\n]{0,90}\b(?:đã\s+(?:ngừng|dừng|hết)|ngừng\s+uống\s+cách\s+nhập\s+viện|"
        r"hiện\s+đã\s+ngừng)\b",
        post_context,
    ):
        explicit_history = True
    if entity_type == "THUỐC" and re.search(
        r"\bhết\b[^.;\n]{0,90}$",
        local,
    ):
        explicit_history = True
    if entity_type == "THUỐC" and re.search(
        r"\b(?:được\s+)?hướng\s+dẫn\s+ngừng\s*$",
        local,
    ):
        explicit_history = True
    if re.match(
        r"[^.;\n]{0,35}\b(?:trước\s+đây|\d+\s*(?:ngày|tuần|tháng|năm)\s+trước)\b",
        post_context,
    ):
        explicit_history = True
    if re.match(r"[^.;\n]{0,35}\bđã\s+(?:nhiều|\d+)\s+(?:năm|tháng)\b", post_context):
        explicit_history = True
    if re.search(r"\bsau\s+đó\s+xuất\s+viện\b", post_context):
        explicit_history = True
    current_cue = bool(
        re.search(r"\bhiện\s+tại\b[^.;\n]{0,90}$", local)
        or re.search(r"\bsau\s+khi\b[^.;\n]{0,90}\bđang\b[^.;\n]{0,45}$", local)
    )
    pre_admission_heading = bool(
        re.search(
            r"\bthuốc\s+trước\s+(?:khi\s+)?nhập\s+viện\b",
            local + " " + broad_history,
        )
    )
    section_history = (
        historical_state
        and entity_type in CLINICAL_TYPES
        and (not current_cue or pre_admission_heading)
    )
    if explicit_history or section_history:
        assertions.append("isHistorical")
    return assertions


def make_entity(
    text: str,
    span: Span,
    entity_type: str,
    historical_transitions: list[tuple[int, bool]],
    family_transitions: list[tuple[int, bool]],
    candidates: Iterable[str] | None = None,
) -> dict:
    entity = {
        "text": text[span.start : span.end],
        "type": entity_type,
    }
    if candidates is not None:
        unique_candidates = list(dict.fromkeys(str(value) for value in candidates if str(value)))
        if unique_candidates:
            entity["candidates"] = unique_candidates
    entity["assertions"] = assertions_for(
        text,
        span.start,
        span.end,
        entity_type,
        state_at(historical_transitions, span.start),
        state_at(family_transitions, span.start),
    )
    entity["position"] = [span.start, span.end]
    return entity


MEDICATION_SUFFIX = re.compile(
    r"(?ix)^(?:"
    r"[ \t]*(?:"
    r"\d+(?:[.,]\d+)?(?:[ \t]*[-–/][ \t]*\d+(?:[.,]\d+)?)?[ \t]*"
    r"(?:microgam|gram|mg|mcg|µg|ug|ml|meq|mmol|iu|lần|liều|g|l|"
    r"đơn[ \t]*vị|%)(?![\w])(?:/[ \t]*(?:ml|viên))?|"
    r"x[ \t]*\d+(?:[ \t]*(?:viên|lọ|ống|liều|lần|ml|mg|g))?|"
    r"po|iv|im|sc|sl|pr|dùng|uống|tiêm|truyền(?:\s+tĩnh\s+mạch)?|nebulizer|nebs?|"
    r"\d{1,2}h(?:\d{1,2})?|sau[ \t]+ăn(?:[ \t]+no)?|"
    r"daily|bid|tid|qid|qam|qhs|prn|once|q\d+h|"
    r"mỗi[ \t]+ngày|hàng[ \t]+ngày|/[ \t]*ngày|ngày[ \t]+\d+[ \t]*lần|"
    r",[ \t]*(?:uống|tiêm|truyền|po|iv|im|sc|sl)|sáng|chiều|tối|"
    r"viên|lọ|ống|liều"
    r")"
    r"){0,12}"
)

MEDICATION_CANDIDATE_OVERRIDES = (
    (re.compile(r"(?i)\baspirin[ \t]*325[ \t]*mg\b"), ("212033",)),
    (re.compile(r"(?i)\b(?:acetaminophen|paracetamol)[ \t]*500[ \t]*mg\b"), ("198440",)),
    (re.compile(r"(?i)\b(?:lasix|furosemide|furosemid)[ \t]*80[ \t]*mg\b"), ("197732",)),
    (re.compile(r"(?i)\b80[ \t]*mg[ \t]*po[ \t]*(?:lasix|furosemide|furosemid)\b"), ("197732",)),
    (re.compile(r"(?i)\b80[ \t]*mg[ \t]*(?:iv[ \t]*(?:lasix|furosemide|furosemid)|(?:lasix|furosemide|furosemid)[ \t]*iv)\b"), ("4603",)),
    (re.compile(r"(?i)\bceftriaxone[ \t]*1[ \t]*(?:g|gram)\b"), ("1665021",)),
    (re.compile(r"(?i)\bbactrim[ \t]*ds\b"), ("198335",)),
    (re.compile(r"(?i)\bvancomycin[ \t]*1[ \t]*(?:g|gram)\b"), ("1807513",)),
    (re.compile(r"(?i)\blev(?:o|a)floxacin[ \t]*750[ \t]*mg\b"), ("330371",)),
    (re.compile(r"(?i)\bcoumadin[ \t]*3(?:[.,]0)?[ \t]*mg\b"), ("855318",)),
    (re.compile(r"(?i)\bmethylprednisolone[ \t]*125[ \t]*mg[ \t]*iv\b"), ("1743704",)),
)


def extend_medication_span(text: str, span: Span) -> Span:
    # Ground-truth examples keep strength, route and frequency with the drug.
    prefix_start = max(
        text.rfind("\n", 0, span.start) + 1,
        text.rfind(";", 0, span.start) + 1,
        span.start - 36,
    )
    prefix = text[prefix_start : span.start]
    leading = re.search(
        r"(?i)(?<!\w)\d+(?:[.,]\d+)?[ \t]*(?:mg|mcg|µg|ug|g|gram|ml)"
        r"[ \t]*(?:(?:po|iv|im|sc|sl|pr)[ \t]*)?$",
        prefix,
    )
    if leading:
        span = Span(prefix_start + leading.start(), span.end)
    tail = text[span.end : min(len(text), span.end + 80)]
    boundary = re.search(r"[\r\n;]", tail)
    if boundary:
        tail = tail[: boundary.start()]
    match = MEDICATION_SUFFIX.match(tail)
    if not match or not match.group(0).strip():
        return span
    candidate_end = span.end + match.end()
    while candidate_end > span.end and text[candidate_end - 1].isspace():
        candidate_end -= 1
    return Span(span.start, candidate_end)


def medication_candidates(surface: str, defaults: list[str]) -> list[str]:
    for pattern, candidates in MEDICATION_CANDIDATE_OVERRIDES:
        if pattern.search(surface):
            return list(candidates)
    return defaults


def find_codebook_entities(
    text: str,
    normalized: NormalizedText,
    entries: Iterable[dict],
    entity_type: str,
    historical: list[tuple[int, bool]],
    family: list[tuple[int, bool]],
) -> list[dict]:
    entities: list[dict] = []
    for entry in entries:
        candidates = candidates_from(entry)
        for alias in aliases_from(entry):
            for span in normalized.literal_spans(
                alias, boundary=should_use_boundary(alias, entity_type)
            ):
                if entity_type == "THUỐC":
                    span = extend_medication_span(text, span)
                    entity_candidates = medication_candidates(text[span.start : span.end], candidates)
                else:
                    entity_candidates = candidates
                entities.append(
                    make_entity(text, span, entity_type, historical, family, entity_candidates)
                )
    return entities


def find_contextual_diagnoses(
    text: str,
    normalized: NormalizedText,
    historical: list[tuple[int, bool]],
    family: list[tuple[int, bool]],
) -> list[dict]:
    entities: list[dict] = []
    for span in normalized.literal_spans("áp xe", boundary=True):
        context = NormalizedText.normalize_alias(text[max(0, span.start - 90) : span.start])
        if re.search(r"(?:trong|tại)\s+ổ\s+bụng\b", context):
            entities.append(
                make_entity(text, span, "CHẨN_ĐOÁN", historical, family, ["K65.1"])
            )
    return entities


def find_symptoms(
    text: str,
    normalized: NormalizedText,
    historical: list[tuple[int, bool]],
    family: list[tuple[int, bool]],
) -> list[dict]:
    entities: list[dict] = []
    for entry in SYMPTOMS:
        for alias in aliases_from(entry):
            for span in normalized.literal_spans(alias, boundary=should_use_boundary(alias, "TRIỆU_CHỨNG")):
                # Avoid the very common non-medical phrase "phù hợp".
                normalized_alias = NormalizedText.normalize_alias(alias)
                if normalized_alias == "phù":
                    following = NormalizedText.normalize_alias(text[span.end : span.end + 6])
                    if re.match(r"\s*hợp", following):
                        continue
                if normalized_alias == "yếu":
                    preceding = NormalizedText.normalize_alias(text[max(0, span.start - 8) : span.start])
                    following = NormalizedText.normalize_alias(text[span.end : span.end + 8])
                    if re.search(r"(?:chủ|thiết|tất)\s*$", preceding) or re.match(r"\s*tố\b", following):
                        continue
                if normalized_alias == "đau":
                    preceding = NormalizedText.normalize_alias(text[max(0, span.start - 24) : span.start])
                    if re.search(r"(?:thuốc|giảm|chống)\s*$", preceding):
                        continue
                if normalized_alias == "đau đầu":
                    following = NormalizedText.normalize_alias(text[span.end : span.end + 8])
                    if re.match(r"\s*gối\b", following):
                        continue
                if normalized_alias == "ran":
                    preceding = NormalizedText.normalize_alias(text[max(0, span.start - 8) : span.start])
                    if re.search(r"râm\s*$", preceding):
                        continue
                if normalized_alias == "uống nhiều":
                    following = NormalizedText.normalize_alias(text[span.end : span.end + 16])
                    if re.match(r"\s*(?:rượu|loại)\b", following):
                        continue
                if normalized_alias == "ăn nhiều":
                    preceding = NormalizedText.normalize_alias(text[max(0, span.start - 12) : span.start])
                    if re.search(r"(?:đồ|thức)\s*$", preceding):
                        continue
                if normalized_alias == "ho":
                    following = NormalizedText.normalize_alias(text[span.end : span.end + 24])
                    if re.match(r"\s*đái\s+tháo\s+đường\b", following):
                        continue
                    if re.search(r"-\s*$", text[max(0, span.start - 6) : span.start]) and re.match(
                        r"\s+(?:Bệnh|Rối\s+loạn|Rung)\b",
                        text[span.end : span.end + 28],
                    ):
                        continue
                entities.append(
                    make_entity(text, span, "TRIỆU_CHỨNG", historical, family)
                )
    return entities


VALUE_PATTERN = re.compile(
    r"(?ix)(?:"
    r"(?:tăng|giảm)\s+từ\s+[+-]?\d+(?:[.,]\d+)*\s+"
    r"(?:lên|xuống|đến)\s+[+-]?\d+(?:[.,]\d+)*"
    r"(?:\s*(?:%|g/?l|mg/?dl|mg/?l|mmol/?l|meq/?l|u/?l|ui/?l|"
    r"micromol/?l|µmol/?l|umol/?l|mmhg))?|"
    r"(?:âm\s+tính|dương\s+tính|bình\s+thường|bất\s+thường|tăng|giảm|cao|thấp|"
    r"(?:không|chưa)\s+(?:ghi\s+nhận|phát\s+hiện|thấy)(?:\s+gì)?\s+bất\s+thường|"
    r"(?:trên|dưới)\s+ngưỡng\s+điều\s+trị)|"
    r"(?:[<>≤≥]\s*)?[+-]?\d+(?:[.,]\d+)*(?:\s*(?:-->|→|[-–/])\s*\d+(?:[.,]\d+)*)?"
    r"(?:\s*(?:%|g/?l|mg/?dl|mg/?l|mmol/?l|meq/?l|u/?l|ui/?l|ng/?ml|"
    r"pg/?ml|µg/?l|micromol/?l|µmol/?l|umol/?l|mmhg|bpm|g/l|t/?l|"
    r"°\s*[cf]|lần/?phút|"
    r"chu\s*k[ìi]/phút|l/?ph))?"
    r")"
)

AMBIGUOUS_LAB_ALIASES = {
    "k", "na", "cl", "ca", "ph", "pt", "tq", "hc", "hb", "ct", "ef", "fac", "ua",
    "protein", "hồng cầu", "bạch cầu", "vi khuẩn", "albumin", "glucose", "kali",
    "canxi", "natri", "clorua",
}


def result_spans_after(text: str, end: int, custom_pattern: str | None = None) -> list[Span]:
    window = text[end : min(len(text), end + 85)]
    newline = re.search(r"[\r\n]", window)
    if newline:
        prefix = window[: newline.start()]
        if prefix.count("(") > prefix.count(")"):
            window = window.replace("\r", " ").replace("\n", " ")
        else:
            window = prefix
    semicolon = window.find(";")
    if semicolon >= 0:
        window = window[:semicolon]
    relation = re.match(
        r"(?ix)^[ \t]*(?:\([^\n;]{0,55}\)[ \t]*)?(?::|=|là|ở[ \t]+mức|"
        r"kết[ \t]+quả[ \t]+là)?[ \t]*",
        window,
    )
    search_start = relation.end() if relation else 0
    search_window = window[search_start:]
    pattern = re.compile(custom_pattern, re.IGNORECASE) if custom_pattern else VALUE_PATTERN
    matches: list[Span] = []
    last_value_match_end: int | None = None
    for index, match in enumerate(pattern.finditer(search_window)):
        if match.start() > 18 and not re.search(r"(?i)\b(?:từ|lên|xuống|đến)\s*$", search_window[: match.start()]):
            break
        absolute = end + search_start + match.start()
        absolute_end = end + search_start + match.end()
        following = text[absolute_end : min(len(text), absolute_end + 18)]
        if re.match(r"(?i)[ \t]*(?:mẫu|lần|tuần|tháng|năm|ngày|tuổi|viên|liều)\b", following):
            continue
        value_text = unicodedata.normalize("NFC", match.group(0)).casefold().strip()
        if value_text in {"tăng", "giảm"} and re.match(
            r"\s*từ\s+[+-]?\d", search_window[match.end() :]
        ):
            continue
        if last_value_match_end is not None:
            bridge = search_window[last_value_match_end : match.start()]
            if not re.search(r"(?i)(?:-->|→|\b(?:lên|xuống|đến)\b)", bridge):
                break
        matches.append(Span(absolute, absolute_end))
        last_value_match_end = match.end()
        if len(matches) >= 2:
            break
    return matches


def result_span_before(text: str, start: int) -> Span | None:
    left = max(0, start - 36)
    window = text[left:start]
    matches = list(VALUE_PATTERN.finditer(window))
    if not matches:
        return None
    match = matches[-1]
    between = window[match.end() :]
    if len(between) <= 3 and not re.search(r"[.;:\n]", between):
        return Span(left + match.start(), left + match.end())
    return None


def find_labs(
    text: str,
    normalized: NormalizedText,
    historical: list[tuple[int, bool]],
    family: list[tuple[int, bool]],
) -> list[dict]:
    entities: list[dict] = []
    result_spans: set[tuple[int, int]] = set()
    for entry in LAB_TEST_PATTERNS:
        custom = entry.get("value_pattern") if isinstance(entry, dict) else None
        for alias in aliases_from(entry):
            literal_spans = list(
                normalized.literal_spans(
                    alias, boundary=should_use_boundary(alias, "TÊN_XÉT_NGHIỆM")
                )
            )
            if NormalizedText.normalize_alias(alias) == "ct":
                literal_spans.extend(
                    Span(match.start(), match.end())
                    for match in re.finditer(r"(?i)\bchụp[ \t]+ct(?=chưa\b)", text)
                )
            for span in literal_spans:
                normalized_alias = NormalizedText.normalize_alias(alias)
                if normalized_alias == "glucose" and re.match(
                    r"(?i)-6[ -]?phosphate", text[span.end : span.end + 14]
                ):
                    continue
                if normalized_alias == "ph" and text[span.start : span.end] not in {"pH", "PH"}:
                    continue
                values = result_spans_after(text, span.end, custom)
                before = result_span_before(text, span.start)
                if before is not None:
                    values.append(before)
                if normalized_alias in AMBIGUOUS_LAB_ALIASES:
                    nearby = NormalizedText.normalize_alias(
                        text[max(0, span.start - 45) : min(len(text), span.end + 45)]
                    )
                    has_numeric_value = any(
                        re.search(r"\d", text[value.start : value.end]) for value in values
                    )
                    explicit_lab_context = bool(
                        re.search(
                            r"\b(?:xét nghiệm|kết quả|cận lâm sàng|định lượng|chỉ số|"
                            r"điện giải|nước tiểu|xét nghiệm máu|prothrombin|chụp|scan)\b",
                            nearby,
                        )
                    )
                    explicit_separator = bool(
                        re.match(r"[ \t]*(?::|=)", text[span.end : span.end + 8])
                    )
                    if not (has_numeric_value or explicit_lab_context or explicit_separator):
                        continue
                entities.append(
                    make_entity(text, span, "TÊN_XÉT_NGHIỆM", historical, family)
                )
                for value_span in values:
                    key = (value_span.start, value_span.end)
                    if key in result_spans:
                        continue
                    result_spans.add(key)
                    entities.append(
                        make_entity(
                            text,
                            value_span,
                            "KẾT_QUẢ_XÉT_NGHIỆM",
                            historical,
                            family,
                        )
                    )
    return entities


def overlaps(left: dict, right: dict) -> bool:
    return left["position"][0] < right["position"][1] and right["position"][0] < left["position"][1]


def resolve_entities(entities: list[dict]) -> list[dict]:
    priority = {
        "CHẨN_ĐOÁN": 5,
        "THUỐC": 4,
        "TÊN_XÉT_NGHIỆM": 3,
        "KẾT_QUẢ_XÉT_NGHIỆM": 2,
        "TRIỆU_CHỨNG": 1,
    }
    unique: dict[tuple[int, int, str], dict] = {}
    for entity in entities:
        start, end = entity["position"]
        key = (start, end, entity["type"])
        existing = unique.get(key)
        if existing is None or len(entity.get("candidates", ())) > len(existing.get("candidates", ())):
            unique[key] = entity
    ranked = sorted(
        unique.values(),
        key=lambda entity: (
            -(entity["position"][1] - entity["position"][0]),
            -priority[entity["type"]],
            entity["position"][0],
        ),
    )
    chosen: list[dict] = []
    for entity in ranked:
        if not any(overlaps(entity, other) for other in chosen):
            chosen.append(entity)
    return sorted(chosen, key=lambda item: (item["position"][0], item["position"][1], item["type"]))


def extract(text: str) -> list[dict]:
    normalized = NormalizedText(text)
    historical, family = section_states(text)
    entities = []
    entities.extend(
        find_codebook_entities(text, normalized, DIAGNOSES, "CHẨN_ĐOÁN", historical, family)
    )
    entities.extend(
        find_codebook_entities(text, normalized, MEDICATIONS, "THUỐC", historical, family)
    )
    entities.extend(find_contextual_diagnoses(text, normalized, historical, family))
    entities.extend(find_symptoms(text, normalized, historical, family))
    entities.extend(find_labs(text, normalized, historical, family))
    return resolve_entities(entities)


def validate_record(text: str, entities: list[dict]) -> None:
    seen: set[tuple[int, int, str]] = set()
    for entity in entities:
        assert set(entity) <= {"text", "type", "candidates", "assertions", "position"}
        assert entity["type"] in OFFICIAL_TYPES
        start, end = entity["position"]
        assert isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text)
        assert text[start:end] == entity["text"]
        key = (start, end, entity["type"])
        assert key not in seen
        seen.add(key)
        assertions = entity["assertions"]
        assert isinstance(assertions, list) and len(assertions) <= 3
        assert len(assertions) == len(set(assertions)) and set(assertions) <= OFFICIAL_ASSERTIONS
        if entity["type"] in LAB_TYPES:
            assert assertions == []
        if entity["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
            assert entity.get("candidates") and all(
                isinstance(candidate, str) and candidate for candidate in entity["candidates"]
            )
        else:
            assert "candidates" not in entity


def format_json(data: list[dict]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def run(input_dir: Path, output_dir: Path, zip_path: Path) -> dict:
    sources = sorted(input_dir.glob("*.txt"), key=natural_key)
    if not sources:
        raise SystemExit(f"Không tìm thấy .txt trong {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.json"):
        if stale.stem.isdigit():
            stale.unlink()

    counts: dict[str, int] = {entity_type: 0 for entity_type in sorted(OFFICIAL_TYPES)}
    assertion_counts: dict[str, int] = {name: 0 for name in sorted(OFFICIAL_ASSERTIONS)}
    total = 0
    for source in sources:
        text = source.read_text(encoding="utf-8")
        entities = extract(text)
        validate_record(text, entities)
        for entity in entities:
            counts[entity["type"]] += 1
            for assertion in entity["assertions"]:
                assertion_counts[assertion] += 1
        total += len(entities)
        (output_dir / f"{source.stem}.json").write_text(
            format_json(entities), encoding="utf-8", newline="\n"
        )

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for output_file in sorted(output_dir.glob("*.json"), key=natural_key):
            archive.write(output_file, arcname=f"output/{output_file.name}")

    return {
        "records": len(sources),
        "entities": total,
        "by_type": counts,
        "by_assertion": assertion_counts,
        "zip": str(zip_path.resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.input, args.output, args.zip)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
