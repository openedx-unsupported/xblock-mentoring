# -*- coding: utf-8 -*-
import time

from django.conf.urls import url


def raise_func(*args, **kwargs):
    # Wait until disabled uses polling, if this function takes
    # shorter than poll interval we might not observe that
    # button is disabled. This might be a race condition, but
    # I didn't find a better way to do it.
    time.sleep(1)
    raise ValueError()

urlpatterns = [
    url(r'.*', raise_func),
]
