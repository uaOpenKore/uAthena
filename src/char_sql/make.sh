#!/bin/sh
	rsqlt=`rm -rf *.o`
	gcc -c char.c -I/usr/include/mysql/
	gcc -c int_guild.c -I/usr/include/mysql/
	gcc -c int_party.c -I/usr/include/mysql/
	gcc -c int_pet.c -I/usr/include/mysql/
	gcc -c int_storage.c -I/usr/include/mysql/
	gcc -c inter.c -I/usr/include/mysql/
	gcc -c itemdb.c -I../common/
	gcc -o ../char-server inter.o char.o int_pet.o int_storage.o int_guild.o int_party.o ../common/strlib.o itemdb.o ../common/core.o ../common/socket.o ../common/timer.o ../common/db.o -L/usr/lib/mysql -lmysqlclient -lz
