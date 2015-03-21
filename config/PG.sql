CREATE SCHEMA private;

ALTER SCHEMA private OWNER TO postgres;

CREATE LANGUAGE plpgsql;

SET check_function_bodies = false;

CREATE FUNCTION private.set_session_variable(var_name text, var_value text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
  begin
    perform pg_catalog.set_config('private.' || var_name, var_value, false);
  end;
$_$;

ALTER FUNCTION private.set_session_variable(var_name text, var_value text) OWNER TO postgres;

CREATE FUNCTION audit_fullmodified() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
DECLARE
  user_id integer := private.get_session_variable('audit_user',
    '0')::integer;
  rv record;
BEGIN
  if TG_OP = 'INSERT' or TG_OP = 'UPDATE' THEN
    NEW.modified_timestamp = CURRENT_TIMESTAMP;
    NEW.modified_by_user = user_id;
    rv = NEW;
  else
    rv = OLD;
  END IF;
  perform pg_notify(TG_TABLE_NAME || '_change',
    json_build_object('operation',TG_OP,'pk',rv.id,'id',user_id)::text);
  RETURN rv;
END$_$;

COMMENT ON FUNCTION audit_fullmodified() IS 'Provides created values for audit columns.';

CREATE FUNCTION private.get_session_variable(var_name text, default_value text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
  begin
    return pg_catalog.current_setting('private.' || var_name);
  exception
    when undefined_object then
      return default_value;
  end;
$_$;

ALTER FUNCTION private.get_session_variable(var_name text, default_value text) OWNER TO postgres;

CREATE FUNCTION audit_full() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
DECLARE
  user_id integer := private.get_session_variable('audit_user',
    '0')::integer;
  rv record;
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.created_timestamp = CURRENT_TIMESTAMP;
    NEW.created_by_user = user_id;
    NEW.modified_timestamp = CURRENT_TIMESTAMP;
    NEW.modified_by_user = user_id;
    rv = NEW;
  ELSIF TG_OP = 'UPDATE' THEN
    NEW.created_timestamp = OLD.created_timestamp;
    NEW.created_by_user = OLD.created_by_user;
    NEW.modified_timestamp = CURRENT_TIMESTAMP;
    NEW.modified_by_user = user_id;
    rv = NEW;
  ELSE
    rv = OLD;
  END IF;
  perform pg_notify(TG_TABLE_NAME || '_change',
    json_build_object('operation',TG_OP,'pk',rv.id,'id',user_id)::text);
  RETURN rv;
END$_$;

COMMENT ON FUNCTION audit_full() IS 'Provides created/modified values for audit columns.';

CREATE FUNCTION private.get_session_variable(var_name text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
  begin
    return pg_catalog.current_setting('private.' || var_name);
  end;
$_$;

ALTER FUNCTION private.get_session_variable(var_name text) OWNER TO postgres;

CREATE FUNCTION private.set_session(ab_sid bigint, OUT login_id bigint, OUT session_id bigint, OUT tzname text, OUT ab_session_id bigint) RETURNS record
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
  declare
    srec record;
  begin
    login_id := null;
    session_id := null;
    tzname := null;
    ab_session_id := ab_sid;
    select * into strict srec from session where ab_session_id = ab_sid;
    login_id = srec.login_id;
    perform pg_catalog.set_config('private.audit_user', srec.login_id::text, false);
    session_id = srec.id;
    perform pg_catalog.set_config('private.audit_session', srec.id::text, false);
    if srec.tzname is not null then
      tzname := srec.tzname;
      perform pg_catalog.set_config('timezone', srec.tzname, false);
    end if;
    exception
        when NO_DATA_FOUND then
          raise notice 'ignoring NO_DATA_FOUND setting %', ab_sid;
        when TOO_MANY_ROWS then
          raise notice 'ignoring TOO_MANY_ROWS setting %', ab_sid;
        when others then
          raise notice 'ignoring OTHER error setting %', ab_sid;
          -- crickets
    return;
  end;
$_$;

ALTER FUNCTION private.set_session(ab_sid bigint, OUT login_id bigint, OUT session_id bigint, OUT tzname text, OUT ab_session_id bigint) OWNER TO postgres;

CREATE AGGREGATE private.array_accum(anyelement) (
    SFUNC = array_append,
    STYPE = anyarray,
    INITCOND = '{}');

ALTER AGGREGATE private.array_accum(anyelement) OWNER TO postgres;

CREATE SEQUENCE loginrole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE loginrole_id_seq OWNER TO postgres;

CREATE SEQUENCE topic_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE topic_id_seq OWNER TO postgres;

CREATE SEQUENCE role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE role_id_seq OWNER TO postgres;

CREATE SEQUENCE login_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE login_id_seq OWNER TO postgres;

CREATE SEQUENCE topicrole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE topicrole_id_seq OWNER TO postgres;

CREATE SEQUENCE activity_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE activity_id_seq OWNER TO postgres;

CREATE SEQUENCE session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE session_id_seq OWNER TO postgres;

CREATE SEQUENCE topicrole_role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE topicrole_role_id_seq OWNER TO postgres;

CREATE TABLE session (
    id integer NOT NULL,
    login_id integer,
    ab_session_id bigint,
    tzname text,
    created_by_user integer NOT NULL,
    created_timestamp timestamp with time zone NOT NULL,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE session OWNER TO postgres;

CREATE TABLE activity_type (
    id text NOT NULL,
    name text,
    description text);

ALTER TABLE activity_type OWNER TO postgres;

CREATE TABLE loginrole (
    id integer NOT NULL,
    login_id integer NOT NULL,
    role_id integer NOT NULL,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE loginrole OWNER TO postgres;

CREATE TABLE role (
    bind_to integer,
    name text NOT NULL,
    id integer NOT NULL,
    description text,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE role OWNER TO postgres;

CREATE TABLE activity (
    id integer NOT NULL,
    session_id integer,
    topic_name text,
    type_id text,
    allow boolean,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE activity OWNER TO postgres;

CREATE TABLE topicrole (
    id integer NOT NULL,
    topic_id integer NOT NULL,
    role_id integer NOT NULL,
    type_id text NOT NULL,
    allow boolean,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE topicrole OWNER TO postgres;

CREATE TABLE sqlauth (
    component text NOT NULL,
    version text,
    profile jsonb);

ALTER TABLE sqlauth OWNER TO postgres;

CREATE TABLE login (
    id integer NOT NULL,
    login text,
    fullname text,
    password text NOT NULL,
    salt text,
    tzname text,
    old_login text,
    inactive boolean,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE login OWNER TO postgres;

CREATE TABLE topic (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE topic OWNER TO postgres;

ALTER SEQUENCE loginrole_id_seq OWNED BY loginrole.id;

ALTER SEQUENCE topic_id_seq OWNED BY topic.id;

ALTER SEQUENCE role_id_seq OWNED BY role.id;

ALTER SEQUENCE login_id_seq OWNED BY login.id;

ALTER SEQUENCE topicrole_id_seq OWNED BY topicrole.id;

ALTER SEQUENCE activity_id_seq OWNED BY activity.id;

ALTER SEQUENCE session_id_seq OWNED BY session.id;

ALTER SEQUENCE topicrole_role_id_seq OWNED BY topicrole.role_id;

ALTER TABLE session ALTER COLUMN id SET DEFAULT nextval('session_id_seq'::regclass);

ALTER TABLE loginrole ALTER COLUMN id SET DEFAULT nextval('loginrole_id_seq'::regclass);

ALTER TABLE role ALTER COLUMN id SET DEFAULT nextval('role_id_seq'::regclass);

ALTER TABLE activity ALTER COLUMN id SET DEFAULT nextval('activity_id_seq'::regclass);

ALTER TABLE topicrole ALTER COLUMN id SET DEFAULT nextval('topicrole_id_seq'::regclass);

ALTER TABLE topicrole ALTER COLUMN role_id SET DEFAULT nextval('topicrole_role_id_seq'::regclass);

ALTER TABLE login ALTER COLUMN id SET DEFAULT nextval('login_id_seq'::regclass);

ALTER TABLE topic ALTER COLUMN id SET DEFAULT nextval('topic_id_seq'::regclass);

ALTER TABLE topic ADD CONSTRAINT topic_name_key UNIQUE (name);

ALTER TABLE activity_type ADD CONSTRAINT activity_type_pkey PRIMARY KEY (id);

ALTER TABLE login ADD CONSTRAINT login_login_key UNIQUE (login);

ALTER TABLE role ADD CONSTRAINT role_name_key UNIQUE (name);

ALTER TABLE session ADD CONSTRAINT session_pkey PRIMARY KEY (id);

ALTER TABLE role ADD CONSTRAINT role_pkey PRIMARY KEY (id);

ALTER TABLE topic ADD CONSTRAINT topic_pkey PRIMARY KEY (id);

ALTER TABLE session ADD CONSTRAINT session_ab_session_id_key UNIQUE (ab_session_id);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_pkey PRIMARY KEY (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_pkey PRIMARY KEY (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_topic_id_role_id_type_id UNIQUE (topic_id, role_id, type_id, allow);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_login_id_role_id UNIQUE (login_id, role_id);

ALTER TABLE login ADD CONSTRAINT login_pkey PRIMARY KEY (id);

ALTER TABLE activity ADD CONSTRAINT activity_pkey PRIMARY KEY (id);

ALTER TABLE session ADD CONSTRAINT session_ab_session_id UNIQUE (ab_session_id);

ALTER TABLE sqlauth ADD CONSTRAINT sqlauth_pkey PRIMARY KEY (component);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_login_id_fkey FOREIGN KEY (login_id) REFERENCES login (id);

ALTER TABLE role ADD CONSTRAINT role_topic_binding FOREIGN KEY (bind_to) REFERENCES topic (id) ON DELETE SET NULL;

ALTER TABLE topicrole ADD CONSTRAINT topicrole_role_id_fkey FOREIGN KEY (role_id) REFERENCES role (id);

ALTER TABLE session ADD CONSTRAINT session_login_id_fkey FOREIGN KEY (login_id) REFERENCES login (id);

ALTER TABLE activity ADD CONSTRAINT activity_session_id_fkey FOREIGN KEY (session_id) REFERENCES session (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES topic (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_type_id_fkey FOREIGN KEY (type_id) REFERENCES activity_type (id);

ALTER TABLE activity ADD CONSTRAINT activity_type_id_fkey FOREIGN KEY (type_id) REFERENCES activity_type (id);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_role_id_fkey FOREIGN KEY (role_id) REFERENCES role (id);

CREATE TRIGGER topic_20_audit_fullmodified
    BEFORE INSERT OR UPDATE OR DELETE ON topic
    FOR EACH ROW
    EXECUTE PROCEDURE audit_fullmodified();

CREATE TRIGGER login_20_audit_fullmodified
    BEFORE INSERT OR UPDATE OR DELETE ON login
    FOR EACH ROW
    EXECUTE PROCEDURE audit_fullmodified();

CREATE TRIGGER role_20_audit_fullmodified
    BEFORE INSERT OR UPDATE OR DELETE ON role
    FOR EACH ROW
    EXECUTE PROCEDURE audit_fullmodified();

CREATE TRIGGER activity_20_audit_fullmodified
    BEFORE INSERT OR UPDATE OR DELETE ON activity
    FOR EACH ROW
    EXECUTE PROCEDURE audit_fullmodified();

CREATE TRIGGER topicrole_20_audit_fullmodified
    BEFORE INSERT OR UPDATE OR DELETE ON topicrole
    FOR EACH ROW
    EXECUTE PROCEDURE audit_fullmodified();

CREATE TRIGGER loginrole_20_audit_fullmodified
    BEFORE INSERT OR UPDATE OR DELETE ON loginrole
    FOR EACH ROW
    EXECUTE PROCEDURE audit_fullmodified();

CREATE TRIGGER session_20_audit_full
    BEFORE INSERT OR UPDATE OR DELETE ON session
    FOR EACH ROW
    EXECUTE PROCEDURE audit_full();

--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- Data for Name: activity_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY activity_type (id, name, description) FROM stdin;
call	rpc call	A call to a registered rpc
register	register	Register an rpc so it can be called
publish	publish	Publish a message
subscribe	subscribe	Subscribe to a message
start	begin a session	Begin a new autobahn session
end	end a session	End an existing autobahn session
admin	Admin Domain	Rule over this space
\.


COPY login (id, login, fullname, password, tzname, modified_by_user, modified_timestamp, salt, old_login, inactive) FROM stdin;
0	sys	System Internal Root	17q8IJB2AO5dCvCcjJg/DHcP51dAHrULJUD9zoNZIbg=	America/Chicago	0	2014-12-03 20:21:15.442137-06	oihewuhweg98797325	\N	\N
1	adm	Public System Administrator	17q8IJB2AO5dCvCcjJg/DHcP51dAHrULJUD9zoNZIbg=	America/Chicago	0	2014-12-03 20:21:15.442137-06	oihewuhweg98797325	\N	\N
\.

SELECT pg_catalog.setval('login_id_seq', 2, true);

COPY topic (id, name, description, modified_by_user, modified_timestamp) FROM stdin;
1	sys	All things system, including authentication and authorization	0	2014-11-25 12:59:21.890086-06
2	sys.topic	Topic stuff	0	2014-12-03 19:58:36.862908-06
3	sys.role	Add a topic	0	2014-12-03 20:07:45.035027-06
4	sys.userrole	User role association	0	2014-12-03 19:58:36.862908-06
5	sys.topicrole	Topic role association	0	2014-12-03 19:58:36.862908-06
200	adm	Administrator Space	0	2014-11-26 08:06:09.931566-06
300	com	Community Space	0	2014-11-26 08:06:09.931566-06
400	pub	Public Space	0	2014-11-26 08:06:09.931566-06
500	role	Role Binding Hierarchy	0	2014-11-26 08:06:09.931566-06
501	role.sys	Role sys Binding	0	2014-11-26 08:06:09.931566-06
502	role.adm	Role adm Binding	0	2014-11-26 08:06:09.931566-06
503	role.com	Role com Binding	0	2014-11-26 08:06:09.931566-06
504	role.public	Role Public Binding	0	2014-11-26 08:06:09.931566-06
\.

SELECT pg_catalog.setval('topic_id_seq', 600, true);

COPY role (id, name, description, bind_to, modified_by_user, modified_timestamp) FROM stdin;
1	sys	All things system	501	0	2014-11-25 12:54:50.715127-06
2	adm	Administration	502	0	2014-11-25 12:54:50.715127-06
3	com	Community	503	0	2014-11-25 12:54:50.715127-06
4	public	Public	504	0	2014-11-25 12:54:50.715127-06
\.

SELECT pg_catalog.setval('role_id_seq', 5, true);

COPY loginrole (id, login_id, role_id, modified_by_user, modified_timestamp) FROM stdin;
1	0	1	0	2014-11-25 16:40:27.358583-06
2	0	2	0	2014-11-25 16:41:37.57475-06
3	0	3	0	2014-11-25 16:41:37.57475-06
4	0	4	0	2014-11-25 16:41:37.57475-06
5	1	2	0	2014-11-25 17:00:27.238068-06
6	1	3	0	2014-11-25 17:05:24.62864-06
7	1	4	0	2014-11-25 17:23:28.316645-06
\.

SELECT pg_catalog.setval('loginrole_id_seq', 8, true);

COPY sqlauth (component, version, profile) FROM stdin;
\.

COPY topicrole (id, topic_id, role_id, type_id, allow, modified_by_user, modified_timestamp) FROM stdin;
1	1	1	call	t	0	2014-11-25 13:11:42.31319-06
2	1	1	register	t	0	2014-11-25 13:11:46.196604-06
3	1	1	publish	t	0	2014-11-25 13:11:58.806129-06
4	1	1	subscribe	t	0	2014-11-25 13:12:14.718075-06
5	1	1	admin	t	0	2014-11-25 13:12:29.087589-06
6	200	2	call	t	0	2014-11-25 13:11:42.31319-06
7	200	2	register	t	0	2014-11-25 13:11:46.196604-06
8	200	2	publish	t	0	2014-11-25 13:11:58.806129-06
9	200	2	subscribe	t	0	2014-11-25 13:12:14.718075-06
10	200	2	admin	t	0	2014-11-25 13:12:29.087589-06
11	300	3	call	t	0	2014-11-25 13:11:42.31319-06
12	300	3	register	t	0	2014-11-25 13:11:46.196604-06
13	300	3	publish	t	0	2014-11-25 13:11:58.806129-06
14	300	3	subscribe	t	0	2014-11-25 13:12:14.718075-06
15	300	3	admin	t	0	2014-11-25 13:12:29.087589-06
16	400	4	call	t	0	2014-11-25 13:11:42.31319-06
17	400	4	register	t	0	2014-11-25 13:11:46.196604-06
18	400	4	publish	t	0	2014-11-25 13:11:58.806129-06
19	400	4	subscribe	t	0	2014-11-25 13:12:14.718075-06
20	400	4	admin	t	0	2014-11-25 13:12:29.087589-06
21	2	4	call	t	0	2014-11-25 13:12:29.087589-06
22	3	4	call	t	0	2014-11-25 13:12:29.087589-06
23	4	4	call	t	0	2014-11-25 13:12:29.087589-06
24	5	4	call	t	0	2014-11-25 13:12:29.087589-06
100	500	1	admin	t	0	2014-11-25 13:12:29.087589-06
101	501	1	admin	t	0	2014-11-25 13:12:29.087589-06
102	502	2	admin	t	0	2014-11-25 13:12:29.087589-06
103	503	3	admin	t	0	2014-11-25 13:12:29.087589-06
104	504	4	admin	t	0	2014-11-25 13:12:29.087589-06
\.


--
-- Name: topicrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('topicrole_id_seq', 500, true);


--
-- Name: topicrole_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('topicrole_role_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--

insert into sqlauth (component,version) values ('database','0.2.9');
