CACHED = $(shell ls | grep Makefile.cache)
ifeq ($(findstring Makefile.cache,$(CACHED)), Makefile.cache)
MKDEF = $(shell cat Makefile.cache)
else

CC = gcc -pipe
# CC = g++ --pipe

MAKE = make
# MAKE = gmake

#OPT = -O2
# OPT += -g
# OPT += -O3
#OPT += -march=generic -mtune=generic
# OPT += -msse
# OPT += -msse2
# OPT += -msse3
# OPT += -rdynamic
# OPT += -fbounds-checking
# OPT += -fomit-frame-pointer
# OPT += -DCHRIF_OLDINFO
# OPT += -DGCOLLECT
# OPT += -DMEMWATCH
# OPT += -DDMALLOC -DDMALLOC_FUNC_CHECK
# OPT += -DBCHECK

# LIBS += -lgc
# LIBS += -ldmalloc

OPT = -Os
OPT += -g3
OPT += -ffast-math
OPT += -march=native -mtune=native

OPT += -Wall
OPT += -Wno-sign-compare
OPT += -Wno-unused-parameter -Wno-pointer-sign -Wno-switch -DHAVE_SETRLIMIT -Wno-unused -Wno-parentheses

OPT += -DPCRE_SUPPORT

OPT += -I../common
OPT += -I/usr/include
OPT += -I/usr/include/mysql

LIBS += -L/usr/lib64
LIBS += -L/usr/lib
LIBS += -lpcre

LIBS += -L/usr/lib64/mysql
LIBS += -L/usr/lib/mysql
LIBS += -lmysqlclient

LIBS += -ldl
GOPT += -m32

PLATFORM = $(shell uname)

CFLAGS = $(OPT) $(OS_TYPE)

ifdef SQLFLAG
  ifdef IS_MINGW
    CFLAGS += -I../mysql
    LIBS += -lmysql
  else
    MYSQLFLAG_CONFIG = $(shell which mysql_config)
    ifeq ($(findstring /,$(MYSQLFLAG_CONFIG)), /)
      MYSQLFLAG_VERSION = $(shell $(MYSQLFLAG_CONFIG) --version | sed s:\\..*::)
      ifeq ($(findstring 5,$(MYSQLFLAG_VERSION)), 5)
        MYSQLFLAG_CONFIG_ARGUMENT = --include
      else
        MYSQLFLAG_CONFIG_ARGUMENT = --cflags
      endif
      CFLAGS += $(shell $(MYSQLFLAG_CONFIG) $(MYSQLFLAG_CONFIG_ARGUMENT))
      LIBS += $(shell $(MYSQLFLAG_CONFIG) --libs)
    endif
  endif
endif

ifneq ($(findstring "[[:space:]]-lz[[:space:]]",$(LIBS)), -lz)
   LIBS += -lz
endif
ifneq ($(findstring "[[:space:]]-lm[[:space:]]",$(LIBS)), -lm)
   LIBS += -lm
endif

MKDEF = CC="$(CC)" CFLAGS="$(CFLAGS) $(GOPT)" LIB_S="$(LIBS) $(GOPT)"

endif

.PHONY: txt sql common login login_sql char char_sql map map_sql ladmin converters \
	addons plugins tools webserver clean zlib depend

all: txt sql

txt : Makefile.cache common login char map

ifdef SQLFLAG
sql: Makefile.cache common login_sql char_sql map_sql
else
sql:
	$(MAKE) SQLFLAG=1 $@
endif

common: src/common/GNUmakefile
	$(MAKE) -C src/$@ $(MKDEF)

login: src/login/GNUmakefile common
	$(MAKE) -C src/$@ $(MKDEF) txt

char: src/char/GNUmakefile common
	$(MAKE) -C src/$@ $(MKDEF) txt

map: src/map/GNUmakefile common
	$(MAKE) -C src/$@ $(MKDEF) txt

login_sql: src/login_sql/GNUmakefile common
	$(MAKE) -C src/$@ $(MKDEF) sql

char_sql: src/char_sql/GNUmakefile common
	$(MAKE) -C src/$@ $(MKDEF) sql

map_sql: src/map/GNUmakefile common
	$(MAKE) -C src/map $(MKDEF) sql

ladmin: src/ladmin/GNUmakefile common
	$(MAKE) -C src/$@ $(MKDEF)

plugins addons: src/plugins/GNUmakefile common
	$(MAKE) -C src/plugins $(MKDEF)

webserver:
	$(MAKE) -C src/$@ $(MKDEF)

tools:
	$(MAKE) -C src/tool $(MKDEF)
	
ifdef SQLFLAG
converters: src/txt-converter/GNUmakefile common
	$(MAKE) -C src/txt-converter $(MKDEF)
else
converters:
	$(MAKE) SQLFLAG=1 $@
endif

zlib:
	$(MAKE) -C src/$@ $(MKDEF)

clean: src/common/GNUmakefile src/login/GNUmakefile src/login_sql/GNUmakefile \
	src/char/GNUmakefile src/char_sql/GNUmakefile src/map/GNUmakefile \
	src/ladmin/GNUmakefile src/plugins/GNUmakefile src/txt-converter/GNUmakefile
	rm -f Makefile.cache
	$(MAKE) -C src/common $@
	$(MAKE) -C src/login $@
	$(MAKE) -C src/login_sql $@
	$(MAKE) -C src/char $@
	$(MAKE) -C src/char_sql $@
	$(MAKE) -C src/map $@
	$(MAKE) -C src/ladmin $@
	$(MAKE) -C src/plugins $@
	$(MAKE) -C src/zlib $@
	$(MAKE) -C src/txt-converter $@

depend: src/common/GNUmakefile src/login/GNUmakefile src/login_sql/GNUmakefile \
	src/char/GNUmakefile src/char_sql/GNUmakefile src/map/GNUmakefile \
	src/ladmin/GNUmakefile src/plugins/GNUmakefile src/txt-converter/GNUmakefile
	cd src/common; makedepend -fGNUmakefile -pobj/ -Y. *.c; cd ../..;
	cd src/login; makedepend -DTXT_ONLY -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	cd src/login_sql; makedepend -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	cd src/char; makedepend -DTXT_ONLY -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	cd src/char_sql; makedepend -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	cd src/map; makedepend -DTXT_ONLY -fGNUmakefile -ptxtobj/ -Y. -Y../common *.c; cd ../..;
	cd src/map; makedepend -fGNUmakefile -a -psqlobj/ -Y. -Y../common *.c; cd ../..;
	cd src/ladmin; makedepend -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	cd src/txt-converter; makedepend -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	$(MAKE) -C src/plugins $@

Makefile.cache:
	printf "$(subst ",\",$(MKDEF))" > Makefile.cache

src/%/GNUmakefile: src/%/Makefile
	sed -e 's/$$>/$$^/' $< > $@

src/common/GNUmakefile: src/common/Makefile
src/login/GNUmakefile: src/login/Makefile
src/login_sql/GNUmakefile: src/login_sql/Makefile
src/char/GNUmakefile: src/char/Makefile
src/char_sql/GNUmakefile: src/char_sql/Makefile
src/map/GNUmakefile: src/map/Makefile
src/plugins/GNUmakefile: src/plugins/Makefile
src/ladmin/GNUmakefile: src/ladmin/Makefile
src/txt-converter/GNUmakefile: src/txt-converter/Makefile
