#!/usr/bin/env python 

import json
import pycurl 
import string 
import sys
from StringIO import StringIO

if __name__ == "__main__":
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'https://fermicloud033.fnal.gov:8443/getStorageAuthzDBFile')

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
        
        
