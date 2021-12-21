from settings import * # pylint: disable=wildcard-import, unused-wildcard-import

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
