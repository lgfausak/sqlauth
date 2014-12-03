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
## userdb.py - database interface used for authentication
##
## this started with the UserDb example in the basic router.
## i abstracted the database layer, then this layer, to separate the router code from this.
###############################################################################

import six, sys
from twisted.python import log
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks, returnValue
from autobahn.wamp import types

class UserDb(object):
    """
    basic user database for authentication
    """

    #
    # UserDb needs to have an app_session to perform the query against. This can
    # be any application session with the authorization to run the rpcs in topic_base.
    # it doeesn't have to be set when the object is created, you can call set_session
    # with the information later.  app_session MUST be set before the first call to get
    # otherwise it will fail.
    #
    # topic_base could be 'sys.db', such that 'sys.db.query' and 'sys.db.watch' and 'sys.db.operation'
    # are all available, and the connection has already been made.
    #
    def __init__(self, topic_base, debug=False, app_session=None):
        if debug is not None and debug:
            log.startLogging(sys.stdout)
        log.msg("UserDb:__init__()")
        self.app_session = app_session
        self.topic_base = topic_base
        self.query = topic_base + '.query'
        self.debug = debug

        return

    def set_session(self, app_session):
        log.msg("UserDb:__init__()")
        self.app_session = app_session

        return
 
    @inlineCallbacks
    def get(self,authid):
        log.msg("UserDb:get({})".format(authid))
        rv = yield self.app_session.call(self.query, "select password, salt, id from login where login = %(login)s",
                { 'login':authid }, options=types.CallOptions(timeout=2000,discloseMe=True))
        if len(rv) > 0:
            defer.returnValue((six.u(rv[0]['salt']), six.u(rv[0]['password']), six.u('user'), rv[0]['id']))
        else:
            defer.returnValue((None, None, None, None))
        return
