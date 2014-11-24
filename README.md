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

Before we can start, we have to have a postgres installation. The example here uses a
database named autobahn, and a user with super user privileges called autouser. Here are
some [notes](docs/postgres_hints.md) I put together.  The starting point here should be
an installed postgres installation, with a postgres superuser named 'autouser'. Given that,
from the linux command line:

```
dropdb -Uautouser autobahn
createdb -Uautouser autobahn
```

I have included a quick setup script for postgres.  You can run it like this:

```
sudo sqlpginit -a
```

This will print out all of the commands necessary to configure postgres (assuming it
it already installed).  The -a flag actually runs the commands.  After running this
command the postgres installation will be recreated from scratch.  This is a very destructive command.
You have been warned!  Anyway, this command does an initdb, creates the database, creates
the schema in the database, and loads the initial data. When this command completes successfully
the database is ready for the sqlauthrouter.

[schema]:https://github.com/lgfausak/sqlauth/raw/master/docs/schema.png "AAA Schema"

