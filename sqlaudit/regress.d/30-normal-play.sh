fresh; : > "$RUN/char.out"; : > "$RUN/map.out"
one "normal play: items, skills, storage, party, guild, pet, homunculus" python3 -I capture2.py
"$SP/srv.sh" stop "$RUN" >/dev/null
errs=$(grep -a -c 'SQL\]' "$RUN/char.out" "$RUN/map.out" | awk -F: '{s+=$2} END{print s+0}')
if [ "$errs" -eq 0 ]; then pass=$((pass+1)); echo "PASS  normal play: no SQL errors in char/map output"; else fail=$((fail+1)); echo "FAIL  normal play: $errs SQL errors"; grep -a -h -A1 'SQL\]' "$RUN/char.out" "$RUN/map.out" | head -6 | cut -c1-200 | sed 's/^/      /'; fi
