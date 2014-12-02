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
## session (list,add,delete,get)
##   list   - list all sessions
##
###############################################################################

from __future__ import absolute_import

import sys, os, argparse, six, json, logging
from tabulate import tabulate
import types as vtypes

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
        if not 'topic_base' in self.svar:
            raise Exception("topic_base is mandatory")
        self.query = self.svar['topic_base'] + '.db.query'
        self.operation = self.svar['topic_base'] + '.db.operation'
        self.watch = self.svar['topic_base'] + '.db.watch'
        self.info = self.svar['topic_base'] + '.db.info'

        log.msg("sending to super.init args {}, kwargs {}".format(args,kwargs))
        ApplicationSession.__init__(self, *args, **kwargs)

    # simple function to change a dictionary from each row
    # to an array of arrays, first row contains the column names
    # second+ rows contain the data.  this routine does not assume
    # that each row has the same keys, so it loops through the
    # entire result set looking for all the unique keys if
    # fullscan=True is in kwargs
    def _columnize(self, *args, **kwargs):
        if len(args) < 1:
            raise Exception("must supply list of dictionaries")
        if not isinstance(args[0], vtypes.ListType):
            raise Exception("fist argument must be list of dictionaries")
        qv = args[0]
        if len(qv) == 0:
            return []
        kv = {}
        # pass argument fullscan=True to consider all rows for column headers
        fs = kwargs.get('fullscan', False)

        for r in qv:
            for k in r.keys():
                kv[k] = True
            # here we only consider the first row if is fullscan is not set.
            # in other words, every row contains the same column keys
            if not fs:
                break

        rv = []
        ra = kv.keys()
        rv.append(ra)
        #append a row in the array for each result, in the same order as the original row 1
        for r in qv:
            rv.append([r.get(c,None) for c in ra])

        return rv

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
    def userList(self, *args, **kwargs):
        log.msg("userList called {}".format(kwargs))
        qv = yield self.call(self.query,
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
                     where
                        l.login is not null
		  group by
		  	l.id
		  order by
		     	l.login
		   """,
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
        defer.returnValue(self._columnize(qv))

    @inlineCallbacks
    def userGet(self, *args, **kwargs):
        log.msg("userGet called {}".format(kwargs))
        qv = yield self.call(self.query,
                """
                    select
                        password, salt, login, fullname, tzname, id
                      from
                        login
		     where
		     	login = %(login)s
		   """,
                   kwargs['action_args'], options=types.CallOptions(timeout=2000,discloseMe=True))
        defer.returnValue(self._columnize(qv))

    @inlineCallbacks
    def userAdd(self, *args, **kwargs):
        log.msg("userAdd called {}".format(kwargs))
        salt = os.urandom(32).encode('base_64')
        qa = kwargs['action_args']
        password = auth.derive_key(qa['secret'].encode('utf8'), salt.encode('utf8')).decode('ascii')
        qa['salt'] = salt
        qa['password'] = password
        qv = yield self.call(self.query,
                """
                    insert into
                        login
                    (
                        login, fullname, password, salt, tzname
                    )
                    values
                    (
                        %(login)s, %(fullname)s, %(password)s, %(salt)s, %(tzname)s
                    )
                    returning
                        id, login, fullname
		   """,
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))
        # qv[0] contains the result
        
        defer.returnValue(self._columnize(qv))

    # the account isn't deleted, rather, its login name is nulled
    # and its groups are removed
    @inlineCallbacks
    def userDelete(self, *args, **kwargs):
        log.msg("userDelete called {}".format(kwargs))
        qa = kwargs['action_args']
        rtitle = [
            "Login to role association",
            "Login"
        ]
        qv = yield self.call(self.query,
                [
                    """
                    delete
                      from
                        loginrole
                     where
                       login_id = (
                           select id from login where login = %(login)s
                       )
                 returning
                        id, login_id, role_id
		    """,
                    """
                    update
                        login
                       set
                        login = null,
                        salt = 'shutdown',
                        password = 'inactive',
                        old_login = %(login)s
                     where
                        login = %(login)s
                 returning
                        id, old_login as login, password, salt
		    """
                   ],
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))
        # qv[0] contains the results as an array of dicts, one dict for each query that ran

        if isinstance(qv, vtypes.DictType):
            # this will never happen for this query.
            defer.returnValue(self._columnize(qv))
        else:
            # this case will always happen
            rv = {}
            for ri in range(len(qv)):
                rv[ri] = {}
                rv[ri]['title'] = rtitle[ri]
                rv[ri]['result'] = self._columnize(qv[ri])
            # we have a dict, keys are numbers starting with 0 increasing by 1, values are
            # the array of results, first row is header, second row - end is data.
            defer.returnValue(rv)

    @inlineCallbacks
    def roleList(self, *args, **kwargs):
        log.msg("roleList called {}".format(kwargs))
        qv = yield self.call(self.query,
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
        defer.returnValue(self._columnize(qv))

    @inlineCallbacks
    def roleGet(self, *args, **kwargs):
        log.msg("roleGet called {}".format(kwargs))
        qv = yield self.call(self.query,
                """
                    select
                        name, description, id
                      from
                        role
		     where
		     	name = %(name)s
		   """,
                   kwargs['action_args'], options=types.CallOptions(timeout=2000,discloseMe=True))
        defer.returnValue(self._columnize(qv))

    @inlineCallbacks
    def roleAdd(self, *args, **kwargs):
        log.msg("roleAdd called {}".format(kwargs))
        qa = kwargs['action_args']
        qv = yield self.call(self.query,
                """
                    insert into
                        role
                    (
                        name, description
                    )
                    values
                    (
                        %(name)s, %(description)s
                    )
                    returning
                        id, name, description
		   """,
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))
        # qv[0] contains the result
        
        defer.returnValue(self._columnize(qv))

    # the account isn't deleted, rather, its login name is nulled
    # and its groups are removed
    @inlineCallbacks
    def roleDelete(self, *args, **kwargs):
        log.msg("roleDelete called {}".format(kwargs))
        qa = kwargs['action_args']
        rtitle = [
            "Role to topic association",
            "Role"
        ]
        qv = yield self.call(self.query,
                [
                    """
                    delete
                      from
                        topicrole
                     where
                       role_id = (
                           select id from role where name = %(name)s
                       )
                 returning
                        id, topic_id, role_id
		    """,
                    """
                    delete
                      from
                        role
                     where
                        name = %(name)s
                 returning
                        id, name, description
		    """
                   ],
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))
        # qv[0] contains the results as an array of dicts, one dict for each query that ran

        if isinstance(qv, vtypes.DictType):
            # this will never happen for this query.
            defer.returnValue(self._columnize(qv))
        else:
            # this case will always happen
            rv = {}
            for ri in range(len(qv)):
                rv[ri] = {}
                rv[ri]['title'] = rtitle[ri]
                rv[ri]['result'] = self._columnize(qv[ri])
            # we have a dict, keys are numbers starting with 0 increasing by 1, values are
            # the array of results, first row is header, second row - end is data.
            defer.returnValue(rv)

    @inlineCallbacks
    def topicList(self, *args, **kwargs):
        log.msg("topicList called {}".format(kwargs))
        qv = yield self.call(self.query,
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
        defer.returnValue(self._columnize(qv))

    @inlineCallbacks
    def topicGet(self, *args, **kwargs):
        log.msg("topicGet called {}".format(kwargs))
        qv = yield self.call(self.query,
                """
                    select
                        name, description, id
                      from
                        topic
		     where
		     	name = %(name)s
		   """,
                   kwargs['action_args'], options=types.CallOptions(timeout=2000,discloseMe=True))
        defer.returnValue(self._columnize(qv))

    @inlineCallbacks
    def topicAdd(self, *args, **kwargs):
        log.msg("topicAdd called {}".format(kwargs))
        qa = kwargs['action_args']
        qv = yield self.call(self.query,
                """
                    insert into
                        topic
                    (
                        name, description
                    )
                    values
                    (
                        %(name)s, %(description)s
                    )
                    returning
                        id, name, description
		   """,
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))
        # qv[0] contains the result
        
        defer.returnValue(self._columnize(qv))

    # the account isn't deleted, rather, its login name is nulled
    # and its groups are removed
    @inlineCallbacks
    def topicDelete(self, *args, **kwargs):
        log.msg("topicDelete called {}".format(kwargs))
        qa = kwargs['action_args']
        rtitle = [
            "Topic to role association",
            "Role"
        ]
        qv = yield self.call(self.query,
                [
                    """
                    delete
                      from
                        topicrole
                     where
                       topic_id = (
                           select id from topic where name = %(name)s
                       )
                 returning
                        id, topic_id, role_id
		    """,
                    """
                    delete
                      from
                        topic
                     where
                        name = %(name)s
                 returning
                        id, name, description
		    """
                   ],
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))
        # qv[0] contains the results as an array of dicts, one dict for each query that ran

        if isinstance(qv, vtypes.DictType):
            # this will never happen for this query.
            defer.returnValue(self._columnize(qv))
        else:
            # this case will always happen
            rv = {}
            for ri in range(len(qv)):
                rv[ri] = {}
                rv[ri]['title'] = rtitle[ri]
                rv[ri]['result'] = self._columnize(qv[ri])
            # we have a dict, keys are numbers starting with 0 increasing by 1, values are
            # the array of results, first row is header, second row - end is data.
            defer.returnValue(rv)

    @inlineCallbacks
    def activityListold(self, *args, **kwargs):
        log.msg("activityList called {}".format(kwargs))
	av = yield self.call('adm.session.list', options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(av) == 0:
            defer.returnValue([])
            return

        idx = 0
        try:
            idx = av[0].index('id')
        except:
            log.msg("activityList: can't find id field in session list: {}, returning".format(av[0]))
            defer.returnValue([])
            return

        # this array contains the session_id for all of the active sessions
        active_sessions = [a[idx] for a in av[1:]]
            
        # this query picks up active activity, for which there is a current session
        # call, register, publish, subscribe are the interesting activities.
        # this activity could be bound to a session that no longer exists, that is why we
        # pick up the X.session.list from above, that returns just the
        # active sessions. we use that to filter the list we get back from
        # this query.  if the database is in sync with the router, then these two will
        # be identical.  otherwise, if the router has crashed and cleanup hasn't happened,
        # or is multiple routers are sharing the same sqlauth installation, then there
        # could be more entries in the database than there is in the router.
        qv = yield self.call(self.query,
                """
                    select
                        a.id, a.session_id, s.ab_session_id, a.type_id, a.topic_name, l.login,
                        to_char(a.modified_timestamp,'YYYY-MM-DD HH24:MI:SS') as action_timestamp
		      from
		        activity a,
                        session s,
                        login l
                     where
                        a.session_id = s.id
                       and
                        a.allow = true
                       and
                        a.type_id in ( 'call', 'register', 'subscribe', 'publish' )
                       and
                        s.login_id = l.id
                       and
                        s.ab_session_id is not null
		  order by
		     	a.id
		   """,
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(qv) == 0:
            defer.returnValue([])
            return

        ra = qv[0].keys()
        rv = []
        rv.append(ra)
        for r in qv:
            if r['session_id'] in active_sessions:
                rv.append([r.get(c,None) for c in ra])

        defer.returnValue(rv)

    @inlineCallbacks
    def activityList(self, *args, **kwargs):
        log.msg("activityList called {}".format(kwargs))
	active_sessions = yield self.call(self.svar['topic_base'] + '.session.list',
            options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(active_sessions) == 0:
            defer.returnValue([])
            return

        # this query picks up active activity, for which there is a current session
        # call, register, publish, subscribe are the interesting activities.
        # this activity could be bound to a session that no longer exists, that is why we
        # pick up the X.session.list from above, that returns just the
        # active sessions. we use that to filter the list we get back from
        # this query.  if the database is in sync with the router, then these two will
        # be identical.  otherwise, if the router has crashed and cleanup hasn't happened,
        # or is multiple routers are sharing the same sqlauth installation, then there
        # could be more entries in the database than there is in the router.
        qv = yield self.call(self.query,
                """
                    select
                        a.id, a.session_id, s.ab_session_id, a.type_id, a.topic_name, l.login,
                        to_char(a.modified_timestamp,'YYYY-MM-DD HH24:MI:SS') as action_timestamp
		      from
		        activity a,
                        session s,
                        login l
                     where
                        a.session_id = s.id
                       and
                        a.allow = true
                       and
                        a.type_id in ( 'call', 'register', 'subscribe', 'publish' )
                       and
                        s.login_id = l.id
                       and
                        s.ab_session_id is not null
		  order by
		     	a.id
		   """,
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(qv) == 0:
            defer.returnValue([])
            return

        ra = qv[0].keys()
        rv = []
        rv.append(ra)
        for r in qv:
            if r['session_id'] in active_sessions:
                rv.append([r.get(c,None) for c in ra])

        defer.returnValue(rv)

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
    def sessionList(self, *args, **kwargs):
        log.msg("sessionList()")
        sidkeys = yield self.call('sys.session.listid')
        log.msg("sessionList:sidkeys {}".format(sidkeys))

        qv = yield self.call(self.query,
                """select s.login_id,s.ab_session_id,s.tzname,
                          to_char(s.created_timestamp,'YYYY-MM-DD HH24:MI:SS') as started,
                          to_char(now() - s.created_timestamp, 'HH24:MI:SS') as duration,
                          s.id,
                          l.login,
                          l.fullname
                     from session s,
                          login l
                   where l.id = s.login_id
                     and s.ab_session_id is not null""",
                   {}, options=types.CallOptions(timeout=2000,discloseMe=True))
        rv = {}
        for k in qv:
	    sid = k['ab_session_id']
            log.msg("sessionList:qv.key({})".format(sid))
	    if sid in sidkeys:
	        rv[sid] = k
	    else:
                log.msg("sessionList:warning")
	        k['warning'] = '!'
                log.msg("sessionList: db has extra sessions, should set ab_session_id null:{}, authid: {}!".format(sid,k['login_id']),
                    logLevel = logging.WARNING)
                #uncomment this if we want to see invalid sessions, they were probably left there
                #after an unplanned stop of the Autobahn router.  These should be set to null
                #before starting the router, with the statement:
                #update session set ab_session_id = null wher ab_session_id is not null
                #after that, then start the router.
	        #rv[sid] = k
        rvkeys = rv.keys()
        log.msg("sessionList:rvkeys {}".format(rvkeys))
        for k in sidkeys:
	    if k in rvkeys:
                log.msg("sessionList:continue")
	        continue
            log.msg("sessionList:on {}".format(k))
            sib = sidkeys[k]
            log.msg("sessionList: session in memory but not in db, this can happen if sessions are deleted while running the Autobahn router, ab_session_id:{}, authid: {}!".format(k,sib['authid']),
                logLevel = logging.WARNING)
            rv[k] = { 'ab_session_id':k,
                      'login_id': sib['authid'],
		      'warning': '*'}

        log.msg("sessionList:Ended up with {}".format(rv.values()))

        defer.returnValue(self._columnize(rv.values(), fullscan=True))

    @inlineCallbacks
    def onJoin(self, details):
        log.msg("onJoin session attached {}".format(details))
        rpc_register = {
            'user.list': {'method': self.userList },
            'user.get': {'method': self.userGet },
            'user.add': {'method': self.userAdd },
            'user.delete': {'method': self.userDelete },
            'role.list': {'method': self.roleList },
            'role.get': {'method': self.roleGet },
            'role.add': {'method': self.roleAdd },
            'role.delete': {'method': self.roleDelete },
            'topic.list': {'method': self.topicList },
            'topic.get': {'method': self.topicGet },
            'topic.add': {'method': self.topicAdd },
            'topic.delete': {'method': self.topicDelete },
            'activity.list': {'method': self.activityList },
            'session.list': {'method': self.sessionList }
        }
        #
        # register postgres admin functions
        #
        for r in rpc_register.keys():
            try:
                reg = yield self.register(rpc_register[r]['method'],
                    self.svar['topic_base'] + '.' + r,
                    RegisterOptions(details_arg = 'details'))
                log.msg("onJoin register {}".format(self.svar['topic_base']+'.'+r))
            except Exception as e:
                log.msg("onJoin register exception {} {}".format(self.svar['topic_base']+'.'+r, e))
                self.leave(reason=six.u(e.__class__.__name__),log_message=six.u('test'))

    def onLeave(self, details):
        sys.stderr.write("Leaving realm : {}\n".format(details))
        log.msg("onLeave: {}".format(details))

        self.disconnect()

        return

    def onDisconnect(self):
        log.msg("onDisconnect:")
        reactor.stop()

def run():
    prog = os.path.basename(__file__)

    def_wsocket = 'ws://127.0.0.1:8080/ws'
    def_user = 'adm'
    def_secret = '123test'
    def_realm = 'realm1'
    def_topic_base = 'sys'
    def_action_args = '{}'

    p = argparse.ArgumentParser(description="sqlauthrpc postgres backend rpc definitions")

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
