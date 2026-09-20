# Client B — Answer key (hand-calculated, 2026)

Verified independently in a throwaway shell one-liner before being written here.
Deliberately harder than client_a: a credit note (Gutschrift) that reduces income,
an invoice that only states the gross amount (net must be back-calculated), a
rounding wrinkle where net + VAT doesn't reduce to a clean percentage, and a
reverse-charge invoice in French rather than German/English.

## Income (Betriebseinnahmen)
| Doc | Net | VAT (19%) | Gross | Note |
|---|---|---|---|---|
| jan_income_01 | 4200.00 | 798.00 | 4998.00 | |
| apr_income_02 | 3000.00 | 570.00 | 3570.00 | English invoice |
| aug_income_03 | 2500.00 | 475.00 | 2975.00 | |
| sep_credit_note_01 | -500.00 | -95.00 | -595.00 | Gutschrift reducing aug_income_03 |
| **Total** | **9200.00** | **1748.00** | **10948.00** | |

## Expenses (Betriebsausgaben) by category
| Category | Net | VAT | Gross | Note |
|---|---|---|---|---|
| office_supplies | 220.00 | 41.80 | 261.80 | |
| travel | 1430.00 | 100.10 | 1530.10 | mar (1250.00/87.50, German thousands-separator "1.250,00") + oct (180.00/12.60) |
| software | 588.00 | 111.72 | 699.72 | Invoice states only the gross total (699.72) and "49.00 EUR × 12 Monate" — net/VAT back-calculated: 699.72 / 1.19 = 588.00 |
| catering | 333.33 | 23.34 | 356.67 | Invoice's own net+VAT reconcile to its stated gross even though 23.34 isn't exactly 7.000% of 333.33 (23.3331) — trust the document's own numbers, don't silently "correct" them to a clean rate |
| consulting_external | 800.00 | 0.00 | 800.00 | French reverse-charge invoice (Autoliquidation, Art. 196 EU VAT Directive) |
| **Total** | **3371.33** | **276.96** | **3648.29** | |

## Summary
- Net result (Überschuss) = Income net − Expenses net = 9200.00 − 3371.33 = **5828.67**
- USt-Zahllast (VAT payable to Finanzamt) = Income VAT − Expenses VAT (Vorsteuer)
  = 1748.00 − 276.96 = **1471.04**

## Known extractor gaps (as of this answer key)

Verified by running `src/extract.py` against every doc in this folder. Three docs
do not extract correctly with the current text-based extractor — intentional,
documented future work, not a bug to silently patch here:

- **`may_software_01.txt`** — raises `ValueError`. No line matches the net/VAT
  label patterns at all; the extractor doesn't yet know how to back-calculate
  net/VAT from a gross-only total plus a stated rate.
- **`sep_credit_note_01.txt`** — extracts as `net=500.0 vat=95.0` (positive).
  The regex `AMOUNT_RE` has no support for a leading minus sign, so credit
  notes currently get counted as if they were additional income instead of a
  reduction. Direction/category (income/beratung) are correctly inferred.
- **`jul_consulting_external_01.txt`** — raises `ValueError`. `NET_LABELS` and
  `VAT_LABELS` only contain German/English terms; French ("Montant net",
  "TVA") isn't recognized.

`client_a`'s docs and the rest of `client_b`'s docs (7 of 10) extract correctly
with no changes.
