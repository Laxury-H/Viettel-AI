# Post-V45 semantic-context cohort audit

## Decision

Keep V45 as production at **41.9694**. Do not spend a submission on the
current semantic portfolio.

The audit now contains 22 candidate-only changes, which is numerically large
enough to cross `+0.35` only under the most optimistic historical marginal:

| Calibration | Gain per changed occurrence | Projection for 22 |
|---|---:|---:|
| V42 exact-label batch | `+0.016586` score | `+0.3649` |
| V45 residual batch | `+0.004360` score | `+0.0959` |

The 22 changes mix exact Vietnamese synonyms, source-translation recovery,
qualifiers outside the entity boundary, and a multi-candidate composite.
They are not 22 independent V42-grade exact-label corrections. The optimistic
projection is therefore an upper bound, not a safe expectation.

## Template-adjusted inventory

The 100 records reduce to 69 near-duplicate document components at a
character-five-gram Jaccard threshold of `0.45`. The 22 candidate-only
occurrences occupy 18 records but only 14 distinct document templates.

| Cohort | Occurrences | Records | Templates | Proposed candidate | Risk |
|---|---:|---:|---:|---|---|
| Intracranial-pressure translation | 6 | 4 | 3 | H40.9 → G93.2 | Cross-family translation |
| CKD stage 4 outside boundary | 4 | 4 | 4 | N18.9 → N18.4 | Boundary may differ in gold |
| AA amyloidosis qualifier | 3 | 3 | 1 | E85.9 → E85.3 | Strong provenance, one source template |
| Diabetes with neuropathy | 2 | 2 | 2 | E11.9 → E11.4 | Boundary may differ in gold |
| Diabetes with renal disease | 2 | 2 | 2 | E11.9 → E11.2 | Boundary may differ in gold |
| Unspecified cerebrovascular event | 2 | 1 | 1 | I63.9 → I64 | Strong exact Vietnamese synonym |
| Varicella/zoster composite | 2 | 2 | 1 | B02.9 → B01.9 + B02.9 | Multi-candidate uncertainty |
| Bipolar “other” qualifier | 1 | 1 | 1 | F31.9 → F31.8 | Boundary may differ in gold |

Four chronic-osteomyelitis occurrences and two urinalysis/glucose translation
occurrences are deliberately excluded from the candidate-only budget.

## New insight 1 — recover the source concept, not just the Vietnamese surface

The phrase `Bệnh amyloidosis tự miễn dịch` is not an ordinary Vietnamese ICD
display label. It comes from the source taxonomy “Autoimmune (AA)
amyloidosis.” AA amyloidosis is secondary to chronic inflammatory or
infectious disease. The Vietnamese hospital catalogue maps secondary systemic
amyloidosis to E85.3, while E85.9 is unspecified amyloidosis.

The current extractor selects only the prefix `Bệnh amyloidosis`. A
candidate-only contextual correction can still assign E85.3 while preserving
the production span. There are three occurrences, but all belong to one
source template, so they must not be treated as three independent pieces of
evidence.

## New insight 2 — “tai biến mạch máu não” is not “nhồi máu não”

Two occurrences in record 3 use the generic phrase
`tai biến mạch máu não` but carry I63.9, whose Vietnamese label is unspecified
cerebral infarction. Vietnamese hospital and coding references explicitly use
I64 for `đột quỵ (tai biến mạch máu não)` when haemorrhage versus infarction
is not specified.

This is the strongest new candidate-only cohort because it:

- changes the disease branch for a semantic reason rather than specificity;
- preserves entity, span, type, and assertion;
- extends the already-positive V45 rule from `đột quỵ` to its common
  Vietnamese synonym.

It contributes only two occurrences from one document template, so it is not
large enough to submit independently.

## New insight 3 — raw occurrence count overstates the evidence

The hidden data repeatedly pastes the same consumer-health answer or hospital
note into multiple records. Examples:

- three AA-amyloidosis occurrences are one source template;
- two varicella/zoster occurrences are one source template;
- six intracranial-pressure occurrences reduce to three templates.

Submission budgeting should therefore track both occurrence count and
template count. Repetition can increase metric impact, but it does not reduce
the probability that one incorrect hypothesis flips all copies together.

## Negative findings that protect the submission budget

### Generic diabetes should remain E11.9

The Ministry remote-care list associates the plain label `Đái tháo đường`
with E10.9, E11.9, E12.9, E13.9, and E14.9. The surface alone is not a unique
mapping. Most occurrences in these records are adult/type-2 contexts, while
only four explicitly state neuropathic or renal complications. A broad
E11.9 → E14.9 remap is rejected.

### Chronic osteomyelitis is not a safe way to push the count above threshold

The four record-92 occurrences support the M86.6 family clinically, but they
are one duplicated template and their mention boundaries omit chronicity or
site. More importantly, V36 is the nearest causal experiment: its 25
parent/child specificity changes reduced J_candidates. Adding M86 solely to
inflate the batch would ignore the observed negative calibration.

### Medication normalization is not the next large error family

All 219 medication mentions were audited. Their 68 unique RxCUIs resolve to
active RxNorm concepts whose names agree semantically with the extracted
surface, including Vietnamese brand and ingredient aliases. Earlier
strength-specific ablations also showed that only the metoprolol 25 mg rule
survived. No untested high-volume RxNorm family was found.

## Required next breakthrough

The current portfolio has an optimistic upper bound of `+0.3649` but a
V45-calibrated projection of only `+0.0959`. A submission should wait for one
of these:

1. at least 5–8 additional cross-family corrections with evidence comparable
   to the I64 synonym and AA provenance;
2. a new high-volume translation family with at least 20 occurrences across
   several independent templates;
3. a controlled leaderboard ablation that establishes a positive marginal
   for qualifier-outside-boundary corrections.

Until then, `submission/output.zip` remains V45 with SHA-256:

```text
c5afa4be374c7a329f63b2bfe67a613b99910e71408f8c73c755db785e77ece3
```

No new submission ZIP was created.

## Evidence

- National ICD-10 appendix under Circular 06/2026/TT-BYT:
  https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/06-byt-kem.pdf
- Vietnamese hospital catalogue for E85.3:
  https://phusannhidanang.org.vn/TraCuuXetNghiem/lstICD/GetICD?page=229
- Vietnamese hospital catalogue for I64:
  https://bvydhue.vn/modules.php?maLoai=E50&maNhomChinh=E50-E64&name=ICD&op=nodeICD
- Vietnamese ICD coding manual example for an unspecified cerebrovascular
  event:
  https://syt.quangbinh.gov.vn/3cms/upload/soyte/File/BIEU%20MAU/1754-syt-nvy/ICD%2010-%20Tap%202.pdf
- Source wording for “Autoimmune (AA) amyloidosis”:
  https://www.healthline.com/health/amyloidosis
- NLM RxNorm API:
  https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html
