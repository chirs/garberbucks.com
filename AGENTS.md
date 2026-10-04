# AGENTS.md

Garberbucks is a reference site for money in American soccer. Read
[README.md](README.md) for the pipeline and setup.

## Where things live

- Data is not in this repo. Salary files are in `../money_data`, parsed by
  `../parse/parse/salaries.py`, loaded into mongo by `../build`, and copied into
  postgres by `build/load.py` here. A wrong figure is fixed in `money_data`.
- `money/` holds the salary model and every view. `bios/`, `teams/` and
  `competitions/` hold only the identity models the money hangs on.
- `archive/` is the old site. Leave it alone.

## Rules

- Slugs are the soccerstats.us slugs (`slugify(name)`). Do not invent another
  scheme; the cross-links depend on it.
- Design follows `../s2/DESIGN.md`: tables are the content, numerals are
  tabular, a missing value is a marked gap (`templates/gap.html`), never a
  blank cell, and a column empty for the whole view is left out.
- Money renders in whole dollars through the `dollars` filter.
- Charts are inline SVG drawn by `money/templatetags/charts.py`, with no
  JavaScript, and each is followed by a table carrying the same numbers. Never
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
