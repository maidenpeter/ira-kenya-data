"""Guards on the processed tables. They run on the committed CSVs, so no raw files are needed.

Each test protects a result the README relies on. If a change to the extraction breaks one of them,
the numbers downstream (explorer, scorecard) would be wrong without looking wrong.
"""
import os

import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = os.path.join(ROOT, "data", "processed")
V = os.path.join(ROOT, "validation")


def ok(a, b):
    return (a - b).abs() <= pd.concat([a.abs(), b.abs()], axis=1).max(axis=1).mul(0.001).clip(lower=5.0)


@pytest.fixture(scope="module")
def panel():
    return pd.read_csv(os.path.join(P, "general_revenue_panel.csv"))


@pytest.fixture(scope="module")
def wide(panel):
    w = panel.pivot_table(index=["company_id", "year", "quarter"], columns="line", values="ytd_ksh_000", aggfunc="first")
    return w[w.abs().sum(axis=1) > 0].fillna(0)


def test_revenue_account_identities(wide):
    w = wide
    assert ok(w.gross_direct_premium + w.inward_reinsurance - w.outward_reinsurance, w.net_premium_written).all()
    assert ok(w.net_premium_written + w.upr_bf + w.urr_bf - w.upr_cf - w.urr_cf, w.net_earned_premium).all()
    assert ok(w.net_earned_premium - w.incurred_claims - w.net_commissions - w.management_expenses,
              w.underwriting_result).all()
    assert ok(w.underwriting_result + w.investment_income, w.operating_result).all()


def test_single_quarters_rebuild_the_year(panel):
    # where all four quarters of a year were derived, they must add back to the Q4 year-to-date figure
    d = panel.dropna(subset=["quarter_ksh_000"])
    full = d.groupby(["company_id", "year", "line"]).filter(lambda g: set(g.quarter) == {1, 2, 3, 4})
    s = full.groupby(["company_id", "year", "line"]).quarter_ksh_000.sum()
    q4 = full[full.quarter == 4].set_index(["company_id", "year", "line"]).ytd_ksh_000
    assert len(s) > 1000
    assert ok(s, q4.reindex(s.index)).all()


def test_every_company_is_mapped():
    cw = pd.read_csv(os.path.join(ROOT, "reference", "company_crosswalk.csv"))
    assert cw.company_raw.is_unique
    assert cw.company_id.notna().all()
    for f in ["general_revenue_panel.csv", "general_balance_sheets.csv"]:
        ids = pd.read_csv(os.path.join(P, f), usecols=["company_id"]).company_id
        assert ids.notna().all(), f
        assert set(ids) <= set(cw.company_id), f


def test_balance_sheets_balance():
    b = pd.read_csv(os.path.join(P, "general_balance_sheets.csv"))
    w = b.pivot_table(index=["company_id", "year", "quarter"], columns="line_item", values="value_ksh_000", aggfunc="first")
    w = w[w["Total Assets"].fillna(0) != 0]
    assert len(w) > 1300
    assert ok(w["Total Assets"], w["Total Equity And Liabilities"]).all()


def test_known_bad_returns_are_kept_out_of_market_quarters(panel):
    # Intra-Africa's Q3 2024 premium that vanished by Q4, and the two merger quarters
    def reliable(cid, y, q):
        g = panel[(panel.company_id == cid) & (panel.year == y) & (panel.quarter == q) & (panel.line == "gross_direct_premium")]
        return g.reliable_quarter.tolist()
    assert reliable("intra_africa", 2024, 3) == [False]
    assert reliable("mua", 2021, 3) == [False]
    assert reliable("sanlam_allianz_general", 2025, 4) == [False]
    assert reliable("aar", 2024, 3) == [True]


def test_pdf_release_crosscheck_agrees():
    x = pd.read_csv(os.path.join(V, "crosscheck_pdf_releases.csv"))
    assert len(x) == 12
    assert (x.difference == 0).all()


def test_no_unexplained_validation_failures():
    r = pd.read_csv(os.path.join(V, "validation_report.csv"))
    failed = r[~r.passed.astype(bool)]
    assert failed.known_issue.notna().all()
