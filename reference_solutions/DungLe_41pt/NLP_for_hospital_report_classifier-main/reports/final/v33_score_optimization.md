# V33 primary-patient family-scope ablation

## Causal insight

V32 changed assertions only and scored **39.2974**, below V30 by `0.2393`.
WER and J_candidates were byte-for-byte neutral; the complete loss came from
adding `isFamily` (`J_assertion -0.7977`).

The useful boundary is not the presence of a relative word. It is the
clinical point of view:

- in Q&A documents, `mẹ em` or `ông em` can be the primary patient;
- a diagnosis belonging to that primary patient is not family history;
- a wife mentioned in the patient's history, explicit `Tiền sử gia đình`,
  and a hypothetical inherited risk for a child remain secondary-family
  contexts.

## V33 change

V33 restarts from the confirmed V30 control and removes `isFamily` only from
the 18 existing mentions in records 64, 80 and 95, whose opening question
defines a mother or grandfather as the primary patient.

The experiment deliberately preserves all seven family assertions in records
24, 26, 42, 62 and 81. It changes no entity, span, type, candidate, negation,
or historical assertion.

Expected leaderboard behavior:

- WER identical to V30: **55.4442**;
- J_candidates identical to V30: **26.9477**;
- any score movement is exactly `0.3 × delta(J_assertion)`;
- target score range: **39.60–39.78**.

V30 remains the production control until V33 is scored.

## Artifact verification

- Records: **100**
- Entities: **2689**, identical to V30
- Changed records: **3**
- Assertion removals: **18**
- Span/type changes: **0**
- Candidate changes: **0**
- Dependency-free regression suite: **50 passed**
- Strict submission validator: **PASS**
- Deterministic rebuild: byte-identical
- SHA-256:
  `8dd71668044ec35196b55eec740256535a7bf3ad4af9f5d43219d685d83c34b8`

The full machine-readable delta is in
`candidate_v33_v30-primary-patient-family-scope.json`. Leaderboard metrics
will be appended after scoring.
