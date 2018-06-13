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
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'https://fermicloud033.fnal.gov:8443/getStorageAuthzDBFile')

    """
    With very few exceptions, PycURL option names are derived from
    libcurl option names by removing the CURLOPT_ prefix.
    """

    c.setopt(c.CAPATH,"/etc/grid-security/certificates")
    c.setopt(c.SSLCERT,"/etc/grid-security/hostcert.pem")
    c.setopt(c.SSLKEY,"/etc/grid-security/hostkey.pem")

    c.setopt(c.WRITEFUNCTION, buffer.write)
    c.perform()
    rc=c.getinfo(pycurl.HTTP_CODE)
    c.close()

    if rc != 200 :
       sys.exit(1)

    body = json.load(StringIO(buffer.getvalue()))
    body.sort(key=lambda x: x["username"])

    try:
        with open("storage-authzdb.new","w") as f:
            for item in body:
                if item.get("username") == "simons" :
                    continue
                if item.get("username") == "ifisk" :
                    item["root"] = "pnfs/fnal.gov/usr/Simons"
                    item["uid"] = "49331"
                    item["gid"] = ["9323",]
                    continue
                if item.get("username") == "auger" :
                    item["root"] = "pnfs/fnal.gov/usr/fermigrid/volatile/auger"
                    continue
                gids=map(int,item.get("gid"))
                gids.sort()
                f.write("%s\n"%(string.join([item.get("decision","authorize"),
                                             item.get("username"),
                                             item.get("privileges"),
                                             item.get("uid"),
                                             string.join(map(str,gids),","),
                                             item.get("home","/"),
                                             item.get("root"),
                                             item.get("last_path","/")],
                                            " ")))

    except Exception, msg:
        print str(msg)
        sys.exit(1)
    sys.exit(0)


