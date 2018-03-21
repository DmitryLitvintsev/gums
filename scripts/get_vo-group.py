#!/usr/bin/env python 

import json
import pycurl 
import string 
import sys
from StringIO import StringIO

if __name__ == "__main__":
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'https://fermicloud033.fnal.gov:8443/getMappedGidFile')

    """
    With very few exceptions, PycURL option names are derived from 
    libcurl option names by removing the CURLOPT_ prefix. 
    """

    c.setopt(c.CAPATH,"/etc/grid-security/certificates")
    c.setopt(c.SSLCERT,"/tmp/x509up_u8637")

    c.setopt(c.WRITEFUNCTION, buffer.write)
    c.perform()
    rc=c.getinfo(pycurl.HTTP_CODE)
    c.close()

    if rc != 200 : 
        sys.exit(1)
    else:
        with open("vo-group.json","w") as f:
            f.write(buffer.getvalue())
        
        sys.exit(0)
        
