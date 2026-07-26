# V39 — data-archetype and hybrid-document seam research

## Decision

V37 was submitted independently and scored **41.8315**, exactly matching the
projection isolated from V38:

- WER: `55.4442`;
- J_assertion: `51.4203`;
- J_candidates: `32.5967`;
- SHA-256:
  `0fa0f24796a01f07c6e64227abea942945fb61afae6cf65f51a6785bf830e928`.

V37 is production. V39 remains an archived causal artifact on V35. Its six
repairs are composed directly onto V37 as V40, so the next submission retains
the confirmed V37 gain.

## Insight 1 — a record is a mosaic, not one homogeneous document

The 100 records combine several source archetypes:

- 55 contain a consultation/question marker;
- 74 contain a structured hospital-note marker;
- 48 contain educational or patient-advice prose;
- 19 contain strongly translated EHR-style markers;
- many records contain more than one archetype.

Some source seams occur without a clean paragraph or even a newline. Examples
include an educational answer immediately followed by a structured medication
item, or a structured `Tiền sử bệnh` heading immediately followed by the tail
of a user question.

The modeling consequence is important: document-level classification and a
line-level section state are both too coarse. Entity recognition can reuse
surface evidence across clones, but assertion scope must be inferred inside
the local semantic segment.

## Insight 2 — repeated text is useful for entities, not for copying assertions

The corpus contains:

- 44 whole-document pairs with character-5-gram Jaccard at least `0.45`;
- 15 exact paragraphs of at least 80 characters repeated across records;
- exact clinical blocks reused under different headings and subjects.

The exact repeated-clause scan finds no remaining omitted entity proposal in
V35. The exact repeated-line consistency audit finds seven field conflicts,
all caused by contextual assertion differences. For example, the same
`thỉnh thoảng tiêu chảy...` line is historical in a past-history block and
current in an HPI block.

Therefore the safe transfer rule is:

1. reuse an exact or aligned span/type as evidence;
2. never copy `isHistorical`, `isFamily`, or `isNegated`;
3. recompute assertions after locating the target segment and its clinical
   subject.

This explains why the earlier repeated-neurologic entity recovery helped,
while broad family/assertion propagation hurt.

## Insight 3 — 435 test names versus 170 results is mostly a document-state effect

The apparent laboratory imbalance is not a 265-result recall hole. Records 45
and 87 are explicit lists of tests to perform and correctly contain no result.
Record 2 is an educational list of tests for Kawasaki disease. Record 40 mixes
a long order list with only a small actual result block.

Narrative findings after `cho thấy` or `ghi nhận` are usually diagnoses or
symptoms, not automatically `KẾT_QUẢ_XÉT_NGHIỆM`. Promoting the whole finding
phrase to a laboratory-result entity would often create an overlapping
wrong-type concept.

A previous broad experiment that increased laboratory results from 170 to 218
was bundled with other changes and regressed WER by `+0.9680` and
J_assertion by `-2.2535`. It is not a causal laboratory ablation, but it
reinforces the need to separate:

- ordered/planned tests;
- pending tests;
- actual numeric or categorical results;
- diagnostic interpretations of imaging/pathology.

No broad laboratory expansion is justified. The next laboratory experiment,
if any, should contain only explicit `test: numeric/status` pairs.

## Insight 4 — the next assertion errors come from scope leakage at source seams

V35 has 365 `isHistorical` assignments:

- 244 are driven by structured section state;
- 120 are driven by explicit local past-time language;
- one is a reviewed post-process.

The high-confidence residual errors are not ordinary history phrases. They are
mentions semantically outside the history segment but physically placed after
a history heading:

- record 3: two current `run tay` mentions in a user question;
- record 23: `đổ mồ hôi đêm` and `Mất ngủ` in generic menopause/pregnancy
  education;
- record 23: `rối loạn lo âu` and `trầm cảm` in a generic advice block.

V39 removes only these six leaked `isHistorical` values. It changes no entity,
boundary, type, candidate, negation, or family assertion.

## Insight 5 — remaining entity and boundary proposals are low-confidence

After V35:

- the exact repeated-clause entity-gap inventory is empty;
- the medication normalized-surface gap inventory is empty;
- the only repeated diagnosis gaps are the already rejected yes/no
  `có phải là tăng HA thật sự không` mentions;
- remaining symptom gaps are generic warning/advice mentions such as
  `môi đỏ` and `căng thẳng`;
- the broad V31 batch of 34 semantic boundary expansions plus seven recall
  additions worsened WER by `+0.1014` and J_assertion by `-0.1528`.

The data no longer supports another broad boundary or recall batch. Candidate
normalization and local assertion routing remain the evidence-backed levers.

## Candidate V39

Artifact:
`submission/candidate_v39_v35-hybrid-document-seam-assertion-probe.zip`

- control: V35;
- records: 100;
- entities: 2,689;
- assertion changes: 6 removals;
- entity/span/type/candidate changes: 0;
- validation: PASS;
- SHA-256:
  `37446a6fbd2ff6d8cf4d4384dec1b19e8eb777ad1317d60819ffcb1c8a81603b`.

Any leaderboard movement is exactly `0.3 × delta(J_assertion)`.

## Submission order

1. V37 is confirmed and has been promoted.
2. Keep V35 and V39 as rollback/causal artifacts; do not spend a submission
   on the stale V35-based candidate.
3. The changed assertion sets of V37 and V39 are disjoint. Submit V40, which
   applies the same six seam repairs directly to V37 production.
4. Promote only if WER remains `55.4442`, J_candidates remains `32.5967`, and
   total score exceeds `41.8315`.
