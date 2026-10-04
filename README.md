# Garberbucks

The money in American soccer: what players are paid, by season, team and player.
Salaries first; team valuations, owners and the roster rules come later (see
[ROADMAP.md](ROADMAP.md)).

A Django site (5.2, Python 3.12) over its own Postgres database, built the same
way as [soccerstats.us](https://soccerstats.us) (`../s2`) and from the same
pipeline. It holds only money and the people, teams and competitions the money
names; their slugs are the soccerstats.us slugs, so every page links across for
the rest.

`archive/` is the previous garberbucks.com, kept for reference. Nothing uses it.

## How the data gets here

    ../money_data/salaries/<league>/<season>   text files, one per season
      -> ../parse/parse/salaries.py            parser
      -> ../build  (./build.sh)                mongo `soccer.salaries`, names and teams normalized
      -> ./build   (./build.sh)                postgres `garberbucks_dev`

## Local setup

    # postgres with a soccerstats role, and the mongo build, as for ../s2
    cd ~/soccer/garberbucks.com
    uv venv --python 3.12
    uv pip install -p .venv/bin/python -r requirements.txt

    ../build/build.sh       # data repos -> mongo
    ./build.sh              # mongo -> postgres (garberbucks_dev)

    .venv/bin/python manage.py runserver

Settings are env-driven (see `settings.py`): `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`. Local defaults work with a
trusting local postgres and DEBUG on.

`build.sh` loads a fresh `garberbucks_build` and runs the URL smoke test before
replacing `garberbucks_dev`. A failed smoke test leaves the previous dev and
backup databases in place.

## Tests

    .venv/bin/python -m pytest
    ruff check .

## Deploy

Production runs on bert, beside soccerstats.us, at
/home/chris/www/garberbucks.com:

* gunicorn via systemd (`etc/systemd/garberbucks.service`) on 127.0.0.1:8101
* nginx proxies garberbucks.com to it (`etc/nginx/garberbucks.com`);
  www.garberbucks.com 301s to the apex. The vhost leans on the crawler
  defenses s2 installs in `/etc/nginx/conf.d/`.
* secrets live in /home/chris/www/garberbucks.com/.env (not in git). It
  connects as the `soccerstats` role, to database `garberbucks`.

The files under `etc/` are the source of truth, but nothing syncs them; bert
holds copies. Certbot edits the live vhost in place, so copy it back into the
repo after any cert change or the next deploy reverts it. To deploy a change:

    ssh bert 'cd /home/chris/www/garberbucks.com && git pull && \
        sudo cp etc/nginx/garberbucks.com /etc/nginx/sites-available/ && \
        sudo nginx -t && sudo systemctl reload nginx'

To ship the local `garberbucks_dev` database along with the current master:

    ./upload.sh

Request errors go to `journalctl -u garberbucks` on bert.
