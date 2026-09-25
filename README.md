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

## Tables

| File | Rows | What it holds |
|---|---|---|
| `data/processed/general_revenue_accounts.csv` | 21,900 | The general business revenue account for every insurer and reinsurer: gross premium, inward and outward reinsurance, reserves, net earned premium, claims, commissions, expenses, underwriting result, investment income, operating result |
| `data/processed/general_by_class.csv` | 211,785 | The same companies split by 14 classes of business (motor private, medical, fire industrial and so on) across up to ten tables: gross premium, gross direct premium, inward premium, net premium, net earned premium, claims paid, claims incurred, commissions, management expenses, underwriting result |

35 quarters, 66 company names, two segments (insurer, reinsurer). Figures are in KSh thousands, year to date and unaudited, exactly as IRA published them. See `docs/data_dictionary.md` for every column.

## How it is checked

`src/ira_data/validate.py` runs 42,246 checks. The results are in `validation/SUMMARY.md` and each check is listed in `validation/validation_report.csv`.

- Every company's revenue account adds up line by line: 1,460 of 1,460 pass on each of the four identities.
- Every class split adds to its total: 14,118 of 14,118 pass.
- Class tables agree with the revenue account: 11,169 of 11,173 pass.
- Company rows add to IRA's printed totals: 11,022 of 11,115 pass.

Every failure traces to an error in IRA's own publications, and each one is documented:

- IRA's Q4 2024 market total leaves out two micro insurers that it lists in the same table.
- The printed totals on two sheets in Q4 2025 and Q1 2026 are stale.
- In Q2 and Q3 2019, one reinsurer's inward premium was filed under direct premium.

As an independent check, the figures were rebuilt a second way from the PDF industry releases. Market loss ratios agree to one decimal place for all five years tested, 2020 to 2024.

## Layout

```
data/
  raw/          IRA source files (not in git, see below) plus manifest.csv and SOURCES.md
  processed/    the clean tables
src/ira_data/   extraction and validation code
validation/     validation report, summary, published totals, PDF cross-check
docs/           data dictionary
```

## Rebuilding

```
pip install -r requirements.txt
python src/ira_data/extract_quarterly_general.py
python src/ira_data/validate.py
```

The raw files are about 400 MB, and one of them is over GitHub's 100 MB file limit, so they are not in git. `data/raw/manifest.csv` lists all 165 of them with their IRA source link and SHA-256 hash, and `data/raw/SOURCES.md` explains how they were collected, what is missing from IRA's site and why. They will be attached to a GitHub release.

## Coming next

- A company crosswalk, so renamed and merged insurers line up over time (for example AIG Insurance reappearing as NCBA Insurance, and the Jubilee Allianz combination)
- Single-quarter figures derived from the year-to-date series
- The annual statistics workbooks (2017 to 2025) and the reinsurance chapters of the annual reports
- The 2008 to 2016 PDF-only years, extracted with Veridoc, an OCR and document extraction tool in development

## Source

Insurance Regulatory Authority, Kenya: quarterly industry statistics, annual reports and claims settlement statistics, https://www.ira.go.ke. The figures are IRA's; any errors in the processing are mine.

Marion Peter
