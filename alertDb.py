'''
Created on 06.09.2014

@author: dk
'''

import sys
import xlrd
from collections        import defaultdict
from bunch              import Bunch

from alertParameter     import Parameter
from alertRecord        import Alert
from alertExpression    import compileToPostfix
from toposort           import topological_sort
from alertConstant      import ALERT_PARAMETER_BASE_ADDRESS


errorCount = 0
def logerr(msg):
    global errorCount 
    errorCount += 1
    sys.stderr.write(str(msg) + "\n")
    sys.stderr.flush()

def logok(msg):
    sys.stderr.write(str(msg) + "\n")
    sys.stderr.flush()
        
class AlertDb(object):
    '''
    Alert Data Base
    Gathers all info about the FDAS Alerts in a Python Data Model
    ELements:
        alerts: Dictionary of alerts, indexed by Id
        alertsMsgToId: Translation Table from Alert Message to Alert ID
        parameters: Dictionary of parameter used in alert logic expressions
    '''

    # ---------------------------------------------------------------------------------------------------------
    def __init__(self, filenames):
        '''
        Constructor
        Create AlertDb from a list of files
        '''
        
        self.alerts            = {}                # alerts by ID (including collectors and umbrellas)
        self.umbrellas         = defaultdict(list) # cross reference of umbrella relation
        self.collectors        = defaultdict(list) # cross reference of collector relation
        self.alertsMsgXref     = {}                # alert by Message
        self.alertsRefnumXref  = {}                # alert by Refnum
        self.parameters        = {}                # data dictionary
        self.paramSorted       = []                # Sorted list of keys (by increasing offset)
        self.paramOffset       = 0
        
        for filename in filenames:
            try:
                workbook = xlrd.open_workbook(filename)
            except:
                raise Exception, "File %s: open failed" % filename
            
            self.idrecord = self.parseIdentSheet(workbook, filename)

            self.parseAlertSheet(workbook, filename, self.idrecord.system)
            self.parseParamSheet(workbook, filename, self.idrecord.system)
            
        self.validateCollectors()
        self.validateUmbrellas()
        self.compileLogic()
    
    # ---------------------------------------------------------------------------------------------------------
    def parseIdentSheet(self, workbook, filename):
        sheet = workbook.sheet_by_name("Identification")
        idrecord = Bunch(ATA="", system="", version="", ICD="")
        for rowidx in range(1, sheet.nrows):
            row = sheet.row(rowidx)
            attrib = row[0].value.encode('utf-8').strip().lower()
            value  = row[1].value
            if type(value) == type(1.0):
                value = str(int(value))
            else:
                value = value.encode("utf-8").strip()

            if attrib == "member system":
                idrecord.system = value
            if attrib == "ata":
                idrecord.ATA    = value
            elif attrib == "version":
                idrecord.version = value
            elif attrib == "template version":
                idrecord.template_version = value
            else:
                pass

        return idrecord

            
    # ---------------------------------------------------------------------------------------------------------
    def parseAlertSheet(self, workbook, filename, sysname):
        try:
            sheet = workbook.sheet_by_name('Alert_Definition')
            sheetname = "Alert"
        except:
            raise Exception, "File %s: missing Alert_Definition sheet" % filename
        
        for rowidx in range(1, sheet.nrows):
            row = sheet.row(rowidx)

            # skip ignored lines
            status = row[22].value
            if (status.lower() == "ignore"):
                continue
            
            try:
                alert = Alert(row, filename, sheetname, rowidx+1, sysname)
            except Exception, msg:
                logerr(msg)
                continue
            
            if alert.alertId in self.alerts:
                logerr("File %s: Sheet %s: Line %d: Duplicate Alert ID: %d" % (filename, sheetname, rowidx, alert.alertId))
                continue

            if alert.refNum in self.alertsRefnumXref:
                logerr("File %s: Sheet %s: Line %d: Duplicate Alert Ref Number: %s" % (filename, sheetname, rowidx, alert.refNum))
                continue

            self.alerts[alert.alertId]          = alert
            self.alertsRefnumXref[alert.refNum] = alert
            
    # ---------------------------------------------------------------------------------------------------------
    def parseParamSheet(self, workbook, filename, system):
        '''
        Parse parameter sheet and create dictionary of bunches indexed by parameter name
        Full Parameter name is constructed as System.Name. Nevertheless in the expression it may be used with Name only.
        '''
        try:
            sheet = workbook.sheet_by_name('ICD_Parameters')
        except:
            raise Exception, "File %s: missing Parameter sheet" % filename
        
        for rowidx in range(1, sheet.nrows):
            row = sheet.row(rowidx)

            # skip ignored lines
            status = row[9].value
            if (status.lower() == "ignore"):
                continue

            try:
                param = Parameter(row, filename, rowidx+1, system)
            except Exception, msg:
                logerr(msg)
                continue

            if self.parameters.has_key(param.fqname):
                # duplicate, will have to perform source selection
                continue

            param.offset = self.paramOffset
            self.paramOffset += 8       # 4 byte for the value, 4 byte for the validity status
            self.paramSorted.append(param.fqname)
            self.parameters[param.fqname] = param
            
    # ---------------------------------------------------------------------------------------------------------
    def validateCollectors(self):
        '''
        for each alert
            translate collector list into id
            check if references to collector are consistent with collected lists
        '''
        
        # do the translations
        for alert in self.alerts.values():
            for col in alert.collectorMsgs:
                calert = self.alertsRefnumXref.get(col)
                if calert is None:
                    logerr("File %s: Line %d: Alert %d: Collector message <%s> not found" % \
                           (alert.filename, alert.rownum, alert.alertId, col))
                    alert.skip = True
                else:
                    alert.collectorIds.append(calert.alertId)

        # build cross ref structure collectors[ID] = [all messages referring to alert ID as collector]
        for alert in self.alerts.values():
            for uid in alert.collectorIds:
                self.collectors[uid].append(alert.alertId)
                    

    # ---------------------------------------------------------------------------------------------------------
    def validateUmbrellas(self):
        '''
        check that umbrella messages exist
        create dependency relation
        '''
        
        # translate umbrella messages in alert ids
        for alert in self.alerts.values():
            for umsg in alert.umbrellaMsgs:
                ualert = self.alertsRefnumXref.get(umsg)
                if ualert is None:
                    alert.skip = True
                    logerr("File %s: Line %d: Alert %d: Umbrella message <%s> not found" % \
                           (alert.filename, alert.rownum, alert.alertId, umsg))
                else:
                    alert.umbrellaIds.append(ualert.alertId)
        
        # build cross ref structure umbrellas[ID] = [all messages referring to alert ID as umbrella]
        for alert in self.alerts.values():
            for uid in alert.umbrellaIds:
                self.umbrellas[uid].append(alert.alertId)

                
    # ---------------------------------------------------------------------------------------------------------
    def compileLogic(self):
        '''
        for each alert (except Collectors)
            compile Logic into postfix
        if any syntax error, report it but continue
        '''
        
        def lkupParam(name):
            key = alert.sysName + '_' + name
            p = self.parameters.get(key)
            if p:
                return p.fqname, p.datatype
            else:
                raise Exception, "Parameter not found: %s" % key

        def lkupRefnum(key):
            try:
                a = self.alertsRefnumXref[key]
            except Exception as e:
                raise Exception, "File %s: Line %d: Alert: %s - Ref Number not found: %s" % (alert.filename, alert.rownum, alert.alertId, key)

            if key != alert.refNum:
                self.alerts[id].dependson.add(a)  # do not add a dependency to yourself (eg. when PREV operator is used)
            if a:
                return a.alertId, 'INT'
            else:
                raise Exception, "Alert Reference Name not found: %s" % key


        for id, alert in sorted(self.alerts.items()):
                #logok("Alert %d: %s" % (id, alert.logicSrc))
                try:
                    pf = compileToPostfix(alert.logicSrc, lkupParam, lkupRefnum)

                    alert.logicCompiled = pf
                    #logok("Alert %d: OK" % id)
                except Exception, msg:
                    logerr("File %s: Line %d: Alert %d: %s" % \
                           (alert.filename, alert.rownum, alert.alertId, msg))
                    alert.skip = True

                           
    
    # ---------------------------------------------------------------------------------------------------------
    def toXmlUmbrella(self, uid, ulist):
        s = '        <umbrella id="%d">' % uid
        for i in ulist:
            s += str(i) + ' '
        s += '</umbrella>\n'
        return s

    def toXmlCollector(self, uid, ulist):
        s = '        <collector id="%d">' % uid
        for i in ulist:
            s += str(i) + ' '
        s += '</collector>\n'
        return s
        
    # ---------------------------------------------------------------------------------------------------------
    def toXmlDB(self):
        uids = sorted(self.umbrellas.keys())
        cids = sorted(self.collectors.keys())
        
        # topological sort of the alert

        alerts_sorted = topological_sort(self.alerts.values(), lambda a: a.dependson)

        s = '<alertdb>\n'
        s += '    <alerts>\n'
        for alert in alerts_sorted:
            if not alert.skip:
                s += alert.toXml()
        for uid in uids:
            s += self.toXmlUmbrella(uid, self.umbrellas[uid])
        for cid in cids:
            s += self.toXmlCollector(cid, self.collectors[cid])
        s += '    </alerts>\n'
        s += '    <parameters>\n'
        for key in self.paramSorted:
            s += self.parameters[key].toXmlIntern()
        s += '    </parameters>\n'
        s += '</alertdb>\n'
        return s   
    
        # ---------------------------------------------------------------------------------------------------------
    def toXmlDD(self, model):
        aids = self.alerts.keys()
        aids.sort()
        uids = self.umbrellas.keys()
        uids.sort()

        s = '<namelist model="%s" offset="%d">\n' % (model, ALERT_PARAMETER_BASE_ADDRESS)
        for key in self.paramSorted:
            s += self.parameters[key].toXml()
            s += self.parameters[key].toXmlStatus()
        s += '</namelist>\n'
        return s   
