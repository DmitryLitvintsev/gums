#!/usr/bin/env python

"""
massage CMS /etc/grid-security/grid-vorolemap and /etc/grid-security/storage-authzdb
to generate reduced version that contains only

* FQAN username

per line

"""

AUTHZDB_FILE="/etc/grid-security/storage-authzdb"
VOROLEMAP_FILE="/etc/grid-security/grid-vorolemap"

import sys
import shlex

if __name__ == "__main__":

    vorolemap={}
    with open(VOROLEMAP_FILE,"r") as f:
        for line in f:
            if not line : continue
            parts = shlex.split(line.strip())
            """
            ignore entries that are missing FQAN
            """
            if len(parts) != 3 : continue

            fqan     = parts[1]
            username = parts[2]
            """
            only grab entries that contain 'cms' in FQAN string
            """
            if fqan.find("cms") != -1:
                vorolemap[fqan] = username

    authzdb={}
    with open(AUTHZDB_FILE,"r") as f:
        for line in f:
            if not line : continue
            parts = line.strip().split()
            username   = parts[1]
            rw         = line.strip()
            if username in authzdb :
                print "already there, but will take last ", line.strip(), " vs ", authzdb[username]
            authzdb[username] = line.strip()

    items = vorolemap.items()
    items.sort(key=lambda x: x[0])

    """
    write out new grid-vorolemap
    """
    new_authzdb = {}
    with open("grid-vorolemap.new","w") as f:
        for (fqan, username) in items:
            if username in authzdb:
                f.write("\"*\" \"%s\" %s\n"%(fqan,username))
                new_authzdb[username] = authzdb[username]


    items = new_authzdb.items()
    items.sort(key=lambda x: x[0])


    """
    write out new storage-authzdb
    """

    with open("storage-authzdb.new","w") as f:
        for (username,entry) in items:
            f.write("%s\n"%(entry,))




