SET check_function_bodies = false;

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

ALTER FUNCTION audit_fullmodified() OWNER TO postgres;

COMMENT ON FUNCTION audit_fullmodified() IS 'Provides created values for audit columns.';

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

ALTER FUNCTION audit_full() OWNER TO postgres;

COMMENT ON FUNCTION audit_full() IS 'Provides created/modified values for audit columns.';

CREATE SEQUENCE loginrole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE loginrole_id_seq OWNER TO postgres;

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

CREATE SEQUENCE topic_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE topic_id_seq OWNER TO postgres;

CREATE SEQUENCE session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE session_id_seq OWNER TO postgres;

CREATE TABLE activity_type (
    id text NOT NULL,
    name text,
    description text);

ALTER TABLE activity_type OWNER TO postgres;

CREATE TABLE loginrole (
    id integer NOT NULL,
    login_id integer,
    role_id integer,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE loginrole OWNER TO postgres;

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

CREATE TABLE role (
    id integer NOT NULL,
    name text,
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

CREATE TABLE login (
    id integer NOT NULL,
    login text,
    fullname text,
    password text,
    tzname text,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE login OWNER TO postgres;

CREATE TABLE topic (
    id integer NOT NULL,
    name text,
    description text,
    modified_by_user integer NOT NULL,
    modified_timestamp timestamp with time zone NOT NULL);

ALTER TABLE topic OWNER TO postgres;

ALTER SEQUENCE loginrole_id_seq OWNED BY loginrole.id;

ALTER SEQUENCE role_id_seq OWNED BY role.id;

ALTER SEQUENCE login_id_seq OWNED BY login.id;

ALTER SEQUENCE topicrole_id_seq OWNED BY topicrole.id;

ALTER SEQUENCE activity_id_seq OWNED BY activity.id;

ALTER SEQUENCE topic_id_seq OWNED BY topic.id;

ALTER SEQUENCE session_id_seq OWNED BY session.id;

ALTER TABLE loginrole ALTER COLUMN id SET DEFAULT nextval('loginrole_id_seq'::regclass);

ALTER TABLE session ALTER COLUMN id SET DEFAULT nextval('session_id_seq'::regclass);

ALTER TABLE role ALTER COLUMN id SET DEFAULT nextval('role_id_seq'::regclass);

ALTER TABLE activity ALTER COLUMN id SET DEFAULT nextval('activity_id_seq'::regclass);

ALTER TABLE topicrole ALTER COLUMN id SET DEFAULT nextval('topicrole_id_seq'::regclass);

ALTER TABLE login ALTER COLUMN id SET DEFAULT nextval('login_id_seq'::regclass);

ALTER TABLE topic ALTER COLUMN id SET DEFAULT nextval('topic_id_seq'::regclass);

ALTER TABLE activity_type ADD CONSTRAINT activity_type_pkey PRIMARY KEY (id);

ALTER TABLE login ADD CONSTRAINT login_login_key UNIQUE (login);

ALTER TABLE session ADD CONSTRAINT session_pkey PRIMARY KEY (id);

ALTER TABLE role ADD CONSTRAINT role_pkey PRIMARY KEY (id);

ALTER TABLE topic ADD CONSTRAINT topic_pkey PRIMARY KEY (id);

ALTER TABLE session ADD CONSTRAINT session_ab_session_id_key UNIQUE (ab_session_id);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_pkey PRIMARY KEY (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_pkey PRIMARY KEY (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_topic_id_role_id_type_id UNIQUE (topic_id, role_id, allow);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_login_id_role_id UNIQUE (login_id, role_id);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_role_id_key UNIQUE (role_id);

ALTER TABLE login ADD CONSTRAINT login_pkey PRIMARY KEY (id);

ALTER TABLE activity ADD CONSTRAINT activity_pkey PRIMARY KEY (id);

ALTER TABLE session ADD CONSTRAINT session_ab_session_id UNIQUE (ab_session_id);

ALTER TABLE loginrole ADD CONSTRAINT loginrole_login_id_fkey FOREIGN KEY (login_id) REFERENCES login (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_role_id_fkey FOREIGN KEY (role_id) REFERENCES role (id);

ALTER TABLE session ADD CONSTRAINT session_login_id_fkey FOREIGN KEY (login_id) REFERENCES login (id);

ALTER TABLE role ADD CONSTRAINT role_id_fkey FOREIGN KEY (id) REFERENCES loginrole (role_id);

ALTER TABLE activity ADD CONSTRAINT activity_session_id_fkey FOREIGN KEY (session_id) REFERENCES session (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES topic (id);

ALTER TABLE topicrole ADD CONSTRAINT topicrole_type_id_fkey FOREIGN KEY (type_id) REFERENCES activity_type (id);

ALTER TABLE activity ADD CONSTRAINT activity_type_id_fkey FOREIGN KEY (type_id) REFERENCES activity_type (id);

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

