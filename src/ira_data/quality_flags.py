"""Quarter-to-quarter consistency checks on each company's own figures.

The validation in validate.py proves every quarter adds up on its own. It cannot see a return that
adds up but is wrong, for example a company whose year-to-date premium is higher at Q3 than at Q4.
This script looks across quarters for each company and writes validation/quality_flags.csv, one row
per company, quarter and problem, then marks the panel.

Flags (severity):
  premium_reversal (error)   year-to-date written premium falls by more than 5% and KSh 50m from the
                             previous quarter. A running total cannot fall that far, so one of the two
                             returns is wrong. Both quarters are flagged.
  premium_spike (error)      a single quarter's written premium is over 3 times the company's median
                             quarter and over KSh 500m, and the next quarter reverses it.
  claims_collapse (error)    year-to-date incurred claims fall by 80% or more, and by over KSh 200m,
                             from the previous quarter. Claims already incurred cannot disappear that
                             far within a year, so one of the two returns is wrong. Both quarters flagged.
  claims_reversal (warning)  single-quarter incurred claims below minus KSh 200m. Can be a genuine
                             reserve release, can be a bad return.
  loss_ratio_outlier (warning) single-quarter claims over earned premium outside -50% to 300% where
                             earned premium is above KSh 100m.
  not_filed (info)           the company is listed but every figure is zero.
  direct_inward_reclass (info) a reinsurer's direct premium falls while its inward premium rises by a
                             similar amount; the two are combined as written premium for all checks.

Written premium = gross direct premium + inward reinsurance.
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "data", "processed")
V = os.path.join(ROOT, "validation")


def build(pan):
    w = pan.pivot_table(index=["company_id", "segment", "year", "quarter"], columns="line",
                        values=["ytd_ksh_000", "quarter_ksh_000"], aggfunc="first")
    w.columns = [f"{a.split('_')[0]}_{b}" for a, b in w.columns]  # ytd_line / quarter_line
    w = w.reset_index().sort_values(["company_id", "year", "quarter"])
    basis = (pan[pan.line == "gross_direct_premium"]
             .set_index(["company_id", "year", "quarter"]).quarter_basis)
    w = w.join(basis, on=["company_id", "year", "quarter"])
    w["ytd_written"] = w["ytd_gross_direct_premium"].fillna(0) + w["ytd_inward_reinsurance"].fillna(0)
    w["q_written"] = w["quarter_gross_direct_premium"] + w["quarter_inward_reinsurance"]
    flags = []

    def add(r, code, sev, detail):
        flags.append(dict(company_id=r.company_id, segment=r.segment, year=int(r.year), quarter=int(r.quarter),
                          flag=code, severity=sev, detail=detail))

    for cid, g in w.groupby("company_id"):
        g = g.reset_index(drop=True)
        med = g.loc[g.q_written > 0, "q_written"].median()
        for i, r in g.iterrows():
            if r.quarter_basis == "not_filed":
                add(r, "not_filed", "info", "listed with an all-zero account")
                continue
            prev = g[(g.year == r.year) & (g.quarter == r.quarter - 1)]
            if len(prev) and r.quarter_basis in ("derived",):
                p = prev.iloc[0]
                drop = r.ytd_written - p.ytd_written
                if drop < -max(0.05 * abs(p.ytd_written), 50_000):
                    add(r, "premium_reversal", "error",
                        f"year-to-date written premium fell from {p.ytd_written/1e3:,.0f}m at Q{int(p.quarter)} to {r.ytd_written/1e3:,.0f}m")
                    add(p, "premium_reversal", "error",
                        f"year-to-date written premium of {p.ytd_written/1e3:,.0f}m is higher than the {r.ytd_written/1e3:,.0f}m reported at Q{int(r.quarter)}")
                pc, rc = p.get("ytd_incurred_claims"), r.get("ytd_incurred_claims")
                if pd.notna(pc) and pd.notna(rc) and pc > 200_000 and rc <= 0.2 * pc:
                    add(r, "claims_collapse", "error",
                        f"year-to-date incurred claims fell from {pc/1e3:,.0f}m at Q{int(p.quarter)} to {rc/1e3:,.0f}m")
                    add(p, "claims_collapse", "error",
                        f"year-to-date incurred claims of {pc/1e3:,.0f}m all but vanish by Q{int(r.quarter)} ({rc/1e3:,.0f}m)")
                if r.segment == "reinsurer":
                    d_direct = r.ytd_gross_direct_premium - p.ytd_gross_direct_premium
                    d_inward = r.ytd_inward_reinsurance - p.ytd_inward_reinsurance
                    if d_direct < -50_000 and d_inward > 0.5 * abs(d_direct):
                        add(r, "direct_inward_reclass", "info",
                            f"direct premium down {abs(d_direct)/1e3:,.0f}m while inward premium up {d_inward/1e3:,.0f}m")
            nxt = g[(g.year == r.year) & (g.quarter == r.quarter + 1)]
            if pd.notna(r.q_written) and pd.notna(med) and med > 0 and r.q_written > max(3 * med, 500_000) \
                    and len(nxt) and pd.notna(nxt.iloc[0].q_written) and nxt.iloc[0].q_written < 0:
                add(r, "premium_spike", "error",
                    f"single-quarter written premium {r.q_written/1e3:,.0f}m against a typical {med/1e3:,.0f}m, reversed the next quarter")
            qc, qn = r.get("quarter_incurred_claims"), r.get("quarter_net_earned_premium")
            if pd.notna(qc) and qc < -200_000:
                add(r, "claims_reversal", "warning", f"single-quarter incurred claims of {qc/1e3:,.0f}m")
            if pd.notna(qc) and pd.notna(qn) and qn > 100_000:
                lr = qc / qn
                if lr < -0.5 or lr > 3:
                    add(r, "loss_ratio_outlier", "warning", f"single-quarter loss ratio {lr:.0%}")
    f = pd.DataFrame(flags).drop_duplicates(["company_id", "year", "quarter", "flag"])
    return f.sort_values(["year", "quarter", "company_id", "flag"])


def main():
    pan = pd.read_csv(os.path.join(P, "general_revenue_panel.csv"))
    f = build(pan)
    f.to_csv(os.path.join(V, "quality_flags.csv"), index=False, lineterminator="\n")
    # mark the panel: codes per company-quarter, and whether single-quarter figures are fit for market totals
    agg = f.groupby(["company_id", "year", "quarter"]).agg(
        quality_flags=("flag", lambda s: ";".join(sorted(set(s)))),
        worst=("severity", lambda s: "error" if "error" in set(s) else "warning" if "warning" in set(s) else "info"))
    pan = pan.drop(columns=[c for c in ["quality_flags", "reliable_quarter"] if c in pan.columns])
    pan = pan.join(agg, on=["company_id", "year", "quarter"])
    pan["quality_flags"] = pan["quality_flags"].fillna("")
    pan["reliable_quarter"] = (pan["worst"] != "error") & pan["quarter_ksh_000"].notna()
    pan = pan.drop(columns=["worst"])
    pan.to_csv(os.path.join(P, "general_revenue_panel.csv"), index=False, lineterminator="\n")
    print(f.groupby(["severity", "flag"]).size().to_string())
    print()
    print(f[f.severity == "error"].to_string(index=False))


if __name__ == "__main__":
    main()
