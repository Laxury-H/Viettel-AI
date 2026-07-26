# V42 — Vietnamese hospital terminology strategy

## Result

V42 scored **41.9476** and was promoted to production. Relative to V37:

- WER remained `55.4442`;
- J_assertion remained `51.4203`;
- J_candidates increased from `32.5967` to `32.8870` (`+0.2903`);
- total score increased by `+0.1161`.

This clean decomposition confirms the Vietnamese hospital exact-label
strategy. V41 was not submitted and is superseded by V42.

## Three-layer evidence system

### 1. Competition behavior

Candidate similarity has the largest score weight (`0.4`). V34 and V35 changed
candidate codes without changing WER and produced the largest gains:

- V34: `+3.7067` J_candidates from 149 changes;
- V35 over V34: `+1.9423` J_candidates from 78 additional changes.

Both batches yield approximately `+0.02489` J_candidates per successful
occurrence. V36 showed that adding specificity not expressed by the mention
is harmful, so the operative rule is exact mention-level terminology rather
than maximal billing specificity.

### 2. National standard

The 2026 Vietnamese ICD appendix and implementation guidance require codes to
correspond to the documented diagnosis and actual patient condition. After
V35, every production diagnosis candidate is present in the national appendix
except the intentionally combined B/C hepatitis pair. The remaining problem
is therefore not code validity; it is choosing the correct valid code for the
Vietnamese surface.

### 3. Hospital usage

Hospital catalogues expose the national display labels directly:

| Mention in data | Production | Hospital/national label | V42 |
|---|---:|---|---:|
| Bệnh tim mạch do xơ vữa động mạch | I70.90 | I25.1 | I25.1 |
| u xơ tuyến vú | D24 | N60.2 | N60.2 |

The Hospital for Women and Children of Da Nang catalogue lists I25.1 and
N60.2 under these exact Vietnamese names. A chart-based disease-pattern study
at Hanoi General Hospital of Traditional Medicine independently records
`U xơ tuyến vú — N60.2`. The Hospital of Hue University of Medicine and
Pharmacy catalogue distinguishes D24 as the broader `U lành vú`.

This triangulation resolves the apparent clinical ambiguity between
fibroadenoma as a benign neoplasm and the Vietnamese ICD display label:
the competition's earlier behavior favors the national/hospital label
dialect.

## V42 delta

V42 changes exactly seven candidates on V37:

- two `I70.90` → `I25.1`;
- five `D24` → `N60.2`.

There are no entity, span, type or assertion changes. Therefore WER must remain
`55.4442` and J_assertion must remain `51.4203`.

The pre-submission estimate was:

- J_candidates: approximately `32.7709`;
- total score: approximately `41.9012`.

The lower conditional points are:

- only the two I25.1 repairs contribute: approximately `41.8514`;
- only the five N60.2 repairs contribute: approximately `41.8813`.

The observed `41.9476` exceeded the full-batch estimate. Under uniform
attribution across the seven changes, the gain was `0.04147` J_candidates,
or `0.01659` total score, per changed occurrence.

## Deferred boundary layer

Three additional official-label completions are packaged separately as V43:

- `rối loạn cảm xúc lưỡng cực` →
  `rối loạn cảm xúc lưỡng cực khác`, F31.9 → F31.8;
- two `bệnh phổi tắc nghẽn mạn tính` →
  `bệnh phổi tắc nghẽn mạn tính, không xác định`, keeping J44.9.

These have strong terminology evidence but alter WER alignment. Although V42
confirmed the exact-label direction, V43 remains held because a scarce
submission slot is better spent first on another candidate-only expansion.

## Artifacts

V42:

`submission/candidate_v42_v37-vietnam-hospital-exact-label-batch.zip`

SHA-256:

`a2205b94040b164617ab36b9588576bc070a5fa49f895f78cc5447a90bdb663c`

V43 hold:

`submission/candidate_v43_v42-vietnam-official-label-boundary-completion.zip`

SHA-256:

`fb6b366d75a5ab82b009c1ec437eda544e648c4e6ba6dfa4dafa014902ab93fc`

Both artifacts pass the strict validator and deterministic rebuild.
