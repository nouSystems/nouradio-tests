#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import re
import copy
import os
import sys
import subprocess
from pathlib import Path
import numpy as np
import shutil
from datetime import datetime
 
# Add the local path here to make local includes easier
try:
    import grc_utilities as gru
except:
    sys.path.append(str(Path(__file__).parent))
    print(f"Note: Adding path {Path(__file__).parent} to the python path.")
    import grc_utilities as gru

def ReadTestNames(grc:dict, hide_disabled:bool = True) -> list[str]:
    """Read the test names defines in any 'define_test' blocks.

    Args:
        grc (dict): A dict of the GRC file contents
        hide_disabled (bool): Do not return tests that are disabled
        
    Returns:
        list[str]: A list of the test names
    """
    all_tests = gru.GetBlockProperty(grc, "id", "define_test", ['parameters', 'name'])
    output = []
    if hide_disabled:
        for test_block_id, test_name in (copy.deepcopy(all_tests)).items():
            if gru.BlockIsEnabled(grc, test_block_id):
                output.append(test_name)
    else:
        output = list(all_tests.values())
    return output

def GetTestModifiers(grc:dict):
    """Get all nouradio_test blocks

    Args:
        grc (dict): A dict of the GRC file contents

    Returns:
        dict: The block information for each nouradio_test block
    """
    return gru.FilterBlocks(grc, "id", "^nouradio_test")

def ReadBlockParams(block: dict, expected_block_type: str, param_chains: list) -> dict:
    """_summary_

    Args:
        block (dict): A dict of the block information from the GRC yaml
        expected_block_type (str): If the block id does not match this, exit.  It must have been called in error.
        param_chains (list): A list of lists defining the parameters to read

    Raises:
        KeyError: The call was invoked when the underlying block does not match the expected data.

    Returns:
        dict: A flattened version of the block containing all requested information.
    """
    if block["id"] != expected_block_type:
        raise KeyError(f"Block Type {expected_block_type} is not 'nouradio_test_define_test'")
    params = {}
    params["id"] = block["id"]
    params["name"] = block["name"]
    params["type"] = expected_block_type
    for chain in param_chains:
        params[chain[-1]] = gru.nested_get(block, chain)
    return params

def ReadDefineTest(block: dict) -> dict:
    """Read the define_test block

    Args:
        block (dict): GRC block info

    Returns:
        dict: the block params
    """
    EXPECTED_BLOCK_TYPE = "nouradio_test_define_test"
    params = ReadBlockParams(block, EXPECTED_BLOCK_TYPE, [
        ["parameters", "name"],
        ["states", "state"],
    ])
    return params
    
def ReadRunScript(block: dict):
    """Read the run_script block

    Args:
        block (dict): GRC block info

    Returns:
        dict: the block params
    """
    EXPECTED_BLOCK_TYPE = "nouradio_test_run_script"
    params = ReadBlockParams(block, EXPECTED_BLOCK_TYPE, [
        ["parameters", "test_name_filter"],
        ["parameters", "execute_at"],
        ["parameters", "script_path"],
        ["states", "state"],
    ])
    return params

def ReadEnableDisableBlocks(block: dict):
    """Read the enable_disable_blocks block

    Args:
        block (dict): GRC block info

    Returns:
        dict: the block params
    """
    EXPECTED_BLOCK_TYPE = "nouradio_test_enable_disable_blocks"
    params = ReadBlockParams(block, EXPECTED_BLOCK_TYPE, [
        ["parameters", "enable_blocks"],
        ["parameters", "disable_blocks"],
        ["parameters", "test_name_filter"],
        ["states", "state"],
    ])

    params["enable_blocks"] = gru.FixStrings(params["enable_blocks"].split(","))
    params["disable_blocks"] = gru.FixStrings(params["disable_blocks"].split(","))
    return params

def ReadVariableChange(block: dict):
    """Read the variable_change block

    Args:
        block (dict): GRC block info

    Returns:
        dict: the block params
    """
    EXPECTED_BLOCK_TYPE = "nouradio_test_variable_change"
    params = ReadBlockParams(block, EXPECTED_BLOCK_TYPE, [
        ["parameters", "test_name_filter"],
        ["parameters", "mode"],
        ["parameters", "variable"],
        ["parameters", "start_value"],
        ["parameters", "stop_value"],
        ["parameters", "step"],
        ["parameters", "count"],
        ["parameters", "value"],
        ["parameters", "choices"],
        ["states", "state"],
    ])

    def MaybeFloat(item:str):
        # Convert the numbers if possible
        try:
            return float(item)
        except:
            # If it is not easy to coerce to a float, don't do it.
            return item
        
    params["choices"] = gru.FixStrings(params["choices"].split(","))
    params["start_value"] = MaybeFloat(params["start_value"])
    params["stop_value"] = MaybeFloat(params["stop_value"])
    params["step"] = MaybeFloat(params["step"])
    params["count"] = MaybeFloat(params["count"])
    params["value"] = MaybeFloat(params["value"])

    # Resolve the variable choices to a list of values to make processing mostly common
    possibilities = []
    match params["mode"]:
        case "constant":
            possibilities = [params["value"]]
        case "range":
            possibilities = list(np.arange(params["start_value"], params["stop_value"], params["step"]))
        case "linspace":
            possibilities = np.linspace(params["start_value"], params["stop_value"], params["count"])
        case "choices":
            possibilities = params["choices"]

    params["resolved_choices"] = possibilities

    return params

def ReadScreenshot(block: dict):
    """Read the screenshot block

    Args:
        block (dict): GRC block info

    Returns:
        dict: the block params
    """
    EXPECTED_BLOCK_TYPE = "nouradio_test_screenshot"
    params = ReadBlockParams(block, EXPECTED_BLOCK_TYPE, [
        ["parameters", "test_name_filter"],
        ["states", "state"],
    ])
    return params

def ReadRunTestsWrapper(block: dict):
    """Read the run_tests_wrapper block

    Args:
        block (dict): GRC block info

    Returns:
        dict: the block params
    """
    EXPECTED_BLOCK_TYPE = "nouradio_test_run_tests_wrapper"
    params = ReadBlockParams(block, EXPECTED_BLOCK_TYPE, [
        ["states", "state"],
        ["parameters", "stop_after_sample"],
        ["parameters", "staging_dir"],
        ["parameters", "artifacts_dir"],
        ["parameters", "suppress_runner"],
    ])
    # If this flowgraph has a runner block block, disable it.  We don't want it to run this process
    # recursively when the test gets executed.  This disabling will happen when modifiers are applied.

    return params

READ_NOUTEST_MAP ={
    "nouradio_test_define_test": ReadDefineTest,
    "nouradio_test_run_script" : ReadRunScript,
    "nouradio_test_enable_disable_blocks": ReadEnableDisableBlocks,
    "nouradio_test_variable_change": ReadVariableChange,
    "nouradio_test_screenshot": ReadScreenshot,
    "nouradio_test_run_tests_wrapper": ReadRunTestsWrapper,
}

def GatherTestModifiers(grc:dict, testName:str) -> list:
    """Read the modifier information from a GRC file for later processing.

    Args:
        grc (dict): A dict of the GRC file contents
        testName (str): Check all block test_name_filter params to match this test name

    Returns:
        list: A list of block params from all blocks that are enabled and relevant to the test name.
    """
    # Get all blocks with a test_name_filter
    modifier_name_filters = gru.GetBlockProperty(grc, "id", "^nouradio_test", ["parameters", "test_name_filter"], cull_none=True)
    modifier_name_filters = gru.FixStrings(modifier_name_filters)

    # Then get all enabled blocks
    modifier_states = gru.GetBlockProperty(grc, "id", "^nouradio_test", ["states", "state"], cull_none=True)
    modifier_states = gru.FixStrings(modifier_states)

    relevant_block_names = []

    # Cull all modifiers that are not configured for this test
    for block_name, filter in modifier_name_filters.items():
        m = re.search(filter, testName)
        if not m:
            continue

        # Cull this modifier if the block is disabled
        block_state = modifier_states.get(block_name, None)
        if block_state and block_state == "disabled":
            continue

        relevant_block_names.append(block_name)

    decoded_blocks = []
    for name in relevant_block_names:
        block = list(gru.FilterBlocks(grc, "name", name).values())[0]
        try:
            # Read the block params
            decoded_blocks.append(READ_NOUTEST_MAP[block["id"]](block))
        except Exception as e:
            print(e)
 
    return decoded_blocks

def GenerateModifiedFlowgraphs(grc:dict, modifiers:list) -> dict[str,dict]:
    """Using a set of modifiers gathered by GatherTestModifiers(), apply each modifier to the
    flowgraph and generate a set of modified copies of this flowgraph.

    Args:
        grc (dict): A dict of the GRC file contents
        modifiers (list): The output of GatherTestModifiers()

    Raises:
        ValueError: Raised when multiple variable sweeps are present.  Only one is allowed per test.

    Returns:
        dict[str,dict]: A list of generated test names and the modified flowgraph for each.
    """
    outputs = {}
    if not modifiers:
        return {"":grc}
    grc_copy = copy.deepcopy(grc)
    # Process the things that take effect globally first
    for modifier in modifiers:
        match modifier["type"]:
            case "nouradio_test_enable_disable_blocks":
                for block_name in modifier["enable_blocks"]:
                    grc_copy = gru.SetBlockProperty(grc_copy, "name", block_name, ["states", "state"], "enabled")
                for block_name in modifier["disable_blocks"]:
                    grc_copy = gru.SetBlockProperty(grc_copy, "name", block_name, ["states", "state"], "disabled")
            case "nouradio_test_variable_change":
                if modifier["mode"] == "constant":
                    grc_copy = gru.SetBlockProperty(grc_copy, "name", modifier["variable"], ["parameters", "value"], modifier["value"])
            case "nouradio_test_run_tests_wrapper":
                # Disable the test runner portion to prevent recursion.
                grc_copy = gru.SetBlockProperty(grc_copy, "name", modifier["name"], ["parameters", "suppress_runner"], True)
    # Then the things that require us to fork the files
    for modifier in modifiers:
        match modifier["type"]:
            case "nouradio_test_variable_change":
                if len(outputs) > 1:
                    raise ValueError("Can only split based on one variable change at a time!")
                if modifier["mode"] != "constant":
                    for value in modifier["resolved_choices"]:
                        grc_copy = gru.SetBlockProperty(grc_copy, "name", modifier["variable"], ["parameters", "value"], str(value))
                        name_modifier = f"{modifier['variable']}_{str(value).replace(' ','_')}"
                        outputs[name_modifier] = copy.deepcopy(grc_copy)
    # If there are no outputs, ensure at least one output by adding the original file.
    # If outputs already exist, we only want to run the modified copies; not the original.
    if not outputs:
        outputs[''] = grc_copy

    return outputs

def GenerateTestFlowgraphs(grc: dict, output_folder: str | Path)-> list:
    """Given a GRC file, read all tests definitions from it, then generate modified GRC files
    for each test and, if applicable, for each variable value.

    Args:
        grc (dict): A dict of the GRC file contents
        output_folder (str | Path): A path in which to place the outputs.  If this is a file, its parent will be used.
    
    Returns:
        list[str]: A list of paths to the output files
    """
    def ReplaceBadChars(in_str:str, chars:str|list, replace_with: str = "_") -> str:
        """Replace all characters in a string with another.  The inputs and outputs can also be substrings.
        """
        for char in chars:
            in_str = in_str.replace(char, replace_with)
        return in_str

    prepared_test_paths = []
    output_folder: Path = Path(output_folder)

    if not output_folder.is_dir():
        print(f"Note: Output path {str(output_folder)} is not a folder.  Using its parent...")
        output_folder = output_folder.parent

    print(f"Generating test files at {str(output_folder)}")

    # Generate modified flowgraphs for each test
    for test_name in ReadTestNames(grc):
        print(f"Configuring Test {test_name}")
        modifiers = GatherTestModifiers(grc, test_name)
        test_files = GenerateModifiedFlowgraphs(grc, modifiers)
        for i, (name_modifier, grc_contents) in enumerate(test_files.items()):
            # Using the stringified modifier name, make a unique name for resaving this file
            better_name = f"test_{test_name}_{i}"
            if name_modifier:
                better_name += f"_{name_modifier}"
                
            # This is not exhaustive, but replace common characters that may arise from the test name
            # and modifiers with a safe character for file names like the underscore.
            better_name = ReplaceBadChars(better_name, " \t()[]{}-!@#$%^&*+;'\"?/><,`~.", "_")

            filename = output_folder / f"{better_name}.grc"
            grc_contents = gru.SetGrcID(grc_contents, better_name)
            print(f"   Saving {str(filename.absolute())}")
            gru.Save(filename, grc_contents)
            prepared_test_paths.append(filename)

    return prepared_test_paths

def PrepareTests(grc_path: str | Path, output_path: str) -> list:
    """Convenience wrapper for reading a GRC and running the test generation process

    Args:
        grc_path (str | Path): A path to the GRC file.
        output_path (str): A path to a folder in which to generate the GRC files.

    Returns:
        list[str]: A list of paths to the generated .grc files
    """
    grc = gru.Load(grc_path)
    test_files = GenerateTestFlowgraphs(grc, output_path)
    return test_files

def RunTests(artifacts_dir: str|Path, test_files: list[str]|list[Path] = None, test_dir: str|Path = None):
    """Run a collection of tests.  Each time this is called, a new folder containing the starting timestamp
    will be created within the artifacts_dir directory.  For each test, a new folder will be created within
    this first folder.  The name of each subfolder will indicate the test name and configuration used for
    the test.

    For each test, the corresponding grc file will be copied into a folder matching its name.  The "grcc"
    command will generate the python files required to run this flowgraph.  This will change the working
    directory to this folder and execute the .py flowgraph.  During the run, any stdout, stderr, screenshots
    (from the Test: Screenshot block) and error logs (from the Test: Stream Watch block) will also be written
    to this folder, assuming they are configured to save files in the working directory.  All files needed to
    reproduce this run, assuming the same Python environment, will be in this configuration's artifact folder.
    This process will repeat for each configuration of each test.

    When all tests are concluded, the working directory will be restored to its original folder.
    
    Overall, the artifacts directory will be arranged as follows.
    > test_artifacts
    |-->Run_1_Timestamp
       |-->Test_1_Config_1
          |-->test_1_config_1.grc
          |-->test_1_config_1.py
          |-->stdout.txt
          |-->stderr.txt
          |-->screenshot1.png
          |-->error_log.txt
       |-->Test_1_Config_2
       |-->Test_2_Config_1
       |-->Test_2_Config_2 
    |-->Run_2_Timestamp
       |--> ...

    Args:
        artifacts_dir (str | Path): A path in which to place the artifacts from each test run.
        test_files (list[str] | list[Path], optional): A list of .grc files to run. Defaults to None.
        test_dir (str | Path, optional): A directory containing .grc files to run. They will be copied to folders in the artifacts_dir before executing. Defaults to None.
    """
    # Generate a new folder in the artifacts directory using the timestamp
    now = datetime.now()
    timestamp = now.strftime("%m_%d_%Y__%H_%M_%S")
    artifacts_dir = Path(artifacts_dir) / timestamp
    print(f"Test outputs at {str(artifacts_dir)}")
    os.makedirs(str(artifacts_dir))

    def CopyFiles(files: list, copy_to: str|Path):
        copy_to = Path(copy_to)
        print(f"Copying {len(files)} files...")
        for file in files:
            print(f" > Copying {file}")
            shutil.copy2(str(file), str(copy_to))
    
    def ExecuteAndRecord(test_file: str|Path):
        """Run the Python flowgraph and store its outputs

        Args:
            test_file (str | Path): A python version of a grc file to execute
        """
        test_file = Path(test_file).absolute()

        with gru.ChDirContext(test_file.parent, False):
            # Generate the python versions of these files before executing
            gru.GeneratePythonFiles(test_file.parent)
            
            # Execute the flowgraph and store the results
            print(f"Executing {test_file.name}...", end='')
            with open("stdout.txt", "w") as of:
                with open("stderr.txt", "w") as ef:
                    subprocess.run(["python", str(test_file.name)],
                                    stdout=of,
                                    stderr=ef)
        print("Done")

    def PrepareTestArtifactDir(test: str|Path):
        """Create a new subfolder in this run's folder for a particular test configuration.
        Copy the grc file to that directory.

        Args:
            test (str | Path): The path to a particular test grc file

        Returns:
            Path: The path to the .grc file in its new folder
        """
        test = Path(test)
        
        # Make the directory (and/or clear it)
        new_artifacts_dir = artifacts_dir  / test.stem
        os.makedirs(str(new_artifacts_dir))

        related_files = [test]
        CopyFiles(related_files, new_artifacts_dir)

        return new_artifacts_dir / test.with_suffix(".py").name

    def Go(test: str|Path):
        """Prepare a new artifacts folder for a particular test configuration.
        Copy the generated grc file to this folder and generate the python equivalent files.
        Execute the python files and record stdout and stdin, as well as any run artifacts,
        in the folder.

        Args:
            test (str | Path): A path to a particular grc file
        """
        artifact_test_path = PrepareTestArtifactDir(test)
        ExecuteAndRecord(artifact_test_path)

    # If the user specified a directory instead of a list of files, add those
    # to the list here.  Prefer using test_files instead of test_dir to avoid
    # issues where 
    if test_dir is not None:
        test_dir = Path(test_dir)

        # If the user did not supply a list of files, initialize it here.
        # Otherwise, copy it to minimize the risk of modifying the input.
        if test_files is None:
            test_files = []
        else:
            test_files = copy.deepcopy(test_files)

        # Add all python files in this directory to the list of tests.
        # This may fail because many of them may not be flowgraphs, or
        # they may be embedded block definitions.  This function will
        # perform some checking, but it will not be perfect.  Prefer test_files.
        for test in test_dir.glob("*.py"):
            try:
                gru.Load(test)
                test_files.append(test)
            except:
                # Probably not a generated python file from a GRC.  Don't add it.
                pass

    # Now run all of the tests
    for test in test_files:
        Go(test)


if __name__ == "__main__":
    """A harness for basic testing
    """
    file_name = Path(r"my_test_file.grc")
    output_path = Path(r"my_output_path")
    
    if not output_path.exists():
        os.mkdir(output_path)

    tests = PrepareTests(file_name, output_path)
    RunTests(file_name, output_path, test_files=tests)