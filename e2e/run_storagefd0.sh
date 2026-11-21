#!/bin/bash
# run_storagefd0.sh <run-dir>: 950 stackable stacks in testacc3's storage, run storagefd0_e2e.py, stop, check map.out.
E=/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/e2e/tools
RUN="$1"; M="mysql --no-defaults -h127.0.0.1 -uragnarok -pragnarok ragnarok"
bash "$E/srv.sh" stop "$RUN" > /dev/null
$M -e "DELETE FROM storage WHERE account_id=2000003; UPDATE login SET level=1 WHERE account_id=2000003"
python3 -I -c "print('INSERT INTO storage (account_id,nameid,amount,equip,identify,refine,attribute,card0,card1,card2,card3,expire_time) VALUES ' + ','.join('(2000003,909,1,0,1,0,0,0,0,0,0,0)' for i in range(950)) + ';')" | $M
bash "$E/srv.sh" start "$RUN" | tail -1
cd "$E" && timeout 100 python3 -I storagefd0_e2e.py; rc=$?
bash "$E/srv.sh" stop "$RUN" > /dev/null
$M -e "DELETE FROM storage WHERE account_id=2000003; UPDATE login SET level=0 WHERE account_id=2000003"
n=$(grep -a -c 'overflowed pointer\|not valid pointer\|freed pointer' "$RUN/map.out")
grep -a 'overflowed pointer\|not valid pointer\|freed pointer' "$RUN/map.out" | head -3 | sed 's/^/    /'
if [ "$n" -gt 0 ]; then echo "FAIL  memory manager found $n corrupted block(s) (the fd-0 buffer was overrun)"; rc=1
else echo "ok    no corrupted blocks at shutdown"; fi
grep -a -c 'Successfully terminated' "$RUN/map.out" | sed 's/^/    map terminated cleanly: /'
exit $rc
