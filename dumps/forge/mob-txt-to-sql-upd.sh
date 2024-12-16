#!/bin/bash


DEF=$IFS
rm -f ./end.sql

H="ID,Name,Name2,LV,HP,SP,EXP,JEXP,Range1,ATK1,ATK2,DEF,MDEF,STR,AGI,VIT,INT,DEX,LUK,Range2,Range3,Scale,Race,Element,Mode,Speed,ADelay,aMotion,dMotion,Drop1id,Drop1per,Drop2id,Drop2per,Drop3id,Drop3per,Drop4id,Drop4per,Drop5id,Drop5per,Drop6id,Drop6per,Drop7id,Drop7per,Drop8id,Drop8per,Drop9id,Drop9per,DropCardid,DropCardper,MEXP,ExpPer,MVP1id,MVP1per,MVP2id,MVP2per,MVP3id,MVP3per"
IFS="," read -r -a array <<< "$H"
c=0
for x in "${array[@]}"
 do
  a[$c]="$x"
  ((c++))
 done

IFS=$'\n'
c=0
for x in `grep "^[0-1]" ../../db/mob_db.txt` ;
  do
    STRb=""
    c=0
    IFS="," read -r -a array <<< "${x}"
    for y in "${array[@]}"
      do
        if [ "$c" == "57" ]
          then
            break
          fi
	STRb+=" \`${a[$c]}\` = \"$y\","
#	echo "$c	${a[$c]}	$y"
	((c++))
    done

    STRa="update mob_db set "
    STRc=" where id = \"${array[0]}\""
    echo -e "$STRa${STRb:0:-1}$STRc;" >> ./end.sql


done

c=0
for x in `grep "^[0-1]" ../../db/mob_db2.txt` ;
  do
    STRb=""
    c=0
    IFS="," read -r -a array <<< "${x}"
    for y in "${array[@]}"
      do
        if [ "$c" == "57" ]
          then
            break
          fi
	STRb+=" \`${a[$c]}\` = \"$y\","
#	echo "$c	${a[$c]}	$y"
	((c++))
    done

    STRa="update mob_db set "
    STRc=" where id = \"${array[0]}\""
    echo -e "$STRa${STRb:0:-1}$STRc;" >> ./end.sql


done
