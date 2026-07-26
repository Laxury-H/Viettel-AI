# Round 1 rules — evidence ingestion record

Status: user-provided competition text, ingested 2026-07-20.

Authoritative source supplied by the competition participant and summarized in this repository.

SHA-256: `dc156d98b65e8b4b3357aff6c13940fe7b05e91809d34f26df3d0c98b372418e`

## Confirmed facts extracted from the source

- Submit one file named `output.zip`.
- After extraction, JSON files are located at `output/1.json` through `output/100.json`.
- Records use `text`, `type`, `assertions`, `position`, and conditionally `candidates`.
- The official example omits `candidates` on 8/19 symptom records and includes `assertions: []`.
- Observed types: `THUỐC`, `TRIỆU_CHỨNG`; `CHẨN_ĐOÁN` is named in the wrong-type example.
- Observed assertion: `isHistorical`.
- Text uses WER; assertions and candidates use Jaccard similarity.
- Final weights are text 0.3, assertions 0.3, candidates 0.4.
- Empty ground truth and empty prediction receive Jaccard 1; empty ground truth and non-empty prediction receive 0.
- A correct text with the wrong type creates two zero-scored concepts, one missed and one new prediction.
- For LLM/agent solutions, external APIs are prohibited and a self-hosted model is limited to 9B parameters.
- Top teams must provide processing/training/inference code, used data, model weights, and an installation README for private-test reproduction.

## Integrity caveat

The displayed input does not reproduce the example positions: all 19 displayed spans fail `input[start:end] == text`, while every `end - start` equals the corresponding text length. The visible representation likely lost formatting characters. Therefore the guide confirms end-exclusive span lengths and rules out UTF-8-byte lengths, but it does not distinguish Unicode code points from UTF-16 units or prove the index base against a lossless raw input.

This file is a traceable extraction record, not a replacement for the original attachment.
