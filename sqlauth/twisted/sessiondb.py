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

        return

    def set_session(self, app_session):
        log.msg("SessionDb:set_session()")
        self.app_session = app_session

        return
 
    @inlineCallbacks
    def add(self, authid, sessionid, session_body):
        log.msg("SessionDb.add({},sessionid:{})".format(authid,sessionid))
        log.msg("SessionDb.add({},body:{})".format(authid,session_body))
        # first, we remember the session internally in our object store
        self._sessiondb[sessionid] = session_body
        # then record the session in the database
        yield self.app_session.call(self.operation,
                """insert into session
                     (login_id,ab_session_id,tzname)
                   values
                     (%(login_id)s,%(session_id)s,(select tzname from login where id = %(login_id)s))""",
                { 'login_id': authid, 'session_id': sessionid },
                options=types.CallOptions(timeout=2000,discloseMe=True))

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

    def get(self, sessionid):
        log.msg("SessionDb.get({})".format(sessionid))
        ## we return a deferred to simulate an asynchronous lookup
        return self._sessiondb.get(sessionid, {})


    #
    # this builds a list of sessions.  Two sources for the list are used, and
    # it is important that those two sources are equal!  First, the database is queried
    # for all open sessions (those that have ab_session_id not null).  Those are compared
    # to the in memory copy (the active Autobahn session).  The session MUST be represented
    # in both places. The list can be inconsistent if:
    # 1) the data exists in the database but not in memory.  This can occur on
    #    a Autobahn router restart.  The router should set all ab_session_id to null
    #    on startup (they can get this way if the router crashed).
    # 2) the data exists in memory but not the database.  This would indicate there is
    #    a problem writing to the database?  I am not sure why this would happen.
    #
    @inlineCallbacks
    def list(self):
        log.msg("SessionDb.list()")
        qv = yield self.app_session.call(self.query,
                """select s.login_id,s.ab_session_id,s.tzname,
                          to_char(s.created_timestamp,'YYYY-MM-DD HH24:MI:SS') as started,
                          to_char(now() - s.created_timestamp, 'HH24:MI:SS') as duration,
                          l.login,
                          l.fullname
                     from session s,
                          login l
                   where l.id = s.login_id
                     and s.ab_session_id is not null""",
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
        rv = {}
        sidkeys =  self._sessiondb.keys()
        log.msg("SessionDb.list:sidkeys {}".format(sidkeys))
        for k in qv:
	    sid = int(k['ab_session_id'])
            log.msg("SessionDb.list:qv.key({})".format(sid))
	    if sid in sidkeys:
                log.msg("SessionDb.list:no warning")
	        k['warning'] = ''
	        rv[sid] = k
	    else:
                log.msg("SessionDb.list:warning")
	        k['warning'] = '!'
                log.msg("SessionDb.list: database has extra sessions, should set ab_session_id to null for:{}, authid: {}!".format(sid,k['login_id']))
                #uncomment this if we want to see invalid sessions, they were probably left there
                #after an unplanned stop of the Autobahn router.  These should be set to null
                #before starting the router, with the statement:
                #update session set ab_session_id = null wher ab_session_id is not null
                #after that, then start the router.
	        #rv[sid] = k
        rvkeys = rv.keys()
        log.msg("SessionDb.list:rvkeys {}".format(rvkeys))
        for k in self._sessiondb:
	    if k in rvkeys:
                log.msg("SessionDb.list:continue")
	        continue
            log.msg("SessionDb.list:on {}".format(k))
            sib = self._sessiondb[k]
            log.msg("SessionDb.list: session in memory but not in database ab_session_id:{}, authid: {}!".format(k,sib._authid))
            rv[k] = { 'ab_session_id':k,
                      'login_id': sib._authid,
		      'started':'.',
		      'duration':'.',
		      'login':'.',
		      'fullname':'.',
		      'txname':'.',
		      'warning': '*'}

        defer.returnValue(rv)

    @inlineCallbacks
    def delete(self, sessionid):
        log.msg("SessionDb.delete({})".format(sessionid))
        # this terminates the session in the database
        yield self.app_session.call(self.operation,
                "update session set ab_session_id = null where ab_session_id = %(session_id)s",
                { 'session_id': sessionid }, options=types.CallOptions(timeout=2000,discloseMe=True))
        try:
            # then discard of our in memory copy
            del self._sessiondb[sessionid]
        except:
            pass
        return
