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
## sessiondb.py - interface to session data
##
## This tracks sessions in autobahn.  From the instantiation, to termination
## the session life cycle is tracked.
###############################################################################

import six,sys,logging

from twisted.python import log
from twisted.internet.defer import inlineCallbacks

from autobahn import util
from autobahn.wamp import auth
from autobahn.wamp import types
from autobahn.wamp.interfaces import IRouter
from autobahn.twisted.wamp import Router
from autobahn.twisted.wamp import RouterSession
from twisted.internet import defer
from autobahn.twisted.wamp import ApplicationSession

class SessionDb(object):
    """
    A session database.
    """

    #
    # SessionDb needs to have an app_session to perform the query against. This can
    # be any application session with the authorization to run the rpcs in topic_base.
    # it doeesn't have to be set when the object is created, you can call set_session
    # with the information later.
    #
    # topic_base could be 'sys.db', such that 'sys.db.query' and 'sys.db.watch' and 'sys.db.operation'
    # are all available, and the connection has already been made.
    #
    # this only actively tracks 'active' sessions.  once terminated they are no
    # longer available through this interface (like list/get).
    #
    def __init__(self, topic_base, debug=False, app_session=None):
        if debug is not None and debug:
            log.startLogging(sys.stdout)
        log.msg("SessionDb:__init__()")
        self._sessiondb = {}
        self.app_session = app_session
        self.topic_base = topic_base
        self.query = topic_base + '.query'
        self.operation = topic_base + '.operation'
        self.watch = topic_base + '.watch'
        self.debug = debug
        self.system_sessions = None

        return

    def set_session(self, app_session):
        log.msg("SessionDb:set_session()")
        self.app_session = app_session

        return
 
    def set_system_sessions(self, sysses):
        log.msg("SessionDb:set_system_sessions({})".format(sysses))
        self.system_sessions = sysses

        return

    def get_system_sessions(self):
        log.msg("SessionDb:get_system_sessions({})".format(self.system_sessions))
        return (self.system_sessions)
 
    @inlineCallbacks
    def add(self, authid, sessionid, session_body):
        log.msg("SessionDb.add({},sessionid:{})".format(authid,sessionid))
        # first, we remember the session internally in our object store
        self._sessiondb[sessionid] = session_body
        # then record the session in the database
        log.msg("SessionDb.add({}session:{})".format(authid,sessionid))
        try:
            rv = yield self.app_session.call('sys.session.add',
                action_args={ 'login_id':authid, 'ab_session_id':sessionid },
                options = types.CallOptions(timeout=2000,discloseMe = True))
        except Exception as e:
            log.msg("SessionDb.add({}-{},error{})".format(authid,sessionid,e))
            pass
        log.msg("SessionDb.add({},body:{})".format(authid,session_body))

        return

    @inlineCallbacks
    def activity(self, sessionid, topic_name, activity_type, allow):
        log.msg("SessionDb.activity({},{},{},{})".format(sessionid,topic_name,activity_type,allow))
        # then record the session in the database
        yield self.app_session.call(self.operation,
                """insert into activity (session_id,topic_name,type_id,allow)
                   values(
                    (select id from session where ab_session_id = %(session_id)s),
                     %(topic_name)s, %(activity_type)s, %(allow)s)""",
                   { 'topic_name': topic_name,
                      'session_id': sessionid,
                      'activity_type': activity_type,
                      'allow': allow }, options=types.CallOptions(timeout=2000,discloseMe=True))

        return

    #def get(self, sessionid):
    #    log.msg("SessionDb.get({})".format(sessionid))
    #    ## we return a deferred to simulate an asynchronous lookup
    #    return self._sessiondb.get(sessionid, {})

    #
    # build an array of live sessions
    #
    def listid(self):
        s = {}
        log.msg("SessionDb.listid()")
        for k in self._sessiondb.keys():
            s[k] = { 'authid': self._sessiondb[k]._authid }
        return(s)

    @inlineCallbacks
    def delete(self, sessionid):
        log.msg("SessionDb.delete({})".format(sessionid))
        try:
            rv = yield self.app_session.call('sys.session.delete',
                action_args={ 'ab_session_id':sessionid },
                options = types.CallOptions(timeout=2000,discloseMe = True))
        except Exception as e:
            log.msg("SessionDb.delete({},error{})".format(sessionid,e))
            pass

        ## this terminates the session in the database
        #yield self.app_session.call(self.operation,
        #        "update session set ab_session_id = null where ab_session_id = %(session_id)s",
        #        { 'session_id': sessionid }, options=types.CallOptions(timeout=2000,discloseMe=True))

        try:
            # then discard of our in memory copy
            del self._sessiondb[sessionid]
        except:
            pass
        return
