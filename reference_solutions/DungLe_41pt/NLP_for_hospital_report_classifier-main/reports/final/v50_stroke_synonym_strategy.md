# V50 stroke-synonym causal ablation

## Decision

V50 is ready for a controlled submission now that small, informative
ablations are allowed. V45 remains production until the leaderboard confirms
an improvement.

Artifact:

```text
submission/candidate_v50_v45-vietnam-stroke-synonym-ablation.zip
SHA-256 f50106500205ed954a5addc36210f7f6eca355b9c76dba0d4a9f340f7f0d85e0
```

## Isolated change

V50 changes only two existing diagnosis entities in record 3:

```text
tai biến mạch máu não: I63.9 -> I64
```

The two occurrences form one complete record-level substitution. No E85.3
amyloidosis change from V49 is retained.

## Why this is the correct V49 split

- The entity surface itself is a common Vietnamese synonym for stroke.
- I63.9 asserts unspecified cerebral infarction.
- I64 leaves haemorrhage versus infarction unspecified.
- V45 already changed the exact synonym `đột quỵ` to I64 inside a positive
  candidate-only batch.
- Unlike the AA cohort, V50 does not use text outside the entity boundary and
  does not add a second code while leaving the old code elsewhere.

## Safety checks

- records: 100;
- entities: 2,689;
- entity/span/type/assertion changes: 0;
- candidate changes: 2;
- candidate-list length changes: 0;
- direct tests: PASS;
- submission validator: PASS;
- deterministic byte-for-byte rebuild: PASS.

WER must remain `55.4442` and J_assertion must remain `51.4203`. Promote only
if the total exceeds V45's `41.9694`.

## Following experiment

V46 is the next independent candidate-only probe. Its six
`tăng nhãn áp` occurrences create four complete H40.9→G93.2 record
substitutions in hydrocephalus/head-CT/papilloedema contexts. Submit V46
separately after V50, then merge only branches proven positive.
