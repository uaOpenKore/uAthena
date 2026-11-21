# [build] Link target = the real output file (a target named `char-server` writing ../../char-server never
# existed, so it relinked on every `make`).
all txt: ../../char-server

COMMON_OBJ = ../common/obj/core.o ../common/obj/socket.o ../common/obj/send_worker.o ../common/obj/timer.o \
	../common/obj/db.o ../common/obj/plugins.o ../common/obj/lock.o \
	../common/obj/malloc.o ../common/obj/showmsg.o ../common/obj/utils.o \
	../common/obj/strlib.o ../common/obj/grfio.o \
	../common/obj/mapindex.o ../common/obj/ers.o ../common/obj/attacklog.o
COMMON_H = ../common/core.h ../common/socket.h ../common/timer.h ../common/mmo.h \
	../common/version.h ../common/db.h ../common/plugins.h ../common/lock.h \
	../common/malloc.h ../common/showmsg.h ../common/utils.h ../common/strlib.h \
	../common/grfio.h ../common/mapindex.h

# [build] Rebuild on ANY char or common header change (see src/map/Makefile): the hand-kept dep lines
# miss transitive headers, so a struct change (e.g. socket.h) would leave objects with the old layout.
CHAR_ALL_H = $(wildcard *.h) $(wildcard ../common/*.h) $(wildcard ../../Makefile.cache)

%.o: %.c $(CHAR_ALL_H)
	$(COMPILE.c) -DTXT_ONLY $(OUTPUT_OPTION) $<

../../char-server: char.o inter.o int_party.o int_guild.o int_status.o int_storage.o int_pet.o int_homun.o \
	int_quest.o int_achievement.o int_mercenary.o $(COMMON_OBJ)
	$(CC) -o $@ $> $(filter-out -lmysqlclient -lmariadb,$(LIB_S))

clean:
	rm -f *.o ../../char-server GNUmakefile

# DO NOT DELETE

char.o: char.c char.h inter.h int_pet.h int_quest.h int_achievement.h int_mercenary.h $(COMMON_H) ../common/version.h
inter.o: inter.c inter.h int_party.h int_guild.h int_storage.h int_pet.h int_quest.h int_achievement.h int_mercenary.h char.h $(COMMON_H)
int_party.o: int_party.c int_party.h inter.h char.h $(COMMON_H)
int_guild.o: int_guild.c int_guild.h int_storage.h inter.h char.h $(COMMON_H)
int_storage.o: int_storage.c int_storage.h int_guild.h inter.h char.h $(COMMON_H)
int_status.o: int_status.c int_status.h char.h $(COMMON_H)
int_pet.o: int_pet.c int_pet.h inter.h char.h $(COMMON_H)
int_homun.o: int_homun.c int_homun.h inter.h char.h $(COMMON_H)
int_quest.o: int_quest.c int_quest.h inter.h char.h $(COMMON_H)
int_achievement.o: int_achievement.c int_achievement.h inter.h char.h $(COMMON_H)
int_mercenary.o: int_mercenary.c int_mercenary.h inter.h char.h $(COMMON_H)
