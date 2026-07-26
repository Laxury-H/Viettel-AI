# Deep research comparison — Round 1

## Decision

Keep `submission/candidate_v19_xlmr-additive-85.zip` as the control. It is the
highest confirmed artifact at **39.3683**. Do not replace it with a broad LLM
pipeline, generic ConText rules, or unrestricted dense retrieval.

## Evidence from the three supplied designs

| Component | Research proposal | Competition-safe decision |
|---|---|---|
| Offset handling | Preserve raw text and map normalized offsets back | Keep; this is already implemented in `turn2_v9.NormalizedText`. |
| Vietnamese segmentation | VnCoreNLP/PhoBERT preprocessing | Do not segment the final text; segmentation can shift character spans. Use subword tokenization with raw-offset decoding. |
| NER | PhoBERT/ViHealthBERT/ViPubMedDeBERTa, span or CRF | Keep the deterministic extractor plus BamiBERT/ViPubMed/XLM-R teacher gates. Exact-span consensus is safer than a free-form decoder. |
| Assertion | NegEx/ConText scope plus a classifier | Keep the existing conservative section/trigger logic. Broad window expansion previously changed assertions without public-score evidence. |
| Linking | BM25 + SapBERT/bi-encoder + LLM reranker | Do not deploy as-is: the current package has no complete ICD/RxNorm index, and external APIs are prohibited by the round rules. Preserve the validated alias/codebook and high-confidence dosage rules. |
| Relations | Lab-name/result or symptom/diagnosis graph | No score-bearing relation field exists in Round 1 output; adding one would be invalid or ignored. |
| Synthetic data | SNR/LLM-generated clinical notes | Useful for future supervised training, but no labeled assertion/candidate gold is available here; noisy silver data is not evidence for a submission change. |

The scoring weights make candidate mapping important (`0.4`), but the public
ablations show that changing candidate codes without gold evidence is
high-variance. The best verified change so far came from precision-gated
diagnosis candidates and exact-span teacher consensus, not from broad
retrieval.

## New seed experiment

An independent XLM-R LoRA run (seed `123`, 12 requested epochs) was trained on
the official ViMedNER splits and evaluated before touching the submission:

- target strict F1: `0.6266` dev / `0.6482` test;
- seed `42` reference: `0.6803` dev / `0.6837` test;
- on all 100 current records, seed `123` produced no non-overlapping
  high-confidence symptom additions or safe boundary replacements relative to
  V19.

Therefore seed `123` is retained as an ablation record, not a candidate.

## Submission safety

The platform currently shows five submissions on 25/07/2026
(03:05, 03:15, 03:25, 03:36 plus the earlier 01:25 submission). The form
limits submissions to five per day and 600 seconds between attempts. No new
ZIP should be uploaded until the quota resets; this avoids wasting a slot on an
unvalidated artifact.

