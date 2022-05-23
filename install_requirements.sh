#!/usr/bin/env bash

/software/hgi/installs/python3.9/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel -r requirements.txt

