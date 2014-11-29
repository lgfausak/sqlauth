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
                    select
                        l.id, l.login, l.fullname, l.tzname, private.array_accum(r.name)
		      from
		        login l, loginrole lr, role r
		     where
		        l.id = lr.login_id
		       and
		        lr.role_id = r.id
		  group by
		  	l.id
		  order by
		     	l.login
		   """,
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
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
    def onJoin(self, details):
        log.msg("onJoin session attached {}".format(details))
        reg = yield self.register(self.userList, self.svar['topic_base'] + '.user.list', RegisterOptions(details_arg = 'details'))
        log.msg("onJoin userList registered attached {}".format(details, self.svar['topic_base']+'.user.list'))

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
