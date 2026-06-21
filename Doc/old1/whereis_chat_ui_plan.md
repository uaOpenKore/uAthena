# @whereis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `@whereis <mob>` prints where a mob spawns (maps + counts) and what it drops, since the PV7 client has no mob search.

**Architecture:** A read-only player-level atcommand: resolve the mob by name (`mobdb_searchname`), scan `map[].moblist[]` for spawn maps, and read `mob_db()->dropitem[]` for drops; print via `clif_displaymessage`.

**Tech Stack:** C (map-server), eAthena atcommand framework.

**Design spec:** `doc/whereis_chat_ui_design.md` (committed `1e83587`).

**Branch:** `x64`. Run from repo root `/root/uAthena`. Build `make sql`.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/map/atcommand.h` | modify | `AtCommand_WhereIs` enum entry |
| `src/map/atcommand.c` | modify | `ACMD_FUNC(whereis)` decl + impl + table entry |
| `conf/atcommand_athena.conf` | modify | `whereis: 0` |
| `doc/whereis_chat_ui_changes.md` | create | tester checklist |

Only additions. `mobdb_searchname`, `map`/`map_num`/`MAX_MOB_LIST_PER_MAP`, `mob_db`, `MAX_MOB_DROP`, `itemdb_jname` are already available in `atcommand.c` (includes map.h, mob.h, itemdb.h).

---

## Task 1: `@whereis` atcommand

**Files:** Modify `src/map/atcommand.h`, `src/map/atcommand.c`, `conf/atcommand_athena.conf`

- [ ] **Step 1: Enum entry — `src/map/atcommand.h`**

Find `AtCommand_Status, // status/cooldown chat UI` and add after it (still before `AtCommand_Unknown,`):
```c
	AtCommand_WhereIs, // mob spawn/drop search
```

- [ ] **Step 2: ACMD declaration — `src/map/atcommand.c`**

After `ACMD_FUNC(status); // status/cooldown chat UI` add:
```c
ACMD_FUNC(whereis); // mob spawn/drop search
```

- [ ] **Step 3: Table entry — `src/map/atcommand.c`**

After `{ AtCommand_Status, "@cd", 1, atcommand_status }, // alias` add:
```c
	{ AtCommand_WhereIs,            "@whereis",          1, atcommand_whereis }, // mob spawn/drop
```

- [ ] **Step 4: Implementation — append before `int atcommand_status(...)` (or before `atcommand_mobinfo`)**

```c
/*==========================================
 * @whereis : where a mob spawns (maps + count) and what it drops
 * (PV7 client has no mob search)
 *------------------------------------------*/
int atcommand_whereis(const int fd, struct map_session_data* sd, const char* command, const char* message)
{
	int id, m, k, j, total, printed, any;
	struct mob_db *md;
	nullpo_retr(-1, sd);

	if( !message || !*message )
	{
		clif_displaymessage(fd, "Usage: @whereis <mob name>");
		return -1;
	}
	id = mobdb_searchname(message);
	if( id <= 0 )
	{
		snprintf(atcmd_output, sizeof(atcmd_output), "Mob not found: %s", message);
		clif_displaymessage(fd, atcmd_output);
		return -1;
	}
	md = mob_db(id);

	snprintf(atcmd_output, sizeof(atcmd_output), "[%s] (id %d)", md->jname, id);
	clif_displaymessage(fd, atcmd_output);

	// Spawns: one line per map (cap 20), then "(+N more)"
	clif_displaymessage(fd, "Spawns:");
	total = 0; printed = 0;
	for( m = 0; m < map_num; m++ )
		for( k = 0; k < MAX_MOB_LIST_PER_MAP; k++ )
		{
			struct spawn_data *spd = map[m].moblist[k];
			if( spd && spd->class_ == id )
			{
				total++;
				if( printed < 20 )
				{
					snprintf(atcmd_output, sizeof(atcmd_output), "  %s: %d", map[m].name, spd->num);
					clif_displaymessage(fd, atcmd_output);
					printed++;
				}
				break; // count each map once
			}
		}
	if( total == 0 )
		clif_displaymessage(fd, "  (none)");
	else if( total > printed )
	{
		snprintf(atcmd_output, sizeof(atcmd_output), "  ...(+%d more)", total - printed);
		clif_displaymessage(fd, atcmd_output);
	}

	// Drops
	clif_displaymessage(fd, "Drops:");
	any = 0;
	for( j = 0; j < MAX_MOB_DROP; j++ )
	{
		if( md->dropitem[j].nameid <= 0 )
			continue;
		snprintf(atcmd_output, sizeof(atcmd_output), "  %s: %.2f%%",
			itemdb_jname(md->dropitem[j].nameid), md->dropitem[j].p/100.0);
		clif_displaymessage(fd, atcmd_output);
		any = 1;
	}
	if( !any )
		clif_displaymessage(fd, "  (none)");

	return 0;
}
```

- [ ] **Step 5: Player access — `conf/atcommand_athena.conf`**

After the `cd: 0` line add:
```
// Where a mob spawns and what it drops
whereis: 0
```

- [ ] **Step 6: Build**

Run: `make sql 2>&1 | grep -E 'error:|warning:' | grep -ivE 'request|conquest' | head; echo done`
Expected: no errors/warnings in the new code (pre-existing map.c/clif.c/atcommand.c warnings unrelated).

- [ ] **Step 7: Commit**

```bash
git add src/map/atcommand.h src/map/atcommand.c conf/atcommand_athena.conf
git commit -m "whereis: @whereis chat command (mob spawn maps + drops)

mobdb_searchname -> scan map[].moblist for spawn maps (cap 20) + mob_db dropitem
for drops. Player-level, read-only, ASCII labels. Existing commands unchanged.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Verify + tester doc + push

**Files:** Create `doc/whereis_chat_ui_changes.md`

- [ ] **Step 1: Clean build + API-invariant**

Run:
```bash
make sql 2>&1 | grep -E 'error:' | head
git diff 1e83587 -- src/map/atcommand.c | grep -E '^-' | grep -vE '^---' | head
```
Expected: first empty (no errors); second empty (only additions).

- [ ] **Step 2: Boot smoke**

Run: `set +e; timeout 20 ./map-server_sql > /tmp/wi.log 2>&1; for p in $(pgrep -x map-server_sql); do kill -9 "$p"; done; grep -E "entries in 'quest_db.txt'|No memory leaks" /tmp/wi.log`
Expected: server boots, no leaks. (Live `@whereis` needs a client — testers' phase.)

- [ ] **Step 3: Write `doc/whereis_chat_ui_changes.md`**

```markdown
# @whereis — что изменено и что проверять

## Что добавлено
- `@whereis <имя моба>` — игрокам: резолв моба по имени, затем в чат:
  - **Spawns:** карты, где водится, с количеством (кап 20 + «(+N more)»); «(none)» если нигде;
  - **Drops:** предметы дропа с шансом %; «(none)» если нет.
- Read-only (скан `map[].moblist` + `mob_db dropitem`); метки/имена ASCII English. RU позже через msg_txt.
- Только добавления; существующие команды/механики не изменены.

## Что проверять (кластер: клиент)
1. `@whereis Poring` (или иной известный моб) — список карт спавна с количеством + список дропа с шансами.
2. Моб без спавнов/дропа — «(none)» в соответствующей секции.
3. Неизвестное имя → «Mob not found: <ввод>».
4. Частые мобы — список карт обрезан до 20 + «(+N more)» (не флудит).
5. Действующие команды работают как раньше.

## Будущее (дорожная карта)
`@market <item>`; достижения/титулы; отдельный SP — наёмники.
```

- [ ] **Step 4: Commit + push**

```bash
git add doc/whereis_chat_ui_changes.md
git commit -m "doc: tester checklist for @whereis"
git push origin x64   # if rejected: git fetch origin x64 && git rebase origin/x64, re-verify build, push
```

---

## Notes for the implementer
- `mobdb_searchname` is case-insensitive exact jname match; `id<=0` means not found.
- `map[m].moblist[k]` may be NULL (sparse) — guard (done). `break` after first match counts each map once.
- `md->dropitem[j].p` is rate in 0.01% units → `p/100.0` gives percent.
- Only additions: no existing atcommand behaviour changes.
```
