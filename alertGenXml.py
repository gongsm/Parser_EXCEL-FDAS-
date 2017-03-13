'''
Created on 08.09.2014

@author: Dieter Konnerth, TechSAT GmbH
'''

import sys
import glob
import alertDB



def main(args):
    '''
    Usage: alertdbGenXml outputfile inputfile inputfile ...
    '''
    if len(args) == 0:
        print "Usage: alertdbGen outputfile inputfile1 inputfile2 ..."
        return 1
    
    alertfile = args[0]
    if not alertfile.endswith('.xml'):
        alertfile += '.xml'
    ddmapfile = alertfile.rsplit('.', 1)[0] + '.inddmap.xml'
    
    flist = []
    for fn in args[1:]:
        flist.extend(glob.glob(fn))
    db = alertDB.AlertDb(flist)
    open(alertfile, "w").write(db.toXmlDB())
    open(ddmapfile, "w").write(db.toXmlDD('FDAS'))

if __name__ == '__main__':
    args = sys.argv[1:]
    sys.exit(main(args))