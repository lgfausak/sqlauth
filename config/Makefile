# Makefile for massaging sql creation scripts
TFILE=/tmp/make_$$.tmp
MODULE=sqlauth
VFILE=../$(MODULE)/__init__.py
VNUM=/tmp/vnum_$$.tmp
U=-Upostgres
T=temp_autobahn

all: PG.sql MYSQL.sql SQLITE.sql
	echo 'done'

# this produces a version number in $(VNUM) file
$(VNUM): $(VFILE)
	( grep -v '^__version__' $(VFILE); nv=`(cat $(VFILE); echo 'p = __version__.split(".")'; echo 'p[len(p)-1]=str(int(p[len(p)-1])+1)'; echo 'print ".".join(p)';)   | python`; echo '__version__ = "'$$nv'"'; echo $$nv > $(VNUM))


# construct postgres database 
# we do this by dropping the temp work database
# then create a temp work database
# populate it with the basic table definition
# merge in specialize functions and customizations
# augment it (more customization)
autobahn.yaml : PGfunc.sql augment.yaml PGbase.sql
	-dropdb $U $T
	createdb $U $T
	psql $U $T -1 -f PGbase.sql
	psql $U $T -1 -f PGfunc.sql
	dbaugment $U $T augment.yaml -o autobahn.yaml
	dropdb $U $T

PG.sql : autobahn.yaml PGinit.sql
	-dropdb $U $T
	createdb $U $T
	yamltodb $U $T autobahn.yaml > PG.sql
	cat PGinit.sql >> PG.sql

