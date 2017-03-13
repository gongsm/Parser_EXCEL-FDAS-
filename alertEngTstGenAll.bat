@echo off
if "%*" == ""     ( goto :usage )
if "%1" == "help" ( goto :usage )
if "%1" == "-h" ( goto :usage )
if "%1" == "--help" ( goto :usage )
if "%1" == "/h" ( goto :usage )
if "%1" == "/?" ( goto :usage )
if "%1" == "?" ( goto :usage )
rem -------------------------------------------------------

set endian=--littleendian
set outfn=alertDB
set infn=%1
set PYLIBDIR=%~d0%~p0../lib/python

python %PYLIBDIR%\alertGenXML.py alertDB %infn%
python %PYLIBDIR%\alertGenBin.py %endian%  alertDB
python %PYLIBDIR%\iomGenDDCode.py alertEngineDDStruct alertDB.inddmap.xml


goto :eof
:usage
echo Generation of FDAS Binary Alert DB and DD C Structure for Alert Engine Testing
echo Usage: alertGenDB outpufile inputfile ...
echo Example: alertGenDB ATA73_FADEC_Alert.xlsx