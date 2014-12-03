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

###############################################################################
## authorizerouter.py - authorization router
##
## this code sits in the authorize method and makes sure that all requests
## are authorized.  it requires a database connection and the authentication/
## authorization database.
###############################################################################

import json
import sys
import six
import types as vtypes

from twisted.python import log
from twisted.internet.defer import inlineCallbacks, returnValue

from autobahn import util
from autobahn.wamp import auth
from autobahn.wamp import types
from autobahn.wamp.interfaces import IRouter
from autobahn.twisted.wamp import Router
from autobahn.twisted.wamp import RouterSession
from twisted.internet import defer
from autobahn.twisted.wamp import ApplicationSession

class AuthorizeSession(ApplicationSession):
    def ret_func(self, *args, **kwargs):
        log.msg("in ret_func {} {}".format(args,kwargs))
        if not 'router' in self.svar:
            log.msg("router not set in ret_funcs svar")
            raise Exception("PreAuthRouter doesn't have the router set!")
        log.msg("calling function")
        self.svar['app_session'] = self

        fnc = self.svar['router'] (*args, **dict(self.svar.items() + kwargs.items()))

        log.msg("returning that new class")

        return fnc

    def __init__(self, *args, **kwargs):
        self.svar = {}

        log.msg("AuthorizeSession __init__ {},{}".format(args,kwargs))

        # reap init variables meant only for us
        for i in ( 'topic_base', 'app_session', 'debug', 'db', 'router',  ):
            if i in kwargs:
                if kwargs[i] is not None:
                    self.svar[i] = kwargs[i]
                del kwargs[i]

        if 'debug' in self.svar:
            self.debug = self.svar['debug']
            if self.debug:
                log.startLogging(sys.stdout)

        log.msg("PreAuthRouter is ready {},{}".format(args,kwargs))

        ApplicationSession.__init__(self,*args, **kwargs)

        return

class AuthorizeRouter(Router):
    def __init__(self, *args, **kwargs):
        self.svar = {}

        # reap init variables meant only for us
        for i in ( 'topic_base', 'app_session', 'debug', 'db', 'router', ):
            if i in kwargs:
                if kwargs[i] is not None:
                    self.svar[i] = kwargs[i]
                del kwargs[i]

        if 'debug' in self.svar:
            self.debug = self.svar['debug']
            if self.debug:
                log.startLogging(sys.stdout)

        if 'db' in self.svar:
            self.sessiondb = self.svar['db']

        if 'app_session' in self.svar:
            self.app_session = self.svar['app_session']

        log.msg("sending to super.init args {}, kwargs {}".format(args,kwargs))

        if 'topic_base' in self.svar:
            self.topic_base = self.svar['topic_base']
            self.query = self.topic_base + '.query'
            self.operation = self.topic_base + '.operation'
            self.watch = self.topic_base + '.watch'

        Router.__init__(self, *args, **kwargs)

        return

    #
    # authid = integer, from auto.role.id (the id associated with the users login)
    # uri = topic, like com.db.query
    # action = subscribe,publish,etc, from the auto.activity_type.id column
    #
    # we search 'down' the topic '.' (dot) separated list, first hit is our permission to use
    # for example:
    # com.db.query.
    # first we look for permissions with our user with 'com', then 'com.db', then 'com.db.query'.
    # if no permissions exist for all three then the user doesn't have permission.
    # if we get a hit, the first hit is the permission to use. we get the 'allow' column from
    # the topicrole permission table and return that.  using that means that permissions can be
    # allowed (True), or revoked (False).
    #
    @inlineCallbacks
    def check_permission(self, authid, uri, action):
        log.msg("AuthorizeRouter.check_permission: {} {} {}".format(authid, uri, action))
        look = []
        pieces = uri.split('.')
        accum = ''
        extra = ''
        for p in pieces:
            accum = accum + extra + p
            extra = '.'
            look.append(accum)

        query = """
        select t.name, length(t.name) as topic_length, tr.allow
          from topic as t,
               topicrole as tr,
               loginrole as lr
         where
            t.name in %(topiclist)s
           and
            t.id = tr.topic_id
           and
            tr.role_id = lr.role_id
           and
            tr.type_id = %(action)s
           and
            lr.login_id = %(authid)s
      order by
            topic_length"""
        log.msg("AuthorizeRouter.check_permission: query: {}".format(query))
        args = { 'topiclist': tuple(look), 'authid': authid, 'action': action }
        log.msg("AuthorizeRouter.check_permission: args: {}".format(args))

        rv = yield self.app_session.call(self.query, query, args, options = types.CallOptions(timeout=2000,discloseMe=True))

        log.msg("AuthorizeRouter.check_permission: rv: {}".format(rv))

        perm = False
        if len(rv) > 0:
            perm = rv[0]['allow']
            if not isinstance(perm, vtypes.BooleanType):
                log.msg("perm is NOT boolean {}", perm)
                if perm == 't':
                    perm = True
                else:
                    perm = False
            log.msg("perm is {}".format(perm))

        returnValue(perm)

        return

    @inlineCallbacks
    def authorize(self, session, uri, action):
        authid = session._authid
        if authid is None:
            authid = 1
        log.msg("AuthorizeRouter.authorize: {} {} {} {} {}".format(authid,
            session._session_id, uri, IRouter.ACTION_TO_STRING[action], action))
        if authid != 1:
            rv = yield self.check_permission(authid, uri, IRouter.ACTION_TO_STRING[action])
        else:
            rv = yield True

        log.msg("AuthorizeRouter.authorize: rv is {}".format(rv))

        if not uri.startswith(self.svar['topic_base']):
            self.sessiondb.activity(session._session_id, uri, IRouter.ACTION_TO_STRING[action], rv)

        returnValue(rv)

        return

