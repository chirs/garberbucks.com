from settings import *

DATABASES['default']['NAME'] = os.environ.get('BUILD_DB_NAME', 'garberbucks_build')
