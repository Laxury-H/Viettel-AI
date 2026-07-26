# V32 direct-family assertion ablation

## Control decision

V31 scored **39.4604**, below V30 by `0.0763`. Its WER and J_assertion both
regressed, so none of the V31 boundary or recall expansions are carried
forward. V32 starts from the confirmed V30 control at **39.5367**.

## New evidence

An exact repeated-line audit found no remaining high-confidence span,
candidate, or missing-mention discrepancy in V30. It did expose a narrower
assertion-scope issue: the extractor recognizes a relative at the beginning
of a consultation, but loses `isFamily` in the following direct statement.

V32 repairs only reviewed entities in clauses with an explicit relative
subject and assignment cue:

- `cháu bé bị bệnh bàn chân bẹt`;
- `bé mắc phải là dị tật thiểu sản vành tai và tịt ống tai ngoài bẩm sinh`;
- `Mẹ của bạn ... bị run tay`.

This is an assertion-only ablation:

- no entity is added or removed;
- no text span or type changes;
- no candidate changes;
- WER and J_candidates must remain identical to V30.

The target is **39.54–39.57**, entirely through J_assertion. V30 remains the
production control until leaderboard confirmation.

## Artifact verification

- Records: **100**
- Entities: **2689**, identical to V30
- Changed records: **6**
- Assertion repairs: **8**
- Span/type changes: **0**
- Candidate changes: **0**
- Relevant regression tests: **45 passed**
- Strict submission validator: **PASS**
- Deterministic rebuild: byte-identical
- SHA-256:
  `d2f67d210c13b3e33469cba20dfde95802f2bb6e8ee611ed3cf9d08d204806fc`

## Confirmed leaderboard result

V32 scored **39.2974** and is rejected:

| Metric | V30 control | V32 | Delta |
|---|---:|---:|---:|
| Score | **39.5367** | 39.2974 | **-0.2393** |
| WER | 55.4442 | 55.4442 | 0 |
| J_assertion | **51.3029** | 50.5052 | **-0.7977** |
| J_candidates | 26.9477 | 26.9477 | 0 |

The exact `0.3 * -0.7977 = -0.2393` decomposition confirms that all damage
came from `isFamily`. Direct relatives who are the subject of a consultation
must not be treated like a family-history assertion. V30 remains the control;
the next experiment tests the reverse correction on existing Q&A mentions
while preserving true `Tiền sử gia đình` assertions.
