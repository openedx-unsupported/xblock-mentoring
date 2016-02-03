from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'mentoring',
        'USER': 'root',
        'TEST': {
            'NAME': 'mentoring_test',
        },
    },
}
