#!/bin/bash

DEFAULT_IFS="$IFS"

echo "Stage 1"

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
  echo "Done: $x"
done

echo "Stage 2"

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
  echo "Done: $x"
done

echo "Stage 3"

cd ..
for x in "${MOBSUARO[@]}"; do
  while IFS=$'\t' read -r var1 var2 var3 var4; do
  IFS="," read -r v1 v2 v3 v4 v5 <<< "$var4"
  IFS="," read -r a1 a2 a3 va a5 <<< "$var1"
    sed -i "s/^$a1[,].*\t$var2\t.*\t$v1[,].*//" ./mobs_uaro/$x
  done < "./mobs/$x"
  echo "Done: $x"
done

echo "Stage 4"

for x in "${MOBSUARO[@]}"; do
  while IFS=$'\n' read -r var1 ; do
    sed -i "s/^[ \t]*$var1[ \t]*$//" ./mobs_uaro/$x
  done < "./mobs/$x"
  echo "Done: $x"
done

echo "Stage 5"

for x in "${MOBSUARO[@]}"; do
  sed -i '/^$/d' ./mobs_uaro/$x
  echo "Done: $x"
done
