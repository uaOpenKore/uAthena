# Quest Progress Chat Notification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notify a player in chat when a quest hunt-objective advances, since the PV7 client cannot pop objective updates.

**Architecture:** A `battle_config.quest_progress_notify` toggle (0=off / 1=each kill / 2=on-completion, default 2) gates a small chat block added inside the SP2 `quest_update_objective` (right after the count increment). ASCII English labels; quest/mob names come from the data.

**Tech Stack:** C (map-server), SP2 quest engine, eAthena battle_config.

**Design spec:** `doc/quest_progress_notify_design.md` (committed `f505c25`).

**Branch:** `x64`. Run from repo root `/root/uAthena`. Build `make sql`.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/map/battle.h` | modify | `unsigned short quest_progress_notify;` field |
| `src/map/battle.c` | modify | default `=2` in `battle_set_defaults()`; config-table entry |
| `conf/battle/player.conf` | modify | `quest_progress_notify: 2` (documented) |
| `src/map/quest.c` | modify | notify block in `quest_update_objective` |
| `doc/quest_progress_notify_changes.md` | create | tester checklist |

Only additions; no existing behaviour changes.

---

## Task 1: battle_config toggle

**Files:** Modify `src/map/battle.h`, `src/map/battle.c`, `conf/battle/player.conf`

- [ ] **Step 1: Add the field in `src/map/battle.h`**

Find `unsigned short quest_skill_reset;` and add after it:
```c
	unsigned short quest_progress_notify; // 0=off, 1=each kill, 2=on objective completion
```

- [ ] **Step 2: Add the default in `battle_set_defaults()` (`src/map/battle.c`)**

Find `battle_config.quest_skill_reset=1;` and add after it:
```c
	battle_config.quest_progress_notify=2;
```

- [ ] **Step 3: Add the config-table entry in `src/map/battle.c`**

Find `{ "quest_skill_reset",                 &battle_config.quest_skill_reset		},` and add after it:
```c
	{ "quest_progress_notify",             &battle_config.quest_progress_notify	},
```

- [ ] **Step 4: Document the setting in `conf/battle/player.conf`**

After the `quest_skill_reset: no` line add:
```
// Notify quest hunt-objective progress in chat (PV7 client has no objective popup).
// 0 = off, 1 = on each counted kill, 2 = only when an objective completes.
quest_progress_notify: 2
```

- [ ] **Step 5: Build**

Run: `make sql 2>&1 | grep -E 'error:' | head; echo done`
Expected: no errors (new field unused yet — clean).

- [ ] **Step 6: Commit**

```bash
git add src/map/battle.h src/map/battle.c conf/battle/player.conf
git commit -m "quest: add battle_config quest_progress_notify (0/1/2, default 2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Notify block in `quest_update_objective`

**Files:** Modify `src/map/quest.c`

- [ ] **Step 1: Add the notification block after the count increment**

In `quest_update_objective`, the inner `if(...) { ... }` currently is:
```c
			{
				sd->quest_log[i].count[j]++;
				sd->save_quest = true;
				clif_quest_update_objective(sd,&sd->quest_log[i],sd->quest_index[i]);
			}
```
Replace it with:
```c
			{
				sd->quest_log[i].count[j]++;
				sd->save_quest = true;
				clif_quest_update_objective(sd,&sd->quest_log[i],sd->quest_index[i]);

				if( battle_config.quest_progress_notify )
				{
					int qidx = sd->quest_index[i];
					int reqd = quest_db[qidx].count[j];
					int cur  = sd->quest_log[i].count[j];
					struct mob_db *mb = mob_db(mob);
					char buf[128];

					if( battle_config.quest_progress_notify == 1 || cur >= reqd )
					{
						snprintf(buf, sizeof(buf), "[Quest] %s: %d/%d (%s)",
							mb ? mb->jname : "?", cur, reqd,
							quest_db[qidx].name[0] ? quest_db[qidx].name : "?");
						clif_displaymessage(sd->fd, buf);
					}
					if( cur >= reqd )
					{
						int k, alldone = 1;
						for( k = 0; k < quest_db[qidx].num_objectives; k++ )
							if( sd->quest_log[i].count[k] < quest_db[qidx].count[k] ) { alldone = 0; break; }
						if( alldone )
						{
							snprintf(buf, sizeof(buf), "[Quest] \"%s\" - all objectives complete!",
								quest_db[qidx].name[0] ? quest_db[qidx].name : "?");
							clif_displaymessage(sd->fd, buf);
						}
					}
				}
			}
```
(`quest.c` already includes `battle.h`, `clif.h`, `mob.h` — `battle_config`, `clif_displaymessage`, `mob_db` are available.)

- [ ] **Step 2: Build**

Run: `make sql 2>&1 | grep -E 'error:|warning:' | grep -ivE 'request|conquest' | head; echo done`
Expected: no errors/warnings.

- [ ] **Step 3: Commit**

```bash
git add src/map/quest.c
git commit -m "quest: chat notification of objective progress (gated by quest_progress_notify)

Per-kill (mode 1) or on-objective-completion (mode 2) line + an 'all objectives
complete' line when the quest's last objective fills. ASCII labels.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Verify + tester doc + push

**Files:** Create `doc/quest_progress_notify_changes.md`

- [ ] **Step 1: Clean build + API-invariant**

Run:
```bash
make sql 2>&1 | grep -E 'error:|warning:' | grep -ivE 'request|conquest' | head
git diff f505c25 -- src/map/quest.c src/map/battle.c | grep -E '^-' | grep -vE '^---' | head
```
Expected: first empty (clean); second empty (only additions — no existing line removed).

- [ ] **Step 2: Boot smoke**

Run: `set +e; timeout 20 ./map-server_sql > /tmp/qpn.log 2>&1; for p in $(pgrep -x map-server_sql); do kill -9 "$p"; done; grep -E "entries in 'quest_db.txt'|No memory leaks" /tmp/qpn.log`
Expected: quest_db reads (1703), no leaks. (Live objective-progress messages need a client + mob kills — testers' phase.)

- [ ] **Step 3: Write `doc/quest_progress_notify_changes.md`**

```markdown
# Нотификация прогресса квеста в чат — что изменено и что проверять

## Что добавлено
- `battle_config quest_progress_notify` (`conf/battle/player.conf`): 0=выкл, 1=каждое зачётное убийство,
  2=только при выполнении цели. **Дефолт 2**.
- В `quest_update_objective` (движок SP2) — чат-строка прогресса:
  - режим 1: `[Quest] <моб>: <тек>/<нужно> (<имя квеста>)` на каждый зачётный килл;
  - режим 2: та же строка только при заполнении цели (`тек>=нужно`);
  - режимы 1 и 2: дополнительно `[Quest] "<имя>" - all objectives complete!` когда заполнена последняя цель.
- Метки ASCII English (клиент 2007 докодовый; имена моба/квеста английские). RU — позже через msg_txt.
- Только добавления; существующее поведение/команды/NPC не изменены.

## Что проверять (кластер: char+map+клиент)
1. `quest_progress_notify: 1` — строка на каждый зачётный килл hunt-квеста.
2. `quest_progress_notify: 2` — строка только когда цель заполнилась; в конце «all objectives complete».
3. `quest_progress_notify: 0` — нотификаций нет.
4. Прогресс сохраняется при перезаходе (SP2); `@quests`/`@quest` показывают те же счётчики.
5. Действующие квесты/команды/NPC не сломаны.

## Будущее (дорожная карта)
`@status`/кулдауны; `@whereis`/`@market`; достижения/титулы; отдельный SP — наёмники.
```

- [ ] **Step 4: Commit + push**

```bash
git add doc/quest_progress_notify_changes.md
git commit -m "doc: tester checklist for quest progress chat notification

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin x64   # if rejected: git fetch origin x64 && git rebase origin/x64, re-verify build, push
```

---

## Notes for the implementer
- `quest_progress_notify` is `unsigned short`; values other than 0/1/2 behave as "1" (non-zero, not >=completion-special) — harmless.
- The notify runs on the mob-death path (SP2 hook) per crediting player — one light chat packet per counted kill in mode 1; negligible.
- Only additions: no existing battle_config / quest-engine behaviour changes.
```
