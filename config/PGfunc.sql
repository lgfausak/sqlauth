/*
** private.sql
** this creates the private schema and the functions that go in it on
** a blank database.
*/
create schema if not exists private;
create or replace function private.get_session_variable(var_name text) returns text as $$
  begin
    return pg_catalog.current_setting('private.' || var_name);
  end;
$$ language plpgsql security definer;
create or replace function private.get_session_variable(var_name text, default_value text) returns text as $$
  begin
    return pg_catalog.current_setting('private.' || var_name);
  exception
    when undefined_object then
      return default_value;
  end;
$$ language plpgsql security definer;
create or replace function private.set_session_variable(var_name text, var_value text) returns void as $$
  begin
    perform pg_catalog.set_config('private.' || var_name, var_value, false);
  end;
$$ language plpgsql security definer;
/*
** this function can be called to set the current session in the executing transaction
** space. variable private.{audit_user and audit_session} are set (autobahn auth id
** autobahn session id). also the timezone is set if it is there making all queries by the user
** relative to their time zone.
** if the session doesnt exist an exception is thrown.
*/
create or replace function private.set_session(ab_sid bigint) returns void as $$
  declare
    srec record;
  begin
    select * into strict srec from session where ab_session_id = ab_sid;
    perform pg_catalog.set_config('private.audit_user', srec.login_id::text, false);
    perform pg_catalog.set_config('private.audit_session', srec.id::text, false);
    if srec.tzname is not null then
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
  end;
$$ language plpgsql security definer;
