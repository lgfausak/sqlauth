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
## this contains most of the sqlauth administration rpc calls.
## I have attempted to get
## all initial sessions into both memory and the database, at the preset
## time there are 4 system sessions when this module has completed
## registering.  I can probably get that cut down, see note below.
## all of these functions are simple front ends to database
## updates.  the database can be updated directly if needed.
##
## this module is specific to the database type accessible via topic_base.
## this is for the postgres database.
## the more i think about it the more the database access routines
## belong in here, not in the basicrouter, I will probably move them
## so the database connection and the database calls are all in one file.
##
## user (list,add,delete)
##   list   - show a list of users and the roles they belong to
##   add    - add a new user
##   delete - delete a user
## role (list,add,delete)
##   list   - show a list of roles and the users that belong to them
##   add    - add a new role
##   delete - delete a user
## topic (list,add,delete)
##   list   - show a list of topics and the roles that belong to them
##   add    - add a new topic
##   delete - delete a topic
## activity (list,add)
##   list   - show a list of activities that belong to active sessions
##   add    - add a new activity
## session (list,add,delete)
##   list   - list all sessions
##   add    - add a new session
##   delete - delete a session
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

    #
    # roleAdd
    #  name         -> name of the role to add, like 'dba' or 'tenant12'
    #  description  -> a description to associate with the role
    #  bind_topic   -> the topic binding for the role, like 'adm.dba' or 'com.tenants.tenant12'
    #  roles        -> array of roles to be a member of. like [ 'public', 'adm' ]
    #
    # This is the logic behind a role.
    # A role is 'bound' to a topic.  The topic is specified at role create time.
    # The topic can be just the role name, or, it can be prefixed by any
    # number of intermediate vectors. The entire bind name is prefixed with 'role.',
    # so in the above example we would ultimately have 'role.adm.dba' and 'role.com.tenants.tenant12'
    # The first step of creating a role is to create the topic binding, so the user creating
    # the role must have the permission to do that. Then the role itself is created with the
    # 'bind_to' field set to the topic we just created. Finally, an 'admin' record is created in
    # topicrole indicating that the new bind role topic has admin over that new topic.
    #
    @inlineCallbacks
    def roleAdd(self, *args, **kwargs):
        qa = kwargs['action_args']
        details = kwargs['details']
        log.msg("roleAdd called {},{}".format(args, kwargs))

        # this will throw exception if we don't have permission to add
        # this topic, so we won't proceed because of the exception
        rv = yield self.topicAdd( action_args={
            'topic_name':qa['bind_topic'],'description':qa['description'] }, details=kwargs['details'] )
        if len(rv) == 0:
            raise Exception("impossible situation, no return value from topicAdd in roleAdd")
        # we will bind the new role to the newly created topic.
        qa['bind_to'] = rv[1][rv[0].index('id')]
        # there is a transaction issue here.
        # i should really do the creation of the topic and the creation of the role
        # in the same transaction.  that would mess up my layering a bit, but it makes more
        # database sense.  however, because i am lazy, i am going to leave it this way.
        # that means that the role creation could fail and leave a dangling topic
        # this could happen if the role already exists, but the topic doesn't.
        # i might clean this up later if it ever matters.
        qv = yield self.call(self.query,
                """
                    insert into
                        role
                    (
                        name, description, bind_to
                    )
                    values
                    (
                        %(name)s, %(description)s, %(bind_to)s
                    )
                    returning
                        id, name, description, bind_to
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
    # checkPermission
    #  authid         -> the autobahn user id to check permission for
    #  topic_name     -> com.db, sys.whatever, etc..
    #  type_id        -> one of call,register,publish,subscribe,admin,start,end
    @inlineCallbacks
    def topicrolePermission(self, *args, **kwargs):
        qa = kwargs['action_args']
        log.msg("topicrolePermission: {} {} {}".format(qa['authid'], qa['topic_name'], qa['type_id']))
        s = qa['topic_name']
        log.msg("topicrolePermission: name {}".format(s))
        # this gives us an array of ['com','com.db','com.db.query'] in above example
        qa['topiclist'] = ['.'.join(s.split('.')[:i+1]) for i in range(s.count('.')+1)]
        log.msg("topicrolePermission: topiclist {}".format(qa['topiclist']))

        try:
            qv = yield self.call(self.query,
                """
                select
                        t.name, length(t.name) as topic_length, tr.allow
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
                        tr.type_id = %(type_id)s
                   and
                        lr.login_id = %(authid)s
              order by
                        topic_length
                """,
                    qa, options = types.CallOptions(timeout=2000,discloseMe=True))
        except Exception as e:
            log.msg("topicrolePermission: exception {}".format(e))

        log.msg("topicrolePermission: initial result {}".format(qv))

        # the allow is not coming back as a boolean, coerce here.
        for i in qv:
            if not isinstance(i['allow'], vtypes.BooleanType):
                if i['allow'] == 't':
                    i['allow'] = True
                else:
                    i['allow'] = False

        log.msg("topicrolePermission: result {}".format(qv))

        defer.returnValue(self._columnize(qv))

        return

    # topicAdd
    #  name           -> the name of the topic (com.db, com.db.query, etc)
    #  description    -> the description of the topic
    #
    # Note: the role adding the topic MUST have admin permission of something in
    #       topic hierarchy.  So, if you are adding com.db.query, you must have
    #       admin permission for com or com.db
    @inlineCallbacks
    def topicAdd(self, *args, **kwargs):
        log.msg("topicAdd called {}".format(kwargs))
        qa = kwargs['action_args']

        # permission from here
        details = kwargs['details']

        rv = yield self.topicrolePermission( action_args={
            'authid':details.authid, 'topic_name':qa['name'],'type_id':'admin' })

        log.msg("topicAdd.topicrolePermission {}".format(rv))
        if len(rv) == 0:
            raise Exception("no permission to add a topic in that hierchy")
        if not rv[1][rv[0].index('allow')]:
            raise Exception("False permission to add a topic in that hierchy")

        log.msg("topicAdd.topicrolePermission, assert, {} has permission for admin in {}".format(details.authid, qa['name']))
        # to here

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

        # permission from here
        details = kwargs['details']

        rv = yield self.topicrolePermission( action_args={
            'authid':details.authid, 'topic_name':qa['name'],'type_id':'admin' })

        log.msg("topicDelete.topicrolePermission {}".format(rv))
        if len(rv) == 0:
            raise Exception("no permission to delete a topic in that hierchy")
        if not rv[1][rv[0].index('allow')]:
            raise Exception("False permission to delete a topic in that hierchy")

        log.msg("topicDelete.topicrolePermission, assert, {} has permission for admin in {}".format(details.authid, qa['name']))
        # to here

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
    def activityList(self, *args, **kwargs):
        log.msg("activityList called {}".format(kwargs))
        qa = kwargs['action_args']
	av = yield self.call(self.svar['topic_base'] + '.session.listid',
            options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(av) == 0:
            defer.returnValue([])
            return

        active_sessions = av.keys()

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
            if r['ab_session_id'] in active_sessions:
                rv.append([r.get(c,None) for c in ra])

        defer.returnValue(rv)

    # activityAdd
    #  ab_session_id  -> the autobahn session id
    #  topic_name     -> com.db, sys.whatever, etc..
    #  type_id        -> one of call,register,publish,subscribe,admin,start,end
    #  allow          -> boolean, is the activity allowed or denied (true or false)
    @inlineCallbacks
    def activityAdd(self, *args, **kwargs):
        log.msg("activityAdd called {}".format(kwargs))
        qa = kwargs['action_args']
        qv = yield self.call(self.query,
                """
                    insert into
                        activity
                    (
                        session_id,topic_name,type_id,allow
                    )
                    values
                    (
                        (
                            select
                                    id
                              from
                                    session
                             where
                                    ab_session_id = %(ab_session_id)s
                        ),
                        %(topic_name)s, %(type_id)s, %(allow)s
                    )
                    returning
                        id,session_id,topic_name,type_id,allow,%(ab_session_id)s as ab_session_id
                """,
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))

        defer.returnValue(self._columnize(qv))


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
    def sessionAdd(self, *args, **kwargs):
        log.msg("sessionAdd called {}".format(kwargs))
        qa = kwargs['action_args']
        qv = yield self.call(self.query,
                """
                    insert into
                        session
                    (
                        login_id, ab_session_id, tzname
                    )
                    values
                    (
                        %(login_id)s, %(ab_session_id)s,
                        ( select tzname from login where id = %(login_id)s )
                    )
                    returning
                        id, login_id, ab_session_id, tzname
		   """,
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))

        defer.returnValue(self._columnize(qv))

    @inlineCallbacks
    def sessionDelete(self, *args, **kwargs):
        log.msg("sessionDelete called {}".format(kwargs))
        qa = kwargs['action_args']
        qv = yield self.call(self.query,
                """
                    update
                        session
                       set
                        ab_session_id = null
                     where
                        ab_session_id = %(ab_session_id)s
                    returning
                        id, login_id
		   """,
                   qa, options=types.CallOptions(timeout=2000,discloseMe=True))

        defer.returnValue(self._columnize(qv))

    @inlineCallbacks
    def onJoin(self, details):
        self.my_session_id = details.session
        self.my_authid = details.authid
        log.msg("onJoin session attached {}".format(details))
        #
        # ok, now this is a bit goofy, but, we need to
        # call the sessionAdd method to add our session.
        # normally, the session is recorded when the authentication is
        # done.  but, since we authenticate before we register these
        # routines that record the session, we need to do this now. make sense?
        # also, we want to do this before we do any actions, like register, so
        # that our activity tracker will work.
        #
        log.msg("onJoin add our session record {}:{},{}".format(
            self.svar['topic_base']+'.session.add', details.authid, details.session))
        rv = yield self.sessionAdd( action_args={ 'login_id':details.authid, 'ab_session_id':details.session })
        log.msg("onJoin added late session record {}".format(rv))
        #
        # just a little more goofiness, there are a few sessions set up by the authentication, authorization,
        # and database components connected to the main router.  We now query for those sessions
        # and create a database entry for them.
        #
        sysses = yield self.call('sys.session.listsysid')
        log.msg("onJoin :sysses {}".format(sysses))
        for dt in sysses.values():
            rv = yield self.sessionAdd( action_args={ 'login_id':details.authid, 'ab_session_id':dt })

        # call the activityAdd manually, first, so we catch all of the registrations
        # in the activity table
        reg = yield self.register(self.activityAdd, self.svar['topic_base']+'.activity.add',
                    RegisterOptions(details_arg = 'details'))
        rv = self.activityAdd( action_args={ 'ab_session_id':details.session,
            'topic_name':self.svar['topic_base']+'.activity.add',
            'type_id':'register',
            'allow':True})

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
            'topicrole.permission': {'method': self.topicrolePermission },
            'activity.list': {'method': self.activityList },
            'session.list': {'method': self.sessionList },
            'session.add': {'method': self.sessionAdd },
            'session.delete': {'method': self.sessionDelete },
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

        # attempt to clean up our session, no guarantees
        #log.msg("onLeave delete our session record {}:{}".format(
        #    self.svar['topic_base']+'.session.delete', self.my_session_id, self.my_authid))
        #rv = self.sessionDelete( action_args={ 'ab_session_id':self.my_session_id })
        #log.msg("onLeave delete late session record {}".format(rv))

        self.disconnect()

        return

    def onDisconnect(self):
        log.msg("onDisconnect:")
        reactor.stop()

def run():
    prog = os.path.basename(__file__)

    def_wsocket = 'ws://127.0.0.1:8080/ws'
    def_user = 'sys'
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
