#!/bin/bash

make clean
rm -fr ./autom4te.cache
rm -f ./char-server
rm -f ./login-server
rm -f ./map-server
rm -f ./char-server_sql
rm -f ./login-server_sql
rm -f ./map-server_sql
rm -f ./config.log
rm -f ./config.status
rm -f ./configure
rm -f ./Makefile
rm -f ./src/char/Makefile
rm -f ./src/char_sql/Makefile
rm -f ./src/common/Makefile
rm -f ./src/ladmin/Makefile
rm -f ./src/login/Makefile
rm -f ./src/login_sql/Makefile
rm -f ./src/map/Makefile
rm -f ./src/mysql/Makefile
rm -f ./src/plugins/Makefile
rm -f ./src/tool/Makefile
rm -f ./src/txt-converter/Makefile
rm -fr ./conf/import
