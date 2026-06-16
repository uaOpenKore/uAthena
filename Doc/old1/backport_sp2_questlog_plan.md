# SP2 Quest-Log Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port eAthena's quest-log engine (state + persistence) into uAthena as the foundation for quest NPCs, adding only new API and never changing existing script commands or NPCs.

**Architecture:** Faithful port of the eathena-ref quest subsystem. Map-server holds `sd->quest_log[]` in memory, exposes 5 script commands, requests the questlog on login and saves it diff-wise to the char-server over new inter-server packets (`0x3060/0x3061` map→char, `0x3860/0x3861` char→map); the char-server persists to the SQL `quest` table. The client journal window (`clif_quest_*`) is ported but guarded by `#if PACKETVER >= 20080000`, so it is dormant under uAthena's current PACKETVER 7 and the engine runs headless.

**Tech Stack:** C (map-server + char_sql server), MySQL/MariaDB, eAthena inter-server framework.

**Design spec:** `doc/backport_sp2_questlog_design.md` (committed `1100889`).

**Branch:** `x64`. Run from repo root `/root/uAthena`. Build with `make sql`.

**Port sources (read these from `/tmp/eathena-ref` with the Read tool — do NOT shell-`grep` `.c` there, it's wrapped):**
`src/map/quest.h`, `src/map/quest.c`, `src/char_sql/int_quest.c`, `src/char_sql/int_quest.h`,
`src/common/mmo.h` (struct quest @188-199, MAX_QUEST_DB/MAX_QUEST_OBJECTIVES @111-112),
`src/map/clif.c` (clif_quest_* @14550+), `src/map/intif.c` (quest funcs @1344-1410, packet_len @43, parse @2067),
`src/map/script.c` (BUILDIN setquest/checkquest/erasequest/completequest/changequest).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/common/mmo.h` | modify | `struct quest`, `enum quest_state`, `MAX_QUEST_DB`, `MAX_QUEST_OBJECTIVES` |
| `src/map/pc.h` | modify | session fields: `num_quests`, `avail_quests`, `quest_log[]`, `quest_index[]`, `save_quest` |
| `src/map/quest.h` / `quest.c` | create | quest engine (db load, add/delete/change/check, login, objective) |
| `src/map/clif.c` / `clif.h` | modify | `clif_quest_*` (6 funcs) guarded by `#if PACKETVER >= 20080000` |
| `src/map/intif.c` | modify | map-side request/save/parse + packet_len row 0x3860 |
| `src/map/script.c` | modify | 5 BUILDIN_DEF + implementations |
| `src/map/chrif.c` | modify | quest save hook in `chrif_save` |
| `src/map/pc.c` | modify | `intif_request_questlog(sd)` in `pc_authok` |
| `src/map/mob.c` | modify | `quest_update_objective` hook in `mob_dead` |
| `src/map/map.c` | modify | `do_init_quest()` in `do_init`, `do_final_quest` if any |
| `src/char_sql/int_quest.c` / `int_quest.h` | create | char-side SQL load + diff-save |
| `src/char_sql/inter.c` | modify | chain `inter_quest_parse_frommap`, length table 0x3060/0x3061, init |
| `src/char_sql/char.c` | modify | `char quest_db[256] = "quest";` table-name config |
| `db/quest_db.txt` | create | quest definitions (port) |
| `sql-files/quest.sql` + `dumps/migrations/` | create | `quest` table + idempotent migration |
| `src/map/Makefile`,`GNUmakefile`; `src/char_sql/Makefile`,`GNUmakefile` | modify | `obj/quest.o`, `int_quest.o` |

> The build goes green at the END of Task 3 (map-side) and Task 4 (char-side); intermediate states within a task may not compile. Do not push until Task 8 verifies a clean build of both servers.

---

## Task 1: Common types (mmo.h + pc.h)

**Files:** Modify `src/common/mmo.h`, `src/map/pc.h`

- [ ] **Step 1: Add quest constants + struct to `src/common/mmo.h`**

Find the existing `#define MAX_...` block near the top of `mmo.h` and add:

```c
#define MAX_QUEST_DB 2000 //Max quests that the server will load
#define MAX_QUEST_OBJECTIVES 3 //Max quest objectives for a quest
```

Then, just BEFORE `struct item {` (the struct quest must precede anything using it), add:

```c
//Questlog system [Kevin] [Inkfish]
typedef enum quest_state { Q_INACTIVE, Q_ACTIVE, Q_COMPLETE } quest_state;

struct quest {
	int quest_id;
	unsigned int time;
	int count[MAX_QUEST_OBJECTIVES];
	quest_state state;
};
```

- [ ] **Step 2: Add session fields to `struct map_session_data` in `src/map/pc.h`**

Find `struct mmo_charstatus status;` inside `struct map_session_data` and add immediately after it:

```c
	// Questlog system
	int num_quests;          // total quests (active + inactive + complete)
	int avail_quests;        // active + inactive (not yet complete)
	int quest_index[MAX_QUEST_DB]; // index into quest_db[] per quest_log entry
	struct quest quest_log[MAX_QUEST_DB];
	bool save_quest;
```

- [ ] **Step 3: Verify it compiles (types only)**

Run: `make sql 2>&1 | grep -iE 'error|quest' | head`
Expected: no errors (struct additions only; nothing references the new fields yet).

- [ ] **Step 4: Commit**

```bash
git add src/common/mmo.h src/map/pc.h
git commit -m "quest(common): struct quest + map_session_data questlog fields

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: clif quest-window functions (guarded, dormant under PV7)

**Files:** Modify `src/map/clif.c`, `src/map/clif.h`

- [ ] **Step 1: Port the 6 clif quest functions into `src/map/clif.c`, each body guarded**

Read the 6 functions from `/tmp/eathena-ref/src/map/clif.c` (starting at `clif_quest_send_list` @14550): `clif_quest_send_list`, `clif_quest_send_mission`, `clif_quest_add`, `clif_quest_delete`, `clif_quest_update_objective`, `clif_quest_update_status`. Append them near the end of uAthena `clif.c` (before the parse table), wrapping **each function body** so it is dormant under the current client:

```c
void clif_quest_send_list(struct map_session_data *sd)
{
#if PACKETVER >= 20080000
	... (verbatim eathena body) ...
#endif
}
```
Apply the SAME `#if PACKETVER >= 20080000 ... #endif` wrapper inside all 6 bodies. Adaptation notes: uAthena `clif.c` uses the same `WFIFOHEAD/WFIFOW/WFIFOL/WFIFOSET` idioms — copy verbatim; `struct quest` and `quest_db[]`/`quest_index[]` are available from Task 1/Task 3 headers (include `quest.h`).

- [ ] **Step 2: Declare the 6 prototypes in `src/map/clif.h`**

Find the block of `void clif_*` prototypes and add:

```c
void clif_quest_send_list(struct map_session_data *sd);
void clif_quest_send_mission(struct map_session_data *sd);
void clif_quest_add(struct map_session_data *sd, struct quest *qd, int index);
void clif_quest_delete(struct map_session_data *sd, int quest_id);
void clif_quest_update_objective(struct map_session_data *sd, struct quest *qd, int index);
void clif_quest_update_status(struct map_session_data *sd, int quest_id, bool active);
```

- [ ] **Step 3: Verify clif compiles (functions present, dormant)**

Run: `make sql 2>&1 | grep -iE 'error' | head`
Expected: no errors. (Under PACKETVER 7 the bodies are empty; unused-parameter warnings are acceptable.)

- [ ] **Step 4: Commit**

```bash
git add src/map/clif.c src/map/clif.h
git commit -m "quest(clif): port quest-window packets, guarded by PACKETVER (dormant under PV7)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Map-side quest engine (quest.c + intif + script + wiring)

**Files:** Create `src/map/quest.h`, `src/map/quest.c`; Modify `src/map/intif.c`, `src/map/script.c`, `src/map/map.c`, `src/map/Makefile`, `src/map/GNUmakefile`

- [ ] **Step 1: Create `src/map/quest.h` and `src/map/quest.c` (port)**

Copy `/tmp/eathena-ref/src/map/quest.h` → `src/map/quest.h` verbatim.
Copy `/tmp/eathena-ref/src/map/quest.c` → `src/map/quest.c` verbatim. Adaptation check (all already satisfied in uAthena): `ARR_FIND`, `save_settings`, `chrif_save`, `clif_quest_*` (Task 2), `intif_*` (Step 2 below), `ShowError/ShowStatus`, `db_path` are all present. No code changes expected; if a symbol is missing, stop and report.

- [ ] **Step 2: Add map-side intif quest plumbing to `src/map/intif.c`**

Read the four functions from `/tmp/eathena-ref/src/map/intif.c` (`intif_request_questlog` @1344, `intif_parse_questlog` @1353, `intif_parse_questsave` @1391, `intif_quest_save` @1404) and copy them into uAthena `intif.c` (near the other request/parse funcs). Then:

(a) In the `packet_len_table[]` (line 30), set the `0x3860` row. The table is laid out 16 entries per comment-row; replace the `0x3860` row (currently all-zero) with:
```c
	-1, 7, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0,  0, 0, //0x3860  Quests
```
(b) In `intif_parse()` switch (near the homun cases ~1561), add:
```c
	case 0x3860:	intif_parse_questlog(fd); break;
	case 0x3861:	intif_parse_questsave(fd); break;
```
(c) Declare `int intif_request_questlog(struct map_session_data *sd);` and `int intif_quest_save(struct map_session_data *sd);` in `src/map/intif.h`.

- [ ] **Step 3: Add the 5 script commands to `src/map/script.c`**

In the `buildin_func[]` table add (next to other BUILDIN_DEF lines):
```c
	BUILDIN_DEF(setquest,"i"),
	BUILDIN_DEF(erasequest,"i"),
	BUILDIN_DEF(completequest,"i"),
	BUILDIN_DEF(changequest,"ii"),
	BUILDIN_DEF(checkquest,"i?"),
```
Then add the 5 implementations (port from `/tmp/eathena-ref/src/map/script.c`; uAthena uses `int buildin_x(struct script_state *st)` returning 0):
```c
BUILDIN_FUNC(setquest)
{
	struct map_session_data *sd = script_rid2sd(st);
	nullpo_retr(0, sd);
	quest_add(sd, script_getnum(st, 2));
	return 0;
}
BUILDIN_FUNC(erasequest)
{
	struct map_session_data *sd = script_rid2sd(st);
	nullpo_retr(0, sd);
	quest_delete(sd, script_getnum(st, 2));
	return 0;
}
BUILDIN_FUNC(completequest)
{
	struct map_session_data *sd = script_rid2sd(st);
	nullpo_retr(0, sd);
	quest_update_status(sd, script_getnum(st, 2), Q_COMPLETE);
	return 0;
}
BUILDIN_FUNC(changequest)
{
	struct map_session_data *sd = script_rid2sd(st);
	nullpo_retr(0, sd);
	quest_change(sd, script_getnum(st, 2), script_getnum(st, 3));
	return 0;
}
BUILDIN_FUNC(checkquest)
{
	struct map_session_data *sd = script_rid2sd(st);
	quest_check_type type = HAVEQUEST;
	nullpo_retr(0, sd);
	if( script_hasdata(st, 3) )
		type = (quest_check_type)script_getnum(st, 3);
	script_pushint(st, quest_check(sd, script_getnum(st, 2), type));
	return 0;
}
```
Note: `BUILDIN_FUNC` is uAthena's macro alias for the buildin function signature — confirm it exists in script.c; if uAthena spells it `int buildin_setquest(struct script_state *st)`, use that exact form instead. Add `#include "quest.h"` to script.c's includes.

- [ ] **Step 4: Initialize the engine — `src/map/map.c`**

In `do_init()` add `do_init_quest();` (near other `do_init_*` calls). Add `#include "quest.h"`.

- [ ] **Step 5: Add `quest.o` to the map build**

In `src/map/Makefile` and `src/map/GNUmakefile`, add `obj/quest.o` to `OBJECTS` (alongside `obj/livemob.o obj/mobgrid.o`), and add the dependency rule:
```
sqlobj/quest.o: quest.c quest.h map.h pc.h npc.h itemdb.h script.h intif.h battle.h mob.h party.h unit.h log.h clif.h chrif.h $(COMMON_H)
```
(`GNUmakefile` is generated from `Makefile` via `sed 's/$>/$^/'` — edit both; verify they match.)

- [ ] **Step 6: Build the map-server green**

Run: `make sql 2>&1 | grep -iE 'error' | head; echo "exit ${PIPESTATUS[0]}"`
Expected: no errors; `map-server_sql` links. Fix any missing-symbol/signature mismatches before committing.

- [ ] **Step 7: Commit**

```bash
git add src/map/quest.c src/map/quest.h src/map/intif.c src/map/intif.h src/map/script.c src/map/map.c src/map/Makefile src/map/GNUmakefile
git commit -m "quest(map): engine, intif plumbing, 5 script commands, init + build

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Char-side quest storage (int_quest.c + inter/char wiring)

**Files:** Create `src/char_sql/int_quest.c`, `src/char_sql/int_quest.h`; Modify `src/char_sql/inter.c`, `src/char_sql/char.c`, `src/char_sql/Makefile`, `src/char_sql/GNUmakefile`

- [ ] **Step 1: Create the char-side files (port)**

Copy `/tmp/eathena-ref/src/char_sql/int_quest.c` → `src/char_sql/int_quest.c` and `int_quest.h` → `src/char_sql/int_quest.h` verbatim. Adaptation check: uAthena has `SqlStmt_*`, `Sql_Query`, `ARR_FIND`, `RFIFO*/WFIFO*` — all present. The table-name global is `quest_db` (added in Step 2).

- [ ] **Step 2: Add the quest table-name config to `src/char_sql/char.c`**

Find `char guild_db[256] = "guild";` (line ~46) and add after it:
```c
char quest_db[256] = "quest";
```
Add `extern char quest_db[256];` to `src/char_sql/char.h` next to the other `extern char *_db[...]` declarations.

- [ ] **Step 3: Register the quest handler in `src/char_sql/inter.c`**

(a) In `inter_recv_packet_length[]` (line 67, indexed by `cmd-0x3000`), set entries for `0x3060` and `0x3061`:
```c
	// 0x3060 quest load (req), 0x3061 quest save (var)
```
Set index `[0x60] = 6` (load: 2+char_id4) and `[0x61] = -1` (save: variable). (Match the array's existing layout/offsets exactly.)
(b) In `inter_parse_frommap()` (line 837), add to the handler chain (next to `|| inter_pet_parse_frommap(fd)` @862):
```c
		  || inter_quest_parse_frommap(fd)
```
(c) Add `#include "int_quest.h"` to inter.c includes.

- [ ] **Step 4: Add `int_quest.o` to the char build**

In `src/char_sql/Makefile` and `src/char_sql/GNUmakefile`, add `int_quest.o` to the char-server OBJECTS and a dependency rule mirroring `int_homun.o`'s:
```
int_quest.o: int_quest.c int_quest.h char.h inter.h $(COMMON_H)
```

- [ ] **Step 5: Build the char-server green**

Run: `make sql 2>&1 | grep -iE 'error' | head; echo done`
Expected: no errors; `char-server_sql` links.

- [ ] **Step 6: Commit**

```bash
git add src/char_sql/int_quest.c src/char_sql/int_quest.h src/char_sql/inter.c src/char_sql/char.c src/char_sql/char.h src/char_sql/Makefile src/char_sql/GNUmakefile
git commit -m "quest(char): SQL load + diff-save (int_quest), inter/char wiring + build

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Lifecycle hooks (login load, save, mob objective)

**Files:** Modify `src/map/pc.c`, `src/map/chrif.c`, `src/map/mob.c`

- [ ] **Step 1: Request the questlog on login — `src/map/pc.c`**

In `pc_authok()` (line ~579), after the character status is fully set up and the player is registered (near the end of the function, where other post-auth requests are issued), add:
```c
	intif_request_questlog(sd);
```
Ensure `#include "quest.h"` and `intif.h` are included in pc.c (intif.h already is).

- [ ] **Step 2: Save the questlog with the character — `src/map/chrif.c`**

In `chrif_save()` (line 156), next to the homunculus save (`if (sd->hd && merc_is_hom_active(sd->hd)) merc_save(sd->hd);` @195), add:
```c
	if (sd->save_quest)
		intif_quest_save(sd);
```
Add `#include "quest.h"` to chrif.c.

- [ ] **Step 3: Update hunt objectives on mob death — `src/map/mob.c`**

In `mob_dead()` (line 1691), inside the damage-log loop over `tmpsd[i]` (the players credited with the kill, ~line 1808 `if (!tmpsd[i]) continue;`), add after the continue guard:
```c
		if (tmpsd[i]->avail_quests)
			quest_update_objective(tmpsd[i], md->mob_id);
```
Confirm the mob's db id field name in uAthena `struct mob_data` — it is `md->mob_id` (use `md->class_` only if `mob_id` does not exist). Add `#include "quest.h"` to mob.c.

- [ ] **Step 4: Build green**

Run: `make sql 2>&1 | grep -iE 'error' | head; echo done`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add src/map/pc.c src/map/chrif.c src/map/mob.c
git commit -m "quest(map): hooks - login load, char-save, mob-kill objective update

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Data — quest_db + SQL table + migration

**Files:** Create `db/quest_db.txt`, `sql-files/quest.sql`, `dumps/migrations/7-questlog.sql`

- [ ] **Step 1: Port `db/quest_db.txt`**

Copy `/tmp/eathena-ref/db/quest_db.txt` → `db/quest_db.txt` verbatim.

- [ ] **Step 2: Create `sql-files/quest.sql` (the `quest` table)**

```sql
--
-- Table structure for table `quest`
--
CREATE TABLE IF NOT EXISTS `quest` (
  `char_id` int(11) unsigned NOT NULL default '0',
  `quest_id` int(10) unsigned NOT NULL,
  `state` enum('0','1','2') NOT NULL default '0',
  `time` int(11) unsigned NOT NULL default '0',
  `count1` mediumint(8) unsigned NOT NULL default '0',
  `count2` mediumint(8) unsigned NOT NULL default '0',
  `count3` mediumint(8) unsigned NOT NULL default '0',
  PRIMARY KEY  USING BTREE (`char_id`,`quest_id`)
) ENGINE=MyISAM;
```
(Table name `quest` matches `char.c` config. State enum order matches eAthena's stored ints 0/1/2.)

- [ ] **Step 3: Create an idempotent migration `dumps/migrations/7-questlog.sql`**

```sql
CREATE TABLE IF NOT EXISTS `quest` (
  `char_id` int(11) unsigned NOT NULL default '0',
  `quest_id` int(10) unsigned NOT NULL,
  `state` enum('0','1','2') NOT NULL default '0',
  `time` int(11) unsigned NOT NULL default '0',
  `count1` mediumint(8) unsigned NOT NULL default '0',
  `count2` mediumint(8) unsigned NOT NULL default '0',
  `count3` mediumint(8) unsigned NOT NULL default '0',
  PRIMARY KEY  USING BTREE (`char_id`,`quest_id`)
) ENGINE=MyISAM;
```
(Follows the migrations pattern from `dumps/migrations/`; see [[mob-db-sql-import-pipeline]] — `dumps.sh update` re-applies migrations.)

- [ ] **Step 4: Lint quest_db.txt format**

Run:
```bash
python3 - <<'EOF'
bad=0
for ln in open('db/quest_db.txt', encoding='latin-1'):
    s=ln.strip()
    if not s or s.startswith('//'): continue
    f=s.split(',')
    if len(f) < 8 or not f[0].isdigit():
        print('BAD:', s[:60]); bad+=1
print('format errors:', bad)
EOF
```
Expected: `format errors: 0`.

- [ ] **Step 5: Commit**

```bash
git add db/quest_db.txt sql-files/quest.sql dumps/migrations/7-questlog.sql
git commit -m "quest(data): quest_db.txt + quest table schema + migration

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Verification

**Files:** none unless a check forces a fix.

- [ ] **Step 1: Clean build of BOTH servers**

Run: `make sql 2>&1 | grep -iE 'error|warning: .*quest' | head; ls -la map-server_sql char-server_sql`
Expected: no errors; both binaries rebuilt (recent timestamps).

- [ ] **Step 2: API-invariant check — no existing script command changed**

Run: `git diff e16ca55 -- src/map/script.c | grep -E '^-\s*BUILDIN_DEF' | head`
Expected: empty (no existing `BUILDIN_DEF` line removed/changed; only additions).

- [ ] **Step 3: ASan smoke boot (best-effort, no cluster)**

Run: `timeout 12 ./char-server_sql 2>&1 | grep -iE 'quest|error' | grep -iv 'connect|inter-server' | head`
Expected: char-server reads config and references the `quest` table without a parse/SQL-definition error attributable to quests. (Full quest flow needs a running cluster — testers' phase.)

- [ ] **Step 4: No commit unless a check forced a fix.**

---

## Task 8: Tester document + push

**Files:** Create `doc/backport_sp2_questlog_changes.md`

- [ ] **Step 1: Write `doc/backport_sp2_questlog_changes.md`**

```markdown
# SP2 quest-лог: что изменено и что проверять

## Что добавлено
- Движок quest-лога (порт eAthena): `src/map/quest.c` + 5 команд (`setquest/erasequest/
  completequest/changequest/checkquest`); хранение на char-сервере (`src/char_sql/int_quest.c`,
  таблица `quest`); межсервер `0x3060/0x3061`↔`0x3860/0x3861`.
- Клиентское окно журнала (`clif_quest_*`) портировано, но под `#if PACKETVER>=20080000` — при текущем
  PACKETVER 7 спит (видимого окна нет; пакеты старому клиенту не шлются).
- **API не менялся:** добавлены только новые команды/функции; существующие NPC не затронуты.

## Перед запуском (БД)
- Применить миграцию `dumps/migrations/7-questlog.sql` (или `sql-files/quest.sql`) — создаёт таблицу `quest`.

## Что проверять (кластер: char+map+GRF)
1. Тест-NPC: `setquest`, `checkquest` (HAVEQUEST/PLAYTIME/HUNTING), `changequest`, `completequest`,
   `erasequest` — состояния меняются как ожидается.
2. Перезаход персонажа — активные/выполненные квесты сохранились и загрузились.
3. Hunt-квест: убийство нужного моба двигает счётчик; по достижении — `checkquest(id,HUNTING)`==2.
4. Time-limit квест: по истечении времени `checkquest(id,PLAYTIME)`==2.
5. Действующие NPC и команды не сломаны (выборочно).
6. (Окно журнала не появляется — ожидаемо под текущим клиентом.)

## Когда «подтянете клиент»
Поднять PACKETVER до даты ≥2008 (+ совместимый клиент) — окно журнала включится без правок кода.
```

- [ ] **Step 2: Commit the doc**

```bash
git add doc/backport_sp2_questlog_changes.md
git commit -m "doc: tester checklist for SP2 quest-log engine

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: Push**

Run: `git push origin x64` (if rejected, `git fetch origin x64 && git rebase origin/x64` then re-verify Task 7 Step 1 and push).
Expected: SP2 commits land on `origin/x64`.

---

## Notes for the implementer
- This is a faithful port: prefer copying the eathena-ref file and adjusting only what the adaptation notes call out, over re-typing.
- The build is RED until Task 3 (map) and Task 4 (char) complete — that is expected for an interdependent subsystem; verify green at each task's build step.
- `struct quest` is all-int (24 bytes, no pointers) → the inter-server `memcpy` is x64-safe; do not add pointer fields.
- Do NOT touch existing `BUILDIN_DEF` entries or change PACKETVER (separate client decision).
- Out of SP2: visible quest window (needs client upgrade), quest NPCs (SP3), mercenary API (SP4).
