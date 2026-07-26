# V40 — direct assertion ablation on confirmed V37

## Control

V37 is the confirmed production artifact:

- score: `41.8315`;
- WER: `55.4442`;
- J_assertion: `51.4203`;
- J_candidates: `32.5967`;
- SHA-256:
  `0fa0f24796a01f07c6e64227abea942945fb61afae6cf65f51a6785bf830e928`.

V35 and the standalone V39 remain archived causal artifacts. V39 should not
be submitted because it would discard the already-confirmed V37 assertion
gain.

## Data insight

Several records are concatenations of Vietnamese consultation questions,
structured hospital notes, and health-education prose. A section heading such
as `Tiền sử` can therefore leak `isHistorical` into a semantically new source
segment even when there is no reliable newline boundary.

V40 repairs six high-confidence leaks:

- two current `run tay` mentions in a direct user question;
- two generic symptom mentions in menopause/pregnancy education;
- two generic mental-health diagnoses in an advice block.

This is local discourse routing, not broad assertion propagation.

## Causal contract

V40 differs from V37 in exactly six assertion arrays across records 3 and 23:

- entity changes: 0;
- span changes: 0;
- type changes: 0;
- candidate changes: 0;
- assertion changes: 6.

Consequently WER must remain `55.4442` and J_candidates must remain `32.5967`.
Any score movement is exactly `0.3 × delta(J_assertion)`.

## Artifact and decision

Artifact:
`submission/candidate_v40_v37-hybrid-document-seam-assertion-probe.zip`

SHA-256:
`f970f1c913464b58f997747bfb51da3324dd496ec33394be3b68c75ba49e53b5`

Validation: PASS, 100 records, 2,689 entities.

## Official result

V40 was submitted at 00:17 on 26/07/2026 and scored exactly `41.8315`:

- WER: `55.4442`;
- J_assertion: `51.4203`;
- J_candidates: `32.5967`.

All metrics are identical to V37. The six changed mentions therefore have no
measurable leaderboard influence, most likely because they are not matched to
gold entities. Reject V40 as neutral and retain V37 as production.
