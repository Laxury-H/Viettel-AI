#!/usr/bin/env python3
"""Fine-tune and evaluate a token classifier on the official ViMedNER splits.

The script intentionally uses a small, explicit PyTorch loop so the exact
training/evaluation behavior is stable across Hugging Face Trainer releases.
Evaluation is strict entity-level BIO micro F1 on original input words.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)


@dataclass(frozen=True)
class Sentence:
    tokens: list[str]
    labels: list[str]


def read_conll(path: Path) -> list[Sentence]:
    sentences: list[Sentence] = []
    tokens: list[str] = []
    labels: list[str] = []
    skipped_empty_tokens = 0

    def flush() -> None:
        nonlocal tokens, labels
        if tokens:
            sentences.append(Sentence(tokens, labels))
        tokens, labels = [], []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines() + [""],
        start=1,
    ):
        if not line.strip():
            flush()
            continue
        fields = line.rsplit(maxsplit=1)
        if len(fields) != 2:
            if line[:1].isspace():
                skipped_empty_tokens += 1
                continue
            raise ValueError(f"{path}:{line_number}: malformed CoNLL row")
        token, label = fields
        token = token.strip()
        if not token:
            skipped_empty_tokens += 1
            continue
        tokens.append(token)
        labels.append(label)
    if skipped_empty_tokens:
        print(f"{path}: skipped {skipped_empty_tokens} empty token rows")
    return sentences


def entity_set(labels: list[str]) -> set[tuple[int, int, str]]:
    entities: set[tuple[int, int, str]] = set()
    active_start: int | None = None
    active_type: str | None = None

    def flush(end: int) -> None:
        nonlocal active_start, active_type
        if active_start is not None and active_type is not None:
            entities.add((active_start, end, active_type))
        active_start, active_type = None, None

    for index, label in enumerate(labels + ["O"]):
        if label == "O" or "-" not in label:
            flush(index)
            continue
        prefix, entity_type = label.split("-", 1)
        if prefix == "B" or active_type != entity_type:
            flush(index)
            active_start, active_type = index, entity_type
        elif active_start is None:
            active_start, active_type = index, entity_type
    return entities


class EncodedDataset(Dataset):
    def __init__(
        self,
        sentences: list[Sentence],
        tokenizer,
        label_to_id: dict[str, int],
        max_length: int,
    ) -> None:
        self.features: list[dict[str, torch.Tensor]] = []
        for sentence in sentences:
            encoded = tokenizer(
                sentence.tokens,
                is_split_into_words=True,
                max_length=max_length,
                truncation=True,
                padding="max_length",
                return_attention_mask=True,
            )
            word_ids = encoded.word_ids()
            aligned = [-100] * len(word_ids)
            previous_word_id: int | None = None
            for token_index, word_id in enumerate(word_ids):
                if word_id is None or word_id == previous_word_id:
                    continue
                aligned[token_index] = label_to_id[sentence.labels[word_id]]
                previous_word_id = word_id
            feature = {
                key: torch.tensor(value, dtype=torch.long)
                for key, value in encoded.items()
            }
            feature["labels"] = torch.tensor(aligned, dtype=torch.long)
            self.features.append(feature)

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        return self.features[index]


def strict_metrics(
    gold_sequences: list[list[str]],
    predicted_sequences: list[list[str]],
) -> dict:
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0}
    )
    for gold, predicted in zip(gold_sequences, predicted_sequences):
        gold_entities = entity_set(gold)
        predicted_entities = entity_set(predicted)
        for entity in gold_entities & predicted_entities:
            counts[entity[2]]["tp"] += 1
        for entity in predicted_entities - gold_entities:
            counts[entity[2]]["fp"] += 1
        for entity in gold_entities - predicted_entities:
            counts[entity[2]]["fn"] += 1

    def scores(tp: int, fp: int, fn: int) -> dict[str, float | int]:
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
        }

    total = {
        name: sum(values[name] for values in counts.values())
        for name in ("tp", "fp", "fn")
    }
    # The downstream competition pipeline consumes only disease and symptom
    # spans from this teacher. Select checkpoints on that exact target instead
    # of allowing unrelated ViMedNER labels to decide which model is kept.
    target_types = ("ten_benh", "trieu_chung_benh")
    target = {
        name: sum(counts.get(entity_type, {}).get(name, 0) for entity_type in target_types)
        for name in ("tp", "fp", "fn")
    }
    return {
        "micro": scores(total["tp"], total["fp"], total["fn"]),
        "target": scores(target["tp"], target["fp"], target["fn"]),
        "by_type": {
            entity_type: scores(**values)
            for entity_type, values in sorted(counts.items())
        },
    }


@torch.inference_mode()
def evaluate(
    model,
    loader: DataLoader,
    id_to_label: dict[int, str],
    device: torch.device,
) -> dict:
    model.eval()
    losses: list[float] = []
    gold_sequences: list[list[str]] = []
    predicted_sequences: list[list[str]] = []
    for batch in loader:
        batch = {key: value.to(device) for key, value in batch.items()}
        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=device.type == "cuda",
        ):
            outputs = model(**batch)
        losses.append(float(outputs.loss.detach().cpu()))
        predictions = outputs.logits.argmax(dim=-1)
        for gold_row, predicted_row in zip(batch["labels"], predictions):
            gold: list[str] = []
            predicted: list[str] = []
            for gold_id, predicted_id in zip(gold_row.tolist(), predicted_row.tolist()):
                if gold_id == -100:
                    continue
                gold.append(id_to_label[gold_id])
                predicted.append(id_to_label[predicted_id])
            gold_sequences.append(gold)
            predicted_sequences.append(predicted)
    metrics = strict_metrics(gold_sequences, predicted_sequences)
    metrics["loss"] = sum(losses) / len(losses)
    metrics["sentences"] = len(gold_sequences)
    return metrics


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--eval-batch-size", type=int, default=16)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument(
        "--lora-rank",
        type=int,
        default=0,
        help="Enable LoRA with this rank; zero keeps ordinary full fine-tuning.",
    )
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.1)
    args = parser.parse_args()

    seed_everything(args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    labels = [
        line.strip()
        for line in (args.data / "labels.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    label_to_id = {label: index for index, label in enumerate(labels)}
    id_to_label = {index: label for label, index in label_to_id.items()}
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    model_kwargs = {
        "num_labels": len(labels),
        "id2label": id_to_label,
        "label2id": label_to_id,
        "ignore_mismatched_sizes": True,
    }
    if args.lora_rank:
        # The XLM-R embedding table is large. Keeping the frozen backbone in
        # fp16 and training compact adapters makes the stronger encoder fit on
        # a 4 GB consumer GPU without quantizing its representations.
        model_kwargs["dtype"] = torch.float16
    model = AutoModelForTokenClassification.from_pretrained(
        args.model,
        **model_kwargs,
    )
    if args.lora_rank:
        try:
            from peft import LoraConfig, TaskType, get_peft_model
        except ImportError as error:
            raise SystemExit(
                "LoRA training requires `pip install peft`"
            ) from error
        model = get_peft_model(
            model,
            LoraConfig(
                task_type=TaskType.TOKEN_CLS,
                r=args.lora_rank,
                lora_alpha=args.lora_alpha,
                lora_dropout=args.lora_dropout,
                target_modules=["query", "value"],
                bias="none",
            ),
        )
        # GradScaler cannot unscale fp16 leaf gradients. Preserve the frozen
        # backbone in fp16, but keep the tiny trainable adapters and classifier
        # in fp32 for stable mixed-precision optimization.
        for parameter in model.parameters():
            if parameter.requires_grad:
                parameter.data = parameter.data.float()
        model.print_trainable_parameters()
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()

    raw = {
        split: read_conll(args.data / f"{split}.txt")
        for split in ("train", "dev", "test")
    }
    datasets = {
        split: EncodedDataset(
            sentences,
            tokenizer,
            label_to_id,
            args.max_length,
        )
        for split, sentences in raw.items()
    }
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        datasets["train"],
        batch_size=args.batch_size,
        shuffle=True,
        generator=generator,
    )
    dev_loader = DataLoader(
        datasets["dev"],
        batch_size=args.eval_batch_size,
        shuffle=False,
    )
    test_loader = DataLoader(
        datasets["test"],
        batch_size=args.eval_batch_size,
        shuffle=False,
    )

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this training run")
    device = torch.device("cuda")
    model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    updates_per_epoch = math.ceil(
        len(train_loader) / args.gradient_accumulation
    )
    total_updates = updates_per_epoch * args.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=round(total_updates * args.warmup_ratio),
        num_training_steps=total_updates,
    )
    scaler = torch.amp.GradScaler("cuda")
    history: list[dict] = []
    best_target_f1 = -1.0
    best_micro_f1 = -1.0
    stale_epochs = 0
    best_dir = args.output / "best"
    best_adapter_dir = args.output / "best_adapter"

    for epoch in range(1, args.epochs + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        train_losses: list[float] = []
        for batch_index, batch in enumerate(train_loader, start=1):
            batch = {key: value.to(device) for key, value in batch.items()}
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                outputs = model(**batch)
                loss = outputs.loss / args.gradient_accumulation
            scaler.scale(loss).backward()
            train_losses.append(float(loss.detach().cpu()) * args.gradient_accumulation)
            if (
                batch_index % args.gradient_accumulation == 0
                or batch_index == len(train_loader)
            ):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scale_before_step = scaler.get_scale()
                scaler.step(optimizer)
                scaler.update()
                # GradScaler may skip optimizer.step() after detecting an
                # overflow. Do not consume a scheduler step in that case.
                if scaler.get_scale() >= scale_before_step:
                    scheduler.step()
                optimizer.zero_grad(set_to_none=True)

        dev_metrics = evaluate(model, dev_loader, id_to_label, device)
        record = {
            "epoch": epoch,
            "train_loss": sum(train_losses) / len(train_losses),
            "learning_rate": scheduler.get_last_lr()[0],
            "dev": dev_metrics,
        }
        history.append(record)
        current_target_f1 = float(dev_metrics["target"]["f1"])
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if current_target_f1 > best_target_f1:
            best_target_f1 = current_target_f1
            best_micro_f1 = float(dev_metrics["micro"]["f1"])
            stale_epochs = 0
            checkpoint_dir = best_adapter_dir if args.lora_rank else best_dir
            model.save_pretrained(checkpoint_dir, safe_serialization=True)
            tokenizer.save_pretrained(checkpoint_dir)
        else:
            stale_epochs += 1
            if stale_epochs >= args.patience:
                break

    del model, optimizer, scheduler, scaler
    torch.cuda.empty_cache()
    if args.lora_rank:
        from peft import PeftModel

        base_model = AutoModelForTokenClassification.from_pretrained(
            args.model,
            **model_kwargs,
        )
        best_model = PeftModel.from_pretrained(base_model, best_adapter_dir).to(device)
    else:
        best_model = AutoModelForTokenClassification.from_pretrained(best_dir).to(device)
    test_metrics = evaluate(best_model, test_loader, id_to_label, device)
    if args.lora_rank:
        merged_model = best_model.merge_and_unload()
        merged_model.save_pretrained(best_dir, safe_serialization=True)
        tokenizer.save_pretrained(best_dir)
    summary = {
        "model": args.model,
        "seed": args.seed,
        "configuration": {
            "epochs_requested": args.epochs,
            "epochs_completed": len(history),
            "patience": args.patience,
            "max_length": args.max_length,
            "batch_size": args.batch_size,
            "gradient_accumulation": args.gradient_accumulation,
            "effective_batch_size": (
                args.batch_size * args.gradient_accumulation
            ),
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "warmup_ratio": args.warmup_ratio,
            "lora_rank": args.lora_rank,
            "lora_alpha": args.lora_alpha if args.lora_rank else None,
            "lora_dropout": args.lora_dropout if args.lora_rank else None,
        },
        "best_dev_target_f1": best_target_f1,
        "best_checkpoint_dev_micro_f1": best_micro_f1,
        "test": test_metrics,
        "history": history,
    }
    (args.output / "metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
