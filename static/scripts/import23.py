#!/usr/bin/python

import os
import os.path
import shutil
import subprocess
import sys
import time
import traceback
from ldif import LDIFParser, CreateLDIF

log = "./import23.log"
logError = "./import23.error"

service = "/usr/sbin/service"
ldapmodify = "/opt/opendj/bin/ldapmodify"

ignore_files = ['101-ox.ldif',
                'gluuImportPerson.properties',
                'oxTrust.properties',
                'oxauth-config.xml',
                'oxauth-errors.json',
                'oxauth.config.reload',
                'oxauth-static-conf.json',
                'oxtrust.config.reload'
                ]

ldap_creds = ['-h',
              'localhost',
              '-p',
              '1389',
              '-D',
              '"cn=directory',
              'manager"',
              '-j',
              password_file
              ]

fixManagerGroupLdif = """dn: %s
changetype: modify
replace: gluuManagerGroup
gluuManagerGroup: %s

"""

bulk_ldif_files =  [ "groups.ldif",
                "people.ldif",
                "u2f.ldif",
                "attributes.ldif",
                "hosts.ldif",
                "scopes.ldif",
                "uma.ldif",
                "clients.ldif",
                "scripts.ldif",
                "site.ldif"
                ]

class ConfigLDIF(LDIFParser):
    def __init__(self, input, output):
        LDIFParser.__init__(self, input)
        self.targetDN = None
        self.targetAttr = None
        self.DNs = []
        self.lastDN = None
        self.lastEntry = None

    def getResults(self):
        return (self.targetDN, self.targetAttr)

    def getDNs(self):
        return self.DNs

    def getLastEntry(self):
        return self.lastEntry

    def handle(self, dn, entry):
        self.lastDN = dn
        self.DNs.append(dn)
        self.lastEntry = entry
        if dn.lower().strip() == targetDN.lower().strip():
            if entry.has_key(self.targetAttr):
                self.targetAttr = entry(self.targetAttr)

def copyFiles():
    os.path.walk ("./etc", walk_function, None)
    os.path.walk ("./opt", walk_function, None)

def getOutput(args):
        try:
            logIt("Running command : %s" % " ".join(args))
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None)
            output = os.popen(" ".join(args)).read().strip()
            return output
        except:
            logIt("Error running command : %s" % " ".join(args), True)
            logIt(traceback.format_exc(), True)
            sys.exit(1)

def logIt(msg, errorLog=False):
    if errorLog:
        f = open(logError, 'a')
        f.write('%s %s\n' % (time.strftime('%X %x'), msg))
        f.close()
    f = open(log, 'a')
    f.write('%s %s\n' % (time.strftime('%X %x'), msg))
    f.close()

def updateConfiguration():
    ouputFolder = "./output_ldif"
    if not os.path.exists(ouputFolder):
        os.mkdir(ouputFolder)

    fn = "./ldif/organization.ldif"
    parser = ConfigLDIF(open(fn, 'rb'), sys.stdout)
    parser.parse()
    orgDN = parser.lastDN
    gluuManagerGroup = parser.lastEntry['gluuManagerGroup'][0]
    f = open("%s/updateManagerGroup.ldif" % ouputFolder, 'w')
    f.write(fixManagerGroupLdif % (orgDN, gluuManagerGroup))
    f.close()

    # Iterate through configuration entries and make changes...

def startOpenDJ():
    output, error = getOutput([service, 'opendj', 'start'])
    if not error and output.index("Directory Server has started successfully") > 0:
        logIt("Directory Server has started successfully")
    else:
        if error:
            login("Error starting OpenDJ:\t%s" % error)
            sys.exit(2)
        else:
            logIt("OpenDJ did not start properly... exiting. Check /opt/opendj/logs/errors")
            sys.exit(3)

def stopOpenDJ():
    output, error = getOutput([service, 'opendj', 'start'])
    if not error and output.index("Directory Server is now stopped") > 0:
        logIt("Directory Server is now stopped")
    else:
        if error:
            login("Error stopping OpenDJ:\t%s" % error)
            sys.exit(2)
        else:
            logIt("OpenDJ did not stop properly... exiting. Check /opt/opendj/logs/errors")
            sys.exit(3)

def uploadBulkLDIF():
    for ldif_file in ldif_files:
        cmd = [ldapmodify] + ldap_creds + ['-a', '-c', '-f' './ldif/%s' % ldif_file]
        output, error = getOutput(cmd)
        if output:
            logIt(output)
        if error:
            logIt("Error uploading %s\n" % ldif_file + error, True)

def walk_function(a, dir, files):
    for file in files:
        if file in ignore_files:
            continue
        fn = "%s/%s" % (dir, file)
        targetFn = fn[1:]
        if os.path.isdir(fn):
            if not os.path.exists(targetFn):
                os.mkdir(targetFn)
        else:
            # It's a file...
            try:
                logIt("copying %s" % targetFn)
                shutil.copyfile(fn, targetFn)
            except:
                logIt("Error copying %s" % targetFn, True)

stopOpenDJ()
copyFiles()
startOpenDJ()
uploadBulkLDIF()
updateConfiguration()