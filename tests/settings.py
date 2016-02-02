DEBUG = True

SECRET_KEY = 'please change it in production environment'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'workbench',
    'sample_xblocks.basic',
    'django_nose',
    'mentoring'
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mentoring.sqlite'
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.eggs.Loader',
)

ROOT_URLCONF = 'urls'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

STATIC_ROOT = ''
STATIC_URL = '/static/'

WORKBENCH = {'reset_state_on_restart': False}
