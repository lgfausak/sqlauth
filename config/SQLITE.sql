/* SQLEditor (SQLite)*/

CREATE TABLE activity_type
(
id TEXT NOT NULL PRIMARY KEY  UNIQUE,
name TEXT,
description TEXT
);

CREATE TABLE login
(
/*Primary Key for the user*/
id SERIAL PRIMARY KEY  AUTOINCREMENT,
login TEXT NOT NULL UNIQUE,
fullname TEXT,
password TEXT NOT NULL,
salt TEXT,
tzname TEXT,
old_login TEXT,
inactive BOOLEAN
);

CREATE TABLE role
(
id SERIAL PRIMARY KEY,
name TEXT NOT NULL UNIQUE,
description TEXT
);

CREATE TABLE session
(
id SERIAL NOT NULL PRIMARY KEY  AUTOINCREMENT,
login_id INTEGER REFERENCES login (id),
ab_session_id BIGINT UNIQUE,
tzname TEXT
);

CREATE TABLE activity
(
id SERIAL NOT NULL PRIMARY KEY  AUTOINCREMENT,
session_id INTEGER REFERENCES session (id),
topic_name TEXT,
type_id TEXT REFERENCES activity_type (id),
allow BOOLEAN
);

CREATE TABLE topicrole
(
id SERIAL NOT NULL PRIMARY KEY  AUTOINCREMENT,
topic_id INTEGER NOT NULL REFERENCES topic (id),
role_id SERIAL NOT NULL REFERENCES role (id),
type_id TEXT NOT NULL REFERENCES activity_type (id),
allow BOOLEAN
);

CREATE TABLE loginrole
(
id SERIAL NOT NULL PRIMARY KEY  AUTOINCREMENT,
login_id INTEGER REFERENCES login (id),
role_id INTEGER REFERENCES role (id)
);

CREATE TABLE sqlauth
(
component TEXT PRIMARY KEY,
version TEXT,
profile JSONB
);

CREATE TABLE topic
(
id SERIAL NOT NULL PRIMARY KEY  AUTOINCREMENT,
name TEXT NOT NULL UNIQUE,
description TEXT
);

CREATE UNIQUE INDEX session_ab_session_id ON session (ab_session_id);

CREATE UNIQUE INDEX topicrole_topic_id_role_id_type_id ON topicrole (topic_id,role_id,type_id,allow);

CREATE UNIQUE INDEX loginrole_login_id_role_id ON loginrole (login_id,role_id);
