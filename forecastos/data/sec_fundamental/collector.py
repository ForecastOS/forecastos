"""Fundamental statements built from SEC's bulk XBRL companyfacts archive."""

from pathlib import Path

import pandas as pd

from ..downloader import FileDownloader
from .extract import extract
from .facts import read_facts
from .normalize import merge_statements, normalize
from .schema import load_schema, required_tags

ARCHIVE_FILENAME = 'companyfacts.zip'

COMPANY_FACTS_URL = 'https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip'

SCHEMA_DIR = Path(__file__).parent / 'schemas'


class SECFundamental:
    @classmethod
    def get_df(
        cls,
        user_agent: str,
        ciks: list = None,
        data_dir: str = None,
        cleanup: bool = True,
    ) -> pd.DataFrame:
        """Fundamental statements, one row per company per period per filing.

        Downloads the 1.4 GB archive, so the whole thing takes a few minutes.
        To go wider, shard `ciks` across separate jobs - every stage shards
        cleanly by company.

        Args:
            user_agent: sent to SEC, which rejects unidentified clients.
                Contact details, e.g. 'Example Corp info@example.com'.
            ciks: any form carrying the digits - 320193, '0000320193' and
                'CIK0000320193' all name Apple. None collects every filer,
                including companies since acquired or delisted, which is what
                you want for anything historical.
            data_dir: where the archive is downloaded. Defaults to ./data,
                resolved against the working directory as of this call.
            cleanup: If True, delete the archive once it has been read. SEC
                rebuilds it nightly, so keeping it only helps across runs on
                the same day.

        Returns:
            One row per company-period-filing: cik, accn, fy, fp, form, start,
            end, period, filed, frame, is_latest, and one column per datapoint.
            Balance sheet figures come as `start_`/`end_` pairs, being instants
            rather than spans.

            `cik` is the padded 10-digit string. `start`, `end` and `filed` are
            datetimes; `period` is the period's length in months. `frame` is
            SEC's calendar label, set only where the period fit a quarter.

            Restatements sit alongside the original. Filter to
            `filed <= your date` for a point-in-time view, or to `is_latest`
            for the newest version of each period.

        Raises:
            ValueError: a named CIK has no member in the archive.
        """
        statements = cls.get_statements(
            user_agent, ciks=ciks, data_dir=data_dir, cleanup=cleanup)
        return merge_statements(statements)

    @classmethod
    def get_statements(
        cls,
        user_agent: str,
        ciks: list = None,
        data_dir: str = None,
        cleanup: bool = True,
    ) -> dict:
        """Each statement on its own, before `get_df` merges them.

        Useful for one statement alone, or to see figures the merge drops - a
        balance sheet whose period has no income statement has nothing to
        attach to.

        Args:
            user_agent, ciks, data_dir, cleanup: as `get_df`.

        Returns:
            Normalized frames keyed by statement name: income_statement,
            cashflow_statement, balance_sheet, other.
        """
        downloader = FileDownloader(
            data_dir or Path.cwd() / 'data', cleanup, {'User-Agent': user_agent})
        schema = load_schema(SCHEMA_DIR)

        with downloader.fetch(COMPANY_FACTS_URL, ARCHIVE_FILENAME) as path:
            print('reading facts')
            facts = read_facts(path, required_tags(schema), ciks=ciks)

        statements = {}
        for statement in schema:
            print(f'building {statement.name}')
            statements[statement.name] = normalize(
                extract(facts, statement), statement)

        return statements
