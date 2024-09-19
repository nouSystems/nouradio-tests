#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import sys
from pathlib import Path
from gnuradio import gr
import numpy as np
import tempfile
import shutil

# Add the local path here to make local includes easier
try:
    import generate_tests as gt
except:
    sys.path.append(str(Path(__file__).parent))
    print(f"Note: Adding path {Path(__file__).parent} to the python path.")
    import generate_tests as gt

class run_tests(gr.sync_block):
    """Generate and run test configurations from within GRC.  This will override the normal execution of
    the flowgraph and replace it with the batched generation and execution functionality of nouradio_test.
    When tests are concluded, the execution of this flowgraph will also terminate.

    Due to how the scheduler appears to work, the start() and stop() functions will not be called unless
    the block has an input or output stream.  The input stream to this block is present purely to allow
    start() to be called; it is not used for other reasons.
    """
    def __init__(self,
                 dtype="complex",
                 grc_file = "",
                 staging_dir="",
                 artifacts_dir="test_artifacts",
                 exit_callback=None):
        """Run tests instead of the typical flowgraph behavior

        Args:
            dtype (str, optional): The string data type for this stream. Can be complex, float, int, short, or byte. Defaults to "complex".
            grc_file (str, optional): The GRC file to execute.  Will be populated automatically if used in GRC. Defaults to "".
            staging_dir (str, optional): Place all modified flowgraph files in this directory. Defaults to "", which generates a temporary directory.
            artifacts_dir (str, optional): A place to put the test outputs. A new subfolder will be generated for each run. Defaults to "test_artifacts".
            exit_callback (Callable, optional): A custom callback to exit the flowgraph.  Accepts no arguments. Defaults to None.
        """
        TYPE_MAP = {"complex": np.complex64,
                    "float": np.float32,
                    "int": np.int32,
                    "short": np.int16,
                    "byte": np.int8}

        assert(dtype in TYPE_MAP)

        gr.sync_block.__init__(self,
            name="run_tests",
            in_sig=[TYPE_MAP[dtype]],
            out_sig=[])
        self.grc_file = grc_file
        
        # If the staging directory is empty, create a temp directory that will be
        # cleaned after executing the tests
        if staging_dir == "":
            self.staging_dir = tempfile.mkdtemp()
            self.staging_dir_is_temp = True
        else:
            self.staging_dir = staging_dir
            self.staging_dir_is_temp = False

        self.artifacts_dir = artifacts_dir
        self.exit_callback = exit_callback

    def start(self):
        """Start executing the tests.  This will replace the normal execution of the flowgraph.
        """
        print("Starting to run tests!")
        tests = gt.PrepareTests(self.grc_file, self.staging_dir)
        gt.RunTests(self.artifacts_dir, test_files = tests)
        print("Tests Done.  Exiting...")

        # Now stop executing.  Use the provided external callback if able.
        self.stop()
        if self.exit_callback is not None:
            self.exit_callback()
        else:
            sys.exit(0)

    def stop(self):
        """If the staging directory is temporary, clean up after execution
        """
        if self.staging_dir_is_temp:
            shutil.rmtree(self.staging_dir, ignore_errors=True)

    def work(self, input_items, output_items):
        """This will not run"""
        return -1