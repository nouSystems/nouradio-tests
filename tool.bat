@echo off
setlocal

set SCRIPT_DIR=%0\..
set INSTALL_CACHE_DIR="%SCRIPT_DIR%\install_cache"
set PACKAGE_NAME=nouradio_test

if "%1"=="reset" goto reset
if "%1"=="cmake" goto cmake
if "%1"=="make" goto build
if "%1"=="make-install" goto make-install
if "%1"=="cache-install" goto cache-install
if "%1"=="update-cache" goto update-cache
if "%1"=="uninstall" goto uninstall
goto eof

:reset
    REM Delete any existing build folder 
    SET /P AREYOUSURE=Are you sure (Y/[N])?
    IF /I "%AREYOUSURE%" NEQ "Y" GOTO eof

    REM Delete the build directory
    if exist "%SCRIPT_DIR%\build" (
        cd %SCRIPT_DIR%
        rd /s /q build
    )
    mkdir build
    goto eof

REM Prepare the build directory
:cmake
    cd %SCRIPT_DIR%
    if not exist build (
        echo The build directory does not exist.  Creating it...
        mkdir build
    )
    cd build
    cmake -D CMAKE_INSTALL_PREFIX=%CONDA_PREFIX%  -G "Visual Studio 17 2022" -A x64 ..
    goto eof

REM Build the blocks
:build
    set CONFIGURATION=Release

    REM Check if msbuild is on the path
    where /q msbuild > nul 2>&1
    if %errorlevel% == 0 (
        set MSBUILD_PATH=
        goto msbuild-found
    )

    set MSBUILD_PATH=C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\
    echo msbuild.exe not on the path; checking "%MSBUILD_PATH%msbuild"
    pushd "%MSBUILD_PATH%"
    where /q msbuild > nul 2>&1
    if %errorlevel% == 0 (
        popd
        goto msbuild-found
    )
    popd
    goto msbuild-not-found

:msbuild-found
    echo MSBuild found!
    echo Building %SCRIPT_DIR%\build\gr-%PACKAGE_NAME%.sln ...
    "%MSBUILD_PATH%msbuild" "%SCRIPT_DIR%\build\gr-%PACKAGE_NAME%.sln" /property:Configuration=%CONFIGURATION%
    goto eof

:msbuild-not-found
    echo Cannot build because "msbuild" was not found!  Please add it to the PATH. 
    goto eof

REM Install the files.
:make-install
    REM Install to gnuradio from the build directory
    set COPY_SOURCE_DIR="%SCRIPT_DIR%"
    set COPY_DEST_DIR="%CONDA_PREFIX%"
    set COPY_DEST_LIBRARY_DIR="%CONDA_PREFIX%\Library"
    goto copy-files

:cache-install
    REM Install to gnuradio from the cached repo versions of blocks
    set COPY_SOURCE_DIR="%INSTALL_CACHE_DIR%"
    set COPY_DEST_DIR="%CONDA_PREFIX%"
    set COPY_DEST_LIBRARY_DIR="%CONDA_PREFIX%\Library"
    goto copy-files

REM Update the cached version of the blocks for saving in the repo
:update-cache
    set COPY_SOURCE_DIR="%SCRIPT_DIR%"
    set COPY_DEST_DIR="%INSTALL_CACHE_DIR%"
    set COPY_DEST_LIBRARY_DIR="%INSTALL_CACHE_DIR%"
    goto copy-to-cache


:copy-files
    REM Copy the block files from one place to another
    echo Copying to files to %COPY_DEST_DIR%

    echo Copying Headers...
    xcopy /Y /i "%COPY_SOURCE_DIR%\include\gnuradio\%PACKAGE_NAME%\*.h" "%COPY_DEST_LIBRARY_DIR%\include\gnuradio\%PACKAGE_NAME%\"

    echo Copying Lib...
    xcopy /Y /i "%COPY_SOURCE_DIR%\build\lib\Release\*.lib" "%COPY_DEST_LIBRARY_DIR%\lib\"

    echo Copying DLL...
    xcopy /Y /i "%COPY_SOURCE_DIR%\build\lib\Release\*.dll" "%COPY_DEST_LIBRARY_DIR%\bin\"

    echo Copying CMake Files...
    xcopy /Y /i "%COPY_SOURCE_DIR%\build\lib\cmake\Modules\*.cmake" "%COPY_DEST_LIBRARY_DIR%\lib\cmake\gnuradio\"

    echo Copying Python Files...
    xcopy /Y /i "%COPY_SOURCE_DIR%\python\%PACKAGE_NAME%\__init__.py" "%COPY_DEST_DIR%\Lib\site-packages\gnuradio\%PACKAGE_NAME%\"
    xcopy /Y /i "%COPY_SOURCE_DIR%\build\python\%PACKAGE_NAME%\bindings\Release\%PACKAGE_NAME%_python.cp311-win_amd64.pyd" "%COPY_DEST_DIR%\Lib\site-packages\gnuradio\%PACKAGE_NAME%\"
    REM Now copy all non-qa (unit test) files to the folder
    for /f "tokens=*" %%f in ('dir /b "%COPY_SOURCE_DIR%\python\%PACKAGE_NAME%\*.py" ^| findstr /v /b /c:"qa_"') do (
        echo         %%f
        copy "%COPY_SOURCE_DIR%\python\%PACKAGE_NAME%\%%f" "%COPY_DEST_DIR%\Lib\site-packages\gnuradio\%PACKAGE_NAME%\"
    )

    echo Copying Block YAMLs...
    xcopy /Y /i "%COPY_SOURCE_DIR%\grc\*.yml" "%COPY_DEST_LIBRARY_DIR%\share\gnuradio\grc\blocks\"
    goto eof


:copy-to-cache
    REM Copy the block files from one place to another, preserving the original file structure
    echo Copying to cache to %COPY_DEST_DIR%

    echo Copying Headers...
    xcopy /Y /i "%COPY_SOURCE_DIR%\include\gnuradio\%PACKAGE_NAME%\*.h" "%COPY_DEST_LIBRARY_DIR%\include\gnuradio\%PACKAGE_NAME%\"

    echo Copying Lib...
    xcopy /Y /i "%COPY_SOURCE_DIR%\build\lib\Release\*.lib" "%COPY_DEST_LIBRARY_DIR%\build\lib\Release\"

    echo Copying DLL...
    xcopy /Y /i "%COPY_SOURCE_DIR%\build\lib\Release\*.dll" "%COPY_DEST_LIBRARY_DIR%\build\lib\Release\"

    echo Copying CMake Files...
    xcopy /Y /i "%COPY_SOURCE_DIR%\build\lib\cmake\Modules\*.cmake" "%COPY_DEST_LIBRARY_DIR%\build\lib\cmake\Modules\"

    echo Copying Python Files...
    xcopy /Y /i "%COPY_SOURCE_DIR%\python\%PACKAGE_NAME%\__init__.py" "%COPY_DEST_DIR%\python\%PACKAGE_NAME%\"
    xcopy /Y /i "%COPY_SOURCE_DIR%\build\python\%PACKAGE_NAME%\bindings\Release\%PACKAGE_NAME%_python.cp311-win_amd64.pyd" "%COPY_DEST_DIR%\build\python\%PACKAGE_NAME%\bindings\Release\"
    REM Now copy all non-qa (unit test) files to the folder
	for /f "tokens=*" %%f in ('dir /b "%COPY_SOURCE_DIR%\python\%PACKAGE_NAME%\*.py" ^| findstr /v /b /c:"qa_"') do (
        echo         %%f
        copy "%COPY_SOURCE_DIR%\python\%PACKAGE_NAME%\%%f" "%COPY_DEST_DIR%\python\%PACKAGE_NAME%\"
    )

    echo Copying Block YAMLs...
    xcopy /Y /i "%COPY_SOURCE_DIR%\grc\*.yml" "%COPY_DEST_LIBRARY_DIR%\grc\"
    goto eof

:uninstall
    set COPY_DEST_DIR="%CONDA_PREFIX%"
    set COPY_DEST_LIBRARY_DIR="%CONDA_PREFIX%\Library"
    echo Removing Headers...
    rd /s /q "%COPY_DEST_LIBRARY_DIR%\include\gnuradio\%PACKAGE_NAME%"
    
    echo Removing Lib...
    del "%COPY_DEST_LIBRARY_DIR%\lib\gnuradio-%PACKAGE_NAME%.lib"

    echo Removing DLL...
    del "%COPY_DEST_LIBRARY_DIR%\bin\gnuradio-%PACKAGE_NAME%.dll"

    echo Removing CMake Files...
    del "%COPY_DEST_LIBRARY_DIR%\lib\cmake\gnuradio\gnuradio-%PACKAGE_NAME%Config.cmake"

    echo Removing Python Files...
    rd /s /q "%COPY_DEST_DIR%\Lib\site-packages\gnuradio\%PACKAGE_NAME%"
    
    echo Removing Block YAMLs...
    del "%COPY_DEST_LIBRARY_DIR%\share\gnuradio\grc\blocks\%PACKAGE_NAME%*.yml"
    goto eof

:eof

