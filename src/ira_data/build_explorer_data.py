"""Build the compact JSON behind the data explorer page (explorer/explorer_data.json)."""
import json, os
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "data", "processed")

pan = pd.read_csv(os.path.join(P, "general_revenue_panel.csv"))
cw = pd.read_csv(os.path.join(ROOT, "reference", "company_crosswalk.csv"))
flags = pd.read_csv(os.path.join(ROOT, "validation", "quality_flags.csv"))
bs = pd.read_csv(os.path.join(P, "general_balance_sheets.csv"))
pl = pd.read_csv(os.path.join(P, "general_profit_loss.csv"))
cls = pd.read_csv(os.path.join(P, "general_by_class_panel.csv"))

pan["period"] = pan.year.astype(str) + " Q" + pan.quarter.astype(str)
periods = sorted(pan.period.unique(), key=lambda p: (int(p[:4]), int(p[-1])))
pidx = {p: i for i, p in enumerate(periods)}
LINES = {"gross_direct_premium": "gdp", "inward_reinsurance": "inw", "net_earned_premium": "nep",
         "incurred_claims": "clm", "net_commissions": "com", "management_expenses": "exp",
         "underwriting_result": "uw", "investment_income": "inv", "operating_result": "op"}


def r1(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x) / 1000, 1)  # KSh millions


def series(df, col):
    out = {}
    for line, key in LINES.items():
        arr = [None] * len(periods)
        for _, r in df[df.line == line].iterrows():
            arr[pidx[r.period]] = r1(r[col])
        out[key] = arr
    return out


companies = []
for cid, g in pan.groupby("company_id"):
    names = cw[cw.company_id == cid]
    first = g[["year", "quarter"]].min()
    meta = dict(id=cid, name=names.company_name.iloc[0], segment=g.segment.iloc[0], micro=int(names.is_micro.iloc[0]),
                aliases=sorted(set(g.company_as_published.str.strip())),
                links=[l for l in names.link.fillna("").unique() if l and not l.startswith("spelling")],
                evidence=[e for e in names.evidence.fillna("").unique() if e.startswith("http")])
    ytd = series(g, "ytd_ksh_000"); q = series(g, "quarter_ksh_000")
    basis = [None] * len(periods); rel = [None] * len(periods)
    for _, r in g[g.line == "gross_direct_premium"].iterrows():
        basis[pidx[r.period]] = r.quarter_basis; rel[pidx[r.period]] = bool(r.reliable_quarter)
    meta.update(ytd=ytd, q=q, basis=basis, reliable=rel)
    # balance sheet and profit
    b = bs[bs.company_id == cid].copy(); b["period"] = b.year.astype(str) + " Q" + b.quarter.astype(str)
    ta, te = [None] * len(periods), [None] * len(periods)
    for (per,), gg in b.groupby(["period"]):
        v = gg.drop_duplicates("line_item").set_index("line_item").value_ksh_000
        if per in pidx and v.fillna(0).abs().sum() > 0:
            ta[pidx[per]] = r1(v.get("Total Assets")); te[pidx[per]] = r1(v.get("Total Equity"))
    p_ = pl[pl.company_id == cid].copy(); p_["period"] = p_.year.astype(str) + " Q" + p_.quarter.astype(str)
    pat = [None] * len(periods)
    for (per,), gg in p_.groupby(["period"]):
        v = gg.drop_duplicates("line_item").set_index("line_item").value_ksh_000
        val = v.get("Profit/(Loss) After Taxation", v.get("Profit for the year"))
        if per in pidx and v.fillna(0).abs().sum() > 0:
            pat[pidx[per]] = r1(val)
    meta.update(assets=ta, equity=te, profit=pat)
    # class split, full years only (Q4 year to date)
    c = cls[(cls.company_id == cid) & (cls.quarter == 4) & (cls.table.isin(["gross_premium", "net_earned_premium", "claims_incurred", "underwriting_result"]))]
    cl = {}
    for (yr, t), gg in c.groupby(["year", "table"]):
        cl.setdefault(str(yr), {})[t] = {r.class_of_business: r1(r.ytd_ksh_000) for r in gg.itertuples()}
    meta["classes"] = cl
    f = flags[flags.company_id == cid]
    meta["flags"] = [dict(period=f"{r.year} Q{r.quarter}", flag=r.flag, severity=r.severity, detail=r.detail)
                     for r in f.itertuples() if r.flag != "not_filed"]
    meta["not_filed"] = [f"{r.year} Q{r.quarter}" for r in f.itertuples() if r.flag == "not_filed"]
    companies.append(meta)

# market totals by segment: year to date (all companies) and single quarter (reliable only)
market = {}
for seg in ("insurer", "reinsurer"):
    s = pan[pan.segment == seg]
    ytd = s.groupby(["period", "line"]).ytd_ksh_000.sum().reset_index()
    qq = s[s.reliable_quarter].groupby(["period", "line"]).quarter_ksh_000.sum(min_count=1).reset_index()
    market[seg] = dict(ytd=series(ytd, "ytd_ksh_000"), q=series(qq, "quarter_ksh_000"))

out = dict(data_to=periods[-1], periods=periods, unit="KSh millions",
           companies=companies, market=market)
path = os.path.join(ROOT, "explorer", "explorer_data.json")
json.dump(out, open(path, "w"), separators=(",", ":"))
print("companies", len(companies), "periods", len(periods), "bytes", os.path.getsize(path))

# fill the page template with the data (explorer/kenya-insurer-explorer.html opens in any browser)
tpl = open(os.path.join(ROOT, "explorer", "template.html"), encoding="utf-8").read()
data = open(path, encoding="utf-8").read().replace("</", "<\\/")
page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
        + tpl.replace("__DATA__", data) + "</body></html>")
open(os.path.join(ROOT, "explorer", "kenya-insurer-explorer.html"), "w", encoding="utf-8").write(page)
print("page written")
