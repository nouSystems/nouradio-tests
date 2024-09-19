#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


import numpy as np
from gnuradio import gr
import sys

class stop_and_close(gr.sync_block):
    """
    After some number of samples at the input, stop and close the program.  This accepts a callback
    to circumvent an issue with Ettus B-series radios that will not release the USB connection
    when mechanisms like "sys.exit()" are used.  As implemented, this callback has the form:

    def close_program_from_qt():
          # Some USB radios require a more elegant closing process,
          # so pass along a callback to the Qt functions.
          self.setAttribute(Qt.Qt.WA_DeleteOnClose)
          # Stopping and exiting the program gracefully requires multiple pieces.
          # Note that calling self.close() does not work within this callback.
          # The program stops, but the window never closes.
          self.stop()
          Qt.QApplication.quit()
    """
    def __init__(self, dtype="complex", test_name_filter=".*", stop_after_sample=1000, callback_to_exit=None):
        """Close the flowgraph after a certain number of samples.

        As implemented, this will exit at approximately the time listed.  It waits until the desired sample is
        in the buffer, but this exact placement may change between runs depending on the GNU Radio scheduler.

        Args:
            dtype (str, optional): a string description of the input type.  Can be ["complex", "float", "int", "short", "byte"]. Defaults to "complex".
            test_name_filter (str, optional): When running automated tests, filter which tests trigger this stop. Defaults to ".*" (all tests).
            stop_after_sample (int, optional): A count of the number of samples after which to stop. Defaults to 1000.
            callback_to_exit (Callable, optional): An external function to exit the program.  Callback takes no arguments. Defaults to None.
        """
        TYPE_MAP = {"complex": np.complex64,
                    "float": np.float32,
                    "int": np.int32,
                    "short": np.int16,
                    "byte": np.int8}
        
        assert(dtype in TYPE_MAP)
        
        gr.sync_block.__init__(self,
            name="stop_and_close",
            in_sig=[TYPE_MAP[dtype]],
            out_sig=[],
        )
        
        self.test_name_filter = test_name_filter
        self.stop_after_sample = stop_after_sample
        self.callback_to_exit = callback_to_exit
        self.total_samples_processed = 0

    def stop_flowgraph(self):
        """A fallback to exit the program if no alternate callback is provided.
        """
        print("No exit callback provided.  Falling back to sys.exit().")
        sys.exit(0)

    def work(self, input_items, output_items):
        """Count incoming samples until the specified stop sample is in the buffer,
        then quit.  If no alternative callback was provided, fall back to sys.exit().
        """
        in0 = input_items[0]
        self.total_samples_processed += len(in0)

        if self.total_samples_processed >= self.stop_after_sample:
            if self.callback_to_exit is not None:
                self.callback_to_exit()
            else:
                self.stop_flowgraph()

            return -1 # unlikely to be called since the program will quit in the callback

        return len(in0)