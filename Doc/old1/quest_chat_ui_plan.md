# Quest Chat UI (@quests/@quest) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the SP2 quest-log in chat via `@quests`/`@quest <N>`/`@quest <N> cancel`, so players on the PV7 client (no quest-journal window) can see and manage quests.

**Architecture:** Two new player-level atcommands in `atcommand.c` that read `sd->quest_log[]` + `quest_db[]` and print via `clif_displaymessage`. The SP2 engine is enhanced to store each quest's name (already present in `quest_db.txt`, 9th field). Output labels are ASCII English (the 2007 client is codepage-based; UTF-8 Cyrillic would garble; quest/mob names are already English).

**Tech Stack:** C (map-server), eAthena atcommand framework, SP2 quest engine.

**Design spec:** `doc/quest_chat_ui_design.md` (committed `55d4916`). Builds on SP2 (`doc/backport_sp2_questlog_design.md`).

**Branch:** `x64`. Run from repo root `/root/uAthena`. Build `make sql`.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/map/quest.h` | modify | add `char name[64]` to `struct s_quest_db` |
| `src/map/quest.c` | modify | parse the quoted 9th field (name) in `quest_read_db` |
| `src/map/atcommand.h` | modify | `AtCommand_Quests`, `AtCommand_Quest` enum entries (before `AtCommand_Unknown`) |
| `src/map/atcommand.c` | modify | `#include "quest.h"`; 2 `ACMD_FUNC` decls; helper + 2 implementations; 2 table entries |
| `conf/atcommand_athena.conf` | modify | `quests: 0`, `quest: 0` (player level) |
| `doc/quest_chat_ui_changes.md` | create | tester checklist |

Existing atcommands, NPCs, and the SP2 engine behaviour are unchanged (only additions).

---

## Task 1: Quest names in the engine

**Files:** Modify `src/map/quest.h`, `src/map/quest.c`

- [ ] **Step 1: Add `name` to `struct s_quest_db` in `src/map/quest.h`**

Change the struct (the `//char name[NAME_LENGTH];` line) to a real field:
```c
struct s_quest_db {
	int id;
	unsigned int time;
	int mob[MAX_QUEST_OBJECTIVES];
	int count[MAX_QUEST_OBJECTIVES];
	int num_objectives;
	char name[64];
};
```

- [ ] **Step 2: Parse the name in `quest_read_db` (`src/map/quest.c`)**

Replace the commented line `//memcpy(quest_db[k].name, str[8], sizeof(str[8]));` (right after `quest_db[k].num_objectives = i;`) with a quoted-name extraction. After the 8-field loop, `p` points at the 9th field (the quoted name):
```c
		quest_db[k].num_objectives = i;
		// 9th field: quoted quest name (e.g. ...,"Transcend") - p points past the 8th comma
		{
			char *ns = strchr(p, '"');
			if( ns != NULL )
			{
				char *ne = strchr(ns + 1, '"');
				if( ne != NULL )
				{
					int nlen = (int)(ne - (ns + 1));
					if( nlen >= (int)sizeof(quest_db[k].name) )
						nlen = sizeof(quest_db[k].name) - 1;
					memcpy(quest_db[k].name, ns + 1, nlen);
					quest_db[k].name[nlen] = '\0';
				}
			}
		}
		k++;
```

- [ ] **Step 3: Build the map-server**

Run: `make sql 2>&1 | grep -E 'error:' | head; echo done`
Expected: no errors; `map-server_sql` relinks.

- [ ] **Step 4: Boot-verify quest_db still parses**

Run: `timeout 25 ./map-server_sql > /tmp/qboot.log 2>&1; pkill -9 -f map-server_sql; grep -E "entries in 'quest_db.txt'" /tmp/qboot.log`
Expected: `Done reading '1703' entries in 'quest_db.txt'.` (name parsing didn't break the loader). Use `set +e` so the trailing pkill doesn't abort the line.

- [ ] **Step 5: Commit**

```bash
git add src/map/quest.h src/map/quest.c
git commit -m "quest: store quest name from quest_db.txt (9th field) for chat UI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `@quests` / `@quest` atcommands

**Files:** Modify `src/map/atcommand.h`, `src/map/atcommand.c`, `conf/atcommand_athena.conf`

- [ ] **Step 1: Add enum entries in `src/map/atcommand.h`**

Find `AtCommand_Unknown,` (the comment warns not to place commands after it) and add immediately BEFORE it:
```c
	AtCommand_Quests,
	AtCommand_Quest,
```

- [ ] **Step 2: Add `#include "quest.h"` and ACMD declarations in `src/map/atcommand.c`**

In the include block (after `#include "mob.h"`), add:
```c
#include "quest.h"
```
Also ensure `#include <time.h>` is present among the system includes (the detail line uses `time()`); add it next to `#include <math.h>` if absent.
In the `ACMD_FUNC(...)` declaration block (e.g. after `ACMD_FUNC(whodrops);`), add:
```c
ACMD_FUNC(quests);
ACMD_FUNC(quest);
```

- [ ] **Step 3: Add the two table entries in `atcommand_info[]`**

After the `{ AtCommand_WhoDrops, "@whodrops", 1, atcommand_whodrops },` line add:
```c
	{ AtCommand_Quests,             "@quests",           1, atcommand_quests },
	{ AtCommand_Quest,              "@quest",            1, atcommand_quest },
```

- [ ] **Step 4: Implement the commands (append near other ACMD_FUNC bodies, e.g. before `atcommand_mobinfo`)**

```c
/*==========================================
 * Quest chat UI (PV7 client has no quest journal window)
 *------------------------------------------*/
// Resolve display position N (1-based, completed-first then active) to a quest_log index.
static int atcommand_quest_idx(struct map_session_data *sd, int n)
{
	int i, k = 0;
	for( i = 0; i < sd->num_quests; i++ )
		if( sd->quest_log[i].state == Q_COMPLETE && ++k == n ) return i;
	for( i = 0; i < sd->num_quests; i++ )
		if( sd->quest_log[i].state != Q_COMPLETE && ++k == n ) return i;
	return -1;
}

// One summary line: "[N] <quest_id> "<name>" - <status>[, <time>][ | obj,obj]"
static void atcommand_quest_line(const int fd, struct map_session_data *sd, int idx, int n)
{
	struct s_quest_db *q = &quest_db[sd->quest_index[idx]];
	const char *st = (sd->quest_log[idx].state == Q_COMPLETE) ? "complete" :
	                 (sd->quest_log[idx].state == Q_ACTIVE)   ? "active" : "inactive";
	char tbuf[32] = "";
	char obuf[120] = "";
	int j;
	if( sd->quest_log[idx].time )
	{
		int rem = (int)(sd->quest_log[idx].time - (unsigned int)time(NULL));
		if( rem <= 0 ) snprintf(tbuf, sizeof(tbuf), ", expired");
		else snprintf(tbuf, sizeof(tbuf), ", %dh%02dm left", rem/3600, (rem%3600)/60);
	}
	for( j = 0; j < q->num_objectives; j++ )
	{
		struct mob_db *md = mob_db(q->mob[j]);
		char one[40];
		snprintf(one, sizeof(one), "%s%s %d/%d", j?", ":"", md?md->jname:"?",
		         sd->quest_log[idx].count[j], q->count[j]);
		strncat(obuf, one, sizeof(obuf)-strlen(obuf)-1);
	}
	snprintf(atcmd_output, sizeof(atcmd_output), "[%d] %d \"%s\" - %s%s%s%s",
	         n, sd->quest_log[idx].quest_id, q->name[0]?q->name:"(no name)", st, tbuf,
	         obuf[0]?" | ":"", obuf);
	clif_displaymessage(fd, atcmd_output);
}

ACMD_FUNC(quests)
{
	int i, n = 0;
	nullpo_retr(-1, sd);
	if( sd->num_quests == 0 )
	{
		clif_displaymessage(fd, "You have no quests.");
		return 0;
	}
	clif_displaymessage(fd, "--- Quests (completed) ---");
	for( i = 0; i < sd->num_quests; i++ )
		if( sd->quest_log[i].state == Q_COMPLETE )
			atcommand_quest_line(fd, sd, i, ++n);
	clif_displaymessage(fd, "--- Quests (active) ---");
	for( i = 0; i < sd->num_quests; i++ )
		if( sd->quest_log[i].state != Q_COMPLETE )
			atcommand_quest_line(fd, sd, i, ++n);
	clif_displaymessage(fd, "@quest <N> = details, @quest <N> cancel = drop");
	return 0;
}

ACMD_FUNC(quest)
{
	int n = 0, idx, j;
	char sub[16] = "";
	struct s_quest_db *q;
	nullpo_retr(-1, sd);

	if( !message || !*message || sscanf(message, "%d %15s", &n, sub) < 1 )
	{
		clif_displaymessage(fd, "Usage: @quest <N> [cancel]   (N from @quests)");
		return -1;
	}
	idx = atcommand_quest_idx(sd, n);
	if( idx < 0 )
	{
		clif_displaymessage(fd, "No quest with that number. Type @quests.");
		return -1;
	}

	if( strcmpi(sub, "cancel") == 0 )
	{
		int qid = sd->quest_log[idx].quest_id;
		quest_delete(sd, qid);
		snprintf(atcmd_output, sizeof(atcmd_output), "Quest [%d] (id %d) cancelled.", n, qid);
		clif_displaymessage(fd, atcmd_output);
		return 0;
	}

	// details
	atcommand_quest_line(fd, sd, idx, n);
	q = &quest_db[sd->quest_index[idx]];
	for( j = 0; j < q->num_objectives; j++ )
	{
		struct mob_db *md = mob_db(q->mob[j]);
		snprintf(atcmd_output, sizeof(atcmd_output), "  - %s: %d / %d",
		         md?md->jname:"?", sd->quest_log[idx].count[j], q->count[j]);
		clif_displaymessage(fd, atcmd_output);
	}
	clif_displaymessage(fd, "@quest <N> cancel = drop this quest");
	return 0;
}
```

- [ ] **Step 5: Register player access in `conf/atcommand_athena.conf`**

After the `mobinfo: 0` line (or any clear spot), add:
```
quests: 0
quest: 0
```

- [ ] **Step 6: Build the map-server**

Run: `make sql 2>&1 | grep -E 'error:' | head; echo done`
Expected: no errors; `map-server_sql` relinks.

- [ ] **Step 7: Commit**

```bash
git add src/map/atcommand.h src/map/atcommand.c conf/atcommand_athena.conf
git commit -m "quest: @quests/@quest chat UI (list/details/cancel) for PV7 client

Player-level atcommands reading sd->quest_log + quest_db; completed listed first
(active stays at chat bottom), short display-index id; cancel drops any quest. ASCII
labels (codepage-safe). Engine unchanged.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Verify + tester doc + push

**Files:** Create `doc/quest_chat_ui_changes.md`

- [ ] **Step 1: Final build + API-invariant check**

Run:
```bash
make sql 2>&1 | grep -E 'error:|warning:' | grep -ivE 'request|conquest' | head
git diff 55d4916 -- src/map/atcommand.c | grep -E '^-' | grep -vE '^---' | head
```
Expected: first command empty (clean build); second empty (no existing atcommand line removed — only additions).

- [ ] **Step 2: Boot smoke**

Run: `set +e; timeout 20 ./map-server_sql > /tmp/qboot2.log 2>&1; pkill -9 -f map-server_sql; grep -iE "quest_db.txt|atcommand" /tmp/qboot2.log | grep -ivE 'request' | tail`
Expected: quest_db reads (1703), no atcommand-registration errors. (Live `@quests` exercise needs a client — testers' phase.)

- [ ] **Step 3: Write `doc/quest_chat_ui_changes.md`**

```markdown
# Quest chat UI (@quests/@quest) — что изменено и что проверять

## Что добавлено
- `@quests` — список квестов в чат (сначала выполненные, потом активные — активные внизу/видны),
  каждая строка `[N] <id> "<имя>" - статус[, время][ | цели]`.
- `@quest <N>` — подробности N-го квеста из списка (id, имя, статус, время, цели построчно).
- `@quest <N> cancel` — отмена любого квеста (включая выполненный), без доп. подтверждения.
- Движок SP2 дополнен: имя квеста парсится из `db/quest_db.txt` (9-е поле).
- Доступ: игрокам (`atcommand_athena.conf`: `quests: 0`, `quest: 0`).
- Метки вывода — ASCII English (клиент 2007 докодовый; имена квестов/мобов и так английские).
  Локализацию при желании — через `msg_txt`/msg_athena.conf (отдельно).

## Что проверять (кластер: char+map+клиент)
1. `@quests` показывает квесты с именами, статусом, временем, целями; выполненные сверху, активные снизу.
2. `@quest <N>` — корректные детали N-го; неверный N → подсказка.
3. `@quest <N> cancel` — квест исчезает из `@quests`; перезаход — изменение сохранилось.
4. N стабилен в пределах одного `@quests`; после cancel/выполнения — перечитать `@quests`.
5. Команды влияют только на свои квесты; действующие atcommand'ы/NPC не сломаны.

## Будущее (одобренная дорожная карта)
Нотификация прогресса цели в чат при убийстве моба; `@status`/кулдауны; `@whereis`/`@market`;
достижения/титулы; и отдельный SP — система наёмников (Mercenary) + её команды.
```

- [ ] **Step 4: Commit + push**

```bash
git add doc/quest_chat_ui_changes.md
git commit -m "doc: tester checklist for quest chat UI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin x64   # if rejected: git fetch origin x64 && git rebase origin/x64, re-verify build, push
```

---

## Notes for the implementer
- `atcommand_quest_idx` MUST iterate in the same order `@quests` prints (completed first, then active) so display-N maps to the right quest. Both use that order.
- `mob_db(id)` may return NULL for an unknown objective mob id — guard with `md?md->jname:"?"` (done).
- Output labels stay ASCII; quest/mob names from data are already English. Russian UI = a later msg_txt pass.
- Only additions: no existing atcommand/enum/NPC/engine behaviour changes.
