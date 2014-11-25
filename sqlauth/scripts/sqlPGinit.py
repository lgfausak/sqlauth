#!/usr/bin/env python
###############################################################################
##
##  Copyright (C) 2014 Greg Fausak
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##        http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from __future__ import absolute_import
from __future__ import print_function

import sys, argparse, os
import subprocess, string

## parse command line arguments
##

def_dbname = 'autobahn'
def_dbuser = 'autouser'
def_configdir = '/usr/local/sqlauth'
def_superuser = 'postgres'
def_sql = 'psql'
def_initdb = 'initdb'
def_dbdirectory = '/var/local/pgsql/data'
def_xdir = '/usr/local/pgsql/bin'
def_createdb = 'createdb'
def_schemadb = '{psql} -U{superuser} '

p = argparse.ArgumentParser(description="""
sqlPGinit setup postgres for sqlauth application

WARNING!!! This is highly destructive!!!

This script is very destructive.  It will init the installation (from
scratch, ala initdb).  It will be completely destroyed if it already
exists.  This destruction includes all other databases that may exist
at this site.  This script will totally erase your entire postgres
installation. WARNING!!!  You have been warned!
OK, this script does:
1) create a postgres user and postgres group.
2) delete and recreate directory PGDATA
3) create /etc/profile.d/postgres_hints.sh file (for PGDATA)
4) initdb
5) createdb
6) definition, load the database with complete database definition
7) initialize, load seed data into the database

WARNING!!! This is highly destructive!!!

""")

p.add_argument('-q', '--quiet', action='store_true', dest='quiet',
            default=False, help='Suppress error output as much as humanly possible')
p.add_argument('-b', '--backwards', action='store_true', dest='backwards',
            default=False, help='run command backwards (undo)')
p.add_argument('-n', '--name', action='store', dest='dbname', default=def_dbname,
		help='the database name to initialize, if it exists it will be zapped, default name is: ' + def_dbname)
p.add_argument('-u', '--user', action='store', dest='dbuser', default=def_dbuser,
		help='the user name that will be admin user for newly created database, default user is: ' + def_dbuser)
p.add_argument('-p', '--path', action='store', dest='path', default=def_configdir,
		help='the path to configuration files, default is: ' + def_configdir)
p.add_argument('-s', '--superuser', action='store', dest='superuser', default=def_superuser,
		help='the superuser for the postgres installation, normally "postgres", default is: ' + def_superuser)
p.add_argument('-d', '--directory', action='store', dest='dbdirectory', default=def_dbdirectory,
		help='the superuser for the postgres installation, normally "postgres", default is: ' + def_dbdirectory)
p.add_argument('-x', '--executabledirectory', action='store', dest='xdir', default=def_xdir,
		help='the executable path for all executables postgres, default is: ' + def_xdir)
p.add_argument('-a', '--apply', action='store_true', dest='apply',
            default=False, help='apply changes (if not specified, the commands to run are listed but not actually applied')

args = p.parse_args()

#
# these are the commands we are gonna run, in order
#
cmds = [
    'adduser --system --disabled-password --home {dbdirectory} --shell /bin/sh {superuser}',
    'makeprofile',
    'sudo -i rm -rf {dbdirectory}',
    'mkdir -p {dbdirectory}',
    'chown {superuser} {dbdirectory}',
    'sudo -i -u {superuser} {xdir}/initdb --auth-host=trust {dbdirectory}',
    'sudo -i -u postgres {xdir}/pg_ctl -D {dbdirectory} -l {dbdirectory}/postgres.log start',
    'sleep 5',
    'sudo -i -u postgres {xdir}/createuser -h localhost -U{superuser} --createdb --login --superuser {dbuser}',
    'sudo -i -u postgres {xdir}/createdb -h localhost -U {superuser} {dbname}',
    'psql -U{dbuser} -h localhost -f {configdir}/PG.sql {dbname}',


]

#
# undo, do the opposite of the above (uninstall)
#
backwards_cmds = [
    'sudo -i -u postgres {xdir}/dropdb -h localhost -U{superuser} {dbname}',
    'sudo -i -u postgres {xdir}/dropuser -h localhost -U{superuser} {dbuser}',
    'sudo -i -u postgres {xdir}/pg_ctl -D {dbdirectory} stop',
    'deluser {superuser}',
    'rm {profile}',
]

#
# these are the arguments for those commands
#
cag = {
    'profile': '/etc/profile.d/postgres_hints.sh',
    'dbdirectory': args.dbdirectory,
    'dbuser': args.dbuser,
    'dbname': args.dbname,
    'configdir': args.path,
    'xdir': args.xdir,
    'superuser': args.superuser
}

clist = cmds
if args.backwards:
    clist = backwards_cmds

rv = 0
for i in clist:
    cs = i.format(**cag)
    css = cs.split()
    if not args.quiet:
        print("{}".format(cs), file=sys.stdout)
    if args.apply:
        try:
            if css[0] == 'makeprofile':
                f = open(cag['profile'],'w')
                f.write("PGDATA={dbdirectory}; export PGDATA\n".format(**cag))
                f.write("PATH={xdir}:$PATH\n".format(**cag))
                f.close()
            else:
                subprocess.check_call(css)
        except:
            e = sys.exc_info()[0]
            es = str(e)
            rv = 1
            if not args.quiet:
                print("ERROR:", file=sys.stderr)
                print("\t\t" + string.replace(es, "\n", "\n\t\t"), file=sys.stderr)

sys.exit(rv)
