#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc..
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr

class variable_change(gr.basic_block):
    """This block does not execute.  Instead, it holds data to change variables as a sweep for automated runs.
    Only one variable_change block can be active per test run (except for mode="constant").  Disable others,
    or use the test_name_filter to specify relevant tests.

    Possible modes are as follows:
    "constant": Change the specified variable to the chose value.  Will not produce a sweep.
    "range": Produce one flowgraph for each value in [start:step:stop)
    "linspace": Produce "count" number of values in the range [start:stop]
    "choices": Produce one flowgraph for each choice provided in the list.
    """
    def __init__(self, test_name_filter:str = ".*", mode:str = "constant", variable:str = "", start_value:float = 0.0, stop_value:float = 100.0, step:float=1.0, count:int = 100, choices:str = "", value = None,):
        """_summary_

        Args:
            test_name_filter (str, optional): When running automated tests, filter which tests trigger this stop. Defaults to ".*" (all tests).
            mode (str, optional): How to apply this sweep.  Can be constant, range, linspace, or choices. Defaults to "constant".
            variable (str, optional): The id of the variable block to modify. Defaults to "".
            start_value (float, optional): The start value when mode = "range" or "linspace". Defaults to 0.0.
            stop_value (float, optional): The stop value when mode = "range" or "linspace". Defaults to 100.0.
            step (float, optional): The step size when mode = "range". Defaults to 1.0.
            count (int, optional): The step count when mode = "linspace". Defaults to 100.
            choices (str, optional): A string of comma-separated values when mode = "choice".  Each choice will be copied as-is into the produced flowgraphs. Defaults to "".
            value (Any, optional): The value of the variable when mode = "constant". Defaults to None.

        Raises:
            ValueError: Indicates an invalid mode choice
        """
        gr.basic_block.__init__(self,
            name="Test: Variable Change",
            in_sig=[],
            out_sig=[])
        self.possible_modes = ["constant", "range", "linspace", "choices"]

        if mode not in self.possible_modes:
            raise ValueError(f"Variable Change Mode {mode} is not a valid option!  Must be one of {self.possible_modes}")

        self.test_name_filter = test_name_filter
        self.mode = mode
        self.variable = variable
        self.start_value = start_value
        self.stop_value = stop_value
        self.step = step
        self.choices = choices
        self.value = value
