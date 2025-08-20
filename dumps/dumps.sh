#!/bin/bash

HOST="localhost"
USER="ragnarok"
PASSWORD="ragnarok"
PORT="3306"
DB="ragnarok"

#only for init
rUSER="root"
rPASSWORD=""
#if you have root password then use prefix -r like rPASSWORD="-rMyPaSs"

function make_dumps {
  rm -f ./schema/* ./tables/*
  mysqldump -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB --no-data --single-transaction >./schema/schema.sql
     if [ "$?" != "0" ]
      then
       echo "Problem connecting to database"
       exit 1
      fi
  TABLES=`mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB -sN -e 'show tables'`
  for x in $TABLES
   do
    mysqldump -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB $x --extended-insert=FALSE --skip-dump-date --single-transaction >./tables/${x}.sql
   done
 }

function install_first {

  for x in ./tables/*.sql;
   do
    resu=$(cat $x | mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB)
         if [ -n "$resu" ]
      then
       echo "Problem connecting to database"
       echo "Error: $resu"
       exit 1
      fi
   done
 }

function create_db {
  mysql -h$HOST -P$PORT -u$rUSER -p$rPASSWORD -sN -e 'drop database test'
  mysql -h$HOST -P$PORT -u$rUSER -p$rPASSWORD -sN -e "create database ragnarok"
     if [ $? -ne 0 ]
      then
       echo "Problem connecting to database"
       exit 1
      fi
  mysql -h$HOST -P$PORT -u$rUSER -p$rPASSWORD -sN -e "create user 'ragnarok'@'%' identified by 'ragnarok'"
  mysql -h$HOST -P$PORT -u$rUSER -p$rPASSWORD -sN -e "create user 'ragnarok'@'localhost' identified by 'ragnarok'"
  mysql -h$HOST -P$PORT -u$rUSER -p$rPASSWORD -sN -e "grant all on ragnarok.* to 'ragnarok'@'%'"
  mysql -h$HOST -P$PORT -u$rUSER -p$rPASSWORD -sN -e "FLUSH PRIVILEGES"
 }

function update_db {
   mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB -sN -e "drop table migrations"
  cat ./migrations/1-migrations.sql | mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB
  for x in ./migrations/*.sql;
   do
    y=$(mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB -sN -e "select file from migrations where file = \"$x\" ")
     if [ $? -ne 0 ]
      then
       echo "Problem connecting to database"
       exit 1
      fi
    if [ "$x" != "$y" ]
     then
      cat $x | mysql -h$HOST -P$PORT -u$USER -p$PASSWORD $DB
      mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB -sN -e "insert into migrations (file) values (\"$x\") "
     fi
   done
 }

function make_backup {
  mysqldump -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB --single-transaction|gzip>./backup/${DB}.sql.gz
     if [ $? -ne 0 ] 
      then
       echo "Problem connecting to database"
       exit 1
      fi
 }

function create_test {
  mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB -sN -e 'insert into login (userid,user_pass) values ("Test","Test")'
     if [ "$?" != "0" ]
      then
       echo "Problem connecting to database"
       exit 1
      fi
 }

function uninstall {
  mysql -h$HOST -P$PORT -u$rUSER $rPASSWORD -sN -e "drop user 'ragnarok'@'%'; drop user 'ragnarok'@'localhost';drop database ragnarok;FLUSH PRIVILEGES"
     if [ "$?" != "0" ]
      then
       echo "Problem connecting to database"
       exit 1
      fi
 }

function enc_pass {
  mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB -sN -e "UPDATE `login` SET `user_pass`=MD5(`user_pass`);"
     if [ "$?" != "0" ]
      then
       echo "Problem connecting to database"
       exit 1
      fi
 }


if [ "$1" == "setMD5" ]
 then
  enc_pass
 fi

if [ "$1" == "make" ]
 then
  make_dumps
 fi

if [ "$1" == "install" ]
 then
  install_first
 fi

if [ "$1" == "uninstall" ]
 then
  uninstall
 fi

if [ "$1" == "create" ]
 then
  create_db
 fi

if [ "$1" == "backup" ]
 then
  make_backup
 fi

if [ "$1" == "test" ]
 then
  create_test
 fi

if [ "$1" == "update" ]
 then
  update_db
 fi

if [ "$1" == "old" ]
 then
  mysql -sN -e "drop database ragnarok"
     if [ $? -ne 0 ] 
      then
       echo "Problem connecting to database"
       exit 1
      fi
  create_db
  for x in ./old/*.sql;
   do
    echo "work $x"
    cat $x | mysql -h$HOST -P$PORT -u$USER -p$PASSWORD -D$DB
   done
 fi


exit
