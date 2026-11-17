# Claims settlement checks

32 quarters, 4473 printed rows, 77 companies after the crosswalk.

| Check | Pass | Explained | Fail |
|---|---|---|---|
| counts_not_negative | 3086 | 0 | 8 |
| movement_adds_up | 2830 | 0 | 264 |
| opening_equals_last_closing | 2545 | 0 | 152 |
| payment_ratio_as_printed | 2955 | 0 | 2 |
| sum_equals_printed_total | 943 | 6 | 0 |

12791 checks in all. The failures are listed in claims_checks.csv; they are the insurers' own
returns as IRA printed them, kept as printed. The analysis uses the payment ratio, which does not depend on the
movement adding up: it needs only the claims paid, declined, closed and still outstanding in the quarter.
