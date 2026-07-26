#!/usr/bin/env python3
"""Preprocessor for V7 Breakthrough Pipeline.

Handles UTF-8 normalization and exact bi-directional character offset mapping
to ensure 100% compliance with competition scoring on exact text position.
Also defines medical English-Vietnamese abbreviations glossary.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Iterator


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

    def slice_original(self, span: Span) -> str:
        return self.source[span.start : span.end]


# Glossary of medical English-Vietnamese abbreviations for system prompting or context enrichment
ABBREVIATION_GLOSSARY = {
    "po": "đường uống",
    "iv": "tiêm tĩnh mạch",
    "im": "tiêm bắp",
    "sc": "tiêm dưới da",
    "sl": "ngậm dưới lưỡi",
    "pr": "đặt trực tràng",
    "prn": "khi cần",
    "daily": "hàng ngày",
    "once": "1 lần/ngày",
    "bid": "2 lần/ngày",
    "tid": "3 lần/ngày",
    "qid": "4 lần/ngày",
    "qam": "mỗi sáng",
    "qhs": "mỗi tối trước khi ngủ",
    "q4h": "mỗi 4 giờ",
    "q6h": "mỗi 6 giờ",
    "q8h": "mỗi 8 giờ",
    "q12h": "mỗi 12 giờ",
    "nebs": "khí dung",
    "nebulizer": "khí dung",
}
