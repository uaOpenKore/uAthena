# [build] Trust the cached flags only while Makefile.cache is NEWER than this Makefile. Before, any existing
# cache was used as-is and the `Makefile.cache: Makefile` rule re-wrote it from that same cached MKDEF, so an
# edited OPT/LIBS never took effect until `make clean` deleted the cache.
CACHED = $(shell test Makefile.cache -nt Makefile && echo Makefile.cache)
ifeq ($(findstring Makefile.cache,$(CACHED)), Makefile.cache)
MKDEF = $(shell cat Makefile.cache)
else

CC = gcc -pipe
# CC = g++ --pipe

MAKE = make
# MAKE = gmake

### Dev & Test server
# OPT = -O0 -g3 

### Production server
 OPT = -g -O2 -fno-strict-aliasing


# OPT += -march=generic -mtune=generic
 OPT += -rdynamic

#OPT += -fomit-frame-pointer
OPT += -fno-omit-frame-pointer

 OPT += -DCHRIF_OLDINFO
# OPT += -DGCOLLECT
# OPT += -DMEMWATCH
# OPT += -DDMALLOC -DDMALLOC_FUNC_CHECK
# OPT += -DBCHECK

# LIBS += -lgc
# LIBS += -ldmalloc

OPT += -ffast-math
OPT += -march=native -mtune=native

OPT += -Wall
OPT += -Wno-sign-compare
OPT += -Wno-unused-parameter -Wno-pointer-sign -Wno-switch -DHAVE_SETRLIMIT -Wno-unused -Wno-parentheses -fstack-protector

OPT += -DPCRE_SUPPORT

# PCRE2
OPT += -DPCRE2_CODE_UNIT_WIDTH=8
LIBS += -lpcre2-8

OPT += -I../common
OPT += -I/usr/include
OPT += -I/usr/include/mysql
OPT += -I/usr/local/include


LIBS += -L/usr/lib64 -L/usr/lib/x86_64-linux-gnu
LIBS += -L/usr/lib
LIBS += -L/usr/local/lib

LIBS += -L/usr/lib64/mysql
LIBS += -L/usr/lib/mysql 
LIBS += -lmysqlclient

LIBS += -ldl
LIBS += -lpthread


# Server Packet Protocol version (also defined in src/common/mmo.h)
# OPT += -DPACKETVER=8
#OPT += -DPACKETVER=7

# Makes map-wide script variables be saved to SQL instead of TXT files.
 OPT += -DMAPREGSQL

CFLAGS = $(OPT) $(OS_TYPE)

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

ifneq ($(findstring "[[:space:]]-lz[[:space:]]",$(LIBS)), -lz)
   LIBS += -lz
endif
ifneq ($(findstring "[[:space:]]-lm[[:space:]]",$(LIBS)), -lm)
   LIBS += -lm
endif

MKDEF = CC="$(CC)" CFLAGS="$(CFLAGS) $(GOPT)" LIB_S="$(LIBS) $(GOPT)"

endif

.PHONY: all sql txt common login_sql char_sql map_sql login char map converters ladmin \
	plugins addons tools clean depend install uninstall erase update

all: sql

# TXT (no-MySQL) server set -- restored 2026-10-09 for the tester (branch `txt`). Builds the
# standalone TXT login/char servers plus the map server in -DTXT_ONLY mode, so the whole stack
# runs without a MySQL database. Kept separate from `all`/`sql` so the production SQL build and
# DEPLOY.sh (which run `make`/`make sql`) are untouched -- invoke explicitly with `make txt`.
txt: Makefile.cache common login char map

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
	$(MAKE) -C src/map $(MKDEF) txt

converters: src/txt-converter/GNUmakefile common
	$(MAKE) -C src/txt-converter $(MKDEF)

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

tools:
	$(MAKE) -C src/tool $(MKDEF)
	
# Self-contained, exhaustive clean: nukes EVERY build artifact directly so the next `make`
# always rebuilds from source (no stale .o / stale generated GNUmakefile can survive). It does
# NOT depend on the per-subdir GNUmakefiles (avoids the regenerate-then-delete chicken-and-egg),
# and it covers ALL subdirs incl. src/tool. Keep this in sync if a new src/<dir> is added.
clean:
	rm -f Makefile.cache
	rm -rf src/common/obj src/map/obj src/map/sqlobj src/map/txtobj
	rm -f src/common/*.o src/login_sql/*.o src/char_sql/*.o src/map/*.o src/ladmin/*.o src/tool/*.o src/plugins/*.o
	rm -f src/login/*.o src/char/*.o src/txt-converter/*.o
	rm -f src/common/GNUmakefile src/login_sql/GNUmakefile src/char_sql/GNUmakefile \
		src/map/GNUmakefile src/ladmin/GNUmakefile src/plugins/GNUmakefile \
		src/login/GNUmakefile src/char/GNUmakefile src/txt-converter/GNUmakefile
	rm -f login-server login-server_sql char-server char-server_sql \
		map-server map-server_sql ladmin
	rm -f plugins/*.so plugins/*.conf tools/adduser tools/convert

depend: src/common/GNUmakefile src/login_sql/GNUmakefile \
	src/char_sql/GNUmakefile src/map/GNUmakefile \
	src/ladmin/GNUmakefile src/plugins/GNUmakefile
	cd src/common; makedepend -fGNUmakefile -pobj/ -Y. *.c; cd ../..;
	cd src/login_sql; makedepend -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	cd src/char_sql; makedepend -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	cd src/map; makedepend -fGNUmakefile -psqlobj/ -Y. -Y../common *.c; cd ../..;
	cd src/ladmin; makedepend -fGNUmakefile -Y. -Y../common *.c; cd ../..;
	$(MAKE) -C src/plugins $@

Makefile.cache: Makefile
	printf "$(subst ",\",$(MKDEF))" > Makefile.cache

src/%/GNUmakefile: src/%/Makefile
	sed -e 's/$$>/$$^/' $< > $@

src/common/GNUmakefile: src/common/Makefile
src/login_sql/GNUmakefile: src/login_sql/Makefile
src/char_sql/GNUmakefile: src/char_sql/Makefile
src/map/GNUmakefile: src/map/Makefile
src/plugins/GNUmakefile: src/plugins/Makefile
src/ladmin/GNUmakefile: src/ladmin/Makefile

# [build] install/uninstall/erase/update are plain recipe lines now. They used $(shell ...), which make runs
# while EXPANDING the recipe: every exit status was thrown away and nothing was echoed, so a failed copy
# (busy binary, full disk, missing build output) still ended in a "successful" deploy with the OLD binary
# left in /opt/uathena/bin. Same operations in the same order; a failure now stops the target with an error.
# Binaries are copied with --remove-destination (new inode), so a still-running server can't block the
# copy with "Text file busy". Links are only created when missing, exactly like the old `ln -s` that
# failed silently once they existed.
install:
	mkdir -p /opt/uathena/bin/log/ /opt/uathena/backup/
	cp -r db conf npc /opt/uathena/
	cp --remove-destination *_sql /opt/uathena/bin/
	for d in db conf npc; do [ -e /opt/uathena/bin/$$d ] || ln -s /opt/uathena/$$d/ /opt/uathena/bin/ || exit 1; done
	[ -e /opt/uathena/log ] || ln -s /opt/uathena/bin/log/ /opt/uathena/
	cp scripts/uA* /etc/systemd/system/
	-systemctl daemon-reload
	cp scripts/ua-*.sh /opt/uathena/bin/
	cp -r scripts/cron /opt/uathena/bin/

uninstall:
	rm -fr /opt/uathena/bin /opt/uathena/db /opt/uathena/conf /opt/uathena/npc
	rm -f /opt/uathena/log /etc/systemd/system/uA*
	-systemctl daemon-reload

erase:
	rm -rf /opt/uathena/

# Restores the host's own copies of the per-server confs (kept in /opt/uathena/) over the repo ones that
# `install` just copied. A missing saved copy keeps the repo version, now with a notice instead of silence.
update:
	cp --remove-destination *_sql /opt/uathena/bin/
	cp -rf db npc /opt/uathena/
	for f in login_athena.conf char_athena.conf map_athena.conf subnet_athena.conf packet_athena.conf discord.conf; do \
		if [ -f /opt/uathena/$$f ]; then cp -f /opt/uathena/$$f /opt/uathena/conf/ || exit 1; \
		else echo "update: no saved /opt/uathena/$$f - keeping the repo's conf/$$f"; fi; \
	done

