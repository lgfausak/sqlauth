# sqlauth - Authentication and Authorization via SQL for Autobahn
[![Version](https://pypip.in/version/sqlauth/badge.svg)![Status](https://pypip.in/status/sqlauth/badge.svg)![Downloads](https://pypip.in/download/sqlauth/badge.svg)](https://pypi.python.org/pypi/sqlauth/)[![Build Status](https://travis-ci.org/lgfausak/sqlauth.svg?branch=master)](https://travis-ci.org/lgfausak/sqlauth)

SQL Authorization and Authentication via SQL for Autobahn

## Summary

This module does two things for Autobahn.  Theoretically this can be backended by any
database that sqlbridge supports.  However, I am only interested in (and supporting)
a Postgres backend at this time.  Primarily because the listen/notify functionality
makes it possible.

* Authenticate a user.  At web socket connection time a challenge
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

[schema]:https://github.com/lgfausak/sqlauth/raw/master/docs/schema.png "AAA Schema"

