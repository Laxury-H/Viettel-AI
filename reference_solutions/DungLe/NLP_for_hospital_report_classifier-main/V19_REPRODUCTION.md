# V19 XLM-R consensus reproduction

V19 keeps the scored V18 ZIP immutable and only adds `TRIỆU_CHỨNG` spans when
two independent models predict the exact same character span:

- `cbc-528a/BamiBERT-ViMedNER` confidence >= 0.98.
- the local `FacebookAI/xlm-roberta-base` LoRA model confidence >= the selected
  profile threshold.
- the proposal does not overlap any V18 entity.
- the rule-based assertion inference returns an empty assertion list.

This makes the public experiments nested and attributable. Boundary replacement
profiles were rejected after the `xlmr-safe-94` public score decreased.

## Environment and training

```powershell
python -m pip install -r .\requirements-train.txt

git clone https://github.com/tdtrinh11/ViMedNer.git .\.work\ViMedNer
git -C .\.work\ViMedNer checkout ce3deaa13837b5964c1fc8a83098d82418482a41

python .\scripts\train_vimedner.py `
  --data .\.work\ViMedNer\data `
  --model FacebookAI/xlm-roberta-base `
  --output .\.work\xlmr-base-lora-r16-seed42-gpu2 `
  --seed 42 --epochs 30 --patience 30 `
  --max-length 128 --batch-size 8 --eval-batch-size 16 `
  --gradient-accumulation 4 --learning-rate 0.0001 `
  --lora-rank 16 --lora-alpha 32 --lora-dropout 0.1
```

The selected checkpoint was epoch 25 with ViMedNER dev target F1 `0.680277`.
Its test target precision/recall/F1 were `0.640566 / 0.733123 / 0.683726`.

## Inference and build

Generate the first-model cache as documented in `README.md`, then generate the
second-model cache from the merged LoRA checkpoint:

```powershell
python .\scripts\predict_bamibert.py `
  --input .\input `
  --model .\.work\xlmr-base-lora-r16-seed42-gpu2\best `
  --output .\.work\xlmr_spans_seed42.json `
  --minimum 0.50 --device cuda --batch-size 32

.\scripts\build_cpu_v19.ps1

python .\scripts\validate_submission.py `
  .\submission\candidate_v19_xlmr-additive-85.zip --input .\input
```

The candidate builder requires the current 100-record competition `input/`
directory and the scored V18 control ZIP. Model downloads, ViMedNER data,
checkpoints, and inference caches stay under `.work/` or `resources/models/`
and are intentionally not committed.

## Verified public trajectory

| Profile | Score | WER | J_assertion | J_candidates | Decision |
|---|---:|---:|---:|---:|---|
| V18 control | 39.3358 | 55.7723 | 50.9613 | 26.9477 | control |
| `xlmr-safe-94` | 39.3344 | 55.7873 | 50.9716 | 26.9477 | reject boundaries |
| `xlmr-additive-90` | 39.3438 | 55.7560 | 50.9716 | 26.9477 | promote |
| `xlmr-additive-85` | 39.3683 | 55.7164 | 51.0138 | 26.9477 | promote |
| `xlmr-additive-80` | 39.3421 | 55.7543 | 50.9645 | 26.9477 | reject; keep additive-85 |

Machine-readable calibration and submission IDs are recorded in
`reports/final/xlmr_v19_training_and_calibration.json`.

At the final snapshot, `SOL-GPT` was rank 21 at `39.3683`; rank 10 was
`40.8482`, a gap of `1.4799`. The platform retains the best submission score,
so the lower `additive-80` result (`39.3421`) is intentionally rejected.
