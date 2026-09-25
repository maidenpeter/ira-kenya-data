# Data dictionary

All money figures are KSh thousands, year to date to the period end, from IRA's unaudited quarterly returns.

## Common columns

| Column | Meaning |
|---|---|
| `year`, `quarter` | Reporting period. Q4 figures cover the full year. |
| `period_end` | Last day of the period. |
| `source_file` | Workbook the figure came from, relative to the repo root. |
| `source_sha256_12` | First 12 characters of that workbook's SHA-256, matching `data/raw/manifest.csv`. |
| `source_sheet` | Sheet name inside the workbook. |
| `segment` | `insurer` or `reinsurer`, as IRA groups them. |
| `company` | Company name exactly as IRA printed it. Not yet harmonised across periods. |
| `value_ksh_000` | The figure. Blank where IRA left the cell empty. |

## general_revenue_accounts.csv

`line` takes these values, in the order of IRA's revenue account:

| line | Meaning |
|---|---|
| `gross_direct_premium` | Premium written directly |
| `inward_reinsurance` | Premium accepted from other insurers |
| `outward_reinsurance` | Premium ceded to reinsurers |
| `net_premium_written` | gross direct + inward - outward |
| `upr_bf`, `urr_bf` | Unearned premium reserve and unexpired risk reserve brought forward |
| `upr_cf`, `urr_cf` | The same reserves carried forward |
| `net_earned_premium` | net premium written + reserves b/f - reserves c/f |
| `incurred_claims` | Net incurred claims |
| `net_commissions` | Commissions paid less commissions received |
| `management_expenses` | Expenses of management |
| `underwriting_result` | net earned premium - claims - commissions - expenses |
| `investment_income` | Investment income allocated to general business |
| `operating_result` | underwriting result + investment income |

## general_by_class.csv

`table` names the IRA table. Not every table exists in every period:

| table | Meaning | Periods |
|---|---|---|
| `gross_premium` | Gross premium income | all |
| `gross_direct_premium` | Gross direct premium | Q3 2018 on |
| `inward_premium` | Inward reinsurance premium | Q3 2018 on |
| `net_premium` | Net premium income | Q3 2017 on |
| `net_earned_premium` | Net earned premium | Q3 2017 on |
| `claims_paid` | Claims paid | all |
| `claims_incurred` | Claims incurred | all |
| `commissions` | Net commissions | Q3 2017 on |
| `management_expenses` | Management expenses | Q3 2017 on |
| `underwriting_result` | Underwriting profit or loss | all |

`class_of_business`: Aviation, Engineering, Fire Domestic, Fire Industrial, Liability, Marine, Motor Private, Motor Commercial, Motor Commercial PSV, Personal Accident, Theft, Workmen's Compensation, Medical, Miscellaneous, and Total.

IRA's own incurred claims ratio tables are not copied, since they can be recomputed from these columns.
