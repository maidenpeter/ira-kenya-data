"""Extract general insurance tables from IRA quarterly statistics workbooks.

Reads every data/raw/quarterly/YYYY/IRA_YYYY_QN_Industry_Statistics.xlsx and writes two
long-format tables to data/processed/:

  general_revenue_accounts.csv   one row per period, company and revenue account line
  general_by_class.csv           one row per period, company, table and class of business

Figures are as IRA publishes them: KSh thousands, year to date, unaudited.
Company TOTAL rows are kept aside for validation and not written to the outputs.
"""
import csv, glob, hashlib, os, re, sys, warnings
import openpyxl

warnings.filterwarnings("ignore")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw", "quarterly")
OUT = os.path.join(ROOT, "data", "processed")
WB_DIR = os.environ.get("IRA_WB_DIR")  # optional local cache of the same files, for speed

REV_COLS = ["gross_direct_premium", "inward_reinsurance", "outward_reinsurance", "net_premium_written",
            "upr_bf", "urr_bf", "upr_cf", "urr_cf", "net_earned_premium", "incurred_claims",
            "net_commissions", "management_expenses", "underwriting_result", "investment_income",
            "operating_result"]
CLASSES = {"aviation": "Aviation", "engineering": "Engineering", "fire domestic": "Fire Domestic",
           "fire industrial": "Fire Industrial", "liability": "Liability", "marine": "Marine",
           "motor private": "Motor Private", "motor commercial": "Motor Commercial",
           "motor commercial psv": "Motor Commercial PSV", "personal accident": "Personal Accident",
           "theft": "Theft", "workmens' compensation": "Workmen's Compensation", "medical": "Medical",
           "miscellaneous": "Miscellaneous", "total": "Total"}
# table key -> (how to find the sheet, output name)
TITLE_TABLES = {
    "REV": r"GENERAL INSURANCE BUSINESS REVENUE ACCOUNT",
    "gross_premium": r"GROSS\s+PREMIUM INCOME UNDER GENERAL",
    "claims_paid": r"CLAIMS PAID UNDER GENERAL",
    "claims_incurred": r"CLAIMS INCURRED UNDER GENERAL",
    "underwriting_result": r"UNDERWRITING PROFITS? UNDER GENERAL",
}
NAME_TABLES = {"NPI": "net_premium", "NEPI": "net_earned_premium", "COM": "commissions",
               "MGT": "management_expenses", "INWARD": "inward_premium",
               "UWPROFIT": "underwriting_result", "UW PROFITS": "underwriting_result",
               "GDP": "gross_direct_premium",
               # Q2 2025 carries its by-class underwriting table on an untitled sheet
               "APPENDIX 20_": "underwriting_result"}


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("_x000D_", " ")).strip()


def is_micro(sheet):
    return bool(re.search(r"micro|_m$|\d+m$", sheet, re.I))


def sheet_title(ws):
    for row in ws.iter_rows(min_row=1, max_row=6, values_only=True):
        for c in row[:6]:
            if isinstance(c, str) and ("SUMMARY" in c.upper() or "APPENDIX" in c.upper()):
                return norm(c)
    return ""


def find_sheets(wb):
    found = {}
    for s in wb.sheetnames:
        if is_micro(s):
            continue
        key = s.strip().upper()
        if key in NAME_TABLES:
            found.setdefault(NAME_TABLES[key], s)
            continue
        t = sheet_title(wb[s]).upper()
        for k, pat in TITLE_TABLES.items():
            if re.search(pat, t) and k not in found:
                found[k] = s
    return found


def read_table(ws):
    """Return header list and data rows as (segment, company, [values]) plus total rows."""
    rows = list(ws.iter_rows(values_only=True))
    h = next(i for i, r in enumerate(rows) if any(isinstance(c, str) and c.strip() == "Company" for c in r))
    ci = next(j for j, c in enumerate(rows[h]) if isinstance(c, str) and c.strip() == "Company")
    header = [norm(c) if c is not None else None for c in rows[h][ci + 1:]]
    seg, data, totals = "insurer", [], []
    for r in rows[h + 1:]:
        name = r[ci] if ci < len(r) else None
        if not isinstance(name, str) or not name.strip():
            continue
        n = norm(name)
        u = n.upper()
        vals = list(r[ci + 1: ci + 1 + len(header)])
        if u in ("INSURERS", "INSURER"):
            seg = "insurer"; continue
        if u.startswith("REINSURER"):
            seg = "reinsurer"; continue
        if u.startswith("TOTAL") or u.startswith("MARKET TOTAL") or u.startswith("INDUSTRY"):
            totals.append((seg, u, vals)); continue
        if all(v in (None, "") for v in vals):
            continue
        data.append((seg, n, vals))
    return header, data, totals


def num(v):
    if v in (None, "", "-"):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    files = sorted(glob.glob(os.path.join(RAW, "*", "IRA_*_Q*_Industry_Statistics.xlsx")))
    os.makedirs(OUT, exist_ok=True)
    rev_out, cls_out, tot_out, log = [], [], [], []
    for path in files:
        m = re.search(r"IRA_(\d{4})_Q(\d)_", path)
        year, q = int(m.group(1)), int(m.group(2))
        src = os.path.relpath(path, ROOT).replace(os.sep, "/")
        read_path = os.path.join(WB_DIR, os.path.basename(path)) if WB_DIR else path
        digest = sha256(read_path)[:12]
        wb = openpyxl.load_workbook(read_path, read_only=True, data_only=True)
        sheets = find_sheets(wb)
        log.append((year, q, sorted(sheets.items())))
        for key, sname in sheets.items():
            header, data, totals = read_table(wb[sname])
            base = dict(year=year, quarter=q, period_end=f"{year}-{[3,6,9,12][q-1]:02d}-{[31,30,30,31][q-1]}",
                        source_file=src, source_sha256_12=digest, source_sheet=sname.strip())
            if key == "REV":
                if len(header) < 15:
                    sys.exit(f"{src}: revenue account has {len(header)} columns")
                for seg, co, vals in data:
                    for col, v in zip(REV_COLS, vals[:15]):
                        rev_out.append(dict(base, segment=seg, company=co, line=col, value_ksh_000=num(v)))
                for seg, lab, vals in totals:
                    for col, v in zip(REV_COLS, vals[:15]):
                        tot_out.append(dict(base, table="revenue_account", segment=seg, label=lab, column=col, value=num(v)))
            else:
                cols = []
                for c in header:
                    k = (c or "").lower().strip()
                    cols.append(CLASSES.get(k))
                for seg, co, vals in data:
                    for cls, v in zip(cols, vals):
                        if cls:
                            cls_out.append(dict(base, table=key, segment=seg, company=co, class_of_business=cls, value_ksh_000=num(v)))
                for seg, lab, vals in totals:
                    for cls, v in zip(cols, vals):
                        if cls:
                            tot_out.append(dict(base, table=key, segment=seg, label=lab, column=cls, value=num(v)))
    def write(name, rows):
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader(); w.writerows(rows)
    write("general_revenue_accounts.csv", rev_out)
    write("general_by_class.csv", cls_out)
    os.makedirs(os.path.join(ROOT, "validation"), exist_ok=True)
    with open(os.path.join(ROOT, "validation", "published_totals.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tot_out[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(tot_out)
    for y, q, s in log:
        print(y, f"Q{q}", ", ".join(f"{k}={v.strip()}" for k, v in s))
    print(f"files {len(files)}  revenue rows {len(rev_out)}  class rows {len(cls_out)}  total rows {len(tot_out)}")


if __name__ == "__main__":
    main()
