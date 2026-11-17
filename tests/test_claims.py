"""Guards on the claims settlement tables. The tables carry IRA's figures row by row, so they stay out of git;
these tests run where the tables have been built (run_all.sh) and are skipped elsewhere, as on GitHub."""
import os

import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = os.path.join(ROOT, "data", "processed")
V = os.path.join(ROOT, "validation")
pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(P, "claims_panel.csv")),
                                reason="the claims tables are built locally from the raw files and not kept in git")


@pytest.fixture(scope="module")
def raw():
    return pd.read_csv(os.path.join(P, "claims_settlement.csv"))


@pytest.fixture(scope="module")
def panel():
    return pd.read_csv(os.path.join(P, "claims_panel.csv"))


@pytest.fixture(scope="module")
def checks():
    return pd.read_csv(os.path.join(V, "claims_checks.csv"))


def test_every_printed_name_is_in_the_crosswalk(raw):
    cw = pd.read_csv(os.path.join(ROOT, "reference", "claims_crosswalk.csv"))
    side = raw.business.map(lambda b: "long_term" if b == "long_term" else "general")
    names = set(zip(side, raw.company_raw))
    assert names <= set(zip(cw.side, cw.company_raw))
    assert not cw.duplicated(["side", "company_raw"]).any()


def test_one_row_per_company_quarter_business_and_unit(panel):
    assert not panel.duplicated(["period", "business", "unit", "company_id"]).any()


def test_panel_keeps_every_claim_printed(raw, panel):
    for f in ["paid", "closing", "declined", "closed"]:
        a = raw.groupby(["period", "business", "unit"])[f].sum()
        b = panel.groupby(["period", "business", "unit"])[f].sum()
        assert (a - b).abs().max() < 0.01, f


def test_payment_ratio_is_paid_over_open_claims(panel):
    parts = panel[["paid", "declined", "closed", "declined_closed", "closing"]].fillna(0)
    assert (panel.actionable - parts.sum(axis=1)).abs().max() < 1e-6
    x = panel[panel.payment_ratio.notna()]
    assert ((x.paid / x.actionable) - x.payment_ratio).abs().max() < 1e-5
    assert x.payment_ratio.between(0, 1).all()
    # a ratio is missing only where nothing was open or a count was printed negative
    none = panel[panel.payment_ratio.isna()]
    assert ((none.actionable <= 0) | (parts.loc[none.index] < 0).any(axis=1)).all()


def test_printed_totals_match_or_are_explained(checks):
    t = checks[checks.check == "sum_equals_printed_total"]
    assert (t.result != "fail").all()
    assert set(t[t.result == "explained"].period) == {"2017Q1", "2020Q1"}


def test_ira_payment_ratio_is_recomputed(checks):
    r = checks[checks.check == "payment_ratio_as_printed"]
    assert (r.result == "pass").mean() > 0.999


def test_revived_is_read_as_revised_for_eight_quarters(panel):
    n = panel[panel.unit == "number"]
    eight = n.period.isin(["2018Q3", "2018Q4", "2019Q1", "2019Q2", "2019Q3", "2019Q4", "2020Q1", "2020Q2"])
    assert n[eight].revived.isna().all()
    assert n[eight].revised.notna().any()


def test_life_total_in_q1_2020_misses_absa_life(raw):
    # IRA's printed industry line for long-term claims in Q1 2020 is short by exactly Absa Life's row
    t = pd.read_csv(os.path.join(V, "claims_printed_totals.csv"))
    x = raw[(raw.period == "2020Q1") & (raw.business == "long_term") & (raw.unit == "number")]
    tt = t[(t.period == "2020Q1") & (t.business == "long_term") & (t.unit == "number")].iloc[0]
    absa = x[x.company_raw.str.startswith("ABSA")].iloc[0]
    for f in ["opening", "intimated", "paid", "closing"]:
        assert x[f].sum() - tt[f] == pytest.approx(absa[f])
