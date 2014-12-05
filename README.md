# sqlauth - Authentication and Authorization via SQL for Autobahn
[![Version](https://pypip.in/version/sqlauth/badge.svg)![Status](https://pypip.in/status/sqlauth/badge.svg)![Downloads](https://pypip.in/download/sqlauth/badge.svg)](https://pypi.python.org/pypi/sqlauth/)[![Build Status](https://travis-ci.org/lgfausak/sqlauth.svg?branch=master)](https://travis-ci.org/lgfausak/sqlauth)

SQL Authorization and Authentication via SQL for Autobahn

## Summary

I need the ability to dynamically authorize Autobahn clients in a
multi-tenant fashion.  I do not want to push this to the application
level.  Logically, if an Autobahn client receives a call to an RPC
the client can assume that the caller has the authority to make that
call. Similarly with all the activities (subscribe,publish,register).
The actual authorization is done centrally so that the application
clients can just be concerned with their function, not the
authentication/authorization function.

From an implementation point of view this can be backended by any
database that sqlbridge supports.  However, I am only interested in
(and supporting) a Postgres backend at this time.  Primarily because
the listen/notify functionality.  This makes authentication/authorization
caching extremely efficient. In a nutshell, this code:

* Authenticates a user.  At web socket connection time a challenge
is submitted using wampcra. The credentials and associated permissions
are maintained in an sql database.

* Authorize activities. All web socket activity by an active authenticated session
is authorized.  This means that publish, subscribe, register and call are
permission based.

The side affects of these two activities are:
* A user table is maintained.
* A user is a member of roles. All permissions are granted to roles.
* A user can be a member of 0, 1 or more roles.
* A role can have 0, 1 or more users. (a n:m relationship exists between users and roles)
* A session table is maintained.  All active sessions can be accessed. In other words,
we can determine who the current clients of a Autobahn session are.
* Sessions can be summarily destroyed (Users can be 'kicked off' the Autobahn).
* Activity can be tracked.  Any publish,subscribe,call,register action is
called an activity.

## Schema

A picture is worth 1,000 words:
![alt text][schema]

## Postgres Installation Hints

Before we can start, we have to have a postgres installation. The
example here uses a database named autobahn, and a user with super user
privileges called autouser. Here are some [notes](docs/postgres_hints.md)
I put together.  The starting point here should be an installed postgres
installation, with a postgres superuser named 'autouser'.

I have included a quick setup script for postgres.  You can run it
like this:

First, you need to install the sqlauth code, that is done like this:

```
sudo pip install sqlauth
```

That installion includes the sqlpginit code. WARNING.  DESTRUCTIVE!

```
sudo sqlpginit -a
```

This will run all of the commands necessary to configure postgres.  The -a
flag actually runs the commands, leave it off to just 'see' the commands.
After running this command the postgres installation will be recreated
from scratch.  This is a very destructive command.  You have been warned!
Anyway, this command does an initdb, creates the database, creates the
schema in the database, and loads the initial data. When this command
completes successfully the database is ready for the sqlauthrouter.

## Notes
This code contains the bridge between the database engine (sqlbridge)
and the Autobahn calls.  However, since this router authenticates and
authorizes, there are 2 database calls embedded in the code.  In the
userdb.get() method there is a database query that fetches the user from
the database, this method is used to authenticate a user credentials
on login (for wampcra).  The second is in authorize.check_permission()
method.  This does a lookup of the topic/action being requested for the
current session/authid.  These are both embedded mostly for performance
reasons.  There isn't any reason the code in these two places couldn't
do a call to the db.info rpc to determine the type of database that is
connected, then customize the query accordingly.  I'm just not concerned
with database portability at this moment, so I am stopping work on this
aspect.  Contact me if you need help writing a driver for a different
database, I would be happy to help.

[schema]:https://github.com/lgfausak/sqlauth/raw/master/docs/schema.png "AAA Schema"

