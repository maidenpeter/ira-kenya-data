"""Build the claims settlement panel and check it.

Reads data/processed/claims_settlement.csv (from extract_claims.py) and reference/claims_crosswalk.csv and writes

  data/processed/claims_panel.csv   one row per quarter, business, unit and company, with the payment ratio
  validation/claims_checks.csv      every check, one row each, with its result
  validation/CLAIMS_SUMMARY.md      the checks in a few lines

Two readings are applied, both from the tables themselves:
- From Q3 2018 to Q2 2020 the column printed as "claims revived" does not add to the count. With it, 55 to 62
  of about 99 rows a quarter fail to reconcile; without it, 2 to 17 do. From Q3 2020 IRA prints the same
  column as "claims revised", which never adds to the count. It is read as revised for those eight quarters.
- A company printed twice in one quarter (Jubilee Allianz General and Sanlam Allianz General in Q4 2025, the
  quarter of the merger) is summed.

The payment ratio is IRA's: claims paid in the quarter over the claims that were open to the insurer in the
quarter (paid + declined + closed as no claim + still outstanding at the end). A return that prints a negative
count anywhere in that sum cannot be right; it is kept as printed, counted as a failed check, and given no ratio.
"""
import os
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROC = os.path.join(ROOT, "data", "processed")
VAL = os.path.join(ROOT, "validation")
F = ["opening", "intimated", "revived", "revised", "paid", "declined", "closed", "declined_closed", "closing"]
REVIVED_IS_REVISED = {"2018Q3", "2018Q4", "2019Q1", "2019Q2", "2019Q3", "2019Q4", "2020Q1", "2020Q2"}
# printed totals that do not match their rows, and why
EXPLAINED = {
    ("2020Q1", "long_term", "number"): "IRA's printed industry line leaves out Absa Life Assurance, in the first quarter it was printed "
                                       "under its new name: the gap in every column is Absa Life's row",
    ("2017Q1", "general_liability", "number"): "the printed line is one claim higher than its rows for claims reported and claims paid",
}
TOL = {"number": 0.5, "amount": 1.0}   # one claim; KSh 1,000 (the tables print KSh thousands to three decimals)


def prev_period(p):
    y, q = int(p[:4]), int(p[5])
    return f"{y - 1}Q4" if q == 1 else f"{y}Q{q - 1}"


def main():
    raw = pd.read_csv(os.path.join(PROC, "claims_settlement.csv"))
    cw = pd.read_csv(os.path.join(ROOT, "reference", "claims_crosswalk.csv"))
    raw["side"] = raw.business.map(lambda b: "long_term" if b == "long_term" else "general")
    d = raw.merge(cw, on=["side", "company_raw"], how="left")
    missing = d[d.company_id.isna()][["side", "company_raw"]].drop_duplicates()
    if len(missing):
        raise SystemExit(f"names missing from reference/claims_crosswalk.csv: {missing.values.tolist()}")

    fix = d.period.isin(REVIVED_IS_REVISED) & d.revived.notna()
    d.loc[fix, "revised"] = d.loc[fix, "revived"]
    d.loc[fix, "revived"] = None

    checks = []

    def check(kind, period, business, unit, company, field, value, expected, ok, note=""):
        checks.append(dict(check=kind, period=period, business=business, unit=unit, company=company, field=field,
                           value=value, expected=expected, result="pass" if ok else "explained" if note else "fail", note=note))

    # 1. the rows add up to IRA's printed industry line
    tot = pd.read_csv(os.path.join(VAL, "claims_printed_totals.csv"))
    tot.loc[tot.period.isin(REVIVED_IS_REVISED) & tot.revived.notna(), "revised"] = tot.revived
    tot.loc[tot.period.isin(REVIVED_IS_REVISED), "revived"] = None
    s = d.groupby(["period", "business", "unit"])[F].sum(min_count=1).reset_index()
    m = s.merge(tot, on=["period", "business", "unit"], suffixes=("", "_printed"))
    for _, x in m.iterrows():
        for f in F:
            a, b = x[f], x[f + "_printed"]
            if pd.isna(a) and pd.isna(b):
                continue
            a, b = (0 if pd.isna(a) else a), (0 if pd.isna(b) else b)
            ok = abs(a - b) <= TOL[x.unit]
            note = "" if ok else EXPLAINED.get((x.period, x.business, x.unit), "")
            check("sum_equals_printed_total", x.period, x.business, x.unit, "", f, round(a, 3), round(b, 3), ok, note)

    # one row per company and quarter
    g = d.groupby(["period", "year", "quarter", "business", "unit", "company_id", "company_name", "is_micro"],
                  dropna=False)[F].sum(min_count=1).reset_index()
    names = d.groupby(["period", "business", "unit", "company_id"]).company_raw.nunique().rename("printed_names").reset_index()
    g = g.merge(names, on=["period", "business", "unit", "company_id"], how="left")
    g["actionable"] = g[["paid", "declined", "closed", "declined_closed", "closing"]].fillna(0).sum(axis=1)
    parts = g[["paid", "declined", "closed", "declined_closed", "closing"]]
    negative = (parts.fillna(0) < 0).any(axis=1)
    g["payment_ratio"] = (g.paid / g.actionable).where((g.actionable > 0) & ~negative)
    for _, x in g[(g.unit == "number")].iterrows():
        bad = [f for f in parts.columns if pd.notna(x[f]) and x[f] < 0]
        check("counts_not_negative", x.period, x.business, x.unit, x.company_id, ";".join(bad) or "all",
              min([x[f] for f in bad]) if bad else 0, 0, not bad)
    g["declined_ratio"] = (g.declined / g.actionable).where(g.actionable > 0)   # not printed separately in 2017

    # 2. the quarter's movement adds up, for counts: start + reported + revived - paid - declined - closed = end
    n = g[g.unit == "number"]
    calc = (n.opening.fillna(0) + n.intimated.fillna(0) + n.revived.fillna(0) - n.paid.fillna(0)
            - n.declined.fillna(0) - n.closed.fillna(0) - n.declined_closed.fillna(0))
    for (i, x), c in zip(n.iterrows(), calc):
        check("movement_adds_up", x.period, x.business, x.unit, x.company_id, "closing", x.closing, round(c, 3),
              abs(x.closing - c) <= TOL["number"])

    # 3. a quarter starts where the last one ended, where both quarters were published
    key = g.set_index(["period", "business", "unit", "company_id"])
    for (p, b, u, c), x in key.iterrows():
        q = prev_period(p)
        if u != "number" or (q, b, u, c) not in key.index:
            continue
        before = key.loc[(q, b, u, c), "closing"]
        check("opening_equals_last_closing", p, b, u, c, "opening", x.opening, before, abs(x.opening - before) <= TOL[u])

    # 4. IRA's printed payment ratio is the one recomputed here
    r = d[(d.unit == "number") & d.printed_ratio.notna()].copy()
    r["actionable"] = r[["paid", "declined", "closed", "declined_closed", "closing"]].fillna(0).sum(axis=1)
    r = r[r.actionable > 0]
    for _, x in r.iterrows():
        mine = 100 * x.paid / x.actionable
        check("payment_ratio_as_printed", x.period, x.business, x.unit, x.company_id, "printed_ratio",
              round(mine, 4), round(x.printed_ratio, 4), abs(mine - x.printed_ratio) <= 0.05)

    ch = pd.DataFrame(checks)
    ch.to_csv(os.path.join(VAL, "claims_checks.csv"), index=False, lineterminator="\n")
    cols = ["period", "year", "quarter", "business", "unit", "company_id", "company_name", "is_micro"] + F + \
           ["actionable", "payment_ratio", "declined_ratio", "printed_names"]
    g = g.sort_values(["business", "unit", "company_id", "year", "quarter"])
    g[cols].to_csv(os.path.join(PROC, "claims_panel.csv"), index=False, lineterminator="\n", float_format="%.6f")

    summ = ch.groupby("check").result.value_counts().unstack(fill_value=0)
    lines = ["# Claims settlement checks", "",
             f"{raw.period.nunique()} quarters, {len(raw)} printed rows, {g.company_id.nunique()} companies after the crosswalk.", "",
             "| Check | Pass | Explained | Fail |", "|---|---|---|---|"]
    for k, x in summ.iterrows():
        lines.append(f"| {k} | {x.get('pass', 0)} | {x.get('explained', 0)} | {x.get('fail', 0)} |")
    lines += ["", f"{len(ch)} checks in all. The failures are listed in claims_checks.csv; they are the insurers' own",
              "returns as IRA printed them, kept as printed. The analysis uses the payment ratio, which does not depend on the",
              "movement adding up: it needs only the claims paid, declined, closed and still outstanding in the quarter.", ""]
    open(os.path.join(VAL, "CLAIMS_SUMMARY.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
