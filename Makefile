CACHED = $(shell ls | grep Makefile.cache)
ifeq ($(findstring Makefile.cache,$(CACHED)), Makefile.cache)
MKDEF = $(shell cat Makefile.cache)
else

include build/flags.mk

CC = $(UA_CC)
# CC = g++

MAKE = make
# MAKE = gmake

CFLAGS = $(UA_CFLAGS)
LDFLAGS = $(UA_LDFLAGS)
LDLIBS = $(UA_LDLIBS)


# Server Packet Protocol version (also defined in src/common/mmo.h)
# CFLAGS += -DPACKETVER=8
# CFLAGS += -DPACKETVER=7

# Makes map-wide script variables be saved to SQL instead of TXT files.
CFLAGS += -DMAPREGSQL

ifdef SQLFLAG
  ifdef IS_MINGW
    CFLAGS += -I../mysql
    LDLIBS += -lmysql
  else
    MYSQLFLAG_CONFIG := $(firstword \
        $(shell command -v mysql_config 2>/dev/null) \
        $(shell command -v mariadb_config 2>/dev/null))
    ifneq ($(strip $(MYSQLFLAG_CONFIG)),)
      MYSQLFLAG_CONFIG_NAME := $(notdir $(MYSQLFLAG_CONFIG))
      MYSQLFLAG_CONFIG_ARGUMENT = --cflags
      ifeq ($(MYSQLFLAG_CONFIG_NAME),mysql_config)
        MYSQLFLAG_VERSION = $(shell $(MYSQLFLAG_CONFIG) --version | sed s:\\..*::)
        ifeq ($(findstring 5,$(MYSQLFLAG_VERSION)), 5)
          MYSQLFLAG_CONFIG_ARGUMENT = --include
        endif
      endif
      CFLAGS += $(shell $(MYSQLFLAG_CONFIG) $(MYSQLFLAG_CONFIG_ARGUMENT))
      LDLIBS += $(shell $(MYSQLFLAG_CONFIG) --libs)
    endif
  endif
endif

ifneq ($(filter -lz,$(LDLIBS)),-lz)
   LDLIBS += -lz
endif
ifneq ($(filter -lm,$(LDLIBS)),-lm)
   LDLIBS += -lm
endif

MKDEF = CC="$(CC)" CFLAGS="$(CFLAGS)" LDFLAGS="$(LDFLAGS)" LDLIBS="$(LDLIBS)"

endif

.PHONY: txt sql common login login_sql char char_sql map map_sql ladmin converters \
        addons plugins tools clean depend sanitize docker-build

DOCKER_IMAGE ?= uathena:x64-port

docker-build:
	@command -v docker >/dev/null 2>&1 || { \
		echo 'docker is not installed or not in PATH' >&2; exit 127; \
	}
	$(info Building Docker image $(DOCKER_IMAGE))
	docker build --tag $(DOCKER_IMAGE) .

all: txt sql

txt : Makefile.cache common login char map

sanitize: clean
	$(MAKE) UA_ENABLE_SANITIZE=1 txt
	$(MAKE) UA_ENABLE_SANITIZE=1 SQLFLAG=1 sql
	rm -f Makefile.cache

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

tools:
	$(MAKE) -C src/tool $(MKDEF)
	
ifdef SQLFLAG
converters: src/txt-converter/GNUmakefile common
	$(MAKE) -C src/txt-converter $(MKDEF)
else
converters:
	$(MAKE) SQLFLAG=1 $@
endif

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
	cd src/txt-converter; makedepend -DTXT_SQL_CONVERT -fGNUmakefile -Y. -Y../common *.c; cd ../..;
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

install:
		$(shell mkdir -p /opt/uathena/bin/log/)
		$(shell mkdir -p /opt/uathena/backup/)
		$(shell cp -r save  /opt/uathena/)
		$(shell cp -r db    /opt/uathena/)
		$(shell cp -r conf  /opt/uathena/)
		$(shell cp -r conf-tmpl  /opt/uathena/)
		$(shell cp -r npc   /opt/uathena/)
		$(shell cp *-server* /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/save/    /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/db/      /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/conf/    /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/npc/     /opt/uathena/bin/)
		$(shell ln -s /opt/uathena/bin/log/ /opt/uathena/)
		$(shell cp scripts/uA* /etc/systemd/system/)
		$(shell systemctl daemon-reload)
		$(shell cp scripts/ua-*.sh /opt/uathena/bin/)

uninstall:
		$(shell rm -fr /opt/uathena/bin)
		$(shell rm -fr /opt/uathena/db)
		$(shell rm -fr /opt/uathena/conf)
		$(shell rm -fr /opt/uathena/conf-tmpl)
		$(shell rm -fr /opt/uathena/npc)
		$(shell rm -fr /opt/uathena/bin)
		$(shell rm -fr /opt/uathena/save)
		$(shell rm -f  /opt/uathena/log)
		$(shell rm -f /etc/systemd/system/uA*)
		$(shell systemctl daemon-reload)

erase:
		$(shell rm -rf /opt/uathena/)

update:
		$(shell cp -f *-server* /opt/uathena/bin/)
		$(shell cp -rf db    /opt/uathena/)
		$(shell cp -rf npc   /opt/uathena/)

