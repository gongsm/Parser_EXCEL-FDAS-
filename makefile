ifdef INTEGRATION_HOME
include $(INTEGRATION_HOME)/BuildCommon/globals.cfg
else
TS_TOOL_ROOT	= C:/TechSAT
CP 				= cp
MKDIR 			= mkdir
endif

PYFILES=alertRecord.py \
		alertConstant.py \
		alertDB.py \
		alertGenBin.py \
		alertGenXML.py \
		alertExpression.py \
		alertParameter.py \
		toposort.py

SCRIPTS	= alertGenDB.bat
BINDIR	= $(TS_TOOL_ROOT)/IOMGEN/bin
PYDIR	= $(TS_TOOL_ROOT)/IOMGEN/lib/python

all: install

install: $(BINDIR) $(PYDIR)
	$(CP) -f $(PYFILES) $(PYDIR)
	$(CP) -f $(SCRIPTS) $(BINDIR)
	
	
$(PYDIR):
	$(MKDIR) -p $(PYDIR)

$(BINDIR):
	$(MKDIR) -p $(BINDIR)

generateCode:
generateConfig:
build: