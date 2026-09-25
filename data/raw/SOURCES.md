# IRA Kenya source files

Every statistical publication the Insurance Regulatory Authority (IRA) of Kenya has put online, from the 2008 annual report to the Q1 2026 quarterly release. Pulled on 2026-09-25.

**165 unique files, 414 MB.** Every file is listed in `manifest.csv` with its SHA-256 hash, page count, whether the PDF has a text layer, the IRA page it came from and the download link.

## Layout

```
data/raw/
  annual/
    reports/          IRA_Annual_Report_YYYY.pdf
    statistics/       IRA_Annual_Statistics_YYYY.xlsx|xlsm|xls
    press_releases/   IRA_Annual_Press_Release_YYYY.pdf
  quarterly/YYYY/     IRA_YYYY_QN_Industry_Release.pdf, IRA_YYYY_QN_Industry_Statistics.xlsx
  claims_settlement/YYYY/  IRA_YYYY_QN_Claims_Report.pdf, IRA_YYYY_QN_Claims_Statistics.xlsx
  reference/          IRA reinsurance returns templates (Forms I to VII, 2019)
  manifest.csv
```

The original IRA file names are inconsistent (`2013_Q4_INDUTRY_RELEASE.pdf`, `Q4-2018--Industry-Release.pdf`, `ed0f443c-quarter-2-2025-industry-release.pdf`). They are all renamed to one pattern here. The title each file had on IRA's site, and its download link, are kept in `manifest.csv`.

## Coverage

### Annual

| Year | Industry report | Statistics workbook |
|---|---|---|
| 2008 | PDF scanned | . |
| 2009 | PDF | . |
| 2010 | . | . |
| 2011 | . | . |
| 2012 | PDF | . |
| 2013 | PDF (Parliament copy) scanned | . |
| 2014 | PDF | . |
| 2015 | PDF | . |
| 2016 | PDF | . |
| 2017 | PDF | XLSM |
| 2018 | PDF | . |
| 2019 | PDF (Parliament copy) | XLSM |
| 2020 | PDF | XLSM |
| 2021 | PDF | XLSM |
| 2022 | PDF | XLSM |
| 2023 | PDF | XLSX |
| 2024 | PDF | XLSX |
| 2025 | . | XLSX |

### Quarterly industry releases (year to date, unaudited)

| Year | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| 2013 | PDF | PDF | PDF | PDF |
| 2014 | PDF | PDF | PDF | . |
| 2015 | . | PDF | PDF | . |
| 2016 | PDF | PDF | PDF | PDF + XLSX |
| 2017 | PDF | PDF | PDF + XLSX | PDF |
| 2018 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2019 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2020 | PDF + XLSX | XLSX | PDF + XLSX | PDF + XLSX |
| 2021 | PDF + XLSX | PDF + XLSX | PDF + XLSX | XLSX |
| 2022 | XLSX | PDF + XLSX | PDF + XLSX | XLSX |
| 2023 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2024 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2025 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2026 | PDF + XLSX | . | . | . |

### Quarterly claims settlement

| Year | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| 2017 | XLSX | XLSX | XLSX | XLSX |
| 2018 | XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2019 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2020 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2021 | . | . | . | PDF + XLSX |
| 2022 | . | . | PDF + XLSX | PDF + XLSX |
| 2023 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2024 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2025 | PDF + XLSX | PDF + XLSX | PDF + XLSX | PDF + XLSX |
| 2026 | PDF + XLSX | . | . | . |

`.` means IRA does not have that file online. Q4 2014 was never listed at all.

## Gaps and quirks

- **Missing on IRA's site:** the annual reports for 2010 and 2011, the 2018 annual statistics workbook, the Q1 2015, Q4 2015, Q2 2020, Q4 2021, Q1 2022 and Q4 2022 quarterly releases, the Q4 2017 quarterly statistics and the Q1 2022 claims report. Their pages exist but return "File not found". Q2 2020, Q4 2021, Q1 2022 and Q4 2022 still have their statistics workbook.
- **Recovered from elsewhere:** the listing pages for the 2008, 2009, 2012 and 2015 annual reports and the 2019 statistics workbook are dead, but the files are still on IRA's server under their old names. The 2013 and 2019 annual reports came from the Parliament of Kenya library, where they were tabled.
- **Scanned PDFs:** the 2008 report and the 2013 Parliament copy are images with no text layer. They need OCR before any extraction.
- **Mislabelled on IRA's site:** the 2016 claims entries and the Q1 and Q2 2022 claims entries are the same files as that quarter's industry release or statistics workbook. They are not copied twice. The Q3 and Q4 2018 and Q4 2020 listings swap the "Release" and "Statistics" titles. Files are filed by what they actually contain.
- **Reinsurance:** IRA has no separate reinsurance series. The reinsurance data sits inside the annual reports. The 2023 report, for example, has a chapter on reinsurers (reinsurance premium, retrocession, net earned premium, incurred claims, claims ratios and underwriting results) plus insurers' inward and outward reinsurance premium by class. How far back that chapter runs is still to be checked year by year.
- **Reporting basis:** IFRS 17 applies from 2023, so premium and ratio figures before and after 2023 are not directly comparable.

## Refreshing

IRA's site puts a reCAPTCHA in front of every page, so it has to be opened in a browser once. After that, the listings come from `https://www.ira.go.ke/assets/includes/ajapp.php` (annual reports section 56, quarterly 57, claims 59) and each file downloads from `https://www.ira.go.ke/lib.html?f=<slug>`. The slug for every file is in `manifest.csv`.
