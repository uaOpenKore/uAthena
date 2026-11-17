# [build] Link target = the real output file (a target named `ladmin` writing ../../ladmin never existed,
# so it relinked on every `make ladmin`).
all txt sql: ../../ladmin

COMMON_OBJ = ../common/obj/minicore.o ../common/obj/minisocket.o ../common/obj/timer.o \
	../common/obj/malloc.o ../common/obj/showmsg.o ../common/obj/strlib.o \
	../common/obj/utils.o ../common/obj/md5calc.o
COMMON_H = ../common/core.h ../common/socket.h ../common/timer.h ../common/mmo.h \
	../common/version.h ../common/malloc.h ../common/showmsg.h ../common/strlib.h \
	../common/utils.h ../common/md5calc.h

# [build] Rebuild on ANY ladmin/common header or compiler-flag change (see src/map/Makefile): ladmin links
# common's socket/timer objects, so it must be compiled against the same struct layouts.
LADMIN_ALL_H = $(wildcard *.h) $(wildcard ../common/*.h) $(wildcard ../../Makefile.cache)

%.o: %.c $(LADMIN_ALL_H)
	$(COMPILE.c) $(OUTPUT_OPTION) $<

../../ladmin: ladmin.o $(COMMON_OBJ)
	$(CC) -o $@ ladmin.o $(COMMON_OBJ) $(LIB_S)

clean:
	rm -f *.o ../../ladmin GNUmakefile

# DO NOT DELETE

ladmin.o: ladmin.c ladmin.h $(COMMON_H)
