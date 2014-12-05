/* SQLEditor (Postgres)*/

CREATE TABLE activity_type
(
id TEXT NOT NULL UNIQUE,
name TEXT,
description TEXT,
PRIMARY KEY (id)
);

CREATE TABLE login
(
/*Primary Key for the user*/
id SERIAL,
login TEXT NOT NULL UNIQUE,
fullname TEXT,
password TEXT NOT NULL,
salt TEXT,
tzname TEXT,
old_login TEXT,
inactive BOOLEAN,
PRIMARY KEY (id)
);

CREATE TABLE session
(
id SERIAL NOT NULL,
login_id INTEGER,
ab_session_id BIGINT UNIQUE,
tzname TEXT,
PRIMARY KEY (id)
);

CREATE TABLE activity
(
id SERIAL NOT NULL,
session_id INTEGER,
topic_name TEXT,
type_id TEXT,
allow BOOLEAN,
PRIMARY KEY (id)
);

CREATE TABLE role
(
bind_to INTEGER,
name TEXT NOT NULL UNIQUE,
id SERIAL,
description TEXT,
PRIMARY KEY (id)
);

CREATE TABLE topicrole
(
id SERIAL NOT NULL,
topic_id INTEGER NOT NULL,
role_id SERIAL NOT NULL,
type_id TEXT NOT NULL,
allow BOOLEAN,
PRIMARY KEY (id)
);

CREATE TABLE loginrole
(
id SERIAL NOT NULL,
login_id INTEGER,
role_id INTEGER,
PRIMARY KEY (id)
);

CREATE TABLE sqlauth
(
component TEXT,
version TEXT,
profile JSONB,
PRIMARY KEY (component)
);

CREATE TABLE topic
(
id SERIAL NOT NULL,
name TEXT NOT NULL UNIQUE,
description TEXT,
PRIMARY KEY (id)
);

ALTER TABLE session ADD CONSTRAINT session_ab_session_id UNIQUE (ab_session_id);

ALTER TABLE session ADD FOREIGN KEY (login_id) REFERENCES login (id);

ALTER TABLE activity ADD FOREIGN KEY (session_id) REFERENCES session (id);

ALTER TABLE activity ADD FOREIGN KEY (type_id) REFERENCES activity_type (id);

ALTER TABLE role ADD CONSTRAINT role_topic_binding FOREIGN KEY (bind_to) REFERENCES topic (id) ON DELETE SET NULL;

ALTER TABLE topicrole ADD CONSTRAINT topicrole_topic_id_role_id_type_id UNIQUE (topic_id,role_id,type_id,allow);

ALTER TABLE topicrole ADD FOREIGN KEY (topic_id) REFERENCES topic (id);

ALTER TABLE topicrole ADD FOREIGN KEY (role_id) REFERENCES role (id);

ALTER TABLE topicrole ADD FOREIGN KEY (type_id) REFERENCES activity_type (id);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_login_id_role_id UNIQUE (login_id,role_id);

ALTER TABLE loginrole ADD FOREIGN KEY (login_id) REFERENCES login (id);

ALTER TABLE loginrole ADD FOREIGN KEY (role_id) REFERENCES role (id);
