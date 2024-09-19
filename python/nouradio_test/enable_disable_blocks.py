#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr

class enable_disable_blocks(gr.basic_block):
    """
    Specify some blocks to enable or disable during tests.  This does not perform any of the changes; it
    is a container, and its parameters will be read and utilized by the test runner.  These changes can
    be enabled and disabled by enabling or disabling this block in the flowgraph.  However, this block
    must not enable or disable any Test: Define Test blocks.  That may cause them to apply in an undefined
    order and may have undesired results.

    'enable_blocks' and 'disable_blocks' should be strings containing a comma-separate list of
    blocks to enable or disable for a particular test.  test_name_filter should be a regex pattern
    denoting when to apply these changes.
    """
    def __init__(self, test_name_filter:str = ".*", enable_blocks:str = "", disable_blocks:str = "",):
        """Enable and disable certain blocks during a test.

        Args:
            test_name_filter (str, optional): When running automated tests, filter which tests trigger this stop. Defaults to ".*" (all tests).
            enable_blocks (str, optional): A comma-separated list of block ids to enable. Defaults to "".
            disable_blocks (str, optional): A comma-separated list of block ids to disable. Defaults to "".
        """
        gr.basic_block.__init__(self,
            name="Test: Enable/Disable Blocks",
            in_sig=[],
            out_sig=[],)
        self.test_name_filter = test_name_filter
        self.enable_blocks = enable_blocks
        self.disable_blocks = disable_blocks
