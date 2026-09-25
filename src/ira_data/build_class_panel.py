"""Class-of-business tables on stable company ids, with single-quarter figures.

Uses the same rules as build_panel.py. The basis for each company and quarter (derived, q1,
new_in_quarter, not_filed, prior_not_filed, no_prior_workbook) and the reliability mark from
quality_flags.py are taken from the revenue panel, so a quarter that is unreliable for the revenue
account is unreliable for its class split too.

Output: data/processed/general_by_class_panel.csv (provenance columns are in general_by_class.csv).
"""
import os
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "data", "processed")

cls = pd.read_csv(os.path.join(P, "general_by_class.csv"))
cw = pd.read_csv(os.path.join(ROOT, "reference", "company_crosswalk.csv"))
pan = pd.read_csv(os.path.join(P, "general_revenue_panel.csv"),
                  usecols=["company_id", "year", "quarter", "line", "quarter_basis", "reliable_quarter", "quality_flags"])
basis = pan[pan.line == "gross_direct_premium"].drop(columns="line")

cls["company"] = cls["company"].str.strip()
df = cls.merge(cw[["company_raw", "company_id"]], left_on="company", right_on="company_raw", how="left")
if df.company_id.isna().any():
    raise SystemExit("unmapped company names in the class tables")
df["ytd_ksh_000"] = df["value_ksh_000"].fillna(0.0)
df = df[["company_id", "segment", "year", "quarter", "table", "class_of_business", "ytd_ksh_000"]]

prev = df.copy(); prev["quarter"] += 1
prev = prev.rename(columns={"ytd_ksh_000": "prev_ytd"}).drop(columns="segment")
df = df.merge(prev, on=["company_id", "year", "quarter", "table", "class_of_business"], how="left")
df = df.merge(basis, on=["company_id", "year", "quarter"], how="left")

b = df.quarter_basis
df["quarter_ksh_000"] = pd.NA
df.loc[b.isin(["q1", "new_in_quarter"]), "quarter_ksh_000"] = df.loc[b.isin(["q1", "new_in_quarter"]), "ytd_ksh_000"]
m = b == "derived"
# a table can be missing in the previous workbook (IRA added tables over time): then leave it blank
df.loc[m & df.prev_ytd.notna(), "quarter_ksh_000"] = df.loc[m & df.prev_ytd.notna(), "ytd_ksh_000"] - df.loc[m & df.prev_ytd.notna(), "prev_ytd"]
df.loc[m & df.prev_ytd.isna(), "quarter_basis"] = "table_new_in_quarter"
df["reliable_quarter"] = df["reliable_quarter"].fillna(False) & df["quarter_ksh_000"].notna()
out = df.drop(columns="prev_ytd").sort_values(["company_id", "year", "quarter", "table", "class_of_business"])
out.to_csv(os.path.join(P, "general_by_class_panel.csv"), index=False, lineterminator="\n", float_format="%.3f")
print(out.quarter_basis.value_counts().to_string()); print("rows", len(out))

# check: classes of the single-quarter figures still add to the single-quarter Total
q = out[out.quarter_ksh_000.notna()]
parts = q[q.class_of_business != "Total"].groupby(["company_id", "year", "quarter", "table"]).quarter_ksh_000.sum()
tot = q[q.class_of_business == "Total"].set_index(["company_id", "year", "quarter", "table"]).quarter_ksh_000
gap = (parts.reindex(tot.index).astype(float) - tot.astype(float)).abs()
print("single-quarter classes add to Total within KSh 10k (rounding):", int((gap <= 10).sum()), "of", int(gap.notna().sum()))
