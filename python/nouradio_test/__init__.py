#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

# The presence of this file turns this directory into a Python package

'''
This project adds flowgraph test functionality to GNU Radio Companion.
'''

# import pybind11 generated symbols into the nouradio_test namespace
try:
    # this might fail if the module is python-only
    from .nouradio_test_python import *
except ModuleNotFoundError:
    pass

# import any pure python here
from .define_test import define_test
from .enable_disable_blocks import enable_disable_blocks
from .variable_change import variable_change
from .run_command import run_command
from .run_tests import run_tests
from .screenshot import screenshot
from .stop_and_close import stop_and_close
from .run_tests_wrapper import run_tests_wrapper
from .stream_watch import stream_watch