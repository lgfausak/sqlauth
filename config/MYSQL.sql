/* SQLEditor (MySQL (2))*/

CREATE TABLE activity_type
(
id TEXT NOT NULL UNIQUE,
name TEXT,
description TEXT,
PRIMARY KEY (id)
);

CREATE TABLE login
(
id SERIAL AUTO_INCREMENT COMMENT 'Primary Key for the user',
login TEXT UNIQUE,
fullname TEXT,
password TEXT,
salt TEXT,
tzname TEXT,
old_login TEXT,
inactive BOOLEAN,
PRIMARY KEY (id)
);

CREATE TABLE role
(
id SERIAL,
name TEXT UNIQUE,
description TEXT,
PRIMARY KEY (id)
);

CREATE TABLE session
(
id SERIAL NOT NULL AUTO_INCREMENT,
login_id INTEGER,
ab_session_id BIGINT UNIQUE,
tzname TEXT,
PRIMARY KEY (id)
);

CREATE TABLE activity
(
id SERIAL NOT NULL AUTO_INCREMENT,
session_id INTEGER,
topic_name TEXT,
type_id TEXT,
allow BOOLEAN,
PRIMARY KEY (id)
);

CREATE TABLE topicrole
(
id SERIAL NOT NULL AUTO_INCREMENT,
topic_id INTEGER NOT NULL,
role_id SERIAL NOT NULL,
type_id TEXT NOT NULL,
allow BOOLEAN,
PRIMARY KEY (id)
);

CREATE TABLE loginrole
(
id SERIAL NOT NULL AUTO_INCREMENT,
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
id SERIAL NOT NULL AUTO_INCREMENT,
name TEXT UNIQUE,
description TEXT,
PRIMARY KEY (id)
);

CREATE UNIQUE INDEX session_ab_session_id ON session (ab_session_id);

ALTER TABLE session ADD FOREIGN KEY login_id_idxfk (login_id) REFERENCES login (id);

ALTER TABLE activity ADD FOREIGN KEY session_id_idxfk (session_id) REFERENCES session (id);

ALTER TABLE activity ADD FOREIGN KEY type_id_idxfk (type_id) REFERENCES activity_type (id);

CREATE UNIQUE INDEX topicrole_topic_id_role_id_type_id ON topicrole (topic_id,role_id,type_id(50),allow);

ALTER TABLE topicrole ADD FOREIGN KEY topic_id_idxfk (topic_id) REFERENCES topic (id);

ALTER TABLE topicrole ADD FOREIGN KEY role_id_idxfk (role_id) REFERENCES role (id);

ALTER TABLE topicrole ADD FOREIGN KEY type_id_idxfk_1 (type_id) REFERENCES activity_type (id);

CREATE UNIQUE INDEX loginrole_login_id_role_id ON loginrole (login_id,role_id);

ALTER TABLE loginrole ADD FOREIGN KEY login_id_idxfk_1 (login_id) REFERENCES login (id);

ALTER TABLE loginrole ADD FOREIGN KEY role_id_idxfk_1 (role_id) REFERENCES role (id);
