# postgres - Hints about how to set up a postgres environment

Postgres setup on linux

## Summary

Quickly set up a Postgres environment. The easiest way is to use the native
installation techniques.  Here is a good write up at [postgres installation](digitalocean).s It
basically boils down to:

* sudo apt-get install postgresql postgresql-contrib

After doing this, I always edit the pg_hba.conf file to trust local connections.

Or you can install from source.  This always requires downloading the current software
(or whatever version you want) from postgres, unpacking, ./configure, make and make install.
This is the technique I use, outlined below:

1. create a postgres user and group if it doesn't already exist
2. create a file called /etc/profile.d/postgres_hints.sh with this in it:
PATH=/usr/local/pgsql/bin:$PATH
PGDATA=/var/local/pgsql/data; export PGDATA
3. logout
4. log back in
5. Download from [postgres download](Postgresql.org)
6. Make sure that /usr/local/pgsql doesn't exist (mv or rm it if it does)
7. unpack the downloaded source
8. cd to unpacked directory
9. ./configure
* often during this step you will find you are missing the c compiler, or zlib, or readline, etc.  install
those packages as needed
10. make -j 4 (the -j flag indicates how many concurrent processes to run, if you are on multi cpu
architecture then this really speeds things up)
11. sudo make -j 4 install (assuming that the make worked)
12. mv /usr/local/pgsql /usr/local/pgsql_version
13. ln -s /usr/local/pgsql_version /usr/local/pgsql
* note, i do these steps to have more than one version at a time on my
machine, you can omit all of this if you don't care.
14. su to postgres
15. initdb --auth-host=trust
*** start the database, this can be placed in /etc/init.d/postgresql with some effort... ***
16. cat > ~/postgres_start.sh
pg_ctl -D /var/local/pgsql/data -l logfile start
^D
17. ~/postgres_start.sh
18. createdb -Upostgres autobahn
19. createuser -Upostgres -s autouser

*** that is it, the database autobahn is up with autouser accessing it ***

[postgres installation]: https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-14-04
[postgres download]: http://www.postgresql.org/ftp/source/

