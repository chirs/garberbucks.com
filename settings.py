import os
from os.path import join
import socket

from secret_settings import *

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS


DEBUG = True

PROJECT_DIR = "/home/chris/www/usmntstats"
STATIC_URL = '/static/'



# Cache instructions.
if DEBUG:
    CACHE_MIDDLEWARE_KEY_PREFIX = "dev:"
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
            }
        }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
            }
        }

PRODUCTION_SITES = (
    "bert",
)




TEMPLATE_CONTEXT_PROCESSORS += (
    #'bios.context_processors.debug_mode',
    'django.core.context_processors.request',

)    


STATICFILES_DIRS = (
    "/Users/chris/www/s2/media",
)


INTERNAL_IPS = ('127.0.0.1',)

TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ("Chris Edgemon", 'chris@soccerstats.us'),
)

MANAGERS = ADMINS


DB_NAME = 'soccerstats'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': DB_NAME,                      # Or path to database file if using sqlite3.
        'USER': 'soccerstats',                      # Not used with sqlite3.
        'PASSWORD': 'ymctas',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}


# Fix this soon.
#EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
#EMAIL_FILE_PATH = '/home/chris/www/www.soccerstats.us/run/messages' # change this to a proper location
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'chris@soccerstats.us'
EMAIL_PORT = 587
EMAIL_USE_TLS = True




# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    #'minidetector.Middleware',

)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    "%s/templates" % PROJECT_DIR,
)

FIXTURE_DIR = "%s/fixtures" % PROJECT_DIR,

ALLOWED_HOSTS = ['.soccerstats.us']

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'django.contrib.gis',
    #'gunicorn',
    #'debug_toolbar',

    #'haystack',
    #'django_extensions',
)


def show_toolbar(request):
    return False
    return DEBUG


DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': show_toolbar,
    # Rest of config
}

# Various apps available
DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.cache.CacheDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
)

HAYSTACK_SITECONF = 'search_sites'
HAYSTACK_SEARCH_ENGINE = 'solr'
HAYSTACK_SOLR_URL = 'http://127.0.0.1:8983/solr'
HAYSTACK_SOLR_URL = 'http://0.0.0.0:8080/solr'

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://127.0.0.1:8983/solr'
    },
}


