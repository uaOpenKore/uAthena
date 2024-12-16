#!/bin/bash

DEF=$IFS
rm -f ./end.sql

H="ID,Name,Name,Type,Price,Sell,Weight,ATK,DEF,Range,Slot,Job,Upper,Gender,Loc,wLV,eLV,Refineable,View,Script"
IFS="," read -r -a array <<< "$H"
c=0
for x in "${array[@]}"
 do
  a[$c]="$x"
  ((c++))
 done

IFS=$'\n'
c=0
for x in `grep "^\+" ./src.sql|sed -e 's/^\+//'`;
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
	((c++))
    done
    STRa="update item_db set "
    STRc=" where id = \"${array[0]}\""
    echo -e "$STRa${STRb:0:-1}$STRc;" >> ./end.sql
done






