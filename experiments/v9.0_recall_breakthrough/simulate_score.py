#!/usr/bin/env python3
"""Mô phỏng điểm theo ĐÚNG công thức chính thức (PDF đề bài, trang 5).

    final_score      = 0.3·text_score + 0.3·assertions_score + 0.4·candidates_score
    text_score       = (1/N)·Σ_i (1 − WER(i))
    assertions_score = (1/N)·Σ_i J_assertions(i)
    candidates_score = Σ_i J_cand(i)·w_i / Σ_i w_i ,  w_i = Σ_{k∈i}(len(gold_cand(k))+1)

    J_X = 1 nếu gold rỗng và pred rỗng; 0 nếu gold rỗng và pred khác rỗng;
          |∩|/|∪| trong các trường hợp còn lại.

Không có ground truth nên đây KHÔNG phải công cụ dự đoán điểm tuyệt đối. Nó
dùng để trả lời một câu hỏi hẹp nhưng quyết định: *với xác suất p mà một khái
niệm thêm vào thực sự nằm trong đáp án, thay đổi này làm điểm tăng hay giảm?*

Mô hình được hiệu chuẩn sao cho cấu hình baseline tái tạo đúng bộ ba số công bố
(WER 55.4298 / J_a 51.4670 / J_c 32.9653) của bài 41.9973 điểm.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

WEIGHTS = (0.3, 0.3, 0.4)


def load(directory: Path) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for path in directory.glob("*.json"):
        if path.stem.isdigit():
            out[int(path.stem)] = json.loads(path.read_text(encoding="utf-8"))
    return out


def score_run(
    preds: dict[int, list[dict]],
    baseline: dict[int, list[dict]],
    *,
    gold_ratio: float,
    p_base: float,
    p_add: float,
    a_bar: float,
    c_bar: float,
) -> dict[str, float]:
    """Ước lượng ba metric dưới một giả định về đáp án.

    gold_ratio : |gold_i| / |baseline_i|, tỉ lệ quy mô đáp án so với bài nền
    p_base     : xác suất một khái niệm của bài nền khớp đáp án
    p_add      : xác suất một khái niệm V9 thêm vào khớp đáp án
    a_bar      : Jaccard assertion trung bình trên cặp đã khớp
    c_bar      : Jaccard candidate trung bình trên cặp đã khớp CÓ mã
    """
    text_terms: list[float] = []
    assert_terms: list[float] = []
    cand_num = 0.0
    cand_den = 0.0

    for doc_id, pred in preds.items():
        base = baseline.get(doc_id, [])
        n_base = len(base)
        n_add = max(0, len(pred) - n_base)
        gold_n = max(1.0, gold_ratio * n_base)

        tp = min(gold_n, p_base * n_base + p_add * n_add)
        union = gold_n + len(pred) - tp

        # --- assertions: trung bình Jaccard theo khái niệm trong hợp
        assert_terms.append(tp * a_bar / union if union else 1.0)

        # --- candidates: Jaccard trên TẬP MÃ cấp tài liệu.
        # Đã kiểm chứng thực nghiệm: hai bản nộp lệch nhau 54 thực thể TRIỆU_CHỨNG
        # trên 22 tài liệu vẫn cho J_candidates giống hệt (26.9369), nên metric này
        # KHÔNG phản ứng với khái niệm không mang mã.
        our_codes = {c for concept in pred for c in concept.get("candidates") or []}
        n_ours = len(our_codes)
        n_gold = max(1.0, gold_ratio * len({
            c for concept in base for c in concept.get("candidates") or []
        } or {""}))
        hit = min(n_ours, n_gold) * c_bar
        j_cand = hit / (n_ours + n_gold - hit) if (n_ours + n_gold - hit) else 1.0
        weight = n_gold + gold_n
        cand_num += j_cand * weight
        cand_den += weight

        # --- text: WER ~ (từ bỏ sót + từ thừa) / từ đáp án
        pred_words = sum(len(c["text"].split()) for c in pred)
        w_per = pred_words / len(pred) if pred else 3.0
        gold_words = gold_n * w_per
        deletions = (gold_n - tp) * w_per
        insertions = (len(pred) - tp) * w_per
        wer = min(1.0, (deletions + insertions) / gold_words) if gold_words else 1.0
        text_terms.append(1 - wer)

    text = 100 * sum(text_terms) / len(text_terms)
    assertions = 100 * sum(assert_terms) / len(assert_terms)
    candidates = 100 * cand_num / cand_den if cand_den else 0.0
    final = WEIGHTS[0] * text + WEIGHTS[1] * assertions + WEIGHTS[2] * candidates
    return {"text": text, "assertions": assertions, "candidates": candidates, "final": final}


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--gold-ratio", type=float, default=1.45)
    parser.add_argument("--p-base", type=float, default=0.86)
    parser.add_argument("--a-bar", type=float, default=0.92)
    parser.add_argument("--c-bar", type=float, default=0.46)
    args = parser.parse_args()

    base = load(args.baseline)
    cand = load(args.candidate)

    ref = score_run(
        base, base,
        gold_ratio=args.gold_ratio, p_base=args.p_base, p_add=0.0,
        a_bar=args.a_bar, c_bar=args.c_bar,
    )
    print("Hiệu chuẩn trên bài nền (mục tiêu: WER 55.43 / J_a 51.47 / J_c 32.97 / final 41.9973)")
    print(f"  mô hình: text={ref['text']:.2f} (WER {100 - ref['text']:.2f})  "
          f"J_a={ref['assertions']:.2f}  J_c={ref['candidates']:.2f}  final={ref['final']:.2f}")
    print()

    n_base = sum(len(v) for v in base.values())
    n_cand = sum(len(v) for v in cand.values())
    print(f"Bài nền {n_base} khái niệm  ->  bài dự tuyển {n_cand} (+{n_cand - n_base})")
    print()
    print(f"{'p_add':>7} {'text':>8} {'J_assert':>10} {'J_cand':>8} {'final':>8} {'Δ vs nền':>10}")
    print("-" * 56)
    for p_add in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        got = score_run(
            cand, base,
            gold_ratio=args.gold_ratio, p_base=args.p_base, p_add=p_add,
            a_bar=args.a_bar, c_bar=args.c_bar,
        )
        delta = got["final"] - ref["final"]
        mark = "  <== hòa vốn" if abs(delta) < 0.35 else ""
        print(f"{p_add:7.2f} {got['text']:8.2f} {got['assertions']:10.2f} "
              f"{got['candidates']:8.2f} {got['final']:8.2f} {delta:+10.2f}{mark}")
    print()
    print("Đọc bảng: p_add là tỉ lệ khái niệm V9 thêm vào thực sự có trong đáp án.")
    print("Chừng nào p_add còn trên điểm hòa vốn thì thay đổi là có lợi.")


if __name__ == "__main__":
    main()
