#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


import numpy as np
from gnuradio import gr
from pathlib import Path
import sys

# Add the local path here to make local includes easier
try:
    from grc_utilities import WriteLater
except:
    sys.path.append(str(Path(__file__).parent))
    print(f"Note: Adding path {Path(__file__).parent} to the python path.")
    from grc_utilities import WriteLater


class stream_watch(gr.sync_block):
    """Watch a given stream of samples.  Report when the incoming signal exceeds some boundaries either to a file or to the console.
    """
    def __init__(self, dtype="float", test_name_filter=".*", save_to: str = "", mode="inside", upper_bound=1.0, lower_bound=-1.0):
        """Watch a given stream of samples.  Report when the incoming signal exceeds some boundaries either to a file or to the console.

        Args:
            dtype (str, optional): Data Type as a string.  Can be float, int, uint, short, ushort, char, uchar. Defaults to "float".
            test_name_filter (str, optional): When running automated tests, filter which tests trigger this stop. Defaults to ".*" (all tests).
            save_to (str, optional): Save to a file. Defaults to "" (print to console).
            mode (str, optional): Controls how boundaries are enforced.  Can be above, below, inside, or outside. Defaults to "inside".
                "inside" : Failure when signal < lower_bound OR signal > upper_bound
                "outside": Failure when signal > lower_bound AND signal < upper_bound
                "above"  : Failure when signal < lower_bound
                "below"  : Failure when signal > upper_bound
            upper_bound (float, optional): Defaults to 1.0.
            lower_bound (float, optional): Defaults to -1.0.
        """
        TYPE_MAP = {#"complex": np.complex64, #Complex type not supported since we only have scalar bounds
                    "float": np.float32,
                    "int": np.int32,
                    "uint": np.uint32,
                    "short": np.int16,
                    "ushort": np.uint16,
                    "char": np.int8,
                    "uchar": np.uint8}

        assert(dtype in TYPE_MAP)

        MODES = ["above", "below", "inside", "outside"]

        assert(mode in MODES)

        gr.sync_block.__init__(self,
            name="stream_watch",
            in_sig=[TYPE_MAP[dtype]],
            out_sig=[])
        
        self.dtype = dtype
        self.test_name_filter = test_name_filter
        self.mode = mode

        self.n_samples_processed = np.ulonglong(0)

        # Save the filename.  This may be modified in WriteLater if the file exists.
        # If the filename is an empty string, only report failures to the console.
        self.filename = save_to
        if self.filename:
            self.output_writer = WriteLater(self.filename, True)
        else:
            self.output_writer = None

        # Coerce the input values into the signal's data type
        conversion_type = TYPE_MAP[dtype]
        self.upper_bound = conversion_type(upper_bound)
        self.lower_bound = conversion_type(lower_bound)

    def start(self):
        """Start the file logger thread automatically when the flowgraph starts.
        """
        if self.output_writer is not None:
            self.output_writer.start()

    def stop(self):
        """Stop and flush the file logger thread automatically when the flowgraph stops.
        """
        if self.output_writer is not None:
            self.output_writer.stop()

    def work(self, input_items, output_items):
        in0 = input_items[0]
        failures = []
        match self.mode:
            case "above":
                failures = np.argwhere(in0 < self.lower_bound)
            case "below":
                failures = np.argwhere(in0 > self.upper_bound)
            case "inside":
                failures = np.argwhere((in0 < self.lower_bound) | (in0 > self.upper_bound))
            case "outside":
                failures = np.argwhere((in0 > self.lower_bound) & (in0 < self.upper_bound))
            
        if len(failures) > 0:
            first_index = self.n_samples_processed
            if self.output_writer is None: 
                # Since reporting to the console takes time and slows processing, only report the number
                # of failures to the console.
                last_index = first_index + len(input_items[0])
                print(f"Signal failed {len(failures)} times between {first_index} and {last_index}")
            else:
                # Don't save this as a generator so it can be copied entirely to the write queue.
                # The indices produced by argwhere() are local to the buffer processed in this call.
                # To get the sample's absolute index, adjust this number for the total number of samples
                # processed by this block.  Then write the failure indices and values to the file.
                notes = [f"{int(index[0] + first_index)},{value[0]}\n" for index, value in zip(failures, in0[failures])]
                self.output_writer.write(notes)

        self.n_samples_processed += len(input_items[0])
        return len(input_items[0])
