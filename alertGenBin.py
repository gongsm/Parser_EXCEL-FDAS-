'''
Created on 18.08.2014

@author: Dieter Konnerth, TechSAT GmbH

Generate binary from XML File.

Structure of the XML File
 <alertdb version="1.0" ICD="BP 4.0.7">
     <alerts>
        <alert id="1" priority="2" aural="chime" message="NOTHING HAPPENING">
            <logicSource>ipA || ipB</logicSource>
            <logic>ipA ipB .bOR</logic>
        </alert>
        <collector id="3" priority="1" aural="yes" message="HAPPENING" >1 2</collector>
        <umbrella id="4">1 2</umbrella>
    </alerts>
    <dataDictionary>
        <param name="ipA" fqname="FCS.ipA_1" signal="HF_LRU.port.message.signal" type="BOOL" offset="0" size=4/>
    </dataDictionary>
 </alertdb >
'''

import struct
import zlib
import sys


from exceptions import Exception
from lxml import etree
import re


ENDIAN     = "@"
prevIndex  = 0          # used for previous values  

import alertConstant

errorCount = 0
def logerr(msg):
    global errorCount 
    errorCount += 1
    sys.stderr.write(str(msg) + "\n")
    sys.stderr.flush()



# -----------------------------------------------------------------------------------
# Global Variables

# dictionary of all alerts, used to avoid duplication ID
alertDict = {}

# Data Dictionary class object, constructed in main
dataDict = {}

# counter for time delay objects
tdCounter = 0

# Utilities

class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

def getint(s):
    if s.startswith("0x"):
        return int(s[2:], 16)
    elif s.endswith("b") or s.endswith("B"):
        return int(s.strip('bB'), 2)
    else:
        return int(s)

def str2bool(s):
    return s.lower() in ("true", "True", "TRUE")
        
        
# Build functions: convert the XML tag into corresponding binary structure
# side effect: build up string table and message dictionary + message offset

# -----------------------------------------------------------------------------------------------------------
def getIntAttrib(x, key):
    '''
    Get an integer attribute from an XML tag
    Parameters:
        x: XML node
        key: attribute name
    Returns:
        value as integer
    Exceptions:
        Exception when attribute not found or on correct integer
    '''
    if x.attrib.has_key(key):
        try:
            val = int(x.attrib[key])
        except:
            raise Exception, "Bad integer attribute %s in alert definition: %s" % (key, x.attrib[key])
    else:
        raise Exception, "No attribute %s in alert definition" % key
    return val

def getCodedAttrib(x, key, valuemap):
    '''
    Get an string attribute from an XML tag and translate it into an integer value through a mapping dictionary
    Parameters:
        x: XML node
        key: attribute name
        map: dictionary with stringvalue : (integerValue, Description)
    Returns:
        value as integer
    Exceptions:
        Exception when attribute not found, not a string or not a key to the map
    '''
    if x.attrib.has_key(key):
        sval = x.attrib[key]
        try:
            ival = valuemap.encode[sval]
        except:
            raise Exception, "Bad attribute %s in alert definition: %s" % (key, x.attrib[key])
    else:
        raise Exception, "No attribute % in alert definition" % key
    return ival

def getCodedFlagsAttrib(x, key, valuemap):
    '''
    Get an string attribute from an XML tag and translate it into an bitfield value through a mapping dictionary
    Parameters:
        x: XML node
        key: attribute name
        map: dictionary with stringvalue : (integerValue, Description)
    Returns:
        value as integer
    Exceptions:
        Exception when attribute not found, not a string or not a key to the map
    '''
    result = 0
    
    if not key in x.attrib:
        raise Exception, "No attribute % in alert definition" % key
        
    val = x.attrib[key]
    for s in val.split():
        try:
            i = valuemap.inhibitBit[s]
        except:
            raise Exception, "Bad attribute %s in alert definition: %s" % (key, x.attrib[key])
        result |= 1 << i

    return result


# -----------------------------------------------------------------------------------------------------------
def getStrAttrib(x, key):
    '''
    Get a string attribute from an XML tag
    Parameters:
        x: XML node
        key: attribute name
    Returns:
        value as string
    Exceptions:
        Exception when attribute not found 
    '''
    if x.attrib.has_key(key):
        val = x.attrib[key]
    else:
        raise Exception, "No alert % in alert definition" % key
    return val
    

def  convId(id):
    if id.lower() in ('', 'tbd', 'none', 'no', 'n/a'):
        id = 0
    else:
        id = int(id)
    return id
    
# -----------------------------------------------------------------------------------------------------------
def buildAlertHeader(xmlalert, startops, numops):
    '''
    Build alert header from the alert xml tag
    Parameters:
        xmlalert: xml root node of alert tag
        startops: offset into operations buffer where the ops of this alert start
        numops: number of operations for this alert
    returns:
        packed alert structure buffer
    Exceptions:
        Exception when any mandatory attribute are missing or of wrong syntax
    '''

    global alertDict

    try:
        alertId  = getIntAttrib(xmlalert, "alertId")
    except Exception, msg:
        logerr("Error in parsing Alert ID: %s" %(alertId, str(msg)))

    try:
        alertMsg  = getStrAttrib(xmlalert, "message")
        cpaLampId = getStrAttrib(xmlalert, "cpaLampId")
        auralId   = getStrAttrib(xmlalert, "auralMessageId")

        # Convert string list to array of 4, calling function convLampId to convert each element
        lampId = map(convId, cpaLampId.split('+'))
        for i in range (0,4-len(lampId)):
            lampId.append(0)  # if list is less than 4, append zeros to pad it to 4

        # Convert string list to array of 2, calling function convId to convert each element
        audioId = map(convId, auralId.split('+'))
        for i in range (0,2-len(audioId)):
            audioId.append(0)  # if list is less than 2, append zeros to pad it to 2

        alert = struct.pack(ENDIAN + "iiiiii32sibbbbiiiiiiiiiiii", 
                        alertId,
                        getCodedAttrib(xmlalert, "alertType", alertConstant.AlertTypes), 
                        getCodedAttrib(xmlalert, "alertClass", alertConstant.AlertClasses), 
                        0,                                               # alertPrio TBD
                        getCodedFlagsAttrib(xmlalert, "flightPhaseInhibit", alertConstant.FlightPhases),
                        len(alertMsg),
                        alertMsg,
                        getCodedAttrib(xmlalert, "otherDisplayEffect", alertConstant.OtherDisplayEffects),
                        0,                                               # isTCASalert,
                        0,                                               # padding
                        0,                                               # padding
                        0,                                               # padding
                        getCodedAttrib(xmlalert, "auralMessageClass", alertConstant.AuralAlertClass),
                        getCodedAttrib(xmlalert, "synopticPage", alertConstant.SynopticPages),
                        0,                                               # riuMsgMapping
                        audioId[0],                                      # audioFileId1
                        audioId[1],                                      # audioFileId2
                        getIntAttrib(xmlalert, "auralMessagePriority"),  # audioFilePriority
                        lampId[0],                                       # CPALampId1
                        lampId[1],                                       # CPALampId2
                        lampId[2],                                       # CPALampId3
                        lampId[3],                                       # CPALampId4
                        numops,
                        startops)
    except Exception, msg:
        logerr("Alert ID %d: %s" %(alertId, str(msg)))
    
    if alertId in alertDict:
        logerr("Duplicate Alert ID %d" % alertId)
        return None

    alertDict[alertId] = alert
    return alert

# -----------------------------------------------------------------------------------------------------------
# Globals for operation gathering

numOperations = 0       # number of captured operations
operations = ""         # Buffer for captuing operations

# -----------------------------------------------------------------------------------------------------------
def buildExpression(s):
    '''
    build binary expression postfix expression from string or space separated tokens
    Parameters:
        s: string containing the postfix expression
    Returns:
        number of operations and packed buffer with operations
    Sideeffect:
        increment global delay object counter.
        
    variable: Identifier, case sensitive
    float constant: x.y
    int constant: decimal number, hex number (0x...) or binary number (01010b)
    boolean constant: .true, .false
    opcodes: 
        .and .or .not 
        .fadd, .fsub, .fmul, .fdiv, .fgt, .flt, .fge, .fle, .feq, .fne
        .iadd, .isub, .imul, .idiv, .igt, .ilt, .ige, .ile, .ieq, .ine
        .td(integer)
        .active(integer)
    opcodes and boolean constants are case insensitive
    '''
    global tdCounter
    global prevIndex

    tokens = s.strip().split()
    expression = ""
    numops = 0
    
    for token in tokens:
        if token[0] == '.':
            if token.startswith(".td"):
                try:
                    delay = int(re.split("[()]",token)[1])
                except:
                    raise Exception, "Bad parameter to Time Delay operation: %s" % token
                if (delay >= 0):
                    op = struct.pack(ENDIAN + "iihh", delay, tdCounter, alertConstant.OPCODES['.tdr'], 0)  # Delay rising edge
                else:
                    op = struct.pack(ENDIAN + "iihh", -delay, tdCounter, alertConstant.OPCODES['.tdf'], 0)  # Delay falling edge
                tdCounter += 1
            elif token.startswith(".active"):
                try:
                    numparam = int(re.split("[()]",token)[1])
                except:
                    raise Exception, "Bad parameter to Active operation: %s" % token
                op = struct.pack(ENDIAN + "iihh", numparam, 0, alertConstant.OPCODES['.active'], 0)
            elif token in ('.true', '.false'):
                op = struct.pack(ENDIAN + "iihh", alertConstant.BOOLCONST[token], -1, alertConstant.OPCODE_CONST, 0)
            elif token.startswith('.valid') or token.startswith('.invalid'):
                try:
                    l = re.split("[()]",token)
                    opcode    = l[0]
                    paramname = l[1]
                except:
                    raise Exception, "Bad parameter to VALID/INVALID/PREV operation: %s" % token
                param = dataDict.get(paramname)
                if not param:
                    raise Exception, "Unknown parameter in VALID/INVALID/PREV expression: %s" % paramname
                op = struct.pack(ENDIAN + "iihh", 0, param.offset + 4, alertConstant.OPCODES[opcode], 0)
            elif token.startswith('.prev'):
                if not alertConstant.OPCODES.has_key(token):
                    raise Exception, "Bad opcode: %s" % token
                op = struct.pack(ENDIAN + "iihh", 0, prevIndex, alertConstant.OPCODES[token], 0)
                prevIndex += 1
            else:
                if not alertConstant.OPCODES.has_key(token):
                    raise Exception, "Bad opcode: %s" % token
                op = struct.pack(ENDIAN + "iihh", 0, -1, alertConstant.OPCODES[token], 0)
        else:
            if token[0].isdigit():
                # if there is a decimal point, it is a float, otherwise its an hex or decimal int
                try:
                    if token.find('.') != -1:
                        value = float(token)
                        op = struct.pack(ENDIAN + "fihh", value, -1, alertConstant.OPCODE_CONST, 0)
                    else:
                        value = getint(token)
                        op = struct.pack(ENDIAN + "iihh", value, -1, alertConstant.OPCODE_CONST, 0)
                except:
                    raise Exception, "Bad numeric constant in expression: %s" % token
            else:
                # it must be the name of a parameter
                param = dataDict.get(token)
                if not param:
                    raise Exception, "Unknown parameter in expression"
                op = struct.pack(ENDIAN + "iihh", 0, param.offset, alertConstant.OPCODE_PARAM, 0)
        
        expression += op
        numops += 1
    
    return numops, expression

    
# -----------------------------------------------------------------------------------------------------------
def buildAlert(xmlalert):
    '''
    Build one alert structure with its expression
    Parameters:
        xmlalert: root node of alert tag
    Returns:
        packed buffer with alert header
    Sideeffect:
        Appends operations to global operations buffer and increments global operations counter
    '''
    
    xmllogic = xmlalert.find("logic")
    if xmllogic is None:
        raise Exception, "No logic expression for alert"
    
    numops, ops = buildExpression(xmllogic.text)
    
    # append operations to global list
    global numOperations
    global operations
    
    # Startops is an offset. Each operation uses 12 bytes
    startops      = firstoperator_offset + (numOperations * 12)
    operations    += ops
    numOperations += numops
    return buildAlertHeader(xmlalert, startops, numops)

# -----------------------------------------------------------------------------------------------------------
def buildCollectors(xmlnode):
    '''
    Builds the list of pairs representing the collector relations
    Parameters:
        xmlnode: root of an collector tag
    Returns:
        Packed buffer with collector relations

    XML tag contains an id attribute which is the ID of the collector
    The XML value contains a list of integers representing the IDs of the alerts under the collector.
    '''
    collectorBuf = ""
    
    try:
        collectorId = int(xmlnode.attrib["id"])
    except:
        logerr("Bad collector ID: %s" % xmlnode.attrib["id"])
        return collectorBuf
    
    if not alertDict.has_key(collectorId):
        logerr("Collector %d: Unknown ID" % collectorId)
        return collectorBuf
        
    alertList = re.split("[     \n]*", xmlnode.text.strip())
    for a in alertList:
        try:
            alertId = int(a)
        except:
            logerr("Bad alert number syntax in collector list :%s" % a)
            continue

        if not alertDict.has_key(alertId):
            logerr("Collector %d: Unknown alert ID in collector list:%d" % (collectorId, alertId))
            continue
    
        collectorBuf += struct.pack(ENDIAN + "hh", collectorId, alertId)

    return collectorBuf
# -----------------------------------------------------------------------------------------------------------
def buildUmbrella(xmlnode):
    '''
    Builds the list of pairs representing the umbrella relations
    Parameters:
        xmlnode: root of an umbrella tag
    Returns:
        Packed buffer with umbrella relations

    XML tag contains an id attribute which is the ID of the umbrella
    The XML value contains a list of integers representing the IDs of the alerts under the umbrella.
    '''
    
    umbrellaBuf = ""

    try:
        umbrellaId = int(xmlnode.attrib["id"])
    except:
        logerr("Bad umbrella ID syntax:%s" % xmlnode.attrib["id"])
        return umbrellaBuf
    
    if not alertDict.has_key(umbrellaId):
        logerr("Unknown alert as umbrella ID:%d" % umbrellaId)
        return umbrellaBuf
        
    alertList = re.split("[     \n]*", xmlnode.text.strip())
    for a in alertList:
        try:
            alertId = int(a)
        except:
            logerr("Umbrella %d: Bad alert number syntax in umbrella list :%s" % (umbrellaId, a))
            continue

        if not alertDict.has_key(alertId):
            logerr("Umbrella %d: Unknown alert ID in umbrella list:%d" % (umbrellaId, alertId))
            continue
    
        umbrellaBuf += struct.pack(ENDIAN + "hh", umbrellaId, alertId)

    return umbrellaBuf

# -----------------------------------------------------------------------------------------------------------
def buildAlertDB(xmlroot):
    '''
    Build complete Alert DB structure from XML
    Parameters:
        xmlroot: XML Root of Xml File
    returns:
        Complete binary object as string
    '''
    alerts      = ""
    numAlerts   = 0
    umbrellas   = ""
    collectors  = ""
    
    global stringtable_offset
    global stringtable_buffer

    global paramdefaults
    global numParamdefaults
    
    global firstoperator_offset

    # set the header size
    headerSize = 4 * 14
    
    # count the number of alerts 
    for x in xmlroot.iterfind("alert"):
        numAlerts += 1
    
    # set the offset of the first operator
    # Note: each Alert Config table has 28 * 4 bytes
    firstoperator_offset = headerSize + numAlerts * 28 * 4
    
    # build alert table
    for x in xmlroot.iterfind("alert"):
        alerts += buildAlert(x)
        
    # append collector table
    for x in xmlroot.iterfind("collector"):
        collectors += buildCollectors(x)
    numCollectors = len(collectors) / 4       # 2 short integers per umbrella entry
    

    # build umbrella table
    for x in xmlroot.iterfind("umbrella"):
        umbrellas += buildUmbrella(x)
    numUmbrellas = len(umbrellas) / 4       # 2 short integers per umbrella entry
    
    # build param table

    # Build Header
    
    # structure of config file:
    #    Header
    #    AlertHeader x numAlerts
    #    Operation x numOperations
    #    Collector x numCollectors
    #    Umbrellas x numUmbrellas
    #    ParamEntries x numParamEntries
    #    CRC

    alertStart      = headerSize
    operationsStart = firstoperator_offset
    collectorStart  = operationsStart   + len(operations)  
    umbrellaStart   = collectorStart    + len(collectors)
    parameterStart  = umbrellaStart     + len(umbrellas)
    totalsize       = parameterStart    + len(paramdefaults) + 4
    alertInParamBaseAddress = 4096
    
    
    hdr = struct.pack(ENDIAN + "Iiiiiiiiiiiiii", 
                      alertConstant.ALERTDB_MAGIC_NUMBER,
                      totalsize, 
                      numAlerts, 
                      numOperations,
                      numCollectors,
                      numUmbrellas, 
                      numParamdefaults,
                      alertStart,
                      operationsStart,
                      collectorStart, 
                      umbrellaStart, 
                      parameterStart, 
                      tdCounter,
                      alertInParamBaseAddress)
    
    output = hdr + alerts + operations + collectors + umbrellas + paramdefaults
    crc = zlib.crc32(output) & 0xffffffff
    output += struct.pack(ENDIAN + "I", crc)

    return output

# -----------------------------------------------------------------------------------------------------------


paramdefaults = ''
numParamdefaults = 0

def parseDD(xmldd):
    ''' 
    parse data dictionary contained in the XML file and create a dictionary of parameter objects
    Parameters: 
        xmldd: root node for data dictionary
    Returns: 
        data dictionary as Python dictionary
    '''

    global paramdefaults 
    global numParamdefaults

    ddd = {}
    paramList = []
    numparams = 0

    for x in xmldd.iterfind("parameter"):
        name = x.attrib['fqname']
        if ddd.has_key(name):
            raise Exception, "Multiple definition of parameter %s" % name

        datatype   = x.attrib['datatype']
        offset     = int(x.attrib['offset'])
        size       = int(x.attrib['size'])
        defaultstr = x.attrib['default']

        if datatype == 'FLOAT':
            try:
                defaultval = float(x.attrib['default'])
            except:
                raise Exception, "Bad FLOAT default value: %s" % defaultstr
        elif datatype == 'INT':
            try:
                defaultval = int(x.attrib['default'])
            except:
                raise Exception, "Bad INT default value: %s" % defaultstr
        elif datatype == 'BOOL':
            try:
                defaultval = str2bool(x.attrib['default'])
            except:
                raise Exception, "Bad BOOL default value: %s" % defaultstr
        else:
            raise Exception, "Illegal data type in data dictionary: %s" % datatype
        
        # and create dictionary with all data for lookup
        ddd[name] = Bunch(
            name     = name,
            offset   = offset,
            size     = size,
            type     = datatype,
            default  = defaultval,
        )
        # append name to name list, so we can use the same order below
        paramList.append(name)
        numparams += 1
        

    for name in paramList:
        param = ddd[name]

        # create copy table for default values
        if param.type == 'FLOAT':
            paramdefaults += struct.pack(ENDIAN + 'if', param.offset, param.default)
        else:
            paramdefaults += struct.pack(ENDIAN + 'ii', param.offset, param.default)

        numParamdefaults += 1

    return ddd

# -----------------------------------------------------------------------------------------------------------
def bin2hex(s):
    output = "unsigned char fdasAlertConfig[] =\n{\n  "
    n = 0
    output += " /* 0x%04x */ " % n
    for c in s[0:-1]:
        output += "0x%02x, " % ord(c)
        n += 1
        if n % 16 == 0:
            output += "\n  "
            output += " /* 0x%04x */ " % n
    output += "0x%02x" % ord(s[-1])
    output += "\n};\n"
    return output
# -----------------------------------------------------------------------------------------------------------
def main(args):
    '''
    Open XML input file, parse it and build binary structure from it.
    Write binary structure to file
    '''
    global ENDIAN
    global dataDict
    global prevIndex

    prevIndex  = 0 # used for previous values  

    if args[0] == "--bigendian":
        ENDIAN=">"
        args = args[1:]
    elif args[0] == "--littleendian":
        ENDIAN="<"
        args = args[1:]

    input_filename  = args[0]
    if not input_filename.endswith('.xml'):
        input_filename += '.xml'
    if len(args) > 1:
        output_filename = args[1]
    else:
        output_filename = input_filename.rsplit('.', 1)[0] + '.bin'

    xmltree = etree.parse(input_filename)
    root = xmltree.getroot()
    
    dataDict = parseDD(root.find("parameters"))
    
    output = buildAlertDB(root.find("alerts"))

    open(output_filename, "wb").write(output)

    # convert also to c
    output_filename = output_filename.rsplit('.', 1)[0] + ".c"
    open(output_filename, "w").write(bin2hex(output))

    return 0

if __name__ == '__main__':
    args = sys.argv[1:]
    sys.exit(main(args))
