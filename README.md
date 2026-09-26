# ira-kenya-data

Kenya's general insurance market, company by company, every quarter from Q4 2016 to Q1 2026, rebuilt from the Insurance Regulatory Authority's own statistics and checked against itself 42,000 times.

This is the data layer for two analysis projects, one on insurance and one on reinsurance. It takes IRA's publications, which arrive as a mix of PDFs and Excel workbooks with shifting layouts and inconsistent labels, and turns them into clean, long-format tables where every figure can be traced back to the file, sheet and row it came from.

## What the data already shows

In every full year in this data, Kenya's general insurers as a group lost money on underwriting and made it back on investments.

| Year | Active insurers | Gross premium (KSh bn) | Loss ratio | Combined ratio | Underwriting result (KSh bn) | Investment income (KSh bn) |
|---|---|---|---|---|---|---|
| 2016 | 35 | 121.7 | 62.3% | 100.5% | -0.39 | 4.58 |
| 2018 | 37 | 129.0 | 62.2% | 101.8% | -1.65 | 5.66 |
| 2019 | 36 | 131.1 | 63.5% | 103.3% | -2.97 | 5.98 |
| 2020 | 35 | 130.8 | 63.6% | 101.3% | -1.18 | 6.78 |
| 2021 | 35 | 152.4 | 68.8% | 106.2% | -6.34 | 7.15 |
| 2022 | 33 | 168.9 | 67.9% | 103.3% | -3.72 | 6.97 |
| 2023 | 35 | 191.3 | 67.9% | 103.9% | -4.96 | 10.02 |
| 2024 | 34 | 204.1 | 70.4% | 103.8% | -5.24 | 18.15 |
| 2025 | 34 | 227.2 | 69.8% | 104.5% | -7.01 | 21.31 |

The local reinsurers tell a different story. They made an underwriting profit in six of the nine years, but slipped to a KSh 0.94bn loss in 2025, after earlier losses in 2018 and 2019.

Full years only (Q4, year to date). Gross premium is gross direct plus inward reinsurance. Loss and combined ratios are on net earned premium. 2017 is missing because IRA has no Q4 2017 workbook online.

Underwriting profit is also getting rarer. In 2016, 19 of the 35 active insurers made an underwriting profit. By 2025 only 9 of 34 did. Five insurers made an underwriting profit in every full year from 2018 to 2025: GA Insurance, ICEA Lion General, Intra-Africa Assurance, Mayfair and Tausi Assurance.

## Tables

| File | Rows | What it holds |
|---|---|---|
| `data/processed/general_revenue_accounts.csv` | 21,900 | The general business revenue account for every insurer and reinsurer: gross premium, inward and outward reinsurance, reserves, net earned premium, claims, commissions, expenses, underwriting result, investment income, operating result |
| `data/processed/general_by_class.csv` | 211,785 | The same companies split by 14 classes of business (motor private, medical, fire industrial and so on) across up to ten tables: gross premium, gross direct premium, inward premium, net premium, net earned premium, claims paid, claims incurred, commissions, management expenses, underwriting result |
| `data/processed/general_revenue_panel.csv` | 21,900 | The revenue accounts on stable company ids, with single-quarter figures derived from IRA's year-to-date numbers and a flag saying how each one was derived |
| `data/processed/general_by_class_panel.csv` | 211,785 | The class tables on stable company ids, with single-quarter figures |
| `data/processed/general_balance_sheets.csv` | 50,462 | Every company's general business balance sheet each quarter: equity, liabilities and 20 asset lines |
| `data/processed/general_profit_loss.csv` | 22,351 | Every company's profit and loss account, on IFRS 4 lines to Q4 2023 and IFRS 17 lines from Q1 2024 |
| `reference/company_crosswalk.csv` | 82 | Every spelling of every company name IRA has used, mapped to 52 companies, with the rename, merger or exit behind each change and a source link |
| `validation/quality_flags.csv` | 112 | Return-quality flags read across each company's quarters: errors, warnings and missing filings |

35 quarters, 52 companies, two segments (insurer, reinsurer). Figures are in KSh thousands, year to date and unaudited, exactly as IRA published them. See `docs/data_dictionary.md` for every column.

## See it

`explorer/kenya-insurer-explorer.html` opens in any browser with no install. Pick a company or the whole market and a year to see its premium, loss and combined ratios, underwriting against investment income, every quarter on its own, its class mix, its balance sheet and every return-quality flag. A league table ranks the whole market for any year.

## How it is checked

`src/ira_data/validate.py` runs 42,246 checks. The results are in `validation/SUMMARY.md` and each check is listed in `validation/validation_report.csv`.

- Every company's revenue account adds up line by line: 1,460 of 1,460 pass on each of the four identities.
- Every class split adds to its total: 14,118 of 14,118 pass.
- Class tables agree with the revenue account: 11,169 of 11,173 pass.
- Company rows add to IRA's printed totals: 11,022 of 11,115 pass.

The balance sheets balance for all 1,388 company quarters, and the profit and loss accounts reconcile down to profit after tax under both IFRS 4 and IFRS 17, with the handful of exceptions listed in `validation/validation_statements.csv`.

A return can add up on its own and still be wrong, so each company is also read across its quarters. Intra-Africa Assurance, for example, reported KSh 4.3bn of year-to-date premium at Q3 2024 and KSh 2.75bn for the full year. A running total cannot fall like that. Left in, it puts a phantom KSh 2.4bn underwriting profit into the market's third quarter. Twelve such returns are flagged as errors and kept out of single-quarter market totals.

Every failure traces to an error in IRA's own publications, and each one is documented:

- IRA's Q4 2024 market total leaves out two micro insurers that it lists in the same table.
- The printed totals on two sheets in Q4 2025 and Q1 2026 are stale.
- In Q2 and Q3 2019, one reinsurer's inward premium was filed under direct premium.

As an independent check, the figures were rebuilt a second way from the PDF industry releases. Market loss ratios agree to one decimal place for all five years tested, 2020 to 2024.

## Following a company through its name changes

IRA prints company names as they stood each quarter, so the same insurer can appear under three or four names. The crosswalk ties them together, and every link that rests on more than a spelling change cites a source:

- Phoenix of East Africa became MUA Insurance, which later absorbed Saham Assurance Kenya
- Cannon Assurance became Metropolitan Cannon, then Cannon General after Momentum Metropolitan sold out in 2022
- UAP became Old Mutual General in 2022
- AIG Kenya became NCBA Insurance after NCBA bought it in 2024
- Jubilee General became Jubilee Allianz, and now reports as Sanlam Allianz General

The panel's single-quarter figures add back to the full-year totals for all 3,300 company years checked. Quarters where IRA printed zeros because a company did not file are flagged and left blank, not turned into false swings.

## Layout

```
data/
  raw/          IRA source files (not in git, see below) plus manifest.csv and SOURCES.md
  processed/    the clean tables
reference/      company crosswalk
explorer/       the data explorer page and its template
src/ira_data/   extraction, panel, quality and validation code
validation/     validation report, summary, published totals, PDF cross-check
docs/           data dictionary
```

## Rebuilding

```
pip install -r requirements.txt
./run_all.sh
```

The raw files are about 400 MB, and one of them is over GitHub's 100 MB file limit, so they are not in git. `data/raw/manifest.csv` lists all 165 of them with their IRA source link and SHA-256 hash, and `data/raw/SOURCES.md` explains how they were collected, what is missing from IRA's site and why. They will be attached to a GitHub release.

## Built on this data

- [ira-kenya-reinsurance](https://github.com/maidenpeter/ira-kenya-reinsurance): every Kenyan general insurer graded A to E each year the way a reinsurer screens a cedant, back-tested against the five insurers the regulator has stepped into since 2022

## Coming next

- The annual statistics workbooks (2017 to 2025) and the reinsurance chapters of the annual reports
- Life and long-term business, as its own module
- The 2008 to 2016 PDF-only years, extracted with Veridoc, an OCR and document extraction tool in development

## Source

Insurance Regulatory Authority, Kenya: quarterly industry statistics, annual reports and claims settlement statistics, https://www.ira.go.ke. The figures are IRA's; any errors in the processing are mine.

Marion Peter
