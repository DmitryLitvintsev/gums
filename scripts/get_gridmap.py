#!/usr/bin/env python

import json
import pycurl
import os
import string
import subprocess
import sys
import time

from StringIO import StringIO
def print_error(text):
    sys.stderr.write(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))+" : " +text+"\n")
    sys.stderr.flush()


def print_message(text):
    sys.stdout.write(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))+" : " +text+"\n")
    sys.stdout.flush()

def execute_command(cmd):
    p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    output, errors = p.communicate()
    rc=p.returncode
    if rc:
        print_error("Command \"%s\" failed: rc=%d, error=%s"%(cmd,rc,errors.replace('\n',' ')))
    return rc

if __name__ == "__main__":

    rc=execute_command("cigetcert -i 'Fermi National Accelerator Laboratory' -o /tmp/x509up_%d_ferry"%(os.getuid()))

    if rc :
        print_error("Failed to create proxy")
        sys.exit(1)


    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'https://fermicloud033.fnal.gov:8443/getGridMapFile')

    """
    With very few exceptions, PycURL option names are derived from
    libcurl option names by removing the CURLOPT_ prefix.
    """


    c.setopt(c.CAPATH,"/etc/grid-security/certificates")
    c.setopt(c.SSLCERT,"/tmp/x509up_%d_ferry"%(os.getuid(),))

    c.setopt(c.WRITEFUNCTION, buffer.write)
    c.perform()
    rc=c.getinfo(pycurl.HTTP_CODE)
    c.close()

    if rc != 200 :
       sys.exit(1)

    body = json.load(StringIO(buffer.getvalue()))
    print body
    body.sort(key=lambda x: x["userdn"])

    try:
        with open("grid-mapfile.new","w") as f:
            for item in body:
                f.write("\"%s\" %s\n"%(item.get("userdn"),
                                       item.get("mapped_uname")))
    except Exception, msg:
        print str(msg)
        sys.exit(1)
    sys.exit(0)


