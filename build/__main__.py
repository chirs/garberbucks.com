import argparse
import os

import django


def main(argv=None):
    parser = argparse.ArgumentParser(description='Run the Mongo → Postgres build.')
    parser.add_argument('--settings', default='build_settings')
    args = parser.parse_args(argv)

    os.environ['DJANGO_SETTINGS_MODULE'] = args.settings
    django.setup()

    from build.load import load
    load()


if __name__ == '__main__':
    main()
