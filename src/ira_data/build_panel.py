"""Build the company panel: stable company ids plus single-quarter figures.

IRA's quarterly figures are year to date. This script:
  - maps every raw company name to a stable company_id (reference/company_crosswalk.csv)
  - derives single-quarter figures for every flow line of the revenue account:
      Q1 = year to date at Q1
      Qn = year to date at Qn minus year to date at Qn-1, same company, same year
  - leaves the reserve balances (UPR and URR brought and carried forward) as balances, since
    differencing a balance is meaningless

Output: data/processed/general_revenue_panel.csv
quarter_basis tells you what the single-quarter figure rests on:
  derived           both year-to-date figures exist
  q1                Q1, so the single quarter is the year to date
  new_in_quarter    the company has no row in the previous quarter's workbook although the workbook
                    exists; treated as zero before (a new entrant or a first filing)
  no_prior_workbook the previous quarter's workbook is not online (before Q1 2018); left blank
  not_filed         the company's revenue account is all zeros this quarter although it is listed;
                    IRA prints zeros when a return is missing, so no single-quarter figure is given
  prior_not_filed   the previous quarter was all zeros, so differencing would be wrong; left blank
"""
import os
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "data", "processed")
BALANCES = {"upr_bf", "urr_bf", "upr_cf", "urr_cf"}

rev = pd.read_csv(os.path.join(P, "general_revenue_accounts.csv"))
cw = pd.read_csv(os.path.join(ROOT, "reference", "company_crosswalk.csv"))
rev["company"] = rev["company"].str.strip()
missing = set(rev.company) - set(cw.company_raw)
if missing:
    raise SystemExit(f"names missing from the crosswalk: {sorted(missing)}")

df = rev.merge(cw[["company_raw", "company_id", "company_name", "is_micro"]],
               left_on="company", right_on="company_raw", how="left")
df = df.rename(columns={"value_ksh_000": "ytd_ksh_000", "company": "company_as_published"})
df["ytd_ksh_000"] = df["ytd_ksh_000"].fillna(0.0)

periods = set(zip(df.year, df.quarter))
filed = (df.groupby(["company_id", "year", "quarter"]).ytd_ksh_000
           .apply(lambda v: bool((v.abs() > 0).any())).rename("filed").reset_index())
df = df.merge(filed, on=["company_id", "year", "quarter"], how="left")
pf = filed.copy(); pf["quarter"] = pf["quarter"] + 1; pf = pf.rename(columns={"filed": "prev_filed"})
df = df.merge(pf, on=["company_id", "year", "quarter"], how="left")
prev = df[["company_id", "year", "quarter", "line", "ytd_ksh_000"]].copy()
prev["quarter"] = prev["quarter"] + 1
prev = prev.rename(columns={"ytd_ksh_000": "prev_ytd"})
df = df.merge(prev, on=["company_id", "year", "quarter", "line"], how="left")

def basis(r):
    if r.line in BALANCES:
        return "balance"
    if not r.filed:
        return "not_filed"
    if r.quarter == 1:
        return "q1"
    if (r.year, r.quarter - 1) not in periods:
        return "no_prior_workbook"
    if pd.isna(r.prev_ytd):
        return "new_in_quarter"
    if r.prev_filed is False or r.prev_filed == False:
        return "prior_not_filed"
    return "derived"

df["quarter_basis"] = df.apply(basis, axis=1)
df["quarter_ksh_000"] = pd.NA
m = df.quarter_basis == "q1"; df.loc[m, "quarter_ksh_000"] = df.loc[m, "ytd_ksh_000"]
m = df.quarter_basis == "derived"; df.loc[m, "quarter_ksh_000"] = df.loc[m, "ytd_ksh_000"] - df.loc[m, "prev_ytd"]
m = df.quarter_basis == "new_in_quarter"; df.loc[m, "quarter_ksh_000"] = df.loc[m, "ytd_ksh_000"]

cols = ["company_id", "company_name", "company_as_published", "segment", "is_micro", "year", "quarter",
        "period_end", "line", "ytd_ksh_000", "quarter_ksh_000", "quarter_basis", "source_file", "source_sheet"]
out = df[cols].sort_values(["company_id", "year", "quarter", "line"])
out.to_csv(os.path.join(P, "general_revenue_panel.csv"), index=False, lineterminator="\n")
print(out.quarter_basis.value_counts().to_string())
print(f"rows {len(out)}  companies {out.company_id.nunique()}")
