# Client C — Answer key (hand-calculated, 2026)

Verified independently in a throwaway shell one-liner before being written here.
Client C is a **Kleinunternehmer** under **§19 UStG** (the German small-business VAT
exemption): they charge no VAT on their own invoices and, because they can't
reclaim input VAT (no Vorsteuerabzug), the *full gross amount* they pay a vendor —
not just the net — is their real deductible business expense. This is a different
EÜR shape from client_a/client_b, not just different numbers: no VAT column on the
income side, no Vorsteuer/Zahllast on the summary line, and expenses booked at
gross. This is deliberately here to force the output pattern to branch correctly
for a client outside the normal VAT system, not just restate one template with
new digits.

## Income (Betriebseinnahmen) — no VAT charged, §19 UStG
| Doc | Amount | Note |
|---|---|---|
| jan_income_01 | 1200.00 | |
| apr_income_02 | 950.00 | English invoice |
| aug_income_03 | 1500.00 | |
| **Total** | **3650.00** | Net = Gross (no VAT) |

## Expenses (Betriebsausgaben) by category — booked at gross (no Vorsteuerabzug)
| Category | Vendor net | Vendor VAT | Booked expense (= gross) |
|---|---|---|---|
| office_supplies | 90.00 | 17.10 | 107.10 |
| travel | 150.00 | 10.50 | 160.50 |
| software | 40.00 | 7.60 | 47.60 |
| catering | 60.00 | 4.20 | 64.20 |
| **Total** | 340.00 | 39.40 | **379.40** |

The "Vendor net"/"Vendor VAT" columns are what each vendor's own invoice states
(they charge normal VAT — being a Kleinunternehmer is Client C's status, not
theirs). For Client C's own EÜR, the **Booked expense** column is what counts.

## Summary
- Net result (Überschuss) = Income − Booked expenses = 3650.00 − 379.40 = **3270.60**
- USt-Zahllast: **entfällt** (Kleinunternehmerregelung §19 UStG — Client C is
  outside the VAT system, not "VAT payable of 0.00" in the normal sense)

## Known gap: current pipeline doesn't model this regime yet

`src/extract.py` extracts every doc in this folder correctly at the field level
(net/VAT/gross all parse fine — verified by running it against all 7 docs). The
gap is in `src/aggregate.py`: it sums `record.net` and `record.vat` directly,
which for Client C's expenses gives **net=340.00, vat=39.40** — the vendor-side
numbers, not the gross-booked numbers above. Running `python run.py client_c`
today would silently produce a wrong Betriebsausgaben total (340.00 instead of
379.40) and a nonsensical USt-Zahllast (0.00 − 39.40 = −39.40, treating
non-reclaimable VAT as Vorsteuer). Fixing this needs a per-client "VAT-exempt"
flag that changes how `aggregate.py` books expenses and skips USt-Zahllast
entirely — not implemented yet, intentionally left as future work.
