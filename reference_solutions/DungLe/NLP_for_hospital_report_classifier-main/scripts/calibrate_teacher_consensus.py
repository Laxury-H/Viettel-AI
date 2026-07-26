#!/usr/bin/env python3
"""Calibrate exact-span consensus between two ViMedNER teachers.

Inference uses overlapping windows and merges predictions back to original
word indices, so the comparison is not biased by tokenizer-specific
truncation at 128 subword tokens.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

try:
    from src.clinical_mentions import turn2_v16, turn2_v17
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.clinical_mentions import turn2_v16, turn2_v17

try:
    from scripts.train_vimedner import Sentence, entity_set, read_conll
except ModuleNotFoundError:
    from train_vimedner import Sentence, entity_set, read_conll


TARGET_TYPES = frozenset({"ten_benh", "trieu_chung_benh"})
MODEL_TO_OUTPUT_TYPE = {
    "ten_benh": "CHẨN_ĐOÁN",
    "trieu_chung_benh": "TRIỆU_CHỨNG",
}
OUTPUT_TO_MODEL_TYPE = {
    output_type: model_type
    for model_type, output_type in MODEL_TO_OUTPUT_TYPE.items()
}
DEFAULT_THRESHOLDS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.98, 0.99)


def normalize_surface(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def decode_words(
    labels_and_scores: dict[int, tuple[str, float]],
    word_count: int,
) -> dict[tuple[int, int, str], float]:
    spans: dict[tuple[int, int, str], float] = {}
    active_start: int | None = None
    active_type: str | None = None
    confidences: list[float] = []

    def flush(end: int) -> None:
        nonlocal active_start, active_type, confidences
        if active_start is not None and active_type in TARGET_TYPES:
            spans[(active_start, end, active_type)] = (
                sum(confidences) / len(confidences)
            )
        active_start, active_type, confidences = None, None, []

    for word_index in range(word_count + 1):
        label, confidence = labels_and_scores.get(word_index, ("O", 0.0))
        if label == "O" or "-" not in label or word_index == word_count:
            flush(word_index)
            continue
        prefix, entity_type = label.split("-", 1)
        if entity_type not in TARGET_TYPES:
            flush(word_index)
            continue
        if prefix == "B" or active_type != entity_type:
            flush(word_index)
            active_start, active_type = word_index, entity_type
        elif active_start is None:
            active_start, active_type = word_index, entity_type
        confidences.append(confidence)
    return spans


@torch.inference_mode()
def predict_sentences(
    model_name: str,
    sentences: list[Sentence],
    *,
    device: torch.device,
    max_length: int,
    stride: int,
    text_batch_size: int,
    inference_batch_size: int,
) -> list[dict[tuple[int, int, str], float]]:
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(model_name).to(device)
    model.eval()
    id_to_label = {
        int(index): label for index, label in model.config.id2label.items()
    }
    predictions: list[dict[tuple[int, int, str], float]] = []

    for text_start in range(0, len(sentences), text_batch_size):
        sentence_batch = sentences[text_start : text_start + text_batch_size]
        encoded = tokenizer(
            [sentence.tokens for sentence in sentence_batch],
            is_split_into_words=True,
            return_offsets_mapping=True,
            return_overflowing_tokens=True,
            truncation=True,
            max_length=max_length,
            stride=stride,
            padding=True,
            return_tensors="pt",
        )
        offsets = encoded.pop("offset_mapping")
        sample_mapping = encoded.pop("overflow_to_sample_mapping")
        word_ids = [
            encoded.word_ids(batch_index=index)
            for index in range(encoded["input_ids"].shape[0])
        ]
        per_sentence: list[dict[int, tuple[str, float]]] = [
            {} for _ in sentence_batch
        ]
        for chunk_start in range(
            0,
            encoded["input_ids"].shape[0],
            inference_batch_size,
        ):
            chunk_end = chunk_start + inference_batch_size
            model_inputs = {
                key: value[chunk_start:chunk_end].to(device)
                for key, value in encoded.items()
            }
            with torch.autocast(
                device_type=device.type,
                dtype=torch.float16,
                enabled=device.type == "cuda",
            ):
                probabilities = torch.softmax(
                    model(**model_inputs).logits,
                    dim=-1,
                )
            scores, label_ids = probabilities.max(dim=-1)
            scores = scores.cpu()
            label_ids = label_ids.cpu()
            for local_chunk in range(label_ids.shape[0]):
                chunk_index = chunk_start + local_chunk
                sample_index = int(sample_mapping[chunk_index])
                for token_index, word_index in enumerate(word_ids[chunk_index]):
                    token_start, token_end = offsets[
                        chunk_index,
                        token_index,
                    ].tolist()
                    if (
                        word_index is None
                        or token_end <= token_start
                        or token_start != 0
                    ):
                        continue
                    confidence = float(scores[local_chunk, token_index])
                    previous = per_sentence[sample_index].get(word_index)
                    if previous is None or confidence > previous[1]:
                        per_sentence[sample_index][word_index] = (
                            id_to_label[int(label_ids[local_chunk, token_index])],
                            confidence,
                        )
        predictions.extend(
            decode_words(word_predictions, len(sentence.tokens))
            for sentence, word_predictions in zip(
                sentence_batch,
                per_sentence,
            )
        )
        print(
            f"{model_name}: {min(text_start + text_batch_size, len(sentences))}"
            f"/{len(sentences)}",
            flush=True,
        )

    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return predictions


def score(
    gold: list[set[tuple[int, int, str]]],
    predicted: list[set[tuple[int, int, str]]],
) -> dict[str, float | int]:
    tp = fp = fn = 0
    for gold_spans, predicted_spans in zip(gold, predicted):
        tp += len(gold_spans & predicted_spans)
        fp += len(predicted_spans - gold_spans)
        fn += len(gold_spans - predicted_spans)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "predicted": tp + fp,
    }


def threshold_predictions(
    predictions: list[dict[tuple[int, int, str], float]],
    threshold: float,
) -> list[set[tuple[int, int, str]]]:
    return [
        {span for span, confidence in sentence.items() if confidence >= threshold}
        for sentence in predictions
    ]


def consensus_predictions(
    first: list[dict[tuple[int, int, str], float]],
    second: list[dict[tuple[int, int, str], float]],
    first_threshold: float,
    second_threshold: float,
) -> list[set[tuple[int, int, str]]]:
    output: list[set[tuple[int, int, str]]] = []
    for first_sentence, second_sentence in zip(first, second):
        output.append(
            {
                span
                for span in first_sentence.keys() & second_sentence.keys()
                if first_sentence[span] >= first_threshold
                and second_sentence[span] >= second_threshold
            }
        )
    return output


def pipeline_baseline_predictions(
    sentences: list[Sentence],
    teacher_predictions: list[dict[tuple[int, int, str], float]],
) -> list[set[tuple[int, int, str]]]:
    output: list[set[tuple[int, int, str]]] = []
    for sentence, predictions in zip(sentences, teacher_predictions):
        raw_text = " ".join(sentence.tokens)
        starts: list[int] = []
        ends: list[int] = []
        cursor = 0
        for token in sentence.tokens:
            starts.append(cursor)
            cursor += len(token)
            ends.append(cursor)
            cursor += 1
        teacher_spans = [
            {
                "start": starts[start],
                "end": ends[end - 1],
                "type": MODEL_TO_OUTPUT_TYPE[entity_type],
                "confidence": confidence,
                "text": raw_text[starts[start] : ends[end - 1]],
            }
            for (start, end, entity_type), confidence in predictions.items()
        ]
        start_to_word = {value: index for index, value in enumerate(starts)}
        end_to_word = {value: index + 1 for index, value in enumerate(ends)}
        baseline: set[tuple[int, int, str]] = set()
        for entity in turn2_v16.extract(
            raw_text,
            teacher_spans,
            "diagnosis-precision",
        ):
            entity_type = OUTPUT_TO_MODEL_TYPE.get(entity["type"])
            start, end = entity["position"]
            if (
                entity_type is not None
                and start in start_to_word
                and end in end_to_word
            ):
                baseline.add(
                    (
                        start_to_word[start],
                        end_to_word[end],
                        entity_type,
                    )
                )
        output.append(baseline)
    return output


def pipeline_profile_metrics(
    sentences: list[Sentence],
    first_predictions: list[dict[tuple[int, int, str], float]],
    second_predictions: list[dict[tuple[int, int, str], float]],
) -> dict:
    gold = [
        {span for span in entity_set(sentence.labels) if span[2] in TARGET_TYPES}
        for sentence in sentences
    ]
    baseline_all: list[set[tuple[int, int, str]]] = []
    profiles_all: dict[str, list[set[tuple[int, int, str]]]] = {
        profile: [] for profile in turn2_v17.PROFILES
    }

    for sentence, first, second in zip(
        sentences,
        first_predictions,
        second_predictions,
    ):
        raw_text = " ".join(sentence.tokens)
        starts: list[int] = []
        ends: list[int] = []
        cursor = 0
        for token in sentence.tokens:
            starts.append(cursor)
            cursor += len(token)
            ends.append(cursor)
            cursor += 1
        start_to_word = {value: index for index, value in enumerate(starts)}
        end_to_word = {value: index + 1 for index, value in enumerate(ends)}

        def teacher_spans(
            predictions: dict[tuple[int, int, str], float],
        ) -> list[dict]:
            return [
                {
                    "start": starts[start],
                    "end": ends[end - 1],
                    "type": MODEL_TO_OUTPUT_TYPE[entity_type],
                    "confidence": confidence,
                    "text": raw_text[starts[start] : ends[end - 1]],
                }
                for (start, end, entity_type), confidence in predictions.items()
            ]

        def word_spans(entities: list[dict]) -> set[tuple[int, int, str]]:
            output: set[tuple[int, int, str]] = set()
            for entity in entities:
                entity_type = OUTPUT_TO_MODEL_TYPE.get(entity["type"])
                start, end = entity["position"]
                if (
                    entity_type is not None
                    and start in start_to_word
                    and end in end_to_word
                ):
                    output.add(
                        (
                            start_to_word[start],
                            end_to_word[end],
                            entity_type,
                        )
                    )
            return output

        first_teacher = teacher_spans(first)
        second_teacher = teacher_spans(second)
        baseline = word_spans(
            turn2_v16.extract(
                raw_text,
                first_teacher,
                "diagnosis-precision",
            )
        )
        baseline_all.append(baseline)
        for profile in turn2_v17.PROFILES:
            profiles_all[profile].append(
                word_spans(
                    turn2_v17.extract(
                        raw_text,
                        first_teacher,
                        second_teacher,
                        profile,
                    )
                )
            )

    baseline_metrics = score(gold, baseline_all)
    profiles: dict[str, dict] = {}
    for profile, predictions in profiles_all.items():
        metrics = score(gold, predictions)
        added = removed = 0
        for baseline, candidate in zip(baseline_all, predictions):
            added += len(candidate - baseline)
            removed += len(baseline - candidate)
        profiles[profile] = {
            **metrics,
            "f1_delta": metrics["f1"] - baseline_metrics["f1"],
            "spans_added": added,
            "spans_removed": removed,
        }
    return {
        "baseline": baseline_metrics,
        "profiles": profiles,
    }


def calibrate_pipeline_extras(
    sentences: list[Sentence],
    first: list[dict[tuple[int, int, str], float]],
    second: list[dict[tuple[int, int, str], float]],
    thresholds: tuple[float, ...],
) -> list[dict]:
    gold = [
        {span for span in entity_set(sentence.labels) if span[2] in TARGET_TYPES}
        for sentence in sentences
    ]
    baseline = pipeline_baseline_predictions(sentences, first)
    rows: list[dict] = []
    for first_threshold in thresholds:
        for second_threshold in thresholds:
            consensus = consensus_predictions(
                first,
                second,
                first_threshold,
                second_threshold,
            )
            extras = [
                {
                    span
                    for span in consensus_sentence - baseline_sentence
                    if span[2] == "trieu_chung_benh"
                }
                for consensus_sentence, baseline_sentence in zip(
                    consensus,
                    baseline,
                )
            ]
            rows.append(
                {
                    "first_threshold": first_threshold,
                    "second_threshold": second_threshold,
                    **score(gold, extras),
                }
            )
    rows.sort(
        key=lambda row: (
            row["precision"],
            row["predicted"],
        ),
        reverse=True,
    )
    return rows


def calibrate_split(
    sentences: list[Sentence],
    first: list[dict[tuple[int, int, str], float]],
    second: list[dict[tuple[int, int, str], float]],
    thresholds: tuple[float, ...],
) -> dict:
    gold = [
        {span for span in entity_set(sentence.labels) if span[2] in TARGET_TYPES}
        for sentence in sentences
    ]
    individual = {
        "first": {
            str(threshold): score(
                gold,
                threshold_predictions(first, threshold),
            )
            for threshold in thresholds
        },
        "second": {
            str(threshold): score(
                gold,
                threshold_predictions(second, threshold),
            )
            for threshold in thresholds
        },
    }
    consensus: list[dict] = []
    for first_threshold in thresholds:
        for second_threshold in thresholds:
            metrics = score(
                gold,
                consensus_predictions(
                    first,
                    second,
                    first_threshold,
                    second_threshold,
                ),
            )
            consensus.append(
                {
                    "first_threshold": first_threshold,
                    "second_threshold": second_threshold,
                    **metrics,
                }
            )
    consensus.sort(
        key=lambda row: (
            row["f1"],
            row["precision"],
            row["predicted"],
        ),
        reverse=True,
    )
    return {
        "individual": individual,
        "consensus": consensus,
        "pipeline_symptom_extras": calibrate_pipeline_extras(
            sentences,
            first,
            second,
            thresholds,
        ),
        "pipeline_profiles": pipeline_profile_metrics(
            sentences,
            first,
            second,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--first-model", required=True)
    parser.add_argument("--second-model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--splits", nargs="+", default=["dev", "test"])
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--stride", type=int, default=32)
    parser.add_argument("--text-batch-size", type=int, default=64)
    parser.add_argument("--inference-batch-size", type=int, default=32)
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        default=list(DEFAULT_THRESHOLDS),
    )
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for consensus calibration")
    device = torch.device("cuda")
    thresholds = tuple(sorted(set(args.thresholds)))

    output: dict[str, dict] = {
        "first_model": args.first_model,
        "second_model": args.second_model,
        "thresholds": thresholds,
        "splits": {},
    }
    for split in args.splits:
        sentences = read_conll(args.data / f"{split}.txt")
        first = predict_sentences(
            args.first_model,
            sentences,
            device=device,
            max_length=args.max_length,
            stride=args.stride,
            text_batch_size=args.text_batch_size,
            inference_batch_size=args.inference_batch_size,
        )
        second = predict_sentences(
            args.second_model,
            sentences,
            device=device,
            max_length=args.max_length,
            stride=args.stride,
            text_batch_size=args.text_batch_size,
            inference_batch_size=args.inference_batch_size,
        )
        output["splits"][split] = calibrate_split(
            sentences,
            first,
            second,
            thresholds,
        )
        print(
            json.dumps(
                {
                    split: output["splits"][split]["consensus"][:5],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
