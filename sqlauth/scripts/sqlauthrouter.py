#!/usr/bin/env python
###############################################################################
##
##  Copyright (C) 2011-2014 Tavendo GmbH
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

import json
import six

from twisted.python import log
from twisted.internet.defer import inlineCallbacks

from autobahn import util
from autobahn.wamp import auth
from autobahn.wamp import types
from autobahn.wamp.types import RegisterOptions
from autobahn.wamp.interfaces import IRouter
from autobahn.twisted.wamp import Router
from autobahn.twisted.wamp import RouterSession
from sqlbridge.twisted.dbengine import DB
from twisted.internet import defer
from autobahn.twisted.wamp import ApplicationSession

from sqlauth.twisted.userdb import UserDb
from sqlauth.twisted.sessiondb import SessionDb
from sqlauth.twisted.authorizerouter import AuthorizeRouter, AuthorizeSession

class SessionData(ApplicationSession):
    def __init__(self, *args, **kwargs):
        log.msg("SessionData:__init__")
        self.svar = {}
        c = args[0]
        sd = args[1]

        # reap init variables meant only for us
        for i in ( 'topic_base', ):
            if i in kwargs:
                if kwargs[i] is not None:
                    self.svar[i] = kwargs[i]
                del kwargs[i]

        ApplicationSession.__init__(self,c)
        self.sessiondb = sd
        # we give the sessiondb a hook so it can publish add/delete
        sd.app_session = self
        return

    def onConnect(self):
        log.msg("SessionData:onConnect")
        self.join(self.config.realm, [u"wampcra"], u'sessiondata')

    def onChallenge(self, challenge):
        log.msg("SessionData:onChallenge {}".format(challenge))

    @inlineCallbacks
    def onJoin(self, details):
        log.msg("onJoin: {}".format(details))

        #
        # this call returns session ids that are registered in memory
        #
        @inlineCallbacks
        def list_session_id(*args, **kwargs):
            log.msg("SessionData:list_session_id()")
            qv = yield self.sessiondb.listid()

            log.msg("list_session_data:qv:{}".format(qv))

            defer.returnValue(qv)

        #
        # this call returns session ids for things that came into existence before
        # we could record them in memory or on disk
        #
        def list_session_sys_id(*args, **kwargs):
            log.msg("SessionData:list_session_sys_id()")
            qv = self.sessiondb.get_system_sessions()
            log.msg("list_session_sys_id:qv:{}".format(qv))

            return(qv)

        #def kill_session(*args, **kwargs):
        #    sid = kwargs['sid']
        #    log.msg("SessionData:kill_session({})".format(sid))
        #    ses = self.sessiondb.get(sid)
        #    ses._transport.sendClose(code=3000,reason=six.u('killed'))
        #    return defer.succeed({ 'killed': sid })

        # this call returns a dictionary, keys are session id, value is a dictionary with at least 'authid' in it
        reg = yield self.register(list_session_id, self.svar['topic_base']+'.session.listid',
            RegisterOptions(details_arg = 'details'))
        reg = yield self.register(list_session_sys_id, self.svar['topic_base']+'.session.listsysid',
            RegisterOptions(details_arg = 'details'))

    def onLeave(self, details):
        log.msg("onLeave: {}".format(details))

    def onDisconnect(self):
        log.msg("disconnected")


class PendingAuth:
    """
    User for tracking pending authentications.
    """

    def __init__(self, key, session, authid, authrole, authmethod, authprovider, uid):
        self.authid = authid
        self.authrole = authrole
        self.authmethod = authmethod
        self.authprovider = authprovider
        self.uid = uid

        self.session = session
        self.timestamp = util.utcnow()
        self.nonce = util.newid()

        challenge_obj = {
            'authid': self.authid,
            'authrole': self.authrole,
            'authmethod': self.authmethod,
            'authprovider': self.authprovider,
            'session': self.session,
            'nonce': self.nonce,
            'timestamp': self.timestamp
        }
        self.challenge = json.dumps(challenge_obj, ensure_ascii = False)
        self.signature = auth.compute_wcs(key.encode('utf8'), self.challenge.encode('utf8')).decode('ascii')


class MyRouterSession(RouterSession):
    """
    Our custom router session that authenticates via WAMP-CRA.
    """
    @defer.inlineCallbacks
    def onHello(self, realm, details):
        """
        Callback fired when client wants to attach session.
        """
        log.msg("onHello: {} {}".format(realm, details))

        self._pending_auth = None

        if details.authmethods:
            for authmethod in details.authmethods:
                if authmethod == u"wampcra":

                    ## lookup user in user DB
                    salt, key, role, uid = yield self.factory.userdb.get(details.authid)
                    log.msg("salt, key, role: {} {} {} {}".format(salt, key, role, uid))

                    ## if user found ..
                    if key:

                        log.msg("found key")

                        ## setup pending auth
                        self._pending_auth = PendingAuth(key, details.pending_session,
                            details.authid, role, authmethod, u"userdb", uid)

                        log.msg("setting challenge")
                        ## send challenge to client
                        extra = {
                            u'challenge': self._pending_auth.challenge
                        }

                        ## when using salted passwords, provide the client with
                        ## the salt and then PBKDF2 parameters used
                        if salt:
                            extra[u'salt'] = salt
                            extra[u'iterations'] = 1000
                            extra[u'keylen'] = 32

                        defer.returnValue(types.Challenge(u'wampcra', extra))

        ## deny client
        defer.returnValue(types.Deny())


    def onAuthenticate(self, signature, extra):
        """
        Callback fired when a client responds to an authentication challenge.
        """
        log.msg("onAuthenticate: {} {}".format(signature, extra))

        ## if there is a pending auth, and the signature provided by client matches ..
        if self._pending_auth:

            if signature == self._pending_auth.signature:

                ## accept the client
                return types.Accept(authid = self._pending_auth.uid,
                    authrole = self._pending_auth.authrole,
                    authmethod = self._pending_auth.authmethod,
                    authprovider = self._pending_auth.authprovider)
            else:

                ## deny client
                return types.Deny(message = u"signature is invalid")
        else:

            ## deny client
            return types.Deny(message = u"no pending authentication")

    def onJoin(self, details):
        log.msg("MyRouterSession.onJoin: {}".format(details))
        self.factory.sessiondb.add(details.authid, details.session, self)
        self.factory.sessiondb.activity(details.session, details.session, 'start', True)
        return

    def onLeave(self, details):
        log.msg("MyRouterSession.onLeave: {}".format(details))
        self.factory.sessiondb.activity(self._session_id, details.message, 'end', True)
        self.factory.sessiondb.delete(self._session_id)
        return

    def onDisconnect(self, details):
        log.msg("onDisconnect: {}".format(details))
        return


def run():
    import sys, argparse
    from twisted.python import log
    from twisted.internet.endpoints import serverFromString

    ## parse command line arguments
    ##

    def_wsocket = 'ws://127.0.0.1:8080/ws'
    def_realm = 'realm1'
    def_topic_base = 'sys'
    def_dsn = 'dbname=autobahn host=localhost user=autouser'
    def_endpoint='tcp:8080'
    def_engine = 'PG9_4'

    p = argparse.ArgumentParser(description="basicrouter example with database")

    p.add_argument('-w', '--websocket', action='store', dest='wsocket', default=def_wsocket,
                        help='web socket '+def_wsocket)
    p.add_argument('-r', '--realm', action='store', dest='realm', default=def_realm,
                        help='connect to websocket using "realm", default '+def_realm)
    p.add_argument('-v', '--verbose', action='store_true', dest='verbose',
            default=False, help='Verbose logging for debugging')
    p.add_argument('--debug', action='store_true', dest='debug',
            default=False, help='Autobahn layer debugging')
    p.add_argument('-e', '--engine', action='store', dest='engine', default=def_engine,
                        help='if specified, a database engine will be attached. Note engine is rooted on --topic')
    p.add_argument("--endpoint", type = str, default = "tcp:8080",
          help = 'Twisted server endpoint descriptor, e.g. "tcp:8080" or "unix:/tmp/mywebsocket", default is "' + def_endpoint + '"')
    p.add_argument('-d', '--dsn', action='store', dest='dsn', default=def_dsn,
                        help='if specified the database in dsn will be connected and ready')
    p.add_argument('-t', '--topic', action='store', dest='topic_base', default=def_topic_base,
                        help='if you specify --dsn then you will need a topic to root it on, the default ' + def_topic_base + ' is fine.')

    args = p.parse_args()
    if args.verbose:
        log.startLogging(sys.stdout)

    ## we use an Autobahn utility to install the "best" available Twisted reactor
    ##
    from autobahn.twisted.choosereactor import install_reactor
    reactor = install_reactor()
    log.msg("Running on reactor {}".format(reactor))

    # database workers...
    userdb = UserDb(topic_base=args.topic_base+'.db',debug=args.verbose)
    sessiondb = SessionDb(topic_base=args.topic_base,debug=args.verbose)

    ## create a WAMP router factory
    ##
    component_config = types.ComponentConfig(realm = args.realm)

    from autobahn.twisted.wamp import RouterFactory
    router_factory = RouterFactory()
    authorization_session = AuthorizeSession(component_config,
        topic_base=args.topic_base+'.db',debug=args.verbose,db=sessiondb,router=AuthorizeRouter)
    router_factory.router = authorization_session.ret_func

    ## create a WAMP router session factory
    ##
    from autobahn.twisted.wamp import RouterSessionFactory
    session_factory = RouterSessionFactory(router_factory)
    session_factory.session = MyRouterSession

    log.msg("session_factory.session")

    session_factory.userdb = userdb
    session_factory.sessiondb = sessiondb

    log.msg("userdb, sessiondb")

    sessiondb_component = SessionData(component_config,session_factory.sessiondb,
        topic_base=args.topic_base)
    session_factory.add(sessiondb_component)
    session_factory.add(authorization_session)

    log.msg("session_factory")

    db_session = DB(component_config, engine=args.engine,
        topic_base=args.topic_base+'.db', dsn=args.dsn, debug=args.verbose)
    session_factory.add(db_session)
    session_factory.userdb.set_session(db_session)
    session_factory.sessiondb.set_session(db_session)

    ## create a WAMP-over-WebSocket transport server factory
    ##
    from autobahn.twisted.websocket import WampWebSocketServerFactory
    transport_factory = WampWebSocketServerFactory(session_factory, debug = args.debug)
    transport_factory.setProtocolOptions(failByDrop = False)


    ## start the server from an endpoint
    ##
    ## this address clash detection was a goody I got from stackoverflow:
    ## http://stackoverflow.com/questions/12007316/exiting-twisted-application-after-listenfailure
    server = serverFromString(reactor, args.endpoint)
    def listen():
        srv = server.listen(transport_factory)
        def ListenFailed(reason):
            log.msg("On Startup Listen Failed with {}".format(reason))
            reactor.stop()
        srv.addErrback(ListenFailed)

    def addsession():
        log.msg("here are three sessions {} {} {}".format(authorization_session, sessiondb_component, db_session))
        qv = {
            "sessiondb_component":sessiondb_component._session_id,
            "db_session":db_session._session_id,
            "authorization_session":authorization_session._session_id
        }
        session_factory.sessiondb.set_system_sessions(qv)
        session_factory.sessiondb.add(0, sessiondb_component._session_id, sessiondb_component)
        session_factory.sessiondb.add(0, db_session._session_id, db_session)
        session_factory.sessiondb.add(0, authorization_session._session_id, authorization_session)

    reactor.callWhenRunning(listen)
    reactor.callWhenRunning(addsession)
    reactor.run()

if __name__ == '__main__':
    run()

