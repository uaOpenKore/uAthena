# [build] Link target = the real output file (a target named `login-server` writing ../../login-server never
# existed, so it relinked on every `make`).
all txt: ../../login-server

COMMON_OBJ = ../common/obj/core.o ../common/obj/socket.o ../common/obj/send_worker.o ../common/obj/timer.o \
	../common/obj/db.o ../common/obj/plugins.o ../common/obj/lock.o \
	../common/obj/malloc.o ../common/obj/showmsg.o ../common/obj/utils.o \
	../common/obj/strlib.o ../common/obj/grfio.o \
	../common/obj/mapindex.o ../common/obj/ers.o ../common/obj/md5calc.o ../common/obj/random.o
COMMON_H = ../common/core.h ../common/socket.h ../common/timer.h ../common/mmo.h \
	../common/version.h ../common/db.h ../common/plugins.h ../common/lock.h \
	../common/malloc.h ../common/showmsg.h ../common/utils.h ../common/strlib.h \
	../common/grfio.h ../common/mapindex.h \
	../common/md5calc.h

# [build] Rebuild on ANY login or common header change (see src/map/Makefile).
LOGIN_ALL_H = $(wildcard *.h) $(wildcard ../common/*.h) $(wildcard ../../Makefile.cache)

%.o: %.c $(LOGIN_ALL_H)
	$(COMPILE.c) -DTXT_ONLY $(OUTPUT_OPTION) $<

../../login-server: login.o $(COMMON_OBJ)
	$(CC) -o $@ login.o $(COMMON_OBJ) $(filter-out -lmysqlclient -lmariadb,$(LIB_S))

clean:
	rm -f *.o ../../login-server GNUmakefile

# DO NOT DELETE

login.o: login.c login.h $(COMMON_H)
