#!/bin/bash

DEF=$IFS
rm -f ./A-item_db.sql
echo "truncate table item_db;" >>./A-item_db.sql
echo -e >>./A-item_db.sql

STRa="insert ignore into \`item_db\` VALUES ("

H="id,name_english,name_japanese,type,price_buy,price_sell,weight,attack,defence,range,slots,equip_jobs,equip_upper,equip_genders,equip_locations,weapon_level,equip_level,refineable,view,script"
IFS="," read -r -a array <<< "$H"
c=0
for x in "${array[@]}"
 do
  a[$c]="$x"
  ((c++))
 done

IFS=$'\n'
C=0
for x in `grep "^[0-9]" ../../db/item_db.txt|sed -e 's/}[[:space:]].$//'`;
 do
#  b[$C]=$x
  STRb=""
  IFS="#"
  A=0
  for y in `echo "$x"|sed -e 's/{/#/'`;
   do
    if [ "0" == "$A" ]
     then
#      c[$C]=$y
      B=0
      IFS="," read -r -a array <<< "${y}"
      for z in "${array[@]}";
       do
        if [ "$B" == "21" ]
         then
          break
        fi
        if [ -n "$z" ]
         then
          #z[$B]="$z"
          STRb+=" \"$z\","
         else
          #z[$B]="$z"
          STRb+=" NULL,"
        fi
        ((B++))
      done
      ((A++))
     else
      if [ -n "$y" ]
       then
        STRb+=" '$y'"
       else
        STRb+=" NULL"
      fi
      A=0
    fi
  done
  STRc=" )"
  `echo -e "${STRa}${STRb}${STRc};" |sed -e 's/, )/, NULL )/g'|sed -e "s/}' );$/' );/"|sed -e "s/ } \/\/.*'/ '/"|sed -e "s/'' );$/NULL );/">> ./A-item_db.sql`
  
  ((C++))  
done
