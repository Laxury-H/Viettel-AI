#!/usr/bin/env python3
"""Evaluate any ViMedNER token-classification checkpoint consistently."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForTokenClassification, AutoTokenizer

try:
    from scripts.train_vimedner import EncodedDataset, evaluate, read_conll
except ModuleNotFoundError:
    from train_vimedner import EncodedDataset, evaluate, read_conll


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--splits", nargs="+", default=["dev", "test"])
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
    )
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(args.model)
    id_to_label = {
        int(index): label for index, label in model.config.id2label.items()
    }
    label_to_id = {label: index for index, label in id_to_label.items()}
    if args.device == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device_name = args.device
    if device_name == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but is unavailable")
    device = torch.device(device_name)
    model.to(device)

    results: dict[str, dict] = {}
    for split in args.splits:
        sentences = read_conll(args.data / f"{split}.txt")
        missing = sorted(
            {
                label
                for sentence in sentences
                for label in sentence.labels
                if label not in label_to_id
            }
        )
        if missing:
            raise SystemExit(
                f"{args.model} is missing labels required by {split}: {missing}"
            )
        dataset = EncodedDataset(
            sentences,
            tokenizer,
            label_to_id,
            args.max_length,
        )
        loader = DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=False,
        )
        results[split] = evaluate(model, loader, id_to_label, device)
        print(
            json.dumps(
                {split: results[split]},
                ensure_ascii=False,
            ),
            flush=True,
        )

    payload = {
        "model": args.model,
        "device": device_name,
        "max_length": args.max_length,
        "results": results,
    }
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
