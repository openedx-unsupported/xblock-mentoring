#!/usr/bin/env bash
pip install -e git://github.com/edx/xblock-sdk.git#egg=xblock-sdk
pip install -r requirements.txt
pip install -r venv/src/xblock-sdk/requirements/base.txt
pip install -r venv/src/xblock-sdk/requirements/test.txt
