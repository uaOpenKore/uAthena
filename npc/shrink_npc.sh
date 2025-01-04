#!/bin/bash

DEFAULT_IFS="$IFS"

cd mobs_uaro
MOBSUARO=($(find . -type f))
for x in "${MOBSUARO[@]}"; do
  sed -i 's/\xbb//g' $x
  sed -i 's/\xab//g' $x
  sed -i 's/\.gat,/,/' $x
  sed -i 's/\r$//' $x
  sed -i 's/^\\.*$//' $x
  sed -i 's\^/.*$\\' $x
  sed -i '/^$/d' $x
done

cd ../mobs
MOBS=($(find . -type f))
for x in "${MOBS[@]}"; do
  sed -i 's/\xbb//g' $x
  sed -i 's/\xab//g' $x
  sed -i 's/\.gat,/,/' $x
  sed -i 's/\r$//' $x
  sed -i 's/^\\.*$//' $x
  sed -i 's\^/.*$\\' $x
  sed -i '/^$/d' $x
done

cd ..
for x in "${MOBSUARO[@]}"; do
  while IFS=$'\t' read -r var1 var2 var3 var4; do
  IFS="," read -r v1 v2 v3 v4 v5 <<< "$var4"
    echo -e "$var1\t$var2\t$var3\t$v1 $v2 $v3 $v4 $v5"
    sed -i "s/^$var1\t$var2\t$var3\t$v1.*//" ./mobs_uaro/$x
  done < "./mobs/$x"
done

for x in "${MOBSUARO[@]}"; do
  sed -i '/^$/d' $x
done
