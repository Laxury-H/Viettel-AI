# V45 — deep Vietnamese ICD and data-context audit

## Leaderboard result

V45 scored **41.9694** and was promoted over V42 (`41.9476`). It changes five
diagnosis candidates only:

| Surface | Occurrences | V42 | V45 | Evidence class |
|---|---:|---:|---:|---|
| `viêm tim` | 1 | I51.4 | I51.8 | official inclusion: carditis, not myocarditis |
| `bệnh tim mạch` | 2 | I51.9 | I51.6 | exact national/hospital label |
| `đột quỵ` | 2 | I63.9 | I64 | exact unspecified-stroke label |

Entity count, text, span, type and assertions are unchanged. WER must stay
`55.4442`, and J_assertion must stay `51.4203`.

Observed metrics:

- WER: `55.4442` (unchanged);
- J_assertion: `51.4203` (unchanged);
- J_candidates: `32.9413` (`+0.0543`);
- total score: `41.9694` (`+0.0218`).

The pre-submission conditional estimate was `42.0305`. The smaller observed
gain shows that the five exact-label changes do not have uniform marginal
effect, even though the aggregate batch is positive.

## Why the Excel audit matters

CDC Đồng Nai publishes the 2026 national ICD appendix as an XLSX with the
primary Vietnamese name and WHO additional coding guidance in separate
columns. That makes it possible to audit inclusions and exclusions instead of
matching only the display name.

The production set contains 760 diagnosis occurrences and 268 normalized
surface–candidate pairs. A direct exact-name scan found 38 surfaces matching a
primary national label. Seventeen apparent mismatches were almost entirely the
expected parent-label versus unspecified-child pattern; V38 already showed
that blindly forcing specificity is negative. The useful residual is therefore
semantic distinction within valid Vietnamese codes.

The inclusion audit also prevented incorrect “repairs”:

- `chèn ép tim` remains I31.9 because the national I31.9 guidance includes it;
- `tâm phế mạn` remains I27.9;
- `bệnh lý chất trắng` remains R90.8;
- M48.00, J96.90, M10.90 and T14.20 are genuine five-character entries in the
  2026 Vietnamese appendix.

## Ranked follow-up hypotheses

### Tier B — contextual translation probe, keep separate

Six `tăng nhãn áp` mentions in records 23/27/45/50 are not ophthalmic glaucoma
in context. The surrounding evidence is head CT, papilloedema, neonatal
ventricular drainage and hydrocephalus. Vietnamese pediatric hospital guidance
codes intracranial hypertension as G93.2. This is a potentially high-value
translation-context correction, but the literal surface says ocular
hypertension, so it remains isolated from V45 as candidate V46. V46 applies
H40.9 → G93.2 exactly six times and does not change entity alignment.

### Tier C — multi-candidate normalization

Two mentions read `Bệnh thủy đậu/Zona (do Varicella Zoster Virus)`. The current
list contains only B02.9. A semantic candidate is `[B01.9, B02.9]`, matching
the slash-combined diseases. This can double Jaccard if gold stores both codes,
but can halve it if gold stores only B02.9; it is not suitable for the same
scarce submission as V45.

### Tier D — recall and boundary

- `Bệnh amyloidosis tự miễn dịch` appears three times between two already
  extracted amyloidosis subtypes. E85.3 is plausible for secondary systemic AA
  amyloidosis, but adding it changes WER and needs a dedicated recall probe.
- `tăng sản tuyến bã nhờn` appears twice in acne pathogenesis. It is a mechanism
  phrase rather than necessarily a patient diagnosis.
- V43 has three official-label boundary completions, but it remains held
  because it changes WER.

## Sources

- [National 2026 ICD appendix (PDF)](https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/06-byt-kem.pdf)
- [CDC Đồng Nai 2026 ICD appendix (XLSX)](https://dongnaicdc.vn/UserFiles/Docs/2026/VBBYT/Phu%20luc%20Bang%20danh%20muc%20ICD10_FINAL%20.xlsx)
- [Ministry implementation notice](https://kcb.vn/tin-tuc/cong-van-so-4059-byt-bh-trien-khai-thong-tu-06-2026-tt-byt-quy-dinh-ma-hoa-benh-tat-theo-icd-10.html)
- [Hospital I51 catalogue](https://phusannhidanang.org.vn/TraCuuXetNghiem/lstICD/GetICD?page=371)
- [Ministry ICD coding guidance for stroke](https://kcb.vn/thong-tin/huong-dan-ma-hoa-benh-tat-tu-vong-theo-icd-10.html)
- [Children's Hospital No. 2 intracranial-hypertension protocol](https://benhviennhi.org.vn/files/202503251327-PHAC%20DO%20NOI%20TRU%202016%20.pdf)

## Artifact

`submission/candidate_v45_v42-vietnam-exact-label-cross-family.zip`

SHA-256:

`c5afa4be374c7a329f63b2bfe67a613b99910e71408f8c73c755db785e77ece3`

Strict validation: PASS. Deterministic rebuild: PASS.
