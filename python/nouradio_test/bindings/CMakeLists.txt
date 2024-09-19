# Copyright 2020 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

########################################################################
# Check if there is C++ code at all
########################################################################
if(NOT nouradio_test_sources)
    message(STATUS "No C++ sources... skipping python bindings")
    return()
endif(NOT nouradio_test_sources)

########################################################################
# Check for pygccxml
########################################################################
gr_python_check_module_raw("pygccxml" "import pygccxml" PYGCCXML_FOUND)

include(GrPybind)

########################################################################
# Python Bindings
########################################################################

list(APPEND nouradio_test_python_files python_bindings.cc)

gr_pybind_make_oot(nouradio_test ../../.. gr::nouradio_test "${nouradio_test_python_files}")

# copy bindings extension for use in QA test module
add_custom_command(
    TARGET nouradio_test_python
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:nouradio_test_python>
            ${PROJECT_BINARY_DIR}/test_modules/gnuradio/nouradio_test/)

install(
    TARGETS nouradio_test_python
    DESTINATION ${GR_PYTHON_DIR}/gnuradio/nouradio_test
    COMPONENT pythonapi)
