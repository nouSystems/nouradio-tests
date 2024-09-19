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
import shlex
import subprocess
import time
import platform

class run_command(gr.sync_block):
    """
    Run a script or command at the beginning or end of a flowgraph run.  The script will block execution until finished.

    Use this to set up external hardware, to kick off post-run analysis, or to perform other per-run tasks.
    """
    def __init__(self, dtype:str = "complex", test_name_filter:str = ".*", execute_at="start", command_type="script", command="", script_path="", args=""):
        TYPE_MAP = {"complex": np.complex64,
                    "float": np.float32,
                    "int": np.int32,
                    "short": np.int16,
                    "byte": np.int8}

        assert(dtype in TYPE_MAP)

        gr.sync_block.__init__(self,
            name="run_command",
            in_sig=[TYPE_MAP[dtype]],
            out_sig=[])
        self.test_name_filter: str = test_name_filter
        self.execute_at: str = execute_at.lower()
        self.command_type: str = command_type
        self.command: str = command
        self.script_path: str = script_path
        self.args: str = args
        
        if self.command_type not in ["script", "command"]:
            raise ValueError(f"Value {self.command_type} is not valid.  Use either 'script' or 'command'!")

        if self.execute_at not in ["start", "stop"]:
            raise ValueError(f"Value {self.execute_at} is not valid.  Use either 'start' or 'stop'!")
        
    def check_script_exists(self):
        if not Path(self.script_path).exists():
            raise FileNotFoundError(f"The script {self.script_path} does not exist!")

    def assemble_command(self) -> str:
        """Generate a string of the command.
        """
        if self.command_type == "script":
            command = [self.script_path] + list(shlex.split(self.args))
            command = ' '.join(command)
        else:
            command = self.command
        return command

    def run_command(self, at: str, detached: bool = False):
        """Run a command

        The 'detached' option is present for the exit call.  When the stop() call is run, it appears to have very little time
        to execute before the process terminates.  Use 'detached' to execute the script during the stop() call to ensure the
        process runs without interruption.
        """
        command = self.assemble_command()
        print(f"Running {at} {self.command_type}: {command}")

        if not detached:
            print(subprocess.check_output(
                command,
                shell=True,
                stderr=subprocess.STDOUT))
        else:
            split_command = shlex.split(command)
            if platform.system() == "Windows":
                process = subprocess.Popen(
                    split_command,
                    shell=True,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, # Detach the process
                )
            else:
                process = subprocess.Popen(
                    split_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,  # Detach the process
                )

    def start(self):
        """If configured to do so, run the setup script now.  This block will block program execution until the
        script completes, and it will print the script output to stdout and stderr.
        
        In all cases, check that the script exists.  If not, throw a FileNotFoundError.  Do this during start()
        since __init__ commands are run while browsing GRC; give the user a chance to make the file.
        """
        if self.command_type == "script":
            self.check_script_exists()

        if self.execute_at == "start":
            self.run_command("startup", detached=False)

    def stop(self):
        """If configured to do so, run the teardown script now.  Ideally, this block will block program execution until the
        script completes, and it will print the script output to stdout and stderr.  However, perhaps due to the quitting
        mechanism from the stop_and_close block, this does not have enough time to execute more than a few basic commands
        before the block exits.
        """
        start_time = time.time()
        print(f"Entering 'stop()' at {start_time}")
        #if self.execute_at == "stop":
        #    self.run_command("teardown", detached=True)
        print(f"Exiting 'stop()' after {time.time() - start_time} seconds")

    def work(self, input_items, output_items):
        """No work to do.
        """
        return len(input_items[0])

