# Makefile for massaging sql creation scripts
TFILE=/tmp/make_$$.tmp
MODULE=sqlauth
VFILE=../$(MODULE)/__init__.py
VNUM=/tmp/vnum_$$.tmp
U=-Upostgres
T=temp_autobahn

all: PG.sql MYSQL.sql SQLITE.sql
	echo 'done'

clean: autobahn.yaml
	rm -f autobahn.yaml
	rm -f PG.sql

# this produces a version number in $(VNUM) file
$(VNUM): $(VFILE)
	( grep -v '^__version__' $(VFILE); nv=`(cat $(VFILE); echo 'p = __version__.split(".")'; echo 'p[len(p)-1]=str(int(p[len(p)-1])+1)'; echo 'print ".".join(p)';)   | python`; echo '__version__ = "'$$nv'"'; echo $$nv > $(VNUM))


# construct postgres database structure.
autobahn.yaml : PGfunc.sql augment.yaml PGbase.sql
	-dropdb $U $T
	createdb $U $T
	psql $U $T -1 -f PGbase.sql
	psql $U $T -1 -f PGfunc.sql
	dbaugment $U $T augment.yaml -o autobahn.yaml
	dropdb $U $T

# this builds the database structure and fills it with initialized content
PG.sql : autobahn.yaml PGinit.sql $(VNUM)
	-dropdb $U $T
	createdb $U $T
	yamltodb $U $T autobahn.yaml > $(TFILE)
	cat PGinit.sql >> $(TFILE)
	echo "insert into $(MODULE) (component,version) values ('database','"` cat $(VNUM)`"');" >> $(TFILE)
	mv $(TFILE) PG.sql

