# -*- coding: utf-8 -*-
import time

from django.conf.urls import url


def raise_func(*args, **kwargs):
    time.sleep(1)
    raise ValueError()

urlpatterns = [
    url(r'.*', raise_func),
]
