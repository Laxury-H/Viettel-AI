# V53 — explicit medication-section temporality

## Decision

V53 is the next submission candidate on top of confirmed V51 production.
It is an assertion-only, two-mention causal probe.

V52 must not be submitted first. The official sample emits separate entities
for repeated `táo bón` and `lo âu` occurrences at different positions, which
confirms mention-level extraction and invalidates generic deduplication.

## Official annotation policy

The official sample establishes two details that must be applied together:

1. medications in the pre-admission list carry `isHistorical`;
2. symptoms used as medication indications keep empty assertions.

Therefore the attached research note is useful for section routing, but its
suggestion to propagate historical temporality from a medication to its
indication is not compatible with the official example.

## Exhaustive cohort

Scanning every line-anchored section named:

- `Thuốc trước khi nhập viện`;
- `Thuốc trước khi nhập viện lần này`;
- `Thuốc đã dùng trước đây`;
- `Thuốc đã điều trị trước khi nhập viện lần này`;

found exactly two unasserted drug mentions in V51:

| Record | Section | Mention | Position | Before | After |
|---|---|---|---:|---|---|
| 57 | Thuốc trước khi nhập viện | Torsemide | `[224,233)` | `[]` | `[isHistorical]` |
| 92 | Thuốc đã dùng trước đây | bactrim | `[321,328)` | `[]` | `[isHistorical]` |

Neighboring drugs in both sections already carry `isHistorical`. The rule
ends at the next strong section heading and never changes symptoms or
diagnoses.

## Invariants

- control: V51 `41.9878`;
- records: 100;
- entities: 2,687;
- assertion additions: 2;
- entity/span/type/candidate changes: 0;
- all non-target entities: byte-for-byte unchanged;
- strict validator: PASS;
- direct tests: PASS;
- deterministic rebuild: PASS.

Promotion requires:

- score greater than `41.9878`;
- J_assertion greater than `51.4354`;
- WER remains `55.4298`;
- J_candidates remains `32.9653`.

Artifact:

`submission/candidate_v53_v51-explicit-medication-section-temporality.zip`

SHA-256:

`04c18e2e77a5105f0c085beb23f2e19b1a1122f788778af1785b4dff8f081ab6`

## Leaderboard result

V53 was submitted at 16:04 on 26/07/2026 and scored `41.9901`, improving
over V51 by `+0.0023`.

| Metric | V51 | V53 | Delta |
|---|---:|---:|---:|
| WER | 55.4298 | 55.4298 | 0 |
| J_assertion | 51.4354 | 51.4432 | +0.0078 |
| J_candidates | 32.9653 | 32.9653 | 0 |
| Total | 41.9878 | 41.9901 | +0.0023 |

The observed result matches the causal prediction exactly: only
J_assertion changed. V53 is promoted to production; V51 remains the rollback
artifact.
