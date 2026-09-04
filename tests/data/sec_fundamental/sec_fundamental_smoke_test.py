"""Smoke tests for the SEC fundamental collector.

Runs the pipeline end to end over `companyfacts_fixture.zip`: a dozen real
filers, packed the way SEC ships the 1.4 GB archive and trimmed to the years
the tests read. `build_companyfacts_fixture.py` rebuilds it.
"""

import json
import shutil
import zipfile
from pathlib import Path

import pytest
import requests

from forecastos.data.downloader import TIMEOUT_SEC
from forecastos.data.sec_fundamental import SECFundamental
from forecastos.data.sec_fundamental.collector import (
    ARCHIVE_FILENAME,
    COMPANY_FACTS_URL,
    SCHEMA_DIR,
)
from forecastos.data.sec_fundamental.facts import read_facts
from forecastos.data.sec_fundamental.schema import load_schema, required_tags

COMPANYFACTS_FIXTURE = Path(__file__).parent / 'companyfacts_fixture.zip'

USER_AGENT = 'forecastos smoke-test@example.com'

# The universe, read off the fixture rather than restated here.
with zipfile.ZipFile(COMPANYFACTS_FIXTURE) as _archive:
    CIKS = {name[3:-5] for name in _archive.namelist()
            if name.endswith('.json')}


@pytest.fixture(scope='module')
def data_dir(tmp_path_factory):
    """The fixture, named so the downloader finds it already there and skips
    the 1.4 GB download."""
    path = tmp_path_factory.mktemp('sec')
    shutil.copy(COMPANYFACTS_FIXTURE, path / ARCHIVE_FILENAME)
    return str(path)


@pytest.fixture(scope='module')
def collected(data_dir):
    return SECFundamental.get_df(USER_AGENT, data_dir=data_dir)


def test_sec_company_facts_zip_still_exists():
    resp = requests.head(
        COMPANY_FACTS_URL,
        headers={'User-Agent': USER_AGENT},
        timeout=TIMEOUT_SEC,
        allow_redirects=True,
    )
    resp.raise_for_status()

    assert resp.headers['content-type'] == 'application/zip'
    # an error page served as a 200 would get past `raise_for_status`
    assert int(resp.headers['content-length']) > 1_000_000_000


def test_schema_compiles():
    schema = load_schema(SCHEMA_DIR)
    by_name = {s.name: s for s in schema}

    assert set(by_name) == {'income_statement', 'cashflow_statement',
                            'balance_sheet', 'other'}
    assert 'revenue' in by_name['income_statement'].datapoint_names
    # calculation-only fallbacks are still output columns
    assert 'gross_revenue' in by_name['income_statement'].datapoint_names

    # balance sheets are instants, so they carry no `start`
    assert by_name['balance_sheet'].is_pit
    assert 'start' not in by_name['balance_sheet'].key_columns

    assert len(required_tags(schema)) > 100


def test_read_facts_keeps_only_annual_and_quarterly_reports(tmp_path):
    """Written out rather than taken from the fixture, which cannot cover this:
    no operating company files an N-CSR, the fund form the filter is really for.
    """
    facts = [{'form': form, 'end': '2024-12-31', 'val': 1, 'accn': 'a',
              'fy': 2024, 'fp': 'FY', 'filed': '2025-01-01'}
             for form in ('10-K', '10-Q', '10-K/A', '8-K', 'N-CSR', '10-D')]

    path = tmp_path / 'facts.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('CIK0000000001.json', json.dumps(
            {'cik': 1, 'entityName': 'Test',
             'facts': {'us-gaap': {'Assets': {'units': {'USD': facts}}}}}))

    kept = read_facts(path, frozenset({'Assets'}), ciks=[1])
    assert set(kept['form']) == {'10-K', '10-Q'}


def test_get_df_output(collected):
    assert set(collected['cik']) == CIKS

    for column in ('accn', 'fy', 'fp', 'form', 'start', 'end',
                   'period', 'filed', 'frame', 'is_latest'):
        assert column in collected.columns

    # quarters or years, nothing in between
    assert collected['period'].dropna().isin([3.0, 12.0]).all()

    latest = collected[collected['is_latest']]
    assert latest['revenue'].dropna().gt(0).all()
    assert latest['end_total_assets'].dropna().gt(0).all()
    assert 'start_total_assets' in latest.columns

    # every filer reports the headline figures somewhere
    for column in ('revenue', 'net_income', 'operating_cf', 'end_total_assets'):
        assert latest.groupby('cik')[column].count().gt(0).all(), column


def test_get_df_implies_quarterly_cash_flow(collected):
    """Cash flow is filed year to date, so Q2 and Q3 have the quarter implied.
    Unrepaired they are six and nine months long, and the period filter drops
    them."""
    latest = collected[collected['is_latest']]

    for fp in ('Q1', 'Q2', 'Q3'):
        rows = latest[latest['fp'].eq(fp)]
        assert set(rows['cik']) == CIKS, fp
        assert rows.groupby('cik')['operating_cf'].count().gt(0).all(), fp


def test_get_df_implies_a_fourth_quarter(collected):
    """No filing reports Q4 on its own - it is the year less three quarters."""
    fourth = collected[collected['fp'].eq('Q4')]

    assert set(fourth['cik']) == CIKS
    assert fourth['period'].eq(3.0).all()
    # derived rows carry no SEC calendar label
    assert fourth['frame'].isna().all()


def test_get_df_keeps_every_filing_of_a_period(collected):
    """Restatements sit alongside the original rather than replacing it."""
    per_period = collected.groupby(
        ['cik', 'fp', 'start', 'end'], dropna=False)['filed'].nunique()
    assert per_period.max() > 1

    # exactly one row per period is the most recent
    flagged = collected.groupby(
        ['cik', 'start', 'end', 'period'], dropna=False)['is_latest'].sum()
    assert flagged.eq(1).all()
