# AGENTS.md

Garberbucks is a reference site for money in American soccer. Read
[README.md](README.md) for the pipeline and setup.

## Where things live

- Data is not in this repo. Salaries, transfers, valuations, sponsorships, TV
  deals and ownership are files in `../money_data`, parsed by `../parse/parse/`,
  loaded into mongo by `../build`, and copied into postgres by `build/load.py`
  here. A wrong figure is fixed in `money_data`.
- `money/` holds every money model and every view. `bios/`, `teams/` and
  `competitions/` hold only the identity models the money hangs on.
- The site follows the data: league → club → player, with topic pages across
  them. The nav is six sections, MLS (the league hub, also `/`), clubs, pay,
  transfers, value & ownership (valuations, ownership) and revenue
  (sponsorships, TV). A new page joins one of them, marks it with `section`
  in its context, and a page below a club or league sets `crumbs`; it does not
  get a nav link of its own.
- `archive/` is the old site. Leave it alone.

## Rules

- Slugs are the soccerstats.us slugs (`slugify(name)`). Do not invent another
  scheme; the cross-links depend on it.
- Design follows `../s2/DESIGN.md`: tables are the content, numerals are
  tabular, a missing value is a marked gap (`templates/gap.html`), never a
  blank cell, and a column empty for the whole view is left out.
- Money renders in whole dollars through the `dollars` filter.
- Charts are inline SVG drawn by `money/templatetags/charts.py`, and each is
  followed by a table carrying the same numbers. A chart must read fully
  without JavaScript; the one script, `_chart_readout.html`, only names a mark
  under the chart when it is clicked or tapped. Never
  two y-scales on one plot: measures of different size get their own panels,
  and lines sharing a panel differ by dash and marker, not color alone.
- A salary carries a pay period. Only annual figures count toward coverage;
  anything else says its period wherever it is shown.
- `ruff check .` uses the narrow rule set in `ruff.toml`, as the sibling repos
  do. No `ruff format`: the code is hand-wrapped in the s2 style.

## Commands

    .venv/bin/python -m pytest      # tests need a local postgres
    ./build.sh                      # rebuild garberbucks_dev from mongo
    .venv/bin/python manage.py smoketest
