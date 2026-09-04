"""The extraction schema, compiled into a shape the extractor can vectorize.

Each datapoint is a list of candidates, tried in order; the first that produces
a value wins. A candidate is written one of four ways:

    "Assets"                             read this tag
    {"tag": "Assets", "multiplier": -1}  read it, then apply modifiers (`Tag`)
    ["Assets", "AssetsNet"]              read the first of these the filing has
    {"sum": ["Assets", "Goodwill"]}      add these together

Anything in a `sum` can itself be written any of the first three ways, so a
total can be built from tags filers disagree about:

    {"sum": [["Assets", "AssetsNet"], "Goodwill"]}

Order matters in a list of alternatives - put the most specific tag first.

Watch the position of a list: alone it picks one tag, inside a `sum` it lists
what to add.

Compiling also answers once which tags the schema can reference - the set the
reader filters the archive down to, ~150 against a median of ~270 us-gaap tags
per company.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Statements measured at an instant rather than over a period. Keyed by `end`
# alone; their values become start/end pairs.
_PIT_STATEMENTS = frozenset({'balance_sheet', 'other'})


@dataclass(frozen=True)
class Tag:
    """One XBRL tag, and what to do with the value found under it."""

    name: str
    multiplier: float = 1.0
    ignore_if_zero: bool = False
    default: Optional[float] = None


@dataclass(frozen=True)
class Sum:
    """Terms added together to produce one candidate value.

    Args:
        terms: what to add. Each is a tuple of `Tag`s tried in order, the
            first one the filing reported winning.
        require_all_terms: fail the sum where a term matched nothing, rather
            than counting it as zero. Keeps a total like `total_liabilities`
            off a row where only one half was found.
    """

    terms: tuple
    require_all_terms: bool = False


@dataclass(frozen=True)
class StatementSchema:
    """Everything needed to build one statement.

    A datapoint is one output column, and maps to the sums that produce it -
    tried in order, first non-null wins.

    Args:
        name: statement name, also the key used against the JSON files.
        mappings: datapoint -> sums read from XBRL tags.
        calculations: datapoint -> sums derived from other columns, in
            dependency order - `total_liabilities` reads a column that
            `total_non_current_liabilities` writes, so order is load-bearing.
        overrides: cik -> datapoint -> sums, with the shared ones already
            appended as a fallback.
    """

    name: str
    mappings: dict
    calculations: dict
    overrides: dict

    @property
    def is_pit(self) -> bool:
        """Whether facts here are measured at an instant, not over a period."""
        return self.name in _PIT_STATEMENTS

    @property
    def key_columns(self) -> list:
        """What identifies a row, before anything derived is added.

        `filed` is deliberate: periods are reported again in later filings,
        sometimes restated, and collapsing those would leave only the newest
        version - the one not knowable at the time. Point-in-time statements
        have no `start`; they are measured at `end`.
        """
        columns = ['cik', 'accn', 'fy', 'fp', 'form', 'start', 'end', 'filed']
        if self.is_pit:
            columns.remove('start')
        return columns

    @property
    def datapoint_names(self) -> list:
        """Output columns, mappings first, in the order the JSON declared."""
        return list(dict.fromkeys([*self.mappings, *self.calculations]))

    @property
    def required_tags(self) -> frozenset:
        """Every XBRL tag any mapping or override could read.

        Calculations are excluded - they read datapoint columns, not tags.
        """
        return frozenset(
            tag.name
            for datapoints in (self.mappings, *self.overrides.values())
            for sums in datapoints.values()
            for sum_ in sums
            for term in sum_.terms
            for tag in term)


def load_schema(schema_dir) -> tuple:
    """Compile the JSON schema files in `schema_dir`, one entry per statement."""
    mappings, calculations, overrides = (
        json.loads((Path(schema_dir) / f'{name}.json').read_text())
        for name in ('base_mappings', 'base_calculations', 'override_mappings'))

    return tuple(
        _compile_statement(name, datapoints,
                           calculations.get(name, {}), overrides.get(name, {}))
        for name, datapoints in mappings.items())


def required_tags(statements: tuple) -> frozenset:
    """Every tag any statement could read, which is what the reader keeps."""
    return frozenset().union(*(s.required_tags for s in statements))


def _compile_statement(
    name: str,
    mappings: dict,
    calculations: dict,
    overrides: dict,
) -> StatementSchema:
    compiled = {dp: _compile_datapoint(entries)
                for dp, entries in mappings.items()}

    return StatementSchema(
        name=name,
        mappings=compiled,
        calculations={dp: _compile_datapoint(entries)
                      for dp, entries in calculations.items()},
        overrides={
            # The shared sums are appended here rather than consulted at
            # extraction time, so an override still falls back to them.
            cik: {dp: _compile_datapoint(entries) + compiled.get(dp, ())
                  for dp, entries in datapoints.items()}
            for cik, datapoints in overrides.items()
        },
    )


def _compile_datapoint(entries: list) -> tuple:
    """One datapoint's JSON entries as sums, tried in the order written."""
    return tuple(_compile_sum(e) for e in entries)


def _compile_sum(spec) -> Sum:
    """One candidate as a sum of terms.

    `{"sum": [...]}` lists what to add; anything else is a sum of one term.
    """
    if isinstance(spec, dict) and 'sum' in spec:
        terms = spec['sum']
        # A bare string here would otherwise compile one Tag per character.
        if not isinstance(terms, list) or not terms:
            raise ValueError(f'"sum" takes a non-empty list of terms: {spec!r}')
        return Sum(
            terms=tuple(_compile_term(t) for t in terms),
            require_all_terms=spec.get('require_all_terms', False),
        )
    return Sum(terms=(_compile_term(spec),))


def _compile_term(spec) -> tuple:
    """The tags one term may read, tried in order. A list gives the choices;
    anything else is a single tag."""
    if isinstance(spec, list):
        return tuple(_compile_tag(t) for t in spec)
    return (_compile_tag(spec),)


def _compile_tag(spec) -> Tag:
    """One tag: a bare name, or a dict naming it under `tag` with modifiers."""
    if isinstance(spec, str):
        spec = {'tag': spec}

    return Tag(
        name=spec['tag'],
        multiplier=float(spec.get('multiplier', 1.0)),
        ignore_if_zero=bool(spec.get('ignore_if_zero', False)),
        default=spec.get('default'),
    )
