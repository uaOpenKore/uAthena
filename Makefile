CACHED = $(shell ls | grep Makefile.cache)
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

.PHONY: sql common login_sql char_sql map_sql ladmin \
	plugins tools clean depend

all: sql

ifdef SQLFLAG
sql: Makefile.cache common login_sql char_sql map_sql
else
sql:
	$(MAKE) SQLFLAG=1 $@
endif

common: src/common/GNUmakefile
	$(MAKE) -C src/$@ $(MKDEF)

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
	rm -rf src/common/obj src/map/obj src/map/sqlobj
	rm -f src/common/*.o src/login_sql/*.o src/char_sql/*.o src/map/*.o src/ladmin/*.o src/tool/*.o src/plugins/*.o
	rm -f src/common/GNUmakefile src/login_sql/GNUmakefile src/char_sql/GNUmakefile \
		src/map/GNUmakefile src/ladmin/GNUmakefile src/plugins/GNUmakefile
	rm -f login-server login-server_sql char-server char-server_sql \
		map-server map-server_sql ladmin
	rm -f plugins/*.so tools/adduser tools/convert

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

install:
		$(shell mkdir -p /opt/uathena/bin/log/)
		$(shell mkdir -p /opt/uathena/backup/)
		$(shell cp -r db    /opt/uathena/)
		$(shell cp -r conf  /opt/uathena/)
		$(shell cp -r npc   /opt/uathena/)
		$(shell cp *_sql /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/db/      /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/conf/    /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/npc/     /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/bin/log/ /opt/uathena/)
		$(shell cp scripts/uA* /etc/systemd/system/)
		$(shell systemctl daemon-reload)
		$(shell cp scripts/ua-*.sh /opt/uathena/bin/)
		$(shell cp -r scripts/cron /opt/uathena/bin/)

uninstall:
		$(shell rm -fr /opt/uathena/bin)
		$(shell rm -fr /opt/uathena/db)
		$(shell rm -fr /opt/uathena/conf)
		$(shell rm -fr /opt/uathena/npc)
		$(shell rm -f  /opt/uathena/log)
		$(shell rm -f /etc/systemd/system/uA*)
		$(shell systemctl daemon-reload)

erase:
		$(shell rm -rf /opt/uathena/)

update:
		$(shell cp -f *_sql /opt/uathena/bin/)
		$(shell cp -rf db    /opt/uathena/)
		$(shell cp -rf npc   /opt/uathena/)
		$(shell cp -f /opt/uathena/login_athena.conf /opt/uathena/conf/)
		$(shell cp -f /opt/uathena/char_athena.conf  /opt/uathena/conf/)
		$(shell cp -f /opt/uathena/map_athena.conf   /opt/uathena/conf/)
		$(shell cp -f /opt/uathena/exp.conf   /opt/uathena/conf/battle/)
		$(shell cp -f /opt/uathena/drops.conf /opt/uathena/conf/battle/)
		$(shell cp -f /opt/uathena/subnet_athena.conf /opt/uathena/conf/)
		$(shell cp -f /opt/uathena/packet_athena.conf /opt/uathena/conf/)
