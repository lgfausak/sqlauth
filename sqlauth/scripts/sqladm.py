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
import types as vtypes
from tabulate import tabulate

import twisted
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet import defer

from autobahn.twisted.wamp import ApplicationRunner,ApplicationSession
from autobahn.wamp import auth
from autobahn.wamp import types
from autobahn.wamp.types import CallOptions

from autobahn import util

import argparse

class Component(ApplicationSession):
    """
    An application component for administration on sessions and users
    """

    def __init__(self, *args, **kwargs):
        log.msg("__init__")

        self.db = {}
        self.svar = {}

        log.msg("got args {}, kwargs {}".format(args,kwargs))

        # reap init variables meant only for us
        for i in ( 'command', 'action', 'action_args', 'debug', 'authinfo', 'topic_base', ):
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
    def onJoin(self, details):
        log.msg("onJoin session attached {}".format(details))
        rv = []

        try:
            log.msg("{}.{}.{}".format(self.svar['topic_base'],self.svar['command'],self.svar['action']))
            nv = yield self.call(self.svar['topic_base'] + '.' + self.svar['command'] + '.' +
                self.svar['action'], action_args=self.svar['action_args'],
                options = CallOptions(timeout=2000,discloseMe = True))

            drv = nv
            if isinstance(nv, vtypes.ListType):
                drv = {}
                drv['0'] = {
                    'title':self.svar['command'],
                    'result':nv
                }
    
            for i in range(len(drv)):
                log.msg("onJoin: result index {}: title {}".format(i,drv[str(i)]['title']))
                rv = drv[str(i)]['result']
         
                if len(rv) > 0:
                    log.msg("onJoin: rv is {}".format(rv))
                    print "Result set {} {}".format(i + 1, drv[str(i)]['title'])
                    print tabulate(rv, headers="firstrow", tablefmt="simple")
                else:
                    print "Result set {} {}, [no results]".format(i + 1, drv[str(i)]['title'])
        except Exception as e:
            sys.stderr.write("ERROR: {}\n".format(e))

        log.msg("onJoin disconnecting : {}")
        self.disconnect()

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
    def_user = 'sys'
    def_secret = '123test'
    def_realm = 'realm1'
    def_topic_base = 'sys'
    def_action_args = '{}'

    # http://stackoverflow.com/questions/3853722/python-argparse-how-to-insert-newline-the-help-text
    p = argparse.ArgumentParser(description="db admin manager for autobahn", formatter_class=SmartFormatter)

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
    sp = p.add_subparsers(dest='command')
    session_p = sp.add_parser('session')
    session_p.add_argument('action', choices=['list','get','kill'], help='Session commands')
    session_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

    ses_p = sp.add_parser('ses')
    ses_p.add_argument('action', choices=['list','get','kill'], help='Ses commands')
    ses_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

    user_p = sp.add_parser('user')
    user_p.add_argument('action', choices=['list', 'get', 'add', 'update', 'delete'], help='User commands')
    user_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

    userrole_p = sp.add_parser('userrole')
    userrole_p.add_argument('action', choices=['add', 'delete'], help='User role association commands')
    userrole_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

    role_p = sp.add_parser('role')
    role_p.add_argument('action', choices=['list', 'get', 'add', 'update', 'delete'], help='Role commands')
    role_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

    role_p = sp.add_parser('topic')
    role_p.add_argument('action', choices=['list', 'get', 'add', 'update', 'delete'], help='Topic commands')
    role_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

    topicrole_p = sp.add_parser('topicrole')
    topicrole_p.add_argument('action', choices=['add', 'delete'], help='Topic role association commands')
    topicrole_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

    role_p = sp.add_parser('activity')
    role_p.add_argument('action', choices=['list', 'get', 'add', 'update', 'delete'], help='Activity commands')
    role_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

    role_p = sp.add_parser('topicrole')
    role_p.add_argument('action', choices=['permission', 'list', 'add', 'delete'], help='TopicRole commands')
    role_p.add_argument('-a', '--args', action='store', dest='action_args', default=def_action_args,
                        help='action args, json format, default: ' + def_action_args)

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
            authinfo=ai,topic_base=args.topic_base,debug=args.verbose,
            command=args.command,action=args.action,action_args=json.loads(args.action_args))
    runner = ApplicationRunner(args.wsocket, args.realm)
    runner.run(lambda _: mdb)


if __name__ == '__main__':
   run()
