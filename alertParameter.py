'''
Created on 06.09.2014

@author: dk
'''
import sys

def logok(msg):
    sys.stderr.write(str(msg) + "\n")
    sys.stderr.flush()


class Parameter():
    '''
    Object holding one parameter 
    class members:
        name:      local name
        fqname:    full qualified name
        signal:    ICD DP name
        datatype:  FLOAT, INTEGER, BOOLEAN
        size:      size in bytes
        offset:    offset in FDAS input buffer
    '''
    COL_PARAMETER  = 0
    COL_EXTERNAL   = 9
    COL_DATATYPE   = 2
    COL_DEFAULTVAL = 3
    COL_STATUS     = 8
    COL_RPNAME     = 10
    COL_SPECIAL    = 13
    COL_SOURCENAME = 14

    normalize_datatype = {
        'integer':  'INT',
        'bitfield': 'INT',
        'boolean':  'BOOL',
        'float':    'FLOAT',
    }

    def __init__(self, row, filename, lineno, sysname):

        def getStrOrZero(val):
            if isinstance(val, basestring): # accepts 'str' or 'unicode', they both have a common type 'basestring'
                # this is a string
                if val.lower() in ('', 'tbc', 'tbd', 'none', 'no', 'n/a'):
                    # value not specified, set to 0
                    val = "0"
            return val

        '''
        Constructor: Build a parameter object from an excel row
        '''
        # name
        self.name       = row[self.COL_PARAMETER].value.encode('utf-8').strip()
        self.fqname     = sysname + '_' + self.name

        # datatype
        try:
            s = row[self.COL_DATATYPE].value.encode('utf-8').strip().lower()
            self.datatype = self.normalize_datatype[s]
        except:
            raise Exception, "Filename %s: Sheet Parameters: Line %d: Bad data type value" % (filename, lineno)

        # default value
        if self.datatype == "FLOAT":
            try:
                val          = getStrOrZero (row[self.COL_DEFAULTVAL].value)
                self.default = str(float(val))
            except:
                raise Exception, "Filename %s: Sheet Parameters: Line %d: Bad default value format" % (filename, lineno)

        elif self.datatype == "INT":
            val = getStrOrZero (row[self.COL_DEFAULTVAL].value)
            if type(val) == type(1.0):
                self.default    = str(int(val))
            else:
                try:
                    sval = val.encode('utf-8').strip().lower()
                    if sval.startswith('0x'):
                        ival = int(sval[2:], 16)
                    elif sval.endswith('b'):
                        ival = int(sval[0:-1], 2)
                    else:
                        ival = int(sval)
                    self.default = str(ival)
                except Exception, msg:
                    raise Exception, "Filename %s: Sheet Parameters: Line %d: Bad default value - %s" \
                        % (filename, lineno, str(msg))

        elif self.datatype == "BOOL":
            val = getStrOrZero (row[self.COL_DEFAULTVAL].value)
            try:
                self.default = str(bool(val))
            except:
                try:
                    ival         = int(val)
                    self.default = str({0:True, 1:False}[ival])
                except:
                    raise Exception, "Filename %s: Sheet Parameters: Line %d: Bad default value format" % (filename, lineno)
        else:
            raise Exception, "Filename %s: Sheet Parameters: Line %d: Bad data type: %s" % (filename, lineno, self.datatype)

        self.offset     = 0
        self.size       = 4
        
    def toXml(self):
        return '''      <parameter name="%(fqname)s" localname="%(name)s"  offset="%(offset)d" size="%(size)d" elements="1" type="%(datatype)s"/>
''' % self.__dict__

    def toXmlStatus(self):
        return '''      <parameter name="%s_Status" localname="%s_Status"  offset="%d" size="4" elements="1" type="INT"/>
''' % (self.fqname, self.name, self.offset + 4)

    def toXmlIntern(self):
        return '''      <parameter name="%(name)s" fqname="%(fqname)s" datatype="%(datatype)s" default="%(default)s" offset="%(offset)d" size="%(size)d"/>
''' % self.__dict__
