#!/usr/bin/env python
import os
import sys

from custom_settings import DEBUG
from settings import PROJECT_DIRNAME



if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "usmntstats.settings")

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
