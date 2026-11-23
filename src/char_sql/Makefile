# [build] Link target = the real output file (a target named `char-server_sql` writing
# ../../char-server_sql never existed, so the server was relinked on every `make`).
all sql: ../../char-server_sql

COMMON_OBJ = ../common/obj/core.o ../common/obj/socket.o ../common/obj/send_worker.o ../common/obj/timer.o \
	../common/obj/db.o ../common/obj/plugins.o ../common/obj/lock.o \
	../common/obj/malloc.o ../common/obj/showmsg.o ../common/obj/utils.o \
	../common/obj/strlib.o ../common/obj/grfio.o \
	../common/obj/mapindex.o ../common/obj/ers.o ../common/obj/attacklog.o
COMMON_H = ../common/core.h ../common/socket.h ../common/timer.h ../common/mmo.h \
	../common/version.h ../common/db.h ../common/plugins.h ../common/lock.h \
	../common/malloc.h ../common/showmsg.h ../common/utils.h ../common/strlib.h \
	../common/grfio.h ../common/mapindex.h

# [build] Rebuild on ANY char or common header change (see src/map/Makefile): the dep lines below are
# hand-kept and incomplete (char.o does not list socket.h/mmo.h), so a struct change would leave
# objects compiled against the old layout. ../../Makefile.cache holds the compiler flags (flag change ->
# rebuild).
CHAR_ALL_H = $(wildcard *.h) $(wildcard ../common/*.h) $(wildcard ../../Makefile.cache)

%.o: %.c $(CHAR_ALL_H)
	$(COMPILE.c) $(OUTPUT_OPTION) $<

# [onlinestat] MongoDB through libmongoc (Debian: apt install libmongoc-dev) when pkg-config finds it; without it
# the char-server still builds and keeps the online statistics in its spool file only. MONGOC_CFLAGS /
# MONGOC_LIBS on the make command line override pkg-config.
MONGOC_CFLAGS ?= $(shell pkg-config --cflags libmongoc-1.0 2>/dev/null)
MONGOC_LIBS ?= $(shell pkg-config --libs libmongoc-1.0 2>/dev/null)
# no pkg-config on the box (22.11 prod: libmongoc-dev installed, the char-server built without it): the Debian paths
MONGOC_PREFIX ?= /usr
ifeq ($(strip $(MONGOC_LIBS)),)
ifneq ($(wildcard $(MONGOC_PREFIX)/include/libmongoc-1.0/mongoc/mongoc.h),)
MONGOC_CFLAGS = -I$(MONGOC_PREFIX)/include/libmongoc-1.0 -I$(MONGOC_PREFIX)/include/libbson-1.0
MONGOC_LIBS = -L$(MONGOC_PREFIX)/lib/x86_64-linux-gnu -lmongoc-1.0 -lbson-1.0
endif
endif
ifneq ($(strip $(MONGOC_LIBS)),)
ONLINESTAT_DEF = -DONLINESTAT_MONGO $(MONGOC_CFLAGS)
endif
# (its own rule: the top Makefile passes CFLAGS on the command line, which a target-specific += cannot extend)
onlinestat.o: onlinestat.c $(CHAR_ALL_H)
	$(COMPILE.c) $(ONLINESTAT_DEF) $(OUTPUT_OPTION) $<

../../char-server_sql: char.o char_archive.o char_idcompact.o char_webstorage.o char_async_load.o onlinestat.o inter.o int_party.o int_guild.o int_storage.o int_pet.o int_homun.o int_quest.o int_achievement.o int_mercenary.o itemdb.o $(COMMON_OBJ)
	$(CC) -o $@ $^ $(LIB_S) $(MONGOC_LIBS)

clean:
	rm -f *.o ../../char-server_sql GNUmakefile

# DO NOT DELETE

char.o: char.c char.h char_async_load.h ../common/strlib.h itemdb.h ../common/showmsg.h
char_async_load.o: char_async_load.c char_async_load.h ../common/showmsg.h
inter.o: inter.c inter.h int_party.h int_guild.h int_storage.h int_pet.h int_homun.h ../common/mmo.h char.h ../common/socket.h ../common/showmsg.h
int_party.o: int_party.c int_party.h inter.h ../common/mmo.h char.h ../common/socket.h ../common/timer.h ../common/db.h ../common/showmsg.h
int_guild.o: int_guild.c int_guild.h inter.h ../common/mmo.h char.h ../common/socket.h ../common/db.h ../common/showmsg.h
int_storage.o: int_storage.c int_storage.h char.h itemdb.h ../common/showmsg.h
int_pet.o: int_pet.c int_pet.h inter.h char.h ../common/mmo.h ../common/socket.h ../common/db.h ../common/showmsg.h
int_homun.o: int_homun.c int_homun.h inter.h char.h ../common/mmo.h ../common/socket.h ../common/db.h ../common/showmsg.h
int_quest.o: int_quest.c int_quest.h inter.h char.h ../common/mmo.h ../common/socket.h ../common/db.h ../common/showmsg.h
int_achievement.o: int_achievement.c int_achievement.h inter.h char.h ../common/mmo.h ../common/socket.h ../common/db.h ../common/showmsg.h
int_mercenary.o: int_mercenary.c int_mercenary.h inter.h char.h ../common/mmo.h ../common/socket.h ../common/db.h ../common/showmsg.h
itemdb.o: itemdb.c itemdb.h ../common/db.h ../common/mmo.h ../common/showmsg.h
