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
##
## this contains most of the sqlauth administration rpc calls.  the only one
## that is missing is the sessiondb one, because there are two inputs
## for that one.  the database contains one version of the current 'sessions',
## but the more accurate one is in memory of the router process.  so the listSessions
## code actually looks at both sources and will let you know if data exists
## in memory but does not exist in database.
##
## user (list,add,delete,get)
##   list   - show a list of users and the roles they belong to
##   add    - add a new user
##   delete - delete a user
## role (list,add,delete,get)
##   list   - show a list of roles and the users that belong to them
##   add    - add a new role
##   delete - delete a user
## topic (list,add,delete,get)
##   list   - show a list of topics and the roles that belong to them
##   add    - add a new topic
##   delete - delete a topic
## session (not here, in the router code)
##   list   - list all sessions
##   kill   - kill a session
##
###############################################################################

from __future__ import absolute_import

import sys, os, argparse, six, json
from tabulate import tabulate

import twisted
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet import defer

from autobahn.wamp.types import RegisterOptions

from autobahn.twisted.wamp import ApplicationRunner,ApplicationSession
from autobahn.wamp import auth
from autobahn.wamp import types
from autobahn.wamp.types import CallOptions

from autobahn import util

import argparse

class Component(ApplicationSession):
    """
    This component serves most of the sqlauth admin functionality 
    """

    def __init__(self, *args, **kwargs):
        log.msg("__init__")

        self.db = {}
        self.svar = {}

        log.msg("got args {}, kwargs {}".format(args,kwargs))

        # reap init variables meant only for us
        for i in ( 'debug', 'authinfo', 'topic_base', ):
            if i in kwargs:
                if kwargs[i] is not None:
                    self.svar[i] = kwargs[i]
                del kwargs[i]

        log.msg("sending to super.init args {}, kwargs {}".format(args,kwargs))
        ApplicationSession.__init__(self, *args, **kwargs)

    def onConnect(self):
        log.msg("onConnect")
        auth_type = 'none'
        auth_user = 'anon'
        if 'authinfo' in self.svar:
            auth_type = self.svar['authinfo']['auth_type']
            auth_user = self.svar['authinfo']['auth_user']
        log.msg("onConnect with {} {}".format(auth_type, auth_user))
        self.join(self.config.realm, [six.u(auth_type)], six.u(auth_user))

    def onChallenge(self, challenge):
        log.msg("onChallenge - maynard")
        password = 'unknown'
        if 'authinfo' in self.svar:
            password = self.svar['authinfo']['auth_password']
        log.msg("onChallenge with password {}".format(password))
        if challenge.method == u'wampcra':
            if u'salt' in challenge.extra:
                key = auth.derive_key(password.encode('utf8'),
                    challenge.extra['salt'].encode('utf8'),
                    challenge.extra.get('iterations', None),
                    challenge.extra.get('keylen', None))
            else:
                key = password.encode('utf8')
            signature = auth.compute_wcs(key, challenge.extra['challenge'].encode('utf8'))
            return signature.decode('ascii')
        else:
            raise Exception("don't know how to compute challenge for authmethod {}".format(challenge.method))

    @inlineCallbacks
    def userList(self, details):
        log.msg("userList called {}".format(details))
        qv = yield self.call('adm.db.query',
                """
                    with user_roles as (
                        select lr.role_id, lr.login_id, r.name
                          from loginrole lr, role r
                         where lr.role_id = r.id
                        )
                    select
                        l.id, l.login, l.fullname, l.tzname, private.array_accum(u.name) as roles
		      from
		        login l
           left outer join
                        user_roles u on l.id = u.login_id
		  group by
		  	l.id
		  order by
		     	l.login
		   """,
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(qv) == 0:
            defer.returnValue([])
            return
        rv = []

        # insert columns into array, ra and first element of rv (header)
        # scan the entire result set, determine columns
        #rk = {}
        #for r in qv:
        #    for k in r.keys():
        #        rk[k] = True
        #ra = rk.keys()
        #instead, we use the first row, because the columns cannot
        #change on a row to row basis in the same query
        ra = qv[0].keys()
        rv.append(ra)
        #append a row in the array for each result, in the same order as the original row 1
        for r in qv:
            rv.append([r.get(c,None) for c in ra])

        defer.returnValue(rv)

    @inlineCallbacks
    def roleList(self, details):
        log.msg("roleList called {}".format(details))
        qv = yield self.call('adm.db.query',
                """
                    with role_users as (
                        select lr.role_id, lr.login_id, l.login
                          from loginrole lr, login l
                         where lr.login_id = l.id
                        )
                    select
                        r.id, r.name, r.description, private.array_accum(l.login) as users
		      from
                        role r
           left outer join
                        role_users l on l.role_id = r.id
		  group by
		  	r.id
		  order by
		     	r.name
		   """,
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(qv) == 0:
            defer.returnValue([])
            return
        rv = []

        # insert columns into array, ra and first element of rv (header)
        # scan the entire result set, determine columns
        #rk = {}
        #for r in qv:
        #    for k in r.keys():
        #        rk[k] = True
        #ra = rk.keys()
        #instead, we use the first row, because the columns cannot
        #change on a row to row basis in the same query
        ra = qv[0].keys()
        rv.append(ra)
        #append a row in the array for each result, in the same order as the original row 1
        for r in qv:
            rv.append([r.get(c,None) for c in ra])

        defer.returnValue(rv)

    @inlineCallbacks
    def topicList(self, details):
        log.msg("topicList called {}".format(details))
        qv = yield self.call('adm.db.query',
                """
                    with topic_roles as (
                        select distinct lr.role_id, lr.topic_id, r.name
                          from topicrole lr, role r
                         where lr.role_id = r.id
                        )
                    select
                        t.id, t.name, t.description, private.array_accum(u.name) as roles
		      from
		        topic t
           left outer join
                        topic_roles u on t.id = u.topic_id
		  group by
		  	t.id
		  order by
		     	t.name
		   """,
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(qv) == 0:
            defer.returnValue([])
            return

        ra = qv[0].keys()
        rv = []
        rv.append(ra)
        for r in qv:
            rv.append([r.get(c,None) for c in ra])

        defer.returnValue(rv)

    @inlineCallbacks
    def onJoin(self, details):
        log.msg("onJoin session attached {}".format(details))
        reg = yield self.register(self.userList, self.svar['topic_base'] + '.user.list', RegisterOptions(details_arg = 'details'))
        log.msg("onJoin userList registered attached {}".format(details, self.svar['topic_base']+'.user.list'))
        reg = yield self.register(self.roleList, self.svar['topic_base'] + '.role.list', RegisterOptions(details_arg = 'details'))
        log.msg("onJoin roleList registered attached {}".format(details, self.svar['topic_base']+'.role.list'))
        reg = yield self.register(self.topicList, self.svar['topic_base'] + '.topic.list', RegisterOptions(details_arg = 'details'))
        log.msg("onJoin topicList registered attached {}".format(details, self.svar['topic_base']+'.topic.list'))

    def onLeave(self, details):
        log.msg("onLeave: {}".format(details))

        self.disconnect()

        return

    def onDisconnect(self):
        log.msg("onDisconnect:")
        reactor.stop()

# http://stackoverflow.com/questions/3853722/python-argparse-how-to-insert-newline-the-help-text
class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        # this is the RawTextHelpFormatter._split_lines
        if text.startswith('R|'):
            return text[2:].splitlines()  
        return argparse.HelpFormatter._split_lines(self, text, width)

def run():
    prog = os.path.basename(__file__)

    def_wsocket = 'ws://127.0.0.1:8080/ws'
    def_user = 'adm'
    def_secret = '123test'
    def_realm = 'realm1'
    def_topic_base = 'adm'
    def_action_args = '{}'

    # http://stackoverflow.com/questions/3853722/python-argparse-how-to-insert-newline-the-help-text
    p = argparse.ArgumentParser(description="sqlauth backend support", formatter_class=SmartFormatter)

    p.add_argument('-w', '--websocket', action='store', dest='wsocket', default=def_wsocket,
                        help='web socket definition, default is: '+def_wsocket)
    p.add_argument('-r', '--realm', action='store', dest='realm', default=def_realm,
                        help='connect to websocket using realm, default is: '+def_realm)
    p.add_argument('-v', '--verbose', action='store_true', dest='verbose',
            default=False, help='Verbose logging for debugging')
    p.add_argument('-u', '--user', action='store', dest='user', default=def_user,
                        help='connect to websocket as user, default is: '+def_user)
    p.add_argument('-s', '--secret', action='store', dest='password', default=def_secret,
                        help='users "secret" password')
    p.add_argument('-t', '--topic', action='store', dest='topic_base', default=def_topic_base,
                        help='if you specify --dsn then you will need a topic to root it on, the default ' + def_topic_base + ' is fine.')

    args = p.parse_args()
    if args.verbose:
       log.startLogging(sys.stdout)

    component_config = types.ComponentConfig(realm=args.realm)
    ai = {
            'auth_type':'wampcra',
            'auth_user':args.user,
            'auth_password':args.password
            }

    mdb = Component(config=component_config,
            authinfo=ai,topic_base=args.topic_base,debug=args.verbose)
    runner = ApplicationRunner(args.wsocket, args.realm)
    runner.run(lambda _: mdb)


if __name__ == '__main__':
   run()
