'''
Created on 06.09.2014

@author: dk
'''

import alertConstant 

blank = ' '

def _xmlEscape(str):
    outlist = [] 
    for c in str:
        if c == '"':
            outlist.append('&quot;')
        elif c == "'":
            outlist.append('&apos;')
        elif c == "&":
            outlist.append('&amp;')
        elif c == "<":
            outlist.append('&lt;')
        elif c == ">":
            outlist.append('&gt;')
        else:
            outlist.append(c)

    return ''.join(outlist)

class Alert():
    '''
    One Alert object as read from the Excel File

    Class Members
    --------------
    isCollector     
    refNum      
    alertId            
    alertMsg           
    description        
    synopticPage    
    cpaEffect          
    umbrellaMsgs 
    umbrellaIds       
    collectorMsg 
    collectorId        
    alertType
    ALERT 
        logicSrc           
        logicComment       
        logicCompiled      
    COLLECTOR
        collectedMsgs 
        collectedMinimum
        collectedIds  

    alertClass         
    auralMessage      
    flightPhaseInhibit 
    pilotAction        
    actionTime         
    addComment         

    '''
    # column numbers in XLS File
    # Identification
    COL_REFNUM          = 0
    COL_ALERTID         = 1
    # Messaging           
    COL_ALERTMSG        = 2
    COL_DESCRIPTION     = 3
    COL_ALERTTYPE       = 4
    COL_DISPLAYALLOC    = 5
    COL_SYNPAGE         = 6
    COL_OTHERDISPLAY    = 7
    COL_CPAEFFECT       = 8
    COL_CPALAMPID       = 9
    COL_AURALALERTMSG   = 10
    COL_AURALALERTID    = 11
    COL_AURALALERTPRIO  = 12
    COL_AURALALERTCLASS = 13
    # Logic               
    COL_LOGIC           = 14
    # Priority/Inhibition 
    COL_ALERTCLASS      = 15
    COL_FLTPHASEINHIBIT = 16
    COL_UMBRELLAS       = 17
    COL_COLLECTOR       = 18
    # Comments            
    COL_PILOTACTION     = 19
    COL_ACTIONTIME      = 20
    COL_ADDCOMMENT      = 21
    COL_STATUS          = 22
    
    
    def __init__(self, row, filename, sheet, rownum, sysName):
        '''
        Constructor
        Parameters:
            row: Excel row to build object from
            filename, sheet and rownum: string to build error message
            isCollector: Flag is Alert is Collector Alert
        Returns:
            None
        '''
        
        def getIntOrNone(colno, errmsg):
            val = row[colno].value
            try:
                res = int(val)
            except:
                sval = val.encode('utf-8').strip()
                if sval.lower() in ("tbd", "none" , "no", "n/a", ""):
                    res = None
                else:
                    raise Exception, "File %s: Sheet %s: Line %d: %s" % \
                        (filename, sheet, rownum, errmsg)
            return res

        def getIntOrZero(colno, errmsg):
            val = row[colno].value
            try:
                res = int(val)
            except:
                sval = val.encode('utf-8').strip()
                if sval.lower() in ("tbd", "none" , "no", "n/a", ""):
                    res = 0
                else:
                    raise Exception, "File %s: Sheet %s: Line %d: %s" % \
                        (filename, sheet, rownum, errmsg)
            return res

        def getEnum(colno, map, errmsg):
            try:
                sval = row[colno].value.encode('utf-8').strip().lower()
                #svalSplit = sval.split()
                #if len(svalSplit) > 1:
                    # Only one allowed, use first, remove others
                sval = sval.replace(' ','')
            except Exception as e:
                raise Exception, "File %s: Sheet %s: Line %d: %s - %s" % (filename, sheet, rownum, errmsg, str(e))

            res = map.normalize.get(sval)
            if not res: 
                raise Exception, "File %s: Sheet %s: Line %d: %s - illegal value" % (filename, sheet, rownum, errmsg)
            
            return res

        def getEnumList(colno, map, errmsg):
            try:
                sval = row[colno].value.encode('utf-8').strip().lower()
                if sval in ("tbd", "none" , "no", "n/a", ""):
                    return []
            except Exception as e:
                raise Exception, "File %s: Sheet %s: Line %d: %s - %s" % (filename, sheet, rownum, errmsg, str(e))

            res = []
            try:
                for m in sval.split(','):
                    norm = map.normalize.get(m.strip())
                    if norm:
                        res.append(norm)
            except:
                raise Exception, "File %s: Sheet %s: Line %d: %s - illegal value" % (filename, sheet, rownum, errmsg)
            return res

        def getStrList(colno, errmsg):
            try:
                sval = row[colno].value.encode('utf-8').strip()
                if sval.lower() in ("tbd", "none" , "no", "n/a", ""):
                    return []

            except Exception as e:
                raise Exception, "File %s: Sheet %s: Line %d: %s - %s" % (filename, sheet, rownum, errmsg, str(e))

            return [m.strip() for m in sval.split(',')]

        def getStrOrZero(colno, errmsg):
            try:
                res = row[colno].value.encode('utf-8').strip()
                res = res.replace('"', "'")
                if res.lower() in ("tbd", "none" , "no", "n/a", ""):
                    res = "0"
            except Exception as e:
                raise Exception, "File %s: Sheet %s: Line %d: %s - %s" % (filename, sheet, rownum, errmsg, str(e))

            return res

        def getStr(colno, errmsg):
            try:
                res = row[colno].value.encode('utf-8').strip()
                res = res.replace('"', "'")
            except Exception as e:
                raise Exception, "File %s: Sheet %s: Line %d: %s - %s" % (filename, sheet, rownum, errmsg, str(e))
            
            return res

        def getInt(colno, range, errmsg):
            val = row[colno].value
            try:
                res = int(val)
            except Exception as e:
                raise Exception, "File %s: Sheet %s: Line %d: %s - %s" % (filename, sheet, rownum, errmsg, str(e))
            
            if range is not None and res not in range:
                raise Exception, "File %s: Sheet %s: Line %d: %s: Out of range" % (filename, sheet, rownum, errmsg)

            return res
            
        
        # ----------------------------------------------------------------------------------------
        self.skip               = False     # set to true when we find an error in postprocessing
        self.filename           = filename
        self.rownum             = rownum
        self.sysName            = sysName
        self.dependson          = set()
        
        # fetch and validate refNum
        self.refNum             = getStr(Alert.COL_REFNUM, "Bad Alert RefNumber")

        # fetch and validate AlertId (uniqueness not validated here)
        self.alertId            = getInt(Alert.COL_ALERTID, range(1, alertConstant.MAX_ALERT_ID + 1), "Bad Alert ID")
    
        # fetch and validate alert Message
        self.alertMsg           = getStr(Alert.COL_ALERTMSG, "Bad Alert Message")

        # fetch and validate description
        self.description        = getStr(Alert.COL_DESCRIPTION, "Bad Alert Description")

        # fetch and validate alert type (TC, CAS, CPA)
        self.alertType          = getEnum(Alert.COL_ALERTTYPE, alertConstant.AlertTypes, "Invalid Alert Type Code")

        # fetch and validate display allocation
        self.displayAlloc       = getStr(Alert.COL_DISPLAYALLOC, "Bad Display Allocation String")

        # fetch and validate synoptic page code
        self.synopticPage       = getEnum(Alert.COL_SYNPAGE, alertConstant.SynopticPages, "Invalid Synoptic Page Code")

        # fetch and validate other display effect
        self.otherDisplayEffect = getEnum(Alert.COL_OTHERDISPLAY, alertConstant.OtherDisplayEffects, "Invalid Other Display Effect Code")
            
        # fetch and validate control panel annunciator effect
        self.cpaEffect          = getStr(Alert.COL_CPAEFFECT, "Invalid CPA Effect Code")

        # fetch and validate control panel annunciator lamp ID
        try:
            self.cpaLampId          = getStrOrZero(Alert.COL_CPALAMPID, "Invalid CPA Lamp ID")   # NB: there can be a list of 1 to 4 LAMP ID's, separated by comma
        except:
            self.cpaLampId          = getIntOrZero(Alert.COL_CPALAMPID, "Invalid CPA Lamp ID")

        # fetch and validate aural alert tone / message
        self.auralMessage       = getStr(Alert.COL_AURALALERTMSG, "Invalid Aural Message")

        # fetch and validate aural alert ID
        try:
            self.auralMessageId     = getStrOrZero(Alert.COL_AURALALERTID, "Invalid Aural Message ID")
        except:
            self.auralMessageId     = getIntOrZero(Alert.COL_AURALALERTID, "Invalid Aural Message ID")

        # fetch and validate aural alert ID
        self.auralMessagePriority = getIntOrZero(Alert.COL_AURALALERTPRIO, "Invalid Aural Message Priority")

        # fetch and validate aural alert ID
        self.auralMessageClass  = getEnum(Alert.COL_AURALALERTCLASS, alertConstant.AuralAlertClass, "Invalid Aural Message Class")

        self.logicSrc           = getStr(Alert.COL_LOGIC, "Invalid Logic String")
        self.logicCompiled      = []    # computed later

        # fetch and validate alert class (Warning / Caution / Advisory / Status)
        self.alertClass         = getEnum(Alert.COL_ALERTCLASS, alertConstant.AlertClasses, "Invalid Alert Class Code")

        # fetch and validate flight phase inhibits
        l = getEnumList(Alert.COL_FLTPHASEINHIBIT, alertConstant.FlightPhases, "Invalid Flight Phase Code")
        # turn into blank separated string
        self.flightPhaseInhibit = blank.join(l)

        # fetch associated umbrella messages
        # validated later when IDs are computed
        self.umbrellaMsgs       = getStrList(Alert.COL_UMBRELLAS, "Invalid Umbrella Message List")

        # computed later, when all alerts and umbrellas are parsed
        self.umbrellaIds        = []    

        # fetch associated collector message, if any
        # validate and translated to ID later
        self.collectorMsgs      = getStrList(Alert.COL_COLLECTOR, "Invalid Collector List")

        # computed later
        self.collectorIds       = []

        self.pilotAction        = getStr(Alert.COL_PILOTACTION, "Illegal value for Pilot Action")
        self.actionTime         = getStr(Alert.COL_ACTIONTIME, "Illegal value for Pilot Action Time")
        self.addComment         = getStr(Alert.COL_ADDCOMMENT, "Illegal value for comment")
        
                
            

    def toXml(self):
        params1 = 'alertId="%(alertId)d" '                     \
            'sourceId="%(refNum)s" '                           \
            'message="%(alertMsg)s" '                          \
            'alertType="%(alertType)s" '                       \
            'displayAlloc="%(displayAlloc)s" '                 \
            'synopticPage="%(synopticPage)s" '                 \
            'otherDisplayEffect="%(otherDisplayEffect)s" '     \
            'cpaEffect="%(cpaEffect)s" '                       \
            'cpaLampId="%(cpaLampId)s" '                       \
            'auralMessage="%(auralMessage)s" '                 \
            'auralMessageId="%(auralMessageId)s" '             \
            'auralMessagePriority="%(auralMessagePriority)d" ' \
            'auralMessageClass="%(auralMessageClass)s" '       \
            'alertClass="%(alertClass)s" '                     \
            'flightPhaseInhibit="%(flightPhaseInhibit)s" '     \
            'filename="%(filename)s" rownum="%(rownum)s"'      \
             % self.__dict__
        
        params2 = 'umbrellaIds="%s"' % blank.join(str(x) for x in self.umbrellaIds)
        params3 = 'collectorIds="%s"' % blank.join(str(x) for x in self.collectorIds)
            
        return '''        <alert %s %s %s>
            <logicsource>
                %s
            </logicsource>
            <logic>
                %s
            </logic>
        </alert>\n''' % (params1, params2, params3, 
                         _xmlEscape(self.logicSrc), 
                         blank.join(str(t) for t in self.logicCompiled))

