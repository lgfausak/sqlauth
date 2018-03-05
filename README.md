# sqlauth - Authentication and Authorization via SQL for Autobahn
[![Version](https://img.shields.io/pypi/v/sqlauth.svg)![Status](https://img.shields.io/pypi/status/sqlauth.svg)![Downloads](https://img.shields.io/pypi/dm/sqlauth.svg)](https://pypi.python.org/pypi/sqlauth/)[![Build Status](https://travis-ci.org/lgfausak/sqlauth.svg?branch=master)](https://travis-ci.org/lgfausak/sqlauth)

SQL Authorization and Authentication via SQL for Autobahn

## Overview

This is a simple authentication / authorization scheme. Users can be added to the user database.  Once added, authentication can occur.
However, a user has no permissions other than the permission to authenticate.  Once authenticated a session is established and
recorded. At any time a list of current and past sessions can be retrieved. A session remains current until
such time as the endpoint leaves the session, then it becoems historical.

A topic is a dot separated name describing an endpoint.  Examples include:
* com.store.temp
* adm.inventory.rubberbands.quantity
* com.home.garage.door.open
* com.home.garage.door.close

In Autobahn topics can be bound to remote procedure calls, or subscriptions.
Topics have an inherent hierarchy. The root is to the left, the leaf is to the right.  In the
example above, com.home.garage.door would be the logical parent of
com.home.garage.door.open and com.home.garage.door.close.

Roles are groups of users.  There can be 0, 1 or more users belonging to a role.  A user can belong
to many roles.  This forms a n:m (many to many) relationship between the concept of a role
and the concept of a user.  A role is important, because all permissions are granted to roles,
not to users. So, I can grant call, register, subscribe, and publish permission to a topic from a role.
In addition to the 4 basic actions I can grant, there is also 'admin'.  Admin action is the authority
to grant permissions to others.

When a user is connected, they can call Autobahn actions (call,register,subscribe,publish).
Those commands are authorized based upon
the data describing permissions in the database.  Every action (whether authorized or not)
is recorded in the activity table.

Permissions can be granted anywhere in the tree.  For example, I could grant the role 'family'
permission on the action 'call' for the topics :
* com.home.garage.door.open
* com.home.garage.door.close

So that would mean that any user I associate with the role family could open or close
the garage door.  You can grant further up the tree as well.  So, instead of making 2 grants
I could just grant call to the topic:
* com.home.garage.door

And that would accomplish the same thing.  This illustrates a permission concept.  All permissions are
evaluated from the root of the topic chain down to the leaf.  If the permission needed is
anywhere in the chain, the permission is granted.  That means if I have subscribe permission to the
topic 'com', *any* publication with com. in the root would be granted. That would include subscribing to:
* com.one
* com.lower.still
* com.this.is.out.there

Then there is the 'admin' action.  Actually, this is not an Autobahn action, it is just for sqlauth.
Having admin means that you can grant any permission for that object.  That is fairly easy to understand
with a topic.

It is harder with a role, because I left something out previously.  When you create a new role, you
must specify a topic that binds its admin permission.  So, when I create a new role I bind it to
a topic name of my choice.  This new topic is also created when the role is created.  The new topic is
what is used to control permissions for the role.  More on this later...

## Commands

The permissions can be maintained by simply updating the database with appropriate records.
Or, I've created a simple api that can be used to manage the
database.  This is probably a better way to manage it, but either will work.  The utility to
manage them is called sqladm.  You can run sqladm --help to pick up a help message. Also,
you can get help with the activity you want to do, like sqladm user --help to list all of the user commands.

### user (commands: list,get,add,delete)
* list - list all of the users in the database.
* get - specify the login (user name) and fetch the single user record
* add - specify login, fullname, secret, tzname. login is the user id (alphanum), fullname is a string, like 'John Doe'.
secret is the password to assign that user. tzname is a linux time zone, like America/Chicago.
* delete - specify the login (user id) to delete the record.  The record, and all role associates, are deleted.

Examples:
```
sqladm -u adm -s 123test user add --args '{"login":"greg","secret":"spass","fullname":"Greg Last", "tzname":"America/Chicago"}'
sqladm -u adm -s 123test user get --args '{"login":"greg"}'
sqladm -u adm -s 123test user delete --args '{"login":"greg"}'
```
* Note: notice the -u and -s arguments for sqladm.  That is because sqladm is authenticated and authorized as well.
The database is shipped with 2 native users.  sys is one, adm is the other. sys is for internal use, adm is
the root level administrator for your use.  You initial roles and users must be added using
adm or sys.  Once added, you can grant your new users admin, and to your administration with other users.
* Note: Yes, the arguments for each of the activities is json.  Ultimately I may flesh that
out a bit.
* Note: Users records are left in the database when deleted, but they are marked inactive and the login name can
be reused immediately after deletion.

### role (commands: list,get,add,delete)
* list - list all of the roles in the database. Along with each role you get a list of all users associated with
that role.
* get - specify the name (role name) and fetch the single role record
* add - specify name, description, bind_topic and a new role is created. The bind_topic is simply
a topic name.  That name is prepended with the role. string. Also, if the bind_topic doesn't terminate
with the name of the role being created that is appended.  So, for example, if I specify
test as my bind_topic, and the role I am creating's name is 'administrator', then the ultimate
created bind_topic will be 'role.test.administrator'.  That becomes the controlling topic for
the new role 'administrator'.  Further, the current user requesting to create this role
must have admin permission in the role.test.administrator hierarchy.  It boils down to this,
you can't create a role unless you have admin permission somewhere in the role. hierarchy.
* delete - specify the name (role name) to delete.  The role is deleted, along with all records
that reference that role.

Examples:
```
sqladm -u adm -s 123test role add --args '{"name":"myusers","description":"Group of my users", "bind_topic":"adm.myusers"}'
sqladm -u adm -s 123test role get --args '{"name":"myusers"}' 
sqladm -u adm -s 123test role list 
sqladm -u adm -s 123test role delete --args '{"name":"myusers"}' 
```

* Note: The session that is calling the role add call must have admin
permission on the topic 'role.adm.myusers'.  The adm user has admin on the role.adm
topic by default, so, this is fulfilled.  This keeps just anyone from creating a topic, only
those with admin in a role decendant topic can create a new role.

* Note: You can only delete a role if you have admin permission on that role's bind_to
topic.


### userrole (commands: add,delete)
* add - add a user to a role. The name (role name) and login (user name) must be supplied.
* delete - delete a user from a role.  The name (role name) and login (user name) must be supplied.

Examples:
```
sqladm -u adm -s 123test userrole add --args '{"login":"greg","name":"adm"}'
sqladm -u adm -s 123test userrole delete --args '{"login":"greg","name":"adm"}'
```

* Note: When a user is added to a role, the user assumes all authority that has been granted that role.
* Note: The session that is calling these userrole calls must have admin permission on them. In other words
to associate a user with a role, I must be admin for that role.

### topic (commands: list,get,add,delete)
* list - list all of the topics in the database. Along with the topic, all roles that have been granted any permission to this
each topic are listed.
* get - specify the name (topic name) and fetch the single topic record.
* add - specify name, description. A topic with name and description is added (that
is assuming the user requesting the addition has admin permission in the new topic name's hierarchy).
* delete - specify the name (topic name) to delete the record and all associated records.

Examples:
```
sqladm -t sys -u adm -s 123test topic add -a '{"name":"adm.tenants","description":"Test second level"}'
sqladm -t sys -u adm -s 123test topic list
sqladm -t sys -u adm -s 123test topic get -a '{"name":"adm.tenants"}'
sqladm -t sys -u adm -s 123test topic delete -a '{"name":"adm.tenants"}'
```

* Note: When adding a new topic, you must have admin permission in the hierarchy you are adding to.
* Note: When deleting a topic, you must have admin permission on the topic.

### topicrole (commands: add,delete)
* add - add a topic to a role. Minimum of topic_name (the name of the topic) and name (the name of the role)
must be specified.
* delete - delete a topic from a role. Minimum of topic_name (the name of the topic) and name (the name of the role)
must be specified.

Examples:
```
sqladm -t sys -u adm -s 123test topicrole add -a '{"topic_name":"adm.myusers","name":"myusers"}'
sqladm -t sys -u adm -s 123test topicrole delete -a '{"topic_name":"adm.myusers","name":"myusers"}'
sqladm -t sys -u adm -s 123test topicrole add -a '{"topic_name":"adm.myusers","name":"myusers","activity":["admin"]}'
```

* Note: The session calling these api functions must have admin permission on the topic as well as the role.
* Note: an additional argument to the first two of these examples is: "activity":[ "call","register","subscribe","publish","admin"].
If activity is not specified in either add or delete args then the activity is assumed to be all 5 actions.
* Note: the third example shows adding just a single action to the topic/role permission association.


### session (commands: list)
* list - list all of the sessions in the database.

### activity (commands: list)
* list - list all of the ctivities for active sessions in the database

Yes, this documentation is light.  More later...

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

