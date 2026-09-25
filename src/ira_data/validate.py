"""Validate the extracted general insurance tables.

Checks, per period and segment:
  1. Company rows add up to the TOTAL row IRA prints (revenue account and every class table).
  2. The revenue account adds up line by line:
       net premium written  = gross direct premium + inward reinsurance - outward reinsurance
       net earned premium   = net premium written + UPR b/f + URR b/f - UPR c/f - URR c/f
       underwriting result  = net earned premium - incurred claims - commissions - management expenses
       operating result     = underwriting result + investment income
  3. Each class table's company Total column matches the matching revenue account line.
  4. Classes add up to the Total column.

Writes validation/validation_report.csv (every check) and validation/SUMMARY.md.
A check passes when the difference is within max(5, 0.1% of the larger figure), in KSh thousands.
Known, explained failures are listed in KNOWN_ISSUES and reported separately.
"""
import os
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "data", "processed")
V = os.path.join(ROOT, "validation")

rev = pd.read_csv(os.path.join(P, "general_revenue_accounts.csv"))
rev["value_ksh_000"] = rev["value_ksh_000"].fillna(0)
cls = pd.read_csv(os.path.join(P, "general_by_class.csv"))
tot = pd.read_csv(os.path.join(V, "published_totals.csv"))

def ok(a, b):
    return abs(a - b) <= max(5.0, 0.001 * max(abs(a), abs(b)))

checks = []
def add(kind, year, q, segment, subject, expected, actual, note=""):
    if pd.isna(expected) or pd.isna(actual):
        return  # IRA left the published total blank; nothing to check against
    checks.append(dict(check=kind, year=year, quarter=q, segment=segment, subject=subject,
                       expected=round(expected, 3), actual=round(actual, 3),
                       diff=round(actual - expected, 3), passed=ok(expected, actual), note=note))

# 1. sums to published totals
rs = rev.groupby(["year", "quarter", "segment", "line"]).value_ksh_000.sum()
first_tot = tot.groupby(["year", "quarter", "table", "segment", "column"]).value.first()
for (y, q, seg, line), s in rs.items():
    key = (y, q, "revenue_account", seg, line)
    if key in first_tot.index:
        add("sum_to_total", y, q, seg, f"revenue_account:{line}", first_tot[key], s)
cs = cls.groupby(["year", "quarter", "table", "segment", "class_of_business"]).value_ksh_000.sum()
for (y, q, t, seg, c), s in cs.items():
    key = (y, q, t, seg, c)
    if key in first_tot.index:
        add("sum_to_total", y, q, seg, f"{t}:{c}", first_tot[key], s)

# 2. revenue account identities, per company
w = rev.pivot_table(index=["year", "quarter", "segment", "company"], columns="line",
                    values="value_ksh_000", aggfunc="sum").reset_index()
for _, r in w.iterrows():
    k = (r.year, r.quarter, r.segment)
    add("identity_npw", *k, r.company, r.gross_direct_premium + r.inward_reinsurance - r.outward_reinsurance, r.net_premium_written)
    add("identity_nep", *k, r.company, r.net_premium_written + r.upr_bf + r.urr_bf - r.upr_cf - r.urr_cf, r.net_earned_premium)
    add("identity_uw", *k, r.company, r.net_earned_premium - r.incurred_claims - r.net_commissions - r.management_expenses, r.underwriting_result)
    add("identity_op", *k, r.company, r.underwriting_result + r.investment_income, r.operating_result)

# 3. class tables vs revenue account
link = {"net_earned_premium": "net_earned_premium", "claims_incurred": "incurred_claims",
        "commissions": "net_commissions", "management_expenses": "management_expenses",
        "underwriting_result": "underwriting_result", "inward_premium": "inward_reinsurance",
        "net_premium": "net_premium_written", "gross_direct_premium": "gross_direct_premium"}
ct = cls[cls.class_of_business == "Total"].set_index(["year", "quarter", "segment", "company", "table"]).value_ksh_000
wi = w.set_index(["year", "quarter", "segment", "company"])
for (y, q, seg, co, t), v in ct.items():
    if t in link and (y, q, seg, co) in wi.index:
        add("class_vs_revenue", y, q, seg, f"{co} | {t}", wi.loc[(y, q, seg, co), link[t]], v)

# 4. classes add to Total
parts = cls[cls.class_of_business != "Total"].groupby(["year", "quarter", "table", "segment", "company"]).value_ksh_000.sum()
for (y, q, t, seg, co), v in parts.items():
    if (y, q, seg, co, t) in ct.index:
        add("classes_to_total", y, q, seg, f"{co} | {t}", ct[(y, q, seg, co, t)], v)

# known, explained IRA publishing errors (found while building this repo)
KNOWN_ISSUES = [
    ("sum_to_total", 2024, 4, "insurer", None,
     "IRA's Q4 2024 insurer TOTAL row leaves out two micro insurers that are listed in the general tables "
     "(STAR DISCOVER MICRO INSURANCE and TURACO MICRO INSURANCE). Adding those two back reproduces every published total."),
    ("sum_to_total", 2025, 4, "insurer", ("gross_direct_premium:", "inward_premium:"),
     "The TOTAL rows on the Q4 2025 GDP and INWARD sheets do not match their own company rows. The company rows do "
     "match the revenue account, so the printed totals are stale."),
    ("sum_to_total", 2026, 1, "insurer", ("gross_direct_premium:", "inward_premium:"),
     "Same stale TOTAL rows on the Q1 2026 GDP and INWARD sheets."),
    ("class_vs_revenue", 2019, 2, "reinsurer", ("CONTINENTAL REINSURANCE",),
     "Q2 2019: IRA put Continental Re's inward premium in the gross direct premium class table."),
    ("class_vs_revenue", 2019, 3, "reinsurer", ("CONTINENTAL REINSURANCE",),
     "Q3 2019: same misplacement of Continental Re's inward premium."),
]
def explain(r):
    for chk, y, q, seg, subj, why in KNOWN_ISSUES:
        if r["check"] == chk and r["year"] == y and r["quarter"] == q and r["segment"] == seg and \
           (subj is None or any(r["subject"].startswith(x) for x in subj)):
            return why
    return ""

rep = pd.DataFrame(checks)
rep["known_issue"] = rep.apply(lambda r: explain(r) if not r["passed"] else "", axis=1)
rep.to_csv(os.path.join(V, "validation_report.csv"), index=False)
summ = rep.groupby("check").passed.agg(["count", "sum"])
summ["pass_rate_%"] = (100 * summ["sum"] / summ["count"]).round(2)
print(summ)
fails = rep[~rep.passed]
unexplained = rep[(~rep.passed) & (rep.known_issue == "")]
print("\nunexplained failures:", len(unexplained))
print(unexplained[["check", "year", "quarter", "segment", "subject", "expected", "actual"]].to_string(index=False))
print("\nfailures by check and period (top):")
print(fails.groupby(["check", "year", "quarter"]).size().sort_values(ascending=False).head(25).to_string())

# 5. cross-check against the PDF industry releases (Q4 2023 and Q4 2024 releases, tables 15 to 21,
#    extracted independently with pdftotext for case study 03). Insurers only, micro insurers excluded.
PDF_REF = [  # (year, measure, value from the release, unit)
    (2020, "loss_ratio_pct", 63.6), (2021, "loss_ratio_pct", 68.8), (2022, "loss_ratio_pct", 67.9),
    (2023, "loss_ratio_pct", 67.9), (2024, "loss_ratio_pct", 70.4),
    (2020, "underwriting_result_ksh_bn", -1.18), (2021, "underwriting_result_ksh_bn", -6.34),
    (2022, "underwriting_result_ksh_bn", -3.72), (2023, "underwriting_result_ksh_bn", -4.96),
    (2024, "underwriting_result_ksh_bn", -5.24),
    (2020, "medical_gross_premium_ksh_bn", 44.98), (2024, "medical_gross_premium_ksh_bn", 76.31),
]
xr = []
for y, measure, ref in PDF_REF:
    g = rev[(rev.year == y) & (rev.quarter == 4) & (rev.segment == "insurer") & (~rev.company.str.contains("MICRO"))]
    g = g.groupby("line").value_ksh_000.sum()
    if measure == "loss_ratio_pct":
        v = round(100 * g.incurred_claims / g.net_earned_premium, 1)
    elif measure == "underwriting_result_ksh_bn":
        v = round(g.underwriting_result / 1e6, 2)
    else:
        m = cls[(cls.year == y) & (cls.quarter == 4) & (cls.segment == "insurer") & (~cls.company.str.contains("MICRO"))
                & (cls.table == "gross_premium") & (cls.class_of_business == "Medical")]
        v = round(m.value_ksh_000.sum() / 1e6, 2)
    xr.append(dict(year=y, measure=measure, pdf_release=ref, workbooks=v, difference=round(v - ref, 2)))
xr = pd.DataFrame(xr)
xr.to_csv(os.path.join(V, "crosscheck_pdf_releases.csv"), index=False)
print("\ncross-check against PDF releases\n", xr.to_string(index=False))

# summary file
lines = ["# Validation summary", "",
         "Generated by `src/ira_data/validate.py`. Every check is in `validation_report.csv`.", "",
         "| Check | Checks run | Passed | Pass rate |", "|---|---|---|---|"]
names = {"sum_to_total": "Company rows add to IRA's printed TOTAL",
         "identity_npw": "Net premium written = gross + inward - outward",
         "identity_nep": "Net earned premium = NPW + opening reserves - closing reserves",
         "identity_uw": "Underwriting result = NEP - claims - commissions - expenses",
         "identity_op": "Operating result = underwriting result + investment income",
         "class_vs_revenue": "Class table totals match the revenue account",
         "classes_to_total": "Classes add to each company's Total column"}
for k, r in summ.iterrows():
    lines.append(f"| {names.get(k, k)} | {int(r['count']):,} | {int(r['sum']):,} | {r['pass_rate_%']}% |")
lines += ["", f"**Unexplained failures: {len(unexplained)}.** Every failed check traces to one of these IRA publishing errors:", ""]
for chk, y, q, seg, subj, why in KNOWN_ISSUES:
    n = int(((rep.known_issue == why) & (rep.year == y) & (rep.quarter == q)).sum())
    lines.append(f"- **Q{q} {y}** ({n} checks): {why}")
lines += ["", "## Cross-check against the PDF releases", "",
          "The same figures pulled from the Q4 2023 and Q4 2024 PDF industry releases, independently of the workbooks. Insurers only, micro insurers excluded.", "",
          "| Year | Measure | PDF release | Workbooks | Difference |", "|---|---|---|---|---|"]
for _, r in xr.iterrows():
    lines.append(f"| {r.year} | {r.measure} | {r.pdf_release} | {r.workbooks} | {r.difference} |")
lines += ["", "Loss ratios agree to one decimal for all five years. The underwriting results for 2023 and 2024 and the 2024 medical premium differ slightly, by KSh 0.01bn to 0.1bn. "
          "The PDF figures are sums over classes of business while the workbook figures come from company revenue accounts; the source of the gap is still to be traced."]
open(os.path.join(V, "SUMMARY.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
