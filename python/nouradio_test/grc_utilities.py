#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import yaml
import re
import subprocess
from pathlib import Path
from copy import deepcopy
import os
from contextlib import contextmanager
from queue import Queue, Full
from threading import Thread
import time

@contextmanager
def ChDirContext(dir: Path | str, create_okay: bool = False, quiet: bool = False):
    """Temporarily enter a directory.  When exiting the context, return to the original working directory.

    Args:
        dir (Path | str): The new directory to enter
        create_okay (bool, optional): If the directory does not exist, create it. Defaults to False.
        quiet (bool): Suppress the prints indicating directory changes

    Yields:
        None
    """
    starting = Path().absolute()
    dir = Path(dir)

    def enabled_print(string):
        if not quiet:
            print(string)

    try:
        if create_okay:
            enabled_print(f">> Creating {dir}")
            os.makedirs(str(dir), exist_ok=True)
        enabled_print(f">> Changing to {dir}")
        os.chdir(dir.absolute())
        yield
    finally:
        enabled_print(f">> Returning to {starting}")
        os.chdir(starting)


def IncrementFilename(filename: Path | str) -> str:
    # If the file exists, find a variant that does not.
    if os.path.exists(filename):
        path = Path(filename)
        i = 0
        new_path = path.parent / f"{path.stem}_{i}{path.suffix}"
        while os.path.exists(new_path):
            new_path = path.parent / f"{path.stem}_{i}{path.suffix}"
            i += 1
        # We have found a usable file name.  Store it.
        filename = str(new_path)
    return filename


class WriteLater:
    """A simple deferred file writer.  Data will be queued and written in a separate thread
    to reduce the burden on the main thread.  Due to the GIL, this will likely fill in gaps
    between buffers in the GNU Radio scheduler.
    """
    def __init__(self, filename: str, data_is_iterable: bool):
        """Write now to a buffer, then write to a file later.

        Args:
            filename (str): Save to this location.  If it exists, generate a new one with a number at the end.
            data_is_iterable (bool): Allow the data writer to use write_lines().
        """
        self.data_is_iterable: bool = data_is_iterable

        self.filename: str = IncrementFilename(filename)
        if self.filename != filename:
            print(f"File {filename} exists!  Writing to {self.filename}.")

        self.write_queue = Queue()
        self.thread: Thread = None
        self.should_run: bool = False # Used to stop the thread
        self.running: bool = False # Used to indicate that the internal thread is running

        self.stop_called: bool = True
    
    def __del__(self):
        """Stop the thread if it's not already stopped.
        """
        if not self.stop_called:
            self.stop()

    def start(self):
        """Start the period recording thread.  This is required to periodically write data to the
        file while running.  If this function is not called, all data will be written at destruction.
        """
        self.thread = Thread(target=self.run)
        self.should_run = True # This must be True before starting the thread or it will exit immediately
        self.thread.start()
    
    def stop(self):
        """Stop the thread (if running) and flush any remaining data to the file.
        If start() was never called, all data will be written now to the file.
        """
        # Store an indicator to prevent the stop actions from happening multiple times.
        self.stop_called = True

        # Store the initial state of the thread in case it exits quickly
        # when should_run is disabled.
        was_running: bool = self.running
        self.should_run = False
        if was_running:
            self.thread.join()
        
        # If we somehow get here with extra data left, write it to the file.
        self.flush()

    def write(self, data):
        """ Queue some data to write later.
        For threaded usage, you must call start().  Otherwise, data will be queued and written
        when this object is destructed, so no data will be lost for that reason.

        Args:
            data (Any): the thing to write.  Must be supported by {file}.write()
        """
        try:
            self.write_queue.put(data, block=False)
        except Full:
            print(f"Could not write data {data}")
    
    def flush(self, check_thread_running: bool = True):
        """Write all queue contents to the file now.

        Args:
            check_thread_running (bool, optional): A quick guard to warn the user of threading issues. Defaults to True.
        """
        if check_thread_running and self.running:
            print("Warning: Flushing file while thread is running. Data may be out of order and/or corrupted.")
        
        # Append to the file for convenience.  The initialization ensures the file
        # will initially be empty, but it may not exist yet.
        with open(self.filename, "a") as of:
            # Grab all entries and write them to the file
            while not self.write_queue.empty():
                data = self.write_queue.get()
                if self.data_is_iterable:
                    of.writelines(data)
                else:
                    of.write(data)

    def run(self):
        """ Periodically write data to the file.
        Do not call this manually.  Instead, call start().
        """
        self.running = True
        while self.should_run:
            self.flush(check_thread_running=False)
            time.sleep(0.1)
        self.running = False


def FilterBlocks(grc:dict, field:str, pattern:str,):
    """_summary_

    Args:
        grc (dict): A dictionary of the GRC file
        field (str): A particular field to examine (as a dict key).  This will not handle nested keys; only one level.
        pattern (str): Regex to apply to the field value.  If it matches, return the corresponding entry in the GRC.

    Returns:
        dict: The GRC entries that pass the filter.
    """
    output = {}
    for i, block in enumerate(grc["blocks"]):
        if field in block:
            if re.search(pattern, block[field]):
                output[i] = block
    return output

# https://stackoverflow.com/a/13688108, Bakuriu
def nested_set(dic:dict, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value

def nested_get(dic:dict, keys):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    return dic[keys[-1]]

def GetBlockProperty(grc:dict, filter_type: str, filter:str, property_chain: list, cull_none: bool = False) -> dict:
    """Scan the GRC and return the specified properties of all blocks permitted by the filter.

    Args:
        grc (dict): A dictionary of the GRC file
        filter_type (str): A basic filter for the name or id of the blocks.  Use "name" or "id"
        filter (str): A regex pattern to filter the blocks according to the field in filter_type.
        property_chain (list): A list of nested keys to traverse and extract the value.
        cull_none (bool, optional): Some fields have "None" as an intentional value, but this may impact\
 the processing script.  If True, do not pass along values containing "None". Defaults to False.

    Returns:
        dict: A dict of {filtered_block_characteristic:value} for each block.
    """
    output = {}
    for block in FilterBlocks(grc, filter_type, filter).values():
        value = None
        try:
            value = nested_get(block, property_chain)
        except:
            print(f"The requested property {property_chain[-1]} in block {block['name']} does not exist!")
        if value is not None or not cull_none:
            if property_chain[-1] == "state" and isinstance(value, bool):
                # Some blocks return a bool here, and some return a string.  Unify that here.
                value = "enabled" if value else "disabled"
            output[block["name"]] = value
    return output

def SetBlockProperty(grc:dict, filter_type: str, filter:str, property_chain: list, value) -> dict:
    """The counterpart to GetBlockProperty to set properies.

    Args:
        grc (dict): A dictionary of the GRC file
        filter_type (str): A basic filter for the name or id of the blocks.  Use "name" or "id"
        filter (str): A regex pattern to filter the blocks according to the field in filter_type.
        property_chain (list): A list of nested keys to traverse and extract the value.
        value (Any): A new value.  Must be yaml serializable.

    Returns:
        dict: A modified copy of the grc dict with the new properties.
    """
    grc_copy = deepcopy(grc)
    for i, block in FilterBlocks(grc, filter_type, filter).items():
        nested_set(block, property_chain, value)
        grc_copy["blocks"][i] = block
    return grc_copy    

def BlockIsEnabled(grc: dict, block_name: str) -> bool:
    """A shortcut to determine if a block is enabled

    Args:
        grc (dict): A dictionary of the GRC file
        block_name (str): The block "name" property, which is the unique "id" shown in GRC
    
    Returns:
        bool: True if the block is enabled, False otherwise
    """
    state = GetBlockProperty(grc, "name", block_name, ["states", "state"], cull_none=False)[block_name]
    print(f"Block state of {block_name} is {state}")
    # The state can be either a boolean or either of the strings "enabled" or "true"
    if state == "enabled" or state == True or state == "true":
        enabled = True
    else:
        enabled = False
    return enabled

def GeneratePythonFiles(folder_or_file: str | Path = "") -> list:
    """Call grcc to convert .grc files to python files.

    Args:
        folder_or_file (str | Path, optional): The specific file or folder to process. Defaults to "" (the working directory).

    Returns:
        list: A list of the python files generated by this function.
    """
    files_generated = []
   
    folder_or_file: Path = Path(folder_or_file)
    if folder_or_file.is_file():
        file = folder_or_file
        print(f"Generating .py for {file}")
        subprocess.call(["grcc", str(file)])
        files_generated.append(str(file.with_suffix(".py")))
    else:
        folder = folder_or_file
        with ChDirContext(folder, True):
            for file in folder.glob("*.grc"):
                print(f"Generating .py for {file}")
                subprocess.call(["grcc", str(file)])
                files_generated.append(str(file.with_suffix(".py")))
    
    return files_generated

def Load(path: Path|str) -> dict:
    """Read a .grc file for readable by the other functions in grc_utilities

    Args:
        path (Path | str): The path to the .grc file

    Returns:
        dict: A deserialized yaml of the .grc contents.
    """
    if isinstance(path, str):
        path = Path(path)
    grc = None
    with path.open("r") as file:
        grc = yaml.load(file, Loader=yaml.Loader)
    return grc
    
def Save(path: Path|str, grc: dict):
    """Save the grc contents to a new file.  This can overwrite an existing file.

    Args:
        path (Path | str): The path to which to save.
        grc (dict): The grc contents to save
    """
    if isinstance(path, str):
        path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        yaml.dump(grc, file, Dumper=yaml.Dumper)

def FixStrings(iterable: list | dict, convert_numeric:bool = False):
    """Strip excess whitespace and quotes, and optionally convert numeric values to floats.

    Args:
        iterable (list | dict): an iterable containing strings to fix
        convert_numeric (bool, optional): Automatically convert numeric string values to floats. Defaults to False.

    Returns:
        list | dict: The modified container
    """
    if isinstance(iterable, list):
        fixed = [x.strip(" \'\"") for x in iterable]
        if convert_numeric:
            fixed = [float(x) if x.isnumeric() else x for x in fixed]
    else:
        fixed = {k:v.strip(" \'\"") for k, v in iterable.items()}
        if convert_numeric:
            fixed = {k:float(v) if v.isnumeric() else v for k, v in fixed.items()}
    return fixed

def GetGrcID(grc: dict) -> str:
    """Get the name of the GRC file

    Args:
        grc (dict): A dictionary of the GRC file 

    Returns:
        str: The name of the GRC file
    """
    return nested_get(grc, ["options", "parameters", "id"])

def SetGrcID(grc: dict, id: str) -> dict:
    """Change the name of a grc file

    Args:
        grc (dict): A dictionary of the GRC file 
        id (str): The new id

    Returns:
        dict: The modified grc contents
    """
    grc_copy = deepcopy(grc)
    nested_set(grc_copy, ["options", "parameters", "id"], id)
    return grc_copy