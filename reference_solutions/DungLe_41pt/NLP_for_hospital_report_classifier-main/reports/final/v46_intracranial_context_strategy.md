# V46 — Vietnamese translation-context candidate probe

## Control and intervention

V45 is confirmed production at `41.9694`:

- WER `55.4442`;
- J_assertion `51.4203`;
- J_candidates `32.9413`.

V46 changes six diagnosis candidate lists from H40.9 to G93.2 in records
23/27/45/50. It does not globally remap `tăng nhãn áp`; it requires one of two
local context signatures:

1. head CT together with papilloedema;
2. congenital hydrocephalus together with neonatal CSF drainage/shunt history.

The six occurrences split 3/3 across those signatures. Entity count remains
2,689; text, span, type and assertions are unchanged.

## Clinical and terminology evidence

Literal `tăng nhãn áp` ordinarily points to an ophthalmic condition. These
records contradict that reading:

- a drainage system was placed in infancy and revised repeatedly;
- the current encounter is for headache and blurred vision;
- papilloedema is reported by ophthalmology;
- head CT is used for comparison;
- congenital hydrocephalus is an explicit chronic condition.

Vietnamese hospital and Ministry documents connect papilloedema, hydrocephalus
and CSF diversion with raised intracranial pressure. Hospital ICD catalogues
list G93.2 as `Tăng áp lực trong sọ lành tính`.

This is therefore a translation-context correction, not an exact surface-label
correction. It is kept separate from V45 so a negative result can be rolled
back without losing the confirmed exact-label gain.

## Quantitative expectation

V45's five candidate changes increased J_candidates by `0.0543`, or `0.01086`
per change under uniform attribution. Applying that conservative observed
rate to six V46 changes gives a conditional estimate:

- J_candidates `33.0065`;
- total score `41.9956`.

The six changes come from duplicated document archetypes, so their effect is
correlated and the estimate is not a confidence interval. Promotion requires
both J_candidates and total score to exceed V45 while WER/J_assertion remain
unchanged.

## Submission decision

**READY AS THE THIRD CAUSAL PROBE, AFTER V51 AND V50.** The earlier `+0.35`
per-submission threshold has been removed. V46 is therefore worth measuring
because it isolates a repeated Vietnamese translation-context error across
four records and leaves every non-candidate field unchanged. The conditional
`+0.0262` estimate is only a reference, not a promised gain. V45 remains the
rollback control, and V46 must not be merged with V50 until both branches have
separate leaderboard evidence.

## Sources

- [National ICD-10 appendix 2026](https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/06-byt-kem.pdf)
- [Huế University Hospital ICD catalogue](https://bvydhue.vn/modules.php?maLoai=G90&maNhomChinh=G90-G99&name=ICD&op=nodeICD)
- [Children's Hospital No. 2 intracranial-hypertension protocol](https://benhviennhi.org.vn/files/202503251327-PHAC%20DO%20NOI%20TRU%202016%20.pdf)
- [Ministry guidance on hydrocephalus and spina bifida](https://kcb.vn/upload/2005611/20210723/21084b418fdec54573bcf1a9d4c27c50Huong-dan-cham-soc-y-te-Nao-ung-thuy-va-Nut-dot-song-1.pdf)

## Artifact

`submission/candidate_v46_v45-vietnam-intracranial-context-candidate.zip`

SHA-256:

`42fe979ce39959b5cc4b686d61985b7f132d4afa8788ad940accdd7643ecbebc`

Strict validator: PASS. Deterministic rebuild: PASS.
