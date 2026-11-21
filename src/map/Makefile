# [build] Link targets are the real output files: targets named `map-server_sql`/`map-server` that
# write ../../map-server_sql / ../../map-server never exist, so the server was relinked on every `make`.
all: sql
sql: ../../map-server_sql
txt: ../../map-server

sqlobj:
	mkdir -p sqlobj

txtobj:
	mkdir -p txtobj

COMMON_OBJ = ../common/obj/core.o ../common/obj/socket.o ../common/obj/send_worker.o ../common/obj/timer.o \
	../common/obj/db.o ../common/obj/plugins.o ../common/obj/lock.o \
	../common/obj/nullpo.o ../common/obj/malloc.o ../common/obj/showmsg.o \
	../common/obj/utils.o ../common/obj/strlib.o ../common/obj/grfio.o \
	../common/obj/mapindex.o ../common/obj/ers.o ../common/obj/random.o

COMMON_H = ../common/core.h ../common/socket.h ../common/timer.h ../common/db.h \
	../common/plugins.h ../common/lock.h ../common/nullpo.h ../common/malloc.h \
	../common/showmsg.h ../common/utils.h ../common/strlib.h ../common/grfio.h \
	../common/mapindex.h

OBJECTS = obj/map.o obj/chrif.o obj/clif.o obj/pc.o obj/status.o obj/npc.o \
	obj/npc_chat.o obj/chat.o obj/path.o obj/itemdb.o obj/mob.o obj/script.o \
	obj/storage.o obj/skill.o obj/atcommand.o obj/charcommand.o obj/battle.o \
	obj/intif.o obj/trade.o obj/party.o obj/vending.o obj/buyingstore.o obj/guild.o obj/pet.o \
	obj/log.o obj/log_async.o obj/async_db.o obj/async_read.o obj/mail.o obj/date.o obj/unit.o obj/mercenary.o obj/mercenary_soldier.o obj/livemob.o obj/liveskillunit.o obj/mobgrid.o obj/quest.o obj/achievement.o obj/discord.o obj/autotrade.o \
	$(COMMON_OBJ)

../../map-server_sql: $(OBJECTS:obj/%=sqlobj/%)
	$(CC) -o $@ $> $(LIB_S)

# TXT build links WITHOUT the MySQL client -- the no-MySQL stack must build on a box with no
# libmysqlclient/libmariadb installed (S. 2026-10-09). All mysql_* refs are under #ifndef TXT_ONLY.
LIB_TXT = $(filter-out -lmysqlclient -lmariadb,$(LIB_S))
../../map-server: $(OBJECTS:obj/%=txtobj/%)
	$(CC) -o $@ $> $(LIB_TXT)

# [build] Every object depends on ALL map + common headers. The hand-kept dep lines at the bottom are
# incomplete (unit.o, storage.o, mercenary.o use map_session_data but do not list map.h), so after a
# struct change in a header those objects kept the OLD layout -> one binary with two layouts = silent
# memory corruption. Rebuilding everything on any header change is cheap and always correct.
# ../../Makefile.cache holds the compiler flags, so a flag change rebuilds too. `| sqlobj` = order-only:
# the dir exists before any compile (parallel `make -j` raced the mkdir) but never triggers rebuilds.
MAP_ALL_H = $(wildcard *.h) $(wildcard ../common/*.h) $(wildcard ../../Makefile.cache)

sqlobj/%.o: %.c $(MAP_ALL_H) | sqlobj
	$(COMPILE.c) $(OUTPUT_OPTION) $<

txtobj/%.o: %.c $(MAP_ALL_H) | txtobj
	$(COMPILE.c) -DTXT_ONLY $(OUTPUT_OPTION) $<

clean:
	rm -rf *.o obj sqlobj txtobj ../../map-server ../../map-server_sql GNUmakefile

# DO NOT DELETE

sqlobj/map.o: map.c map.h chrif.h clif.h npc.h pc.h mob.h chat.h skill.h itemdb.h storage.h party.h pet.h atcommand.h log.h discord.h $(COMMON_H)
sqlobj/chrif.o: chrif.c map.h battle.h chrif.h clif.h intif.h pc.h npc.h $(COMMON_H)
sqlobj/clif.o: clif.c map.h chrif.h clif.h mob.h intif.h pc.h npc.h itemdb.h chat.h script.h storage.h party.h guild.h atcommand.h pet.h charcommand.h $(COMMON_H)
sqlobj/pc.o: pc.c map.h clif.h intif.h pc.h npc.h mob.h itemdb.h battle.h skill.h script.h party.h guild.h pet.h trade.h storage.h chat.h vending.h log.h $(COMMON_H)
sqlobj/status.o: status.c pc.h map.h clif.h status.h mob.h itemdb.h battle.h skill.h script.h pet.h guild.h $(COMMON_H)
sqlobj/npc.o: npc.c map.h npc.h clif.h pc.h script.h mob.h itemdb.h battle.h $(COMMON_H)
sqlobj/npc_chat.o: npc_chat.c map.h npc.h clif.h pc.h script.h mob.h itemdb.h battle.h $(COMMON_H)
sqlobj/chat.o: chat.c map.h clif.h pc.h chat.h $(COMMON_H)
sqlobj/path.o: path.c map.h battle.h $(COMMON_H)
sqlobj/itemdb.o: itemdb.c map.h battle.h itemdb.h $(COMMON_H)
sqlobj/mob.o: mob.c map.h clif.h intif.h pc.h mob.h skill.h battle.h npc.h itemdb.h log.h date.h discord.h $(COMMON_H)
sqlobj/discord.o: discord.c discord.h ../common/showmsg.h
sqlobj/script.o: script.c itemdb.h map.h pc.h mob.h clif.h intif.h npc.h script.h storage.h skill.h pet.h battle.h log.h $(COMMON_H)
sqlobj/storage.o: storage.c itemdb.h pc.h clif.h intif.h storage.h guild.h $(COMMON_H)
sqlobj/skill.o: skill.c skill.h map.h clif.h pc.h mob.h battle.h itemdb.h script.h log.h date.h $(COMMON_H)
sqlobj/atcommand.o: atcommand.c atcommand.h itemdb.h pc.h map.h skill.h clif.h mob.h intif.h battle.h storage.h guild.h pet.h log.h $(COMMON_H)
sqlobj/battle.o: battle.c battle.h skill.h map.h mob.h pc.h pet.h guild.h $(COMMON_H)
sqlobj/intif.o: intif.c intif.h chrif.h clif.h party.h guild.h storage.h map.h battle.h pet.h $(COMMON_H)
sqlobj/trade.o: trade.c trade.h clif.h itemdb.h map.h pc.h npc.h log.h $(COMMON_H)
sqlobj/party.o: party.c party.h clif.h intif.h pc.h map.h battle.h $(COMMON_H)
sqlobj/vending.o: vending.c vending.h clif.h itemdb.h map.h pc.h log.h $(COMMON_H)
sqlobj/buyingstore.o: buyingstore.c buyingstore.h clif.h itemdb.h map.h pc.h battle.h log.h $(COMMON_H)
sqlobj/guild.o: guild.c guild.h storage.h battle.h clif.h intif.h pc.h npc.h map.h $(COMMON_H)
sqlobj/pet.o: pet.c pet.h map.h clif.h chrif.h intif.h pc.h itemdb.h battle.h mob.h npc.h script.h $(COMMON_H)
sqlobj/mail.o: mail.c mail.h $(COMMON_H)
sqlobj/log.o: log.c log.h map.h $(COMMON_H)
sqlobj/log_async.o: log_async.c log.h map.h $(COMMON_H)
sqlobj/async_db.o: async_db.c async_db.h ../common/showmsg.h
sqlobj/async_read.o: async_read.c async_read.h ../common/showmsg.h
sqlobj/charcommand.o: charcommand.c charcommand.h itemdb.h pc.h map.h skill.h clif.h mob.h intif.h battle.h storage.h guild.h pet.h log.h $(COMMON_H)
sqlobj/date.o: date.c date.h $(COMMON_H)
sqlobj/unit.o: unit.c unit.h $(COMMON_H)
sqlobj/mercenary.o: mercenary.c mercenary.h $(COMMON_H)
sqlobj/mercenary_soldier.o: mercenary_soldier.c mercenary_soldier.h map.h pc.h status.h skill.h clif.h intif.h unit.h npc.h battle.h $(COMMON_H)
sqlobj/livemob.o: livemob.c livemob.h map.h $(COMMON_H)
sqlobj/liveskillunit.o: liveskillunit.c liveskillunit.h map.h $(COMMON_H)
sqlobj/mobgrid.o: mobgrid.c mobgrid.h
sqlobj/quest.o: quest.c quest.h map.h pc.h npc.h itemdb.h script.h intif.h battle.h mob.h party.h unit.h log.h clif.h chrif.h $(COMMON_H)
sqlobj/achievement.o: achievement.c achievement.h map.h pc.h clif.h $(COMMON_H)
