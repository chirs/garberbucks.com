#!/bin/sh
# Ship the locally built database and the current master to production (bert)
# and restart the site.
set -e

DUMP=/tmp/garberbucks.dump

pg_dump -Fc -U soccerstats garberbucks_dev > $DUMP
scp $DUMP bert:/tmp/
rm $DUMP

git push origin master

ssh bert 'set -e
sudo systemctl stop garberbucks
sudo -u postgres dropdb --if-exists garberbucks
sudo -u postgres createdb garberbucks --owner=soccerstats
export PGPASSWORD=$(grep DB_PASSWORD /home/chris/www/garberbucks.com/.env | cut -d= -f2)
pg_restore -h 127.0.0.1 -U soccerstats -d garberbucks --no-owner /tmp/garberbucks.dump
rm /tmp/garberbucks.dump
cd /home/chris/www/garberbucks.com && git pull
set -a && . ./.env && set +a
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
chmod -R a+rX staticfiles
sudo systemctl start garberbucks'

echo "Shipped to bert."
