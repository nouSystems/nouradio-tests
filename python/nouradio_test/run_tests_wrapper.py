#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import numpy as np
from gnuradio import gr
from gnuradio import nouradio_test

class run_tests_wrapper(gr.hier_block2):
    """Run timed tests from within GRC.  The tests will be automatically generated when running the flowgraph.  If
    any variable_change blocks exist with multiple options, or if multiple tests are defined, the flowgraph will not
    execute as-is.  Instead, it will produce other flowgraphs and run those.

    In order to correctly call the "start" function of the test runner, it has to have an external
    stream connection.  Do that here.  The internal block need not be exposed.
    """
    def __init__(self, dtype="complex", grc_file="", staging_dir="", artifacts_dir="", stop_after_sample="", callback_to_exit=None, suppress_runner=False):
        """Generate and run multiple flowgraph tests.

        Args:
            dtype (str, optional): The data type for the stream input. Defaults to "complex".
            grc_file (str, optional): The base GRC file for generating the tests.  Will be auto-populated by the block.yml file. Defaults to "".
            staging_dir (str, optional): When automated tests are generated, temporarily store the flowgraphs in this directory. Defaults to "", which generates a temp
                directory that will be cleaned after execution.
            artifacts_dir (str, optional): Store the results of automated tests to this directory. Defaults to "".
            stop_after_sample (str, optional): Stop after N number of samples have been processed. Defaults to "".
            callback_to_exit (Callable, optional): A custom callback to exit the program.  See stop_and_close for more information. Defaults to None.
            suppress_runner (bool, optional): Do not run tests.  This is primarily used to prevent recursive test generation in automated tests. Defaults to False.
        """
        TYPE_MAP = {"complex": np.complex64,
                    "float": np.float32,
                    "int": np.int32,
                    "short": np.int16,
                    "byte": np.int8}
        
        assert(dtype in TYPE_MAP)

        gr.hier_block2.__init__(self,
            "run_tests_wrapper",
            gr.io_signature(1, 1, TYPE_MAP[dtype](0).itemsize), # Input signature
            gr.io_signature(0, 0, gr.sizeof_char)) # Output signature

        self.stopper = nouradio_test.stop_and_close(dtype, ".*", stop_after_sample, callback_to_exit)
        self.connect(self, self.stopper)

        if not suppress_runner:
            # Do not start another instance of the test runner if we are running within a test runner
            self.runner = nouradio_test.run_tests(dtype, grc_file, staging_dir, artifacts_dir, callback_to_exit)
            self.connect(self, self.runner)
