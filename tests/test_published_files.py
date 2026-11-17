"""Guards on what this repository publishes: the reference files, and that no data table is tracked.

These run everywhere, including on GitHub Actions, where the processed tables are not present.
"""
import os
import re
import subprocess

import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# raw IRA files, the tables built from them, and the full check lists: none of these may be tracked
NOT_PUBLISHED = re.compile(r"^(data/processed/|data/raw/(?!manifest\.csv$|SOURCES\.md$)|explorer/explorer_data\.json$|"
                           r"validation/(published_totals.*|validation_report|transfer_from_revenue|claims_checks|claims_printed_totals)\.csv$)")


def tracked():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return out.splitlines()


def test_no_data_table_is_tracked():
    bad = [f for f in tracked() if NOT_PUBLISHED.match(f)]
    assert not bad, f"data must not be published: {bad}"


def test_every_raw_file_is_listed_with_its_source_and_hash():
    m = pd.read_csv(os.path.join(ROOT, "data", "raw", "manifest.csv"))
    ok = m[m.status == "ok"]
    assert len(ok) > 0
    assert ok.sha256.str.fullmatch(r"[0-9a-f]{64}").all()
    assert ok.download_url.str.startswith("http").all()


def test_crosswalk_and_quality_flags_agree():
    cw = pd.read_csv(os.path.join(ROOT, "reference", "company_crosswalk.csv"))
    assert cw.company_raw.is_unique and cw.company_id.notna().all()
    assert set(cw.segment) <= {"insurer", "reinsurer"}
    qf = pd.read_csv(os.path.join(ROOT, "validation", "quality_flags.csv"))
    assert set(qf.company_id) <= set(cw.company_id)
    assert set(qf.severity) <= {"error", "warning", "info"}
