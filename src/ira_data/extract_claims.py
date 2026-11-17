"""Extract IRA's quarterly claims settlement statistics.

Reads every data/raw/claims_settlement/YYYY/IRA_YYYY_QN_Claims_Statistics.xlsx and writes

  data/processed/claims_settlement.csv   one row per quarter, business, unit and insurer, as printed
  validation/claims_printed_totals.csv   the "Industry" row of every table, kept for validation

Three businesses are read: general insurance liability claims (third-party injury and damage, most of
them motor), general insurance non-liability claims (own damage, medical, property and the rest) and
long-term insurance claims (life, pensions and funeral). Microinsurers are reported separately from
Q2 2025 and are not read. Counts are claims; amounts are KSh thousands and are printed from Q4 2022.

Each row is a quarter's movement: claims outstanding at the start, plus claims intimated (reported) and
revived, less claims paid, declined and closed as no claim, gives claims outstanding at the end.
"Revised" claims are existing claims whose reserve changed; they add nothing to the count. In 2017 IRA
printed declined and closed claims as one figure, kept here as declined_closed.

Figures are as IRA prints them: unaudited monthly returns, summed to the quarter.
"""
import csv, glob, os, re, warnings
import openpyxl

warnings.filterwarnings("ignore")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw", "claims_settlement")
OUT = os.path.join(ROOT, "data", "processed", "claims_settlement.csv")
TOTALS = os.path.join(ROOT, "validation", "claims_printed_totals.csv")

FIELDS = ["opening", "intimated", "revived", "revised", "paid", "declined", "closed", "declined_closed", "closing"]
# header text -> field, tried in order (the first match wins)
HEADERS = [
    (r"name of", "name"),
    (r"outstanding at the beginning", "opening"),
    (r"intimated and revived", "intimated"),
    (r"intimated", "intimated"),
    (r"revived", "revived"),
    (r"revised", "revised"),
    (r"total claims", None),            # "Total claims payable" and "Total claims action" in three 2018 tables
    (r"claims paid", "paid"),
    (r"rejected and closed", "declined_closed"),
    (r"(declined|rejected) during", "declined"),
    (r"closed as no claims? during", "closed"),
    (r"outstanding at the end", "closing"),
    (r"(settlement|payment) ratio", "printed_ratio"),
]


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def classify(title):
    """(business, unit) for a quarterly table, or None for the monthly, declined and reasons tables."""
    t = norm(title).lower()
    if re.search(r"monthly|declined claims|reasons|micro", t):
        return None
    if "long-term" in t or "long term" in t:
        business = "long_term"
    elif re.search(r"non[\s-]*liability", t):
        business = "general_non_liability"
    elif "liability" in t:
        business = "general_liability"
    else:
        return None
    unit = "amount" if "(amount)" in t or "amount)" in t else "number"
    return business, unit


def title_of(rows):
    for r in rows[:6]:
        for v in r:
            if isinstance(v, str) and re.match(r"\s*(appendix \d+\s*:|analysis of)", v, re.I):
                return norm(v)
    return None


def columns(header):
    cols = {}
    for j, v in enumerate(header):
        if v is None:
            continue
        h = norm(v).lower()
        for pat, field in HEADERS:
            if re.search(pat, h):
                if field and field not in cols:
                    cols[field] = j
                break
    return cols


def num(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    if s in ("-", "--"):
        return 0.0
    if s.upper() in ("N/A", "NA", "#DIV/0!", "#VALUE!", "#REF!"):
        return None
    return float(s)


def read(path):
    year, q = map(int, re.search(r"IRA_(\d{4})_Q(\d)", path).groups())
    period = f"{year}Q{q}"
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    out, totals, seen = [], [], set()
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        title = title_of(rows)
        kind = classify(title) if title else None
        if not kind or kind in seen:   # a table printed twice in one workbook is read once
            continue
        h = next((i for i, r in enumerate(rows) if any(isinstance(v, str) and re.match(r"\s*name of", v, re.I) for v in r)), None)
        if h is None:
            continue
        cols = columns(rows[h])
        need = {"name", "opening", "paid", "closing"}
        assert need <= set(cols), f"{path} {ws.title}: columns {cols}"
        seen.add(kind)
        for r in rows[h + 1:]:
            name = r[cols["name"]] if cols["name"] < len(r) else None
            if not isinstance(name, str) or not name.strip():
                continue
            vals = {f: num(r[j]) if j < len(r) else None for f, j in cols.items() if f != "name"}
            if all(vals.get(f) is None for f in ("opening", "paid", "closing")):
                continue
            rec = {"period": period, "year": year, "quarter": q, "business": kind[0], "unit": kind[1],
                   "company_raw": norm(name), "sheet": ws.title.strip()}
            rec.update({f: vals.get(f) for f in FIELDS})
            rec["printed_ratio"] = vals.get("printed_ratio")
            if re.fullmatch(r"(industry|total|industry total|grand total)", norm(name).lower()):
                totals.append(rec)
                break   # the rows after the industry line are the previous quarter and a summary
            out.append(rec)
    return out, totals


def fmt(v):
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else repr(round(v, 6))


def main():
    files = sorted(glob.glob(os.path.join(RAW, "*", "IRA_*_Claims_Statistics.xlsx")))
    rows, totals = [], []
    for f in files:
        r, t = read(f)
        rows += r
        totals += t
    cols = ["period", "year", "quarter", "business", "unit", "company_raw", "sheet"] + FIELDS + ["printed_ratio"]
    for path, data in ((OUT, rows), (TOTALS, totals)):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(cols)
            for rec in data:
                w.writerow([fmt(rec[c]) if c in FIELDS or c == "printed_ratio" else rec[c] for c in cols])
    print(f"{len(files)} workbooks, {len(rows)} rows, {len(totals)} printed totals")


if __name__ == "__main__":
    main()
