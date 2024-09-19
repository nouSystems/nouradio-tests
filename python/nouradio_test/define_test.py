#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


from gnuradio import gr

class define_test(gr.basic_block):
    """
    Define a test for automated processing. Does not run, but instead defines tests for use with the
    "test_name_filter" parameter of other blocks.
    """
    def __init__(self, test_name:str = "test",):
        gr.basic_block.__init__(self,
            name="Test: Define Test",
            in_sig=[],
            out_sig=[])
        self.test_name:str = test_name


