# V36–V38: next Vietnam-specific optimization system

## Confirmed control

V35 is production at **41.8224**:

- WER: `55.4442`;
- J_assertion: `51.3898`;
- J_candidates: `32.5967`;
- ZIP SHA-256:
  `a49ef79d427915d2c3679a96fdcddc8e1454c67e0e44d1562d9e72fbf35777c6`.

## Insight 1 — distinguish all official ICD flags by physical column

The official Vietnam appendix has 29 columns. A trailing repeated code is not
enough to infer that a parent code is invalid: columns 28 and 29 are sex-only
flags. The audit therefore extracts column 26 by its physical PDF coordinate,
which is specifically:

> Mã không được sử dụng vì có mã 4 hoặc 5 ký tự cụ thể hơn.

The V35 output has 191 unique diagnosis codes. Exactly eight intersect column
26:

`A09`, `I70.1`, `M06.9`, `M10.9`, `M11.2`, `M81.0`, `M86.9`, `S06.4`.

V36 resolves all eight using local clinical context. It changes 25 candidate
assignments and nothing else:

- `S06.4 -> S06.40`: 4 epidural haemorrhage mentions without an open
  intracranial wound;
- `M10.9 -> M10.90`: 5 gout mentions involving finger and toe joints;
- `M11.2 -> M11.29`: 4 pseudogout mentions with no stated site;
- `M06.9 -> M06.99`: 1 rheumatoid-arthritis mention with no stated site;
- `M81.0 -> M81.99`: 1 generic osteoporosis mention that does not support
  postmenopausal osteoporosis;
- `I70.1 -> I70.10`: 2 renal-artery stenosis mentions without gangrene;
- `A09 -> A09.0`: 1 explicitly infectious gastrointestinal diagnosis;
- `M86.9 -> M86.69/M86.97/M86.99`: 7 mentions resolved by chronicity and
  anatomical site.

Artifact:
`submission/candidate_v36_v35-vietnam-icd-specificity-probe.zip`.

### Original metric projection from two independent observed batches

The prior Vietnam ICD batches have an unusually stable marginal:

- V34: 149 changes increased J_candidates by `3.7067`, or `0.024877`
  J-candidate points per changed entity;
- V35 over V34: 78 additional changes increased J_candidates by `1.9423`, or
  `0.024901` per changed entity.

Applying the common `~0.02489` marginal to 25 V36 changes projects:

- J_candidates: `32.5967 -> ~33.219`;
- total score contribution: `0.4 * 0.6223 = ~0.2489`;
- total score: `41.8224 -> ~42.0713`.

This projection was falsified by V38. The missing assumption was that the
competition gold follows the appendix's *primary-diagnosis billing validity*
rules. It does not: the gold often keeps a parent code matching the abstraction
level of the mention.

## Insight 2 — RxNorm is not the current bottleneck

All 67 RxCUIs used by V35 are active in the current NLM RxNorm data. Prior
leaderboard ablation already showed:

- metoprolol tartrate 25 mg SCD is beneficial and is already in production;
- brand substitutions are neutral in aggregate;
- strength-component substitutions reduce J_candidates;
- dose text without concentration/form is not sufficient to infer an SCD.

No new medication submission is justified.

## Insight 3 — Vietnamese chart archetypes need local subject/tense routing

The corpus mixes structured encounters, Q&A consultations and educational
text. Forty-six records contain a question marker, 56 contain a structured
history marker and 14 contain both. Global document classification is
therefore unsafe.

V37 applies local discourse rules only:

- inline compact history: `..., tiền sử: suy tim - tăng huyết áp - HoHL`;
- denied personal history: `Tiền sử bản thân: chưa bị ... trước đó`;
- a recently treated infection;
- generic educational `Tiền sử gia đình` risk-factor labels that do not refer
  to an actual relative.

It changes seven assertion arrays and nothing else.

Artifact:
`submission/candidate_v37_v35-vietnam-document-archetype-assertion-probe.zip`.

## Insight 4 — remaining boundary proposals are low value

The repeated-clause scan found no unresolved exact repeated gaps. The
normalized medication scan found no gap. The only repeated accepted-boundary
proposal is the false Vietnamese segmentation `đau đầu` inside `đau đầu gối`,
which V30 already guards against. The only safe diagnosis proposals are the
two yes/no `tăng HA` question mentions already rejected by V21.

Do not spend a submission on a new NER/boundary batch without new evidence.

## Submission portfolio

V38 was submitted at 19:09 on 2026-07-25 and scored **41.7942**:

- WER: `55.4442` (unchanged);
- J_assertion: `51.4203` (`+0.0305`);
- J_candidates: `32.5035` (`-0.0932`);
- SHA-256:
  `1bf8beb6bb7001dd263ece2a6f41dead452f9208956658337e4f4ec8b38c29a1`.

Because V36 changes candidates only and V37 changes assertions only, V38 gives
an exact causal decomposition:

- V36 contribution: `0.4 * -0.0932 = -0.03728` score;
- V37 contribution: `0.3 * +0.0305 = +0.00915` score;
- inferred V36 score on V35: approximately `41.7851`;
- inferred V37 score on V35: approximately **41.8315**.

The revised submission decision is:

1. Reject V36 and V38.
2. **V37 assertion-only was submitted independently** at 00:02 on
   2026-07-26 and scored **41.8315**, exactly matching the causal projection.
   It is now production.
3. Preserve the V35 ICD policy: convert codes absent from the Vietnam
   appendix, but do not force an official child code merely because a parent
   is marked unsuitable as a primary billing diagnosis.

V38 artifact:
`submission/candidate_v38_v35-vietnam-icd-and-document-archetype.zip`.
