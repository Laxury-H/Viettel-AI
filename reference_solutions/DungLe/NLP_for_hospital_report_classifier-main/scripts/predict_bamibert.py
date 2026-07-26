#!/usr/bin/env python3
"""Generate versioned production or legacy teacher caches.

Passing ``--revision`` writes the versioned schema consumed by the refactored
production pipeline. Omitting it preserves the flat record mapping expected by
the V17-V19 research builders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer


LABEL_TO_TYPE = {
    "ten_benh": "CHẨN_ĐOÁN",
    "trieu_chung_benh": "TRIỆU_CHỨNG",
}


@dataclass(frozen=True)
class TokenPrediction:
    start: int
    end: int
    label: str
    confidence: float


@dataclass(frozen=True)
class ModelSpan:
    start: int
    end: int
    type: str
    confidence: float
    text: str


def decode(
    raw_text: str,
    tokens: list[TokenPrediction],
    minimum: float,
) -> list[ModelSpan]:
    best: dict[tuple[int, int], TokenPrediction] = {}
    for token in tokens:
        if token.confidence < minimum or token.end <= token.start:
            continue
        key = (token.start, token.end)
        if key not in best or token.confidence > best[key].confidence:
            best[key] = token

    output: list[ModelSpan] = []
    active_start: int | None = None
    active_end = 0
    active_type: str | None = None
    confidences: list[float] = []

    def flush() -> None:
        nonlocal active_start, active_end, active_type, confidences
        if active_start is not None and active_type is not None:
            start, end = active_start, active_end
            while start < end and raw_text[start].isspace():
                start += 1
            while end > start and (
                raw_text[end - 1].isspace()
                or raw_text[end - 1] in ".,;:!?)]}"
            ):
                end -= 1
            if end > start:
                output.append(
                    ModelSpan(
                        start,
                        end,
                        active_type,
                        sum(confidences) / len(confidences),
                        raw_text[start:end],
                    )
                )
        active_start = None
        active_end = 0
        active_type = None
        confidences = []

    for token in sorted(best.values(), key=lambda value: (value.start, value.end)):
        if token.label == "O" or "-" not in token.label:
            flush()
            continue
        prefix, model_label = token.label.split("-", 1)
        entity_type = LABEL_TO_TYPE.get(model_label)
        if entity_type is None:
            flush()
            continue
        gap = raw_text[active_end : token.start] if active_start is not None else ""
        continues = (
            active_start is not None
            and active_type == entity_type
            and (
                (prefix == "I" and (token.start <= active_end or not gap.strip()))
                or (
                    token.start == active_end
                    and 0 < token.start < len(raw_text)
                    and raw_text[token.start - 1].isalnum()
                    and raw_text[token.start].isalnum()
                )
            )
        )
        if not continues:
            flush()
            active_start = token.start
            active_type = entity_type
        active_end = max(active_end, token.end)
        confidences.append(token.confidence)
    flush()
    return output


class Predictor:
    def __init__(
        self,
        model_path: str | Path,
        minimum: float,
        *,
        device: str = "auto",
        batch_size: int = 8,
    ) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(model_path)
        resolved_device = (
            "cuda" if device == "auto" and torch.cuda.is_available() else device
        )
        if resolved_device == "auto":
            resolved_device = "cpu"
        if resolved_device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable")
        self.device = torch.device(resolved_device)
        self.model.to(self.device)
        self.model.eval()
        self.minimum = minimum
        self.batch_size = batch_size
        self.id2label = {
            int(key): value for key, value in self.model.config.id2label.items()
        }

    def predict(self, raw_text: str) -> list[ModelSpan]:
        word_matches = list(re.finditer(r"\S+", raw_text))
        if not word_matches:
            return []
        encoded = self.tokenizer(
            [match.group(0) for match in word_matches],
            is_split_into_words=True,
            return_offsets_mapping=True,
            return_overflowing_tokens=True,
            truncation=True,
            max_length=128,
            stride=32,
            padding=True,
            return_tensors="pt",
        )
        offsets = encoded.pop("offset_mapping")
        encoded.pop("overflow_to_sample_mapping", None)
        word_ids = [
            encoded.word_ids(batch_index=index)
            for index in range(encoded["input_ids"].shape[0])
        ]
        predictions: list[TokenPrediction] = []
        with torch.inference_mode():
            for start in range(
                0,
                encoded["input_ids"].shape[0],
                self.batch_size,
            ):
                end = start + self.batch_size
                batch = {
                    key: value[start:end].to(self.device)
                    for key, value in encoded.items()
                }
                probabilities = torch.softmax(self.model(**batch).logits, dim=-1)
                scores, labels = probabilities.max(dim=-1)
                scores = scores.cpu()
                labels = labels.cpu()
                for local_index in range(labels.shape[0]):
                    chunk_index = start + local_index
                    for token_index in range(labels.shape[1]):
                        word_index = word_ids[chunk_index][token_index]
                        token_start, token_end = offsets[
                            chunk_index, token_index
                        ].tolist()
                        if (
                            word_index is None
                            or token_end <= token_start
                            or token_start != 0
                        ):
                            continue
                        word = word_matches[word_index]
                        predictions.append(
                            TokenPrediction(
                                word.start(),
                                word.end(),
                                self.id2label[
                                    int(labels[local_index, token_index])
                                ],
                                float(scores[local_index, token_index]),
                            )
                        )
        return decode(raw_text, predictions, self.minimum)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum", type=float, default=0.50)
    parser.add_argument("--model-id", default="cbc-528a/BamiBERT-ViMedNER")
    parser.add_argument(
        "--revision",
        help="Model revision; enables the versioned production cache schema",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
    )
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    predictor = Predictor(
        args.model,
        args.minimum,
        device=args.device,
        batch_size=args.batch_size,
    )
    records: dict[str, list[dict]] = {}
    paths = sorted(
        args.input.glob("*.txt"),
        key=lambda value: int(value.stem),
    )
    fingerprint = hashlib.sha256()
    for path in paths:
        raw_bytes = path.read_bytes()
        fingerprint.update(path.name.encode("utf-8"))
        fingerprint.update(b"\0")
        fingerprint.update(raw_bytes)
        fingerprint.update(b"\0")
        spans = predictor.predict(raw_bytes.decode("utf-8"))
        records[path.stem] = [asdict(span) for span in spans]
        print(path.stem, len(spans), flush=True)
    if args.revision:
        payload = {
            "schema_version": 2,
            "model": args.model_id,
            "revision": args.revision,
            "minimum_token_confidence": args.minimum,
            "device": str(predictor.device),
            "input_sha256": fingerprint.hexdigest(),
            "records": records,
        }
    else:
        payload = records
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
