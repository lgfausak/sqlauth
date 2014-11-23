MODULE=sqlauth
TFILE=/tmp/make_$$.tmp
VFILE=$(MODULE)/__init__.py
VNUM=/tmp/vnum_$$.tmp

all:
	echo 'done'

#
# this will increment the __version__ number in the module's __init__.py file
#
incver:
	( grep -v '^__version__' $(VFILE); nv=`(cat $(VFILE); echo 'p = __version__.split(".")'; echo 'p[len(p)-1]=str(int(p[len(p)-1])+1)'; echo 'print ".".join(p)';)   | python`; echo '__version__ = "'$$nv'"') > $(TFILE); mv $(TFILE) $(VFILE)

#
# this will increment the __version__ number in the module's __init__.py file
# also, the file will be uploaded to pypi with the new version
#
pypi:
	( grep -v '^__version__' $(VFILE); nv=`(cat $(VFILE); echo 'p = __version__.split(".")'; echo 'p[len(p)-1]=str(int(p[len(p)-1])+1)'; echo 'print ".".join(p)';)   | python`; echo '__version__ = "'$$nv'"'; echo $$nv > $(VNUM)) > $(TFILE); mv $(TFILE) $(VFILE)
	python setup.py sdist upload
	git commit -m 'sync with pypi version: '`cat $(VNUM)` .
	git push

#
# register, only do this once per project
#
register:
	python setup.py register
