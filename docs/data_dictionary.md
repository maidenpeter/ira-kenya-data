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

## general_revenue_panel.csv

The revenue accounts joined to the company crosswalk, with single-quarter figures.

| Column | Meaning |
|---|---|
| `company_id`, `company_name` | Stable id and current name from `reference/company_crosswalk.csv` |
| `company_as_published` | The name IRA printed that quarter |
| `is_micro` | 1 for micro insurers that IRA lists in the general tables |
| `ytd_ksh_000` | Year to date, as published |
| `quarter_ksh_000` | That quarter alone |
| `quarter_basis` | `derived` (this year to date minus last quarter's), `q1` (Q1 equals its year to date), `new_in_quarter` (no row in the previous workbook, so treated as starting from zero), `not_filed` (IRA printed zeros for the whole account; left blank), `prior_not_filed` (last quarter was zeros; left blank), `no_prior_workbook` (previous workbook not online; left blank), `balance` (reserve balances are not differenced) |

## company_crosswalk.csv

| Column | Meaning |
|---|---|
| `company_raw` | Name exactly as IRA printed it |
| `company_id`, `company_name` | The company it belongs to |
| `is_micro` | Micro insurer flag |
| `link` | Why names were joined, or what happened to the company |
| `evidence` | Source for the link, or `IRA listing` where it rests on the pattern of names in IRA's own tables |

## general_by_class_panel.csv

`general_by_class.csv` on company ids, with `ytd_ksh_000`, `quarter_ksh_000`, `quarter_basis` (as in the revenue panel, plus `table_new_in_quarter` where IRA added a table that quarter) and `reliable_quarter`.

## general_balance_sheets.csv

| Column | Meaning |
|---|---|
| `line_item` | Balance sheet line as IRA printed it (spelling fixed, for example Liabilites) |
| `line_order` | Position in IRA's statement. Equity lines come before Total Equity, liabilities before Total Equity And Liabilities, assets before Total Assets |
| `reporting_basis` | `IFRS 4` to Q4 2023, `IFRS 17` from Q1 2024 |
| `value_ksh_000` | Position at the quarter end |

## general_profit_loss.csv

As the balance sheets, with `segment` (insurer, reinsurer, micro) and year-to-date values. IFRS 4 lines run from Profit Transferred from Revenue to Unappropriated Profit CF. IFRS 17 lines run from Insurance Revenue to Profit for the year.

## quality_flags.csv

One row per company, quarter and problem: `flag`, `severity` (error, warning, info) and a plain-language `detail`. The rules are at the top of `src/ira_data/quality_flags.py`. The panels carry the same information as `quality_flags` and `reliable_quarter`. `reliable_quarter` is false for any error quarter and for a `merger_step` quarter, where the year-to-date figures take in an absorbed company's earlier quarters.

## transfer_from_revenue.csv

One row per company and quarter on IFRS 4 (to Q4 2023): the P&L's transfer from revenue next to the revenue account's operating and underwriting results, and `matches`, which says how the two tables line up: operating result, underwriting result (the company books investment income in the P&L instead), sign of a loss reversed, no transfer entered, or does not match either table.
