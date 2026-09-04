"""Rebuild `companyfacts_fixture.zip`, the archive the SEC smoke tests run over.

Members carry only the tags and years the tests read, but are nested and named
the way SEC ships the real archive, so the tests run the same `read_facts` code
production does.

    python build_companyfacts_fixture.py 'Name you@example.com'

The User-Agent is required - SEC 403s a client it cannot identify.
"""

import json
import sys
import time
import zipfile
from pathlib import Path

import requests

from forecastos.data.downloader import TIMEOUT_SEC
from forecastos.data.sec_fundamental.collector import SCHEMA_DIR
from forecastos.data.sec_fundamental.schema import load_schema, required_tags

OUT_PATH = Path(__file__).parent / 'companyfacts_fixture.zip'

# One company per call, unlike the bulk zip `collector.COMPANY_FACTS_URL`.
COMPANY_FACTS_API_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'

# The test universe. Keyed by CIK, since a ticker can move to another filer.
CIKS = {
    '0000320193': 'AAPL',
    '0001045810': 'NVDA',
    '0001652044': 'GOOG',
    '0000789019': 'MSFT',
    '0001018724': 'AMZN',
    '0001730168': 'AVGO',
    '0001318605': 'TSLA',
    '0000059478': 'LLY',
    '0000034088': 'XOM',
    '0000019617': 'JPM',
    '0000104169': 'WMT',
    '0001403161': 'V',
}

# 2024 is the floor: any tighter and some filers lose a full year, and with it
# their derived Q4.
FIRST_YEAR = 2023

WANTED_FORMS = frozenset({'10-K', '10-Q'})

# SEC asks for no more than 10 requests a second.
REQUEST_INTERVAL_SEC = 0.15


def trim(company: dict, tags: frozenset) -> dict:
    """One company cut to what the tests read: the schema's tags over recent
    periods, without SEC's labels and descriptions."""
    facts = {}
    for taxonomy, taxonomy_tags in company.get('facts', {}).items():
        for tag, body in taxonomy_tags.items():
            if tag not in tags:
                continue

            units = {}
            for unit, unit_facts in body.get('units', {}).items():
                kept = [f for f in unit_facts
                        if f.get('form') in WANTED_FORMS
                        and f.get('end', '') >= f'{FIRST_YEAR}-01-01']
                if kept:
                    units[unit] = kept

            if units:
                facts.setdefault(taxonomy, {})[tag] = {'units': units}

    return {'cik': company['cik'], 'entityName': company['entityName'],
            'facts': facts}


def main(user_agent: str) -> None:
    tags = required_tags(load_schema(SCHEMA_DIR))

    with zipfile.ZipFile(OUT_PATH, 'w', zipfile.ZIP_DEFLATED) as archive:
        for cik, ticker in CIKS.items():
            resp = requests.get(COMPANY_FACTS_API_URL.format(cik=cik),
                                headers={'User-Agent': user_agent},
                                timeout=TIMEOUT_SEC)
            resp.raise_for_status()
            time.sleep(REQUEST_INTERVAL_SEC)

            member = json.dumps(trim(resp.json(), tags), separators=(',', ':'))
            archive.writestr(f'CIK{cik}.json', member)
            print(f'  {ticker:<5} CIK{cik}  {len(member) / 1024:5.0f} KB')

    print(f'\n{OUT_PATH.name}: {len(CIKS)} companies, '
          f'{OUT_PATH.stat().st_size / 1024:.0f} KB')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(f'usage: {sys.argv[0]} \'<name> <you@example.com>\'')
    main(sys.argv[1])
