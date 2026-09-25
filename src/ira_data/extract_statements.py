"""Extract general insurance balance sheets and profit and loss accounts from the quarterly workbooks.

Balance sheets: IRA prints them transposed, line items down the rows and companies across the columns,
split over four sheets (i to iv). Profit and loss: companies down the rows, line items across.

IRA moved these statements from IFRS 4 to IFRS 17 line items partway through the series, so line
items are kept exactly as printed (cleaned of spacing only), with their order, and each row carries
reporting_basis = IFRS 4 or IFRS 17. A mapping between the two bases is a separate, later step.

Outputs (KSh thousands, IRA states "Amounts in thousand Shillings" on these sheets):
  data/processed/general_balance_sheets.csv   position at the quarter end
  data/processed/general_profit_loss.csv      year to date
"""
import glob, os, re, warnings
import openpyxl
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw", "quarterly")
OUT = os.path.join(ROOT, "data", "processed")
WB_DIR = os.environ.get("IRA_WB_DIR")


LABEL_FIX = {"Share Captial": "Share Capital", "Revaluation Reserve": "Revaluation Reserves",
             "Investment In Related Companies": "Investment in Related Companies",
             "Ordinary Shares UnQuoted": "Ordinary Shares Unquoted",
             "Investment In Unit Trusts": "Investment in Unit Trusts", "Investment in Unit Trust": "Investment in Unit Trusts",
             "Deferred tax liability": "Deferred Tax Liability",
             "Expenses from reinsurance contracts held": "Expenses from reinsurance contracts held"}


def norm(s):
    s = re.sub(r"\s+", " ", str(s).replace("_x000D_", " ")).strip()
    s = s.replace("Liabilites", "Liabilities").replace("Securites", "Securities")
    return LABEL_FIX.get(s, s)


def title(ws):
    for row in ws.iter_rows(min_row=1, max_row=6, values_only=True):
        for c in row[:4]:
            if isinstance(c, str) and "SUMMARY" in c.upper():
                return c.upper()
    return ""


def num(v):
    if v in (None, "", "-"):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def balance_sheet(ws):
    rows = list(ws.iter_rows(values_only=True))
    h = next(i for i, r in enumerate(rows) if any(isinstance(c, str) and c.strip().upper() == "COMPANY" for c in r))
    lab = next(j for j, c in enumerate(rows[h]) if isinstance(c, str) and c.strip().upper() == "COMPANY")
    comps = [(j, norm(c)) for j, c in enumerate(rows[h]) if j > lab and isinstance(c, str) and c.strip()]
    out, order = [], 0
    for r in rows[h + 1:]:
        l = r[lab] if lab < len(r) else None
        if not isinstance(l, str) or not l.strip():
            continue
        l = norm(l)
        if l.lower().startswith(("amounts in", "continued", "appendix", "*")):
            continue
        order += 1
        for j, co in comps:
            if co.upper().startswith(("TOTAL", "GRAND", "INSURERS", "REINSURERS")):
                continue  # market total columns
            v = num(r[j]) if j < len(r) else None
            out.append((co, order, l, v))
    return out


def profit_loss(ws):
    rows = list(ws.iter_rows(values_only=True))
    h = next(i for i, r in enumerate(rows) if any(isinstance(c, str) and c.strip() == "Company" for c in r))
    ci = next(j for j, c in enumerate(rows[h]) if isinstance(c, str) and c.strip() == "Company")
    cols = [(j, norm(c)) for j, c in enumerate(rows[h]) if j > ci and isinstance(c, str) and c.strip()]
    seg, out, totals = "insurer", [], []
    for r in rows[h + 1:]:
        n = r[ci] if ci < len(r) else None
        if not isinstance(n, str) or not n.strip():
            continue
        n = norm(n); u = n.upper()
        if u in ("INSURERS", "INSURER"):
            seg = "insurer"; continue
        if u.startswith("REINSURER"):
            seg = "reinsurer"; continue
        if u.startswith("MICROINSURER") or u.startswith("MICRO INSURER"):
            seg = "micro"; continue
        if u.startswith("AMOUNTS IN") or n.startswith("*"):
            continue
        tgt = totals if (u.startswith("TOTAL") or u.startswith("GRAND")) else out
        for k, (j, lab) in enumerate(cols):
            tgt.append((seg, n, k + 1, lab, num(r[j]) if j < len(r) else None))
    return out, totals


def main():
    files = sorted(glob.glob(os.path.join(RAW, "*", "IRA_*_Q*_Industry_Statistics.xlsx")))
    bs_rows, pl_rows, pl_tot = [], [], []
    for path in files:
        m = re.search(r"IRA_(\d{4})_Q(\d)_", path); y, q = int(m.group(1)), int(m.group(2))
        src = os.path.relpath(path, ROOT).replace(os.sep, "/")
        wb = openpyxl.load_workbook(os.path.join(WB_DIR, os.path.basename(path)) if WB_DIR else path,
                                    read_only=True, data_only=True)
        for s in wb.sheetnames:
            if re.search(r"micro|_m$", s, re.I):
                continue
            t = title(wb[s])
            if "GENERAL INSURANCE BUSINESS BALANCE SHEET" in t:
                for co, order, lab, v in balance_sheet(wb[s]):
                    bs_rows.append(dict(year=y, quarter=q, source_file=src, source_sheet=s.strip(),
                                        company=co, line_order=order, line_item=lab, value_ksh_000=v))
            elif "GENERAL INSURANCE BUSINESS PROFIT" in t:
                data, tots = profit_loss(wb[s])
                for seg, co, order, lab, v in data:
                    pl_rows.append(dict(year=y, quarter=q, source_file=src, source_sheet=s.strip(), segment=seg,
                                        company=co, line_order=order, line_item=lab, value_ksh_000=v))
                for seg, co, order, lab, v in tots:
                    pl_tot.append(dict(year=y, quarter=q, segment=seg, label=co, line_item=lab, value=v))
    bs, pl = pd.DataFrame(bs_rows), pd.DataFrame(pl_rows)
    # IRA sometimes prints the same company twice across the four balance sheet pages (Star Discover,
    # Q3 2024, on both iii and iv with identical figures). Keep the first copy.
    n0 = len(bs)
    bs = bs.drop_duplicates(["year", "quarter", "company", "line_order", "line_item", "value_ksh_000"])
    print("duplicate balance sheet rows dropped:", n0 - len(bs))
    # reporting basis, decided per period from the line items IRA used
    b17 = set(pl.loc[pl.line_item.str.startswith("Insurance Revenue"), "year"].astype(str) + "Q" +
              pl.loc[pl.line_item.str.startswith("Insurance Revenue"), "quarter"].astype(str))
    for d in (bs, pl):
        d["reporting_basis"] = (d.year.astype(str) + "Q" + d.quarter.astype(str)).map(lambda p: "IFRS 17" if p in b17 else "IFRS 4")
    cw = pd.read_csv(os.path.join(ROOT, "reference", "company_crosswalk.csv"))[["company_raw", "company_id"]]
    for name in ("bs", "pl"):
        d = locals()[name]
        d["company"] = d["company"].str.strip()
        d = d.merge(cw, left_on="company", right_on="company_raw", how="left").drop(columns="company_raw")
        if d.company_id.isna().any():
            raise SystemExit(f"unmapped names: {sorted(d.loc[d.company_id.isna(), 'company'].unique())}")
        if name == "bs":
            bs = d
        else:
            pl = d
    bs.to_csv(os.path.join(OUT, "general_balance_sheets.csv"), index=False, lineterminator="\n")
    pl.to_csv(os.path.join(OUT, "general_profit_loss.csv"), index=False, lineterminator="\n")
    pd.DataFrame(pl_tot).to_csv(os.path.join(ROOT, "validation", "published_totals_profit_loss.csv"), index=False, lineterminator="\n")
    print("balance sheet rows", len(bs), "periods", bs[["year", "quarter"]].drop_duplicates().shape[0])
    print("profit and loss rows", len(pl), "periods", pl[["year", "quarter"]].drop_duplicates().shape[0])
    print("IFRS 17 periods:", sorted(b17))


if __name__ == "__main__":
    main()
