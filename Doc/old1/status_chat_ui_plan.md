# @status Chat UI (buffs + cooldowns) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `@status` (alias `@cd`) prints the player's active status changes and skill cooldowns with remaining time in chat, since the PV7 client shows neither numerically.

**Architecture:** A player-level atcommand reads `sd->sc.data[]` (active SCs, remaining via the SC timer) and `sd->blockskill[]` (skills on cooldown). To show exact cooldown time, the skill-block system is extended with a per-skill expiry tick (`sd->blockskill_tick[]`) set in `skill_blockpc_start`.

**Tech Stack:** C (map-server), eAthena atcommand framework, status_change + skill-block systems.

**Design spec:** `doc/status_chat_ui_design.md` (committed `91ce50c`).

**Branch:** `x64`. Run from repo root `/root/uAthena`. Build `make sql`.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/map/map.h` | modify | `unsigned int blockskill_tick[MAX_SKILL]` in `map_session_data` |
| `src/map/skill.c` | modify | record expiry in `skill_blockpc_start` |
| `src/map/atcommand.h` | modify | `AtCommand_Status` enum entry |
| `src/map/atcommand.c` | modify | `ACMD_FUNC(status)` decl; implementation; table entries `@status`+`@cd` |
| `conf/atcommand_athena.conf` | modify | `status: 0`, `cd: 0` |
| `doc/status_chat_ui_changes.md` | create | tester checklist |

Only additions; no existing behaviour changes. All needed APIs (`get_timer`, `gettick`, `DIFF_TICK`, `INVALID_TIMER`, `StatusSkillChangeTable`, `skill_get_name`, `SC_MAX`, `MAX_SKILL`) are already included in `atcommand.c`.

---

## Task 1: Engine extension — per-skill cooldown expiry

**Files:** Modify `src/map/map.h`, `src/map/skill.c`

- [ ] **Step 1: Add `blockskill_tick` to `map_session_data` (`src/map/map.h`)**

Find the PC's `char blockskill[MAX_SKILL];	// [celest]` (≈ line 636; NOT the `hd` one ≈ line 1000) and add after it:
```c
	unsigned int blockskill_tick[MAX_SKILL];	// expiry tick per skill, for @status cooldowns
```

- [ ] **Step 2: Record expiry in `skill_blockpc_start` (`src/map/skill.c`)**

In `skill_blockpc_start` the success path is:
```c
	sd->blockskill[skillid] = 1;
	return add_timer(gettick()+tick,skill_blockpc_end,sd->bl.id,skillid);
```
Change the first line's block to also store the expiry:
```c
	sd->blockskill[skillid] = 1;
	sd->blockskill_tick[skillid] = gettick()+tick;
	return add_timer(gettick()+tick,skill_blockpc_end,sd->bl.id,skillid);
```

- [ ] **Step 3: Build**

Run: `make sql 2>&1 | grep -E 'error:' | head; echo done`
Expected: no errors (new field, one assignment).

- [ ] **Step 4: Commit**

```bash
git add src/map/map.h src/map/skill.c
git commit -m "skill: record per-skill cooldown expiry (blockskill_tick) for @status

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `@status` / `@cd` atcommand

**Files:** Modify `src/map/atcommand.h`, `src/map/atcommand.c`, `conf/atcommand_athena.conf`

- [ ] **Step 1: Add enum entry in `src/map/atcommand.h`**

Find `AtCommand_Quest,  // questlog chat UI` (added by the quest chat UI) — or `AtCommand_ShowMobs,` — and add before `AtCommand_Unknown,`:
```c
	AtCommand_Status, // status/cooldown chat UI
```

- [ ] **Step 2: Add the ACMD declaration in `src/map/atcommand.c`**

After `ACMD_FUNC(quest);  // questlog chat UI` (or `ACMD_FUNC(mobinfo); //by Lupus`) add:
```c
ACMD_FUNC(status); // status/cooldown chat UI
```

- [ ] **Step 3: Add the table entries in `atcommand_info[]`**

After the `{ AtCommand_Quest, "@quest", 1, atcommand_quest },` line (or after `@whodrops`) add:
```c
	{ AtCommand_Status,             "@status",           1, atcommand_status }, // buffs+cooldowns
	{ AtCommand_Status,             "@cd",               1, atcommand_status }, // alias
```

- [ ] **Step 4: Implement the command (append near the quest ACMD bodies, before `atcommand_mobinfo`)**

```c
/*==========================================
 * @status / @cd : active status changes + skill cooldowns with remaining time
 * (PV7 client shows neither numerically)
 *------------------------------------------*/
int atcommand_status(const int fd, struct map_session_data* sd, const char* command, const char* message)
{
	int i, shown;
	unsigned int now = gettick();
	nullpo_retr(-1, sd);

	clif_displaymessage(fd, "--- Status (buffs/debuffs) ---");
	shown = 0;
	for( i = 1; i < SC_MAX; i++ )
	{
		const struct TimerData *td;
		int rem;
		if( sd->sc.data[i].timer == INVALID_TIMER )
			continue;
		td = get_timer(sd->sc.data[i].timer);
		rem = td ? DIFF_TICK(td->tick, now)/1000 : 0;
		if( StatusSkillChangeTable[i] > 0 )
			snprintf(atcmd_output, sizeof(atcmd_output), "[Status] %s: %ds",
				skill_get_name(StatusSkillChangeTable[i]), rem);
		else
			snprintf(atcmd_output, sizeof(atcmd_output), "[Status] SC#%d: %ds", i, rem);
		clif_displaymessage(fd, atcmd_output);
		shown++;
	}
	if( !shown )
		clif_displaymessage(fd, "No active status.");

	clif_displaymessage(fd, "--- Cooldowns ---");
	shown = 0;
	for( i = 1; i < MAX_SKILL; i++ )
	{
		int rem;
		if( sd->blockskill[i] <= 0 )
			continue;
		rem = DIFF_TICK(sd->blockskill_tick[i], now)/1000;
		if( rem < 0 ) rem = 0;
		snprintf(atcmd_output, sizeof(atcmd_output), "[CD] %s: %ds", skill_get_name(i), rem);
		clif_displaymessage(fd, atcmd_output);
		shown++;
	}
	if( !shown )
		clif_displaymessage(fd, "No cooldowns.");

	return 0;
}
```

- [ ] **Step 5: Register player access in `conf/atcommand_athena.conf`**

After the `quest: 0` line (added by the quest chat UI) add:
```
// Show active buffs/debuffs and skill cooldowns with remaining time
status: 0
cd: 0
```

- [ ] **Step 6: Build**

Run: `make sql 2>&1 | grep -E 'error:|warning:' | grep -ivE 'request|conquest' | head; echo done`
Expected: no errors/warnings.

- [ ] **Step 7: Commit**

```bash
git add src/map/atcommand.h src/map/atcommand.c conf/atcommand_athena.conf
git commit -m "status: @status/@cd chat UI (active SCs + skill cooldowns w/ remaining time)

Player-level; SC name via StatusSkillChangeTable/SC#, remaining via get_timer;
cooldown remaining via blockskill_tick. ASCII labels. Existing commands unchanged.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Verify + tester doc + push

**Files:** Create `doc/status_chat_ui_changes.md`

- [ ] **Step 1: Clean build + API-invariant**

Run:
```bash
make sql 2>&1 | grep -E 'error:|warning:' | grep -ivE 'request|conquest' | head
git diff 91ce50c -- src/map/atcommand.c src/map/skill.c src/map/map.h | grep -E '^-' | grep -vE '^---' | head
```
Expected: first empty (clean); second empty (only additions — no existing line removed).

- [ ] **Step 2: Boot smoke**

Run: `set +e; timeout 20 ./map-server_sql > /tmp/st.log 2>&1; for p in $(pgrep -x map-server_sql); do kill -9 "$p"; done; grep -E "entries in 'quest_db.txt'|No memory leaks" /tmp/st.log`
Expected: server boots (quest_db reads, no leaks). (Live `@status` exercise needs a client + active buffs/cooldowns — testers' phase.)

- [ ] **Step 3: Write `doc/status_chat_ui_changes.md`**

```markdown
# @status / @cd — что изменено и что проверять

## Что добавлено
- `@status` (и алиас `@cd`) — игрокам: две секции в чат —
  - **баффы/дебаффы:** активные SC (`timer!=-1`), имя (скилл через StatusSkillChangeTable, иначе `SC#<num>`),
    остаток времени; пусто → «No active status»;
  - **кулдауны:** скиллы на кд (`blockskill[i]>0`) с остатком до готовности; пусто → «No cooldowns».
- Движок: добавлено поле `blockskill_tick[MAX_SKILL]` в сессию + запись expiry в `skill_blockpc_start`
  (для точного времени кулдауна). Поведение кулдаунов не меняется (читается только при флаге>0).
- Метки ASCII English (клиент 2007 докодовый; имена скиллов английские). RU — позже через msg_txt.
- Только добавления; существующие команды/механики не изменены.

## Что проверять (кластер: client)
1. Под баффом (напр. Blessing/Increase Agi/еда) `@status` показывает строку с остатком времени.
2. После скилла с кулдауном — `@status`/`@cd` показывает скилл и остаток до готовности; по истечении исчезает.
3. Без баффов/кд — «No active status» / «No cooldowns».
4. Не-скилловые SC отображаются как `SC#<num>` (имя по иконке в клиенте) — это ожидаемо.
5. Действующие команды/скиллы/кулдауны работают как раньше.

## Вне объёма
Кулдауны гомункула; именованная таблица для не-скилловых SC (позже).

## Будущее (дорожная карта)
`@whereis <моб>`; `@market <item>`; достижения/титулы; отдельный SP — наёмники.
```

- [ ] **Step 4: Commit + push**

```bash
git add doc/status_chat_ui_changes.md
git commit -m "doc: tester checklist for @status chat UI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin x64   # if rejected: git fetch origin x64 && git rebase origin/x64, re-verify build, push
```

---

## Notes for the implementer
- `sd->sc.data[i].timer == INVALID_TIMER` (-1) means inactive — exactly the engine's own active test.
- `blockskill[i]` is indexed by the (possibly remapped guild/homun) skill id; for normal player skills index==id, so `skill_get_name(i)` is correct. Guild/homun cooldowns may show a placeholder name — acceptable, out of scope.
- `blockskill_tick[i]` is only read when `blockskill[i] > 0`, so it never needs clearing on cooldown end.
- Only additions: no existing atcommand / skill-block / status behaviour changes.
```
