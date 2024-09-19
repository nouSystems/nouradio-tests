find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_NOURADIO_TEST gnuradio-nouradio_test)

FIND_PATH(
    GR_NOURADIO_TEST_INCLUDE_DIRS
    NAMES gnuradio/nouradio_test/api.h
    HINTS $ENV{NOURADIO_TEST_DIR}/include
        ${PC_NOURADIO_TEST_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_NOURADIO_TEST_LIBRARIES
    NAMES gnuradio-nouradio_test
    HINTS $ENV{NOURADIO_TEST_DIR}/lib
        ${PC_NOURADIO_TEST_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-nouradio_testTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_NOURADIO_TEST DEFAULT_MSG GR_NOURADIO_TEST_LIBRARIES GR_NOURADIO_TEST_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_NOURADIO_TEST_LIBRARIES GR_NOURADIO_TEST_INCLUDE_DIRS)
