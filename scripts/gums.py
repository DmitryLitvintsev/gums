#!/usr/bin/env python

import copy
import string
import sys
import time
import urllib
import json
import os
import re
from optparse import OptionParser

import mysql.connector
from mysql.connector import errorcode

import xml.etree.ElementTree as ET


def help():
    txt = "usage %prog [options] file_name"

Q="""
select distinct m.ACCOUNT, u.GROUP_NAME, m.MAP
from MAPPING m, USERS u
where u.DN=m.DN
"""


base_url="http://www-giduid.fnal.gov/cd/FUE/uidgid/"
uid_file="uid.lis"
gid_file="gid_id.lis"

gums_config = "/etc/gums/gums.conf"

def print_error(text):
    sys.stderr.write(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))+" : " +text+"\n")
    sys.stderr.flush()


def print_message(text):
    sys.stdout.write(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))+" : " +text+"\n")
    sys.stdout.flush()


if __name__ == "__main__":
    parser = OptionParser(usage=help())
    parser.add_option("-H", "--host",
                      metavar="HOST",type=str,default='localhost',
                      help="gums database host")
    parser.add_option("-u", "--user",
                      metavar="USER",type=str,default='root',
                      help="gums database user")
    parser.add_option("-p", "--password",
                      metavar="PASSWORD",type=str,default=None,
                      help="gums database password")
    parser.add_option("-d", "--dbname",
                      metavar="DBNAME",type=str,default='gums',
                      help="gums database name")
    parser.add_option("-g", "--gums",
                      metavar="GUMS",type=str,default=gums_config,
                      help="path to gums.config")

    parser.add_option("-P", "--port",
                      metavar="PORT",type=str,default=3306,
                      help="port to connect")

    parser.add_option("-v", action="store_true", dest="verbose")

    (options, args) = parser.parse_args()

    #
    # parse Fermi uid list file, generate map account map
    #

    user_to_uid={}
    try:
        contents = urllib.urlopen(base_url+uid_file)
        for c in contents:
            if not c : continue
            parts = c.split("\t\t");
            if len(parts) < 2: continue
            uid = parts[0].strip()
            gid = parts[1].strip()
            lastName = string.join(map(lambda x : x[0]+x[1:].lower(), parts[2].split()),' ')
            firstName = string.join(map(lambda x : x[0]+x[1:].lower(), parts[3].split()),' ')
            account=parts[-1].strip().lower()
            if not user_to_uid.has_key(account):
                user_to_uid[account] = { "groups" : [] , "primary" : gid, "uid" : uid, "lastName" : lastName, "firstName" : firstName }
            if gid not in user_to_uid[account]["groups"]:
                user_to_uid[account]["groups"].append(gid)
        contents.close()
    except Exception, msg:
        print_error(str(msg))
        sys.exit(1)

    if len(user_to_uid) == 0:
        print_error("CRITICAL - Something went wrong - got no user to UID mapping")
        sys.exit(1)

    #
    # parse Fermi group list file, generate group map
    #

    fermi_group_to_gid = {}
    combined_gid_to_group_map  = {}
    try:
        contents = urllib.urlopen(base_url+gid_file)
        for c in contents:
            if not c : continue
            parts = c.split();
            if len(parts) < 2: continue
            gid  = parts[0].strip()
            name = parts[1].lower()
            fermi_group_to_gid[name]=gid
            combined_gid_to_group_map[gid]=name
            if options.verbose: print ("DEBUG Scanning %s, found gid %s name=%s"%(base_url+gid_file,gid,name))
        contents.close()
    except Exception, msg:
        print_error(str(msg))
        sys.exit(1)

    if len(fermi_group_to_gid) == 0:
        print_error("CRITICAL - Something went wrong - got no group to GID mapping")
        sys.exit(1)

    #
    # parse gums.conf
    #

    #
    # generate map from accountMappers to groupName
    #

    mapper_to_gid={}
    tree = ET.parse(options.gums)
    root = tree.getroot()
    for child in root:
        if child.tag=="accountMappers":
            for element in child.getchildren():
                #
                # 'groupName' is GID
                #
                mapper_to_gid[element.attrib.get('name')] = element.attrib.get('groupName')


    #
    # generate map from accountMappers to groupName
    #

    group_to_gid={}
    for child in root:
        if child.tag=="groupToAccountMappings":
            for element in child.getchildren():
                # this is what we match to database
                groupname     = element.attrib.get('userGroups')
                accountMapper = element.attrib.get('accountMappers')
                gid = mapper_to_gid.get(accountMapper)
                if group_to_gid.has_key(groupname):
                    if group_to_gid.get(groupname) != gid :
                        print_error("WARNING - group name %s that has GID %s also has GID %s"%(groupname,group_to_gid.get(groupname),gid,))
                    continue
                group_to_gid[groupname] = gid

    if len(group_to_gid) == 0:
        print_error("CRITICAL - Something went wrong - got no group GID mapping")
        sys.exit(1)

#
# query database
#

    user = {}
    account_map = copy.deepcopy(user_to_uid)
    try:
        con = mysql.connector.connect(user=options.user,
                                      password=options.password,
                                      host=options.host,
                                      database=options.dbname,
                                      port=options.port)
        cursor = con.cursor()
        cursor.execute(Q)
        for account, groupname, mapname in cursor:
            a = str(account)
            g = str(groupname)
            m = str(mapname)
            #
            # kuldge to exclude Pool accounts for which GUMS don't tell us GID
            # and we fallback to GID from Fermi uid.list for these accounts
            #
            if m.endswith("Pool") : continue
            account_record = user_to_uid.get(a)
            uid = account_record.get("uid") if account_record else None
            gid = group_to_gid.get(g)
            if not gid :
                gid = fermi_group_to_gid.get(g)
            if not uid or not gid:
                if options.verbose: print_error("DEBUG - account %s UID=%s, group %s GID=%s, skipping"%(a,uid,g,gid,))
                continue
            else:
                if options.verbose: print_error("DEBUG - account %s UID=%s, group %s GID=%s"%(a,uid,g,gid,))
            if gid not in account_map.get(a)["groups"]:
                account_map.get(a)["groups"].append(gid)
            if not user.has_key(uid):
                 user[uid] = [[]]
                 user[uid].append(a.lower())
            if gid not in user[uid][0]:
                user[uid][0].append(gid)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print_error("CRITICAL - Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print_error("CRITICAL - Database does not exist")
        else:
            print_error(str(err))
    else:
        cursor.close()
        con.close()

    if len(user) == 0:
        print_error("CRITICAL - Something went wrong - got no user records")
        sys.exit(1)

#
# write out storage-authzb
#

    keys = account_map.keys()
    keys.sort()
    group_map={}

    f=open("storage-authzdb","w")
    for k in keys:
        account = k
        uid     = account_map.get(k).get("uid")
        groups  = account_map.get(k).get("groups")
        groups.sort()
        f.write("authorize %s read-write %s %s / /pnfs/fnal.gov/usr /\n"%(account,uid,string.join([str(x) for x in groups],',')))
    f.write("# THE END %d\n"%(int(time.time())))
    f.close()

#
# write out passwd file
#

    f=open("passwd","w")
    for k in keys:
        account = k
        uid     = account_map.get(k).get("uid")
        gid     = account_map.get(k).get("primary")
        firstName = account_map.get(k).get("firstName")
        lastName  = account_map.get(k).get("lastName")
        groups    = account_map.get(k).get("groups")
        for g in groups:
            groupName = combined_gid_to_group_map[g]
            if not group_map.has_key(groupName):
                group_map[groupName]={"gid": g, "accounts" : []}
            #group_map[groupName]["accounts"].add(account)
            if account not in group_map[groupName]["accounts"]:
                group_map[groupName]["accounts"].append(account)
        f.write("%s:x:%s:%s:%s %s:/home/%s:/sbin/nologin\n"%(account,uid,gid,firstName,lastName,account))
    f.close()


#
# Generate json output for passwd file
#

    users = {}
    f=open("passwd","r")
    for line in f:
        (uname, pwd, uid, gid, gecos, homedir, shell) = line.rstrip().split(':')
        users[uname] = {
            'comment': gecos,
            'uid': uid,
            'gid': gid,
            'homedir': homedir,
            'shell': shell
        }
    f.close()

    obj = {}
    obj['generationTime'] = int(time.time())
    obj['numberOfUsers'] = len(users)
    obj['users'] = users

    f=open("passwd.json","w")
    f.write(json.dumps(obj, indent=4, sort_keys=True))
    f.close()

#
# write out group file
#

    f=open("group","w")

    # We get Groups from the list of all groups at the lab (CCD webpage)
    keys = combined_gid_to_group_map.keys()
    keys.sort()

    for k in keys:
        gid   = k
        groupName = combined_gid_to_group_map[gid]
        if groupName in group_map: #There are users with this group
          accounts = group_map[groupName].get("accounts")
          if options.verbose: print("DEBUG - Users found for group %s with GID %s: %s"%(groupName,gid,accounts))
        else: #No users have this group assigned (eg: glexec00..2999 groups)
          print_error("INFO - No users found for group %s with GID %s"%(groupName,gid))
          accounts = ''
        f.write("%s:x:%s:%s\n"%(groupName,gid,string.join(accounts,",")))
    f.close()

#
# Generate json output for group file
#

    groups = {}
    f=open("group","r")
    for line in f:
        (gname, passwd, gid, users) = line.rstrip().split(':')
        groups[gname] = {
            'gid': gid,
            'users': users,
        }
    f.close()

    obj = {}
    obj['generationTime'] = int(time.time())
    obj['numberOfGroups'] = len(groups)
    obj['groups'] = groups

    f=open("group.json","w")
    f.write(json.dumps(obj, indent=4, sort_keys=True))
    f.close()

    sys.exit(0)
