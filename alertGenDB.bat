@echo off
if "%*" == ""     ( goto :usage )
if "%1" == "help" ( goto :usage )
if "%1" == "-h" ( goto :usage )
if "%1" == "--help" ( goto :usage )
if "%1" == "/h" ( goto :usage )
if "%1" == "/?" ( goto :usage )
if "%1" == "?" ( goto :usage )
rem -------------------------------------------------------

set endian=--bigendian
set outfn=%1
set infn=%2
set PYLIBDIR=%~d0%~p0../lib/python

if "%1" == "--littleendian" (
   set endian=--littleendian
   set outfn=%2
   set infn=%3
) 

if "%1" == "--bigendian" (
   set endian=--bigendian
   set outfn=%2
   set infn=%3
)


python %PYLIBDIR%\alertGenXML.py %outfn% %infn%
python %PYLIBDIR%\alertGenBin.py %endian%  %outfn%


goto :eof
:usage
echo Generation of FDAS Binary Alert Database
echo Usage: alertGenDB [--bigendian or --littleendian] outpufile inputfiles ...