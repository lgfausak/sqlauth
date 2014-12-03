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
        self.debug = debug
        self.system_sessions = None

        return

    # this sets the autobahn application that we run against for call,register,publish,subscribe
    def set_session(self, app_session):
        log.msg("SessionDb:set_session()")
        self.app_session = app_session
        return
 
    # there are a few sessions that start before we start recording them, this
    # routine lets the startup routine record the unrecorded sessions.
    def set_system_sessions(self, sysses):
        log.msg("SessionDb:set_system_sessions({})".format(sysses))
        self.system_sessions = sysses

        return

    # return the value set by set_system_sessions().
    # this routine and the above routine are only called once per autobahn router
    def get_system_sessions(self):
        log.msg("SessionDb:get_system_sessions({})".format(self.system_sessions))
        return (self.system_sessions)
 
    # add a new session.
    # we have an internal session hash which lets us record each time the
    # router has another session associated with it.  we also have a call
    # to sys.session.add which initially doesn't exist.  this is the long
    # term persistence, a database.
    @inlineCallbacks
    def add(self, authid, sessionid, session_body):
        log.msg("SessionDb.add({},sessionid:{})".format(authid,sessionid))
        # first, we remember the session internally in our object store
        self._sessiondb[sessionid] = session_body
        # then record the session in the database
        log.msg("SessionDb.add({}session:{})".format(authid,sessionid))
        try:
            rv = yield self.app_session.call(self.topic_base+'.session.add',
                action_args={ 'login_id':authid, 'ab_session_id':sessionid },
                options = types.CallOptions(timeout=2000,discloseMe = True))
            defer.returnValue(rv)
        except Exception as e:
            # if we get an error we don't really care, it just means that the session
            # isn't recorded in the database.  maybe the database doesn't exist yet.
            log.msg("SessionDb.add({}-{},error{})".format(authid,sessionid,e))
            pass
        log.msg("SessionDb.add({},body:{})".format(authid,session_body))

        return

    @inlineCallbacks
    def activity(self, ab_session_id, topic_name, type_id, allow):
        log.msg("SessionDb.activity({},{},{},{})".format(ab_session_id,
            topic_name,type_id,allow))
        if topic_name != self.topic_base+'.activity.add':
            try:
                rv = yield self.app_session.call(self.topic_base+'.activity.add',
                    action_args={ 'ab_session_id':ab_session_id,
                        'topic_name':topic_name,
                        'type_id':type_id,
                        'allow':allow},
                    options = types.CallOptions(timeout=2000,discloseMe = True))
                defer.returnValue(rv)
            except Exception as e:
                # if we get an error we don't really care, it just means that the activity
                # isn't recorded in the database.  maybe the database doesn't exist yet.
                log.msg("SessionDb.activity({},error{})".format(ab_session_id,e))
                pass
        else:
            defer.returnValue([])
        log.msg("SessionDb.activity({},done)".format(ab_session_id))

        return

    # return a dictionary of all of the in memory sessions. this is used
    # by the session.list call which compares its sessions with the memory
    # ones, only the memory ones are listed.  old sessions can be in the database
    # for a number of reasons.
    def listid(self):
        s = {}
        log.msg("SessionDb.listid()")
        for k in self._sessiondb.keys():
            s[k] = { 'authid': self._sessiondb[k]._authid }
        return(s)

    # delete in memory and possible persistent session record.
    @inlineCallbacks
    def delete(self, sessionid):
        log.msg("SessionDb.delete({})".format(sessionid))
        try:
            rv = yield self.app_session.call(self.topic_base+'.session.delete',
                action_args={ 'ab_session_id':sessionid },
                options = types.CallOptions(timeout=2000,discloseMe = True))
        except Exception as e:
            log.msg("SessionDb.delete({},error{})".format(sessionid,e))
            pass

        try:
            # then discard of our in memory copy
            del self._sessiondb[sessionid]
        except:
            pass
        return
