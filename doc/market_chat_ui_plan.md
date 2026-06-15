# @market Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `@market <item>` lists online vendors selling an item (vendor, map+coords, price, amount, shop title), since the PV7 client has no store search.

**Architecture:** A read-only player-level atcommand: resolve the item by name (`itemdb_searchname`), then `map_foreachpc` over online players, matching active vendors' `vending[]` cart items; print via `clif_displaymessage`.

**Tech Stack:** C (map-server), eAthena atcommand + vending + map_foreachpc.

**Design spec:** `doc/market_chat_ui_design.md` (committed `ca6edc2`).

**Branch:** `x64`. Run from repo root `/root/uAthena`. Build `make sql`.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/map/atcommand.h` | modify | `AtCommand_Market` enum entry |
| `src/map/atcommand.c` | modify | `atcommand_market_sub` (map_foreachpc cb) + `ACMD_FUNC(market)` decl + impl + table entry |
| `conf/atcommand_athena.conf` | modify | `market: 0` |
| `doc/market_chat_ui_changes.md` | create | tester checklist |

Only additions. `itemdb_searchname`, `map_foreachpc`, `map[]`, `MAX_CART`, vending fields are available in `atcommand.c`.

---

## Task 1: `@market` atcommand

**Files:** Modify `src/map/atcommand.h`, `src/map/atcommand.c`, `conf/atcommand_athena.conf`

- [ ] **Step 1: Enum entry — `src/map/atcommand.h`**

Find `AtCommand_WhereIs, // mob spawn/drop search` and add after it (before `AtCommand_Unknown,`):
```c
	AtCommand_Market, // vendor/price search
```

- [ ] **Step 2: ACMD declaration — `src/map/atcommand.c`**

After `ACMD_FUNC(whereis); // mob spawn/drop search` add:
```c
ACMD_FUNC(market); // vendor/price search
```

- [ ] **Step 3: Table entry — `src/map/atcommand.c`**

After `{ AtCommand_WhereIs, "@whereis", 1, atcommand_whereis }, // mob spawn/drop` add:
```c
	{ AtCommand_Market,             "@market",           1, atcommand_market }, // vendor/price search
```

- [ ] **Step 4: Implementation — append before `int atcommand_whereis(...)`**

```c
/*==========================================
 * @market : online vendors selling an item (PV7 client has no store search)
 *------------------------------------------*/
static int atcommand_market_sub(DBKey key, void* data, va_list ap)
{
	struct map_session_data* vsd = (struct map_session_data*)data;
	int fd      = va_arg(ap, int);
	int nameid  = va_arg(ap, int);
	int* total  = va_arg(ap, int*);
	int* printed = va_arg(ap, int*);
	int i;
	char out[200];

	if( vsd->vender_id == 0 )
		return 0;
	for( i = 0; i < vsd->vend_num; i++ )
	{
		int slot = vsd->vending[i].index;
		if( slot < 0 || slot >= MAX_CART )
			continue;
		if( vsd->status.cart[slot].nameid != nameid )
			continue;
		(*total)++;
		if( *printed < 20 )
		{
			snprintf(out, sizeof(out), "  %s @ %s %d,%d: %uz x%u (\"%s\")",
				vsd->status.name, map[vsd->bl.m].name, vsd->bl.x, vsd->bl.y,
				vsd->vending[i].value, vsd->vending[i].amount, vsd->message);
			clif_displaymessage(fd, out);
			(*printed)++;
		}
	}
	return 0;
}

int atcommand_market(const int fd, struct map_session_data* sd, const char* command, const char* message)
{
	struct item_data* id;
	int total = 0, printed = 0;
	nullpo_retr(-1, sd);

	if( !message || !*message )
	{
		clif_displaymessage(fd, "Usage: @market <item name>");
		return -1;
	}
	id = itemdb_searchname(message);
	if( id == NULL )
	{
		snprintf(atcmd_output, sizeof(atcmd_output), "Item not found: %s", message);
		clif_displaymessage(fd, atcmd_output);
		return -1;
	}

	snprintf(atcmd_output, sizeof(atcmd_output), "Vendors selling %s:", id->jname);
	clif_displaymessage(fd, atcmd_output);

	map_foreachpc(atcommand_market_sub, fd, id->nameid, &total, &printed);

	if( total == 0 )
		clif_displaymessage(fd, "No vendors selling that.");
	else if( total > printed )
	{
		snprintf(atcmd_output, sizeof(atcmd_output), "  ...(+%d more)", total - printed);
		clif_displaymessage(fd, atcmd_output);
	}
	return 0;
}
```

- [ ] **Step 5: Player access — `conf/atcommand_athena.conf`**

After the `whereis: 0` line add:
```
// Find online vendors selling an item
market: 0
```

- [ ] **Step 6: Build**

Run: `make sql 2>&1 | grep -E 'error:|warning:' | grep -iE 'market|atcommand_market' | head; echo done`
Expected: no errors/warnings in the new code.

- [ ] **Step 7: Commit**

```bash
git add src/map/atcommand.h src/map/atcommand.c conf/atcommand_athena.conf
git commit -m "market: @market chat command (online vendor/price search)

itemdb_searchname + map_foreachpc over active vendors' vending[] (match cart item)
-> vendor/map/price/amount/shop-title (cap 20). Player-level, read-only, ASCII labels.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Verify + tester doc + push

**Files:** Create `doc/market_chat_ui_changes.md`

- [ ] **Step 1: Clean build + API-invariant**

Run:
```bash
make sql 2>&1 | grep -E 'error:' | head
git diff ca6edc2 -- src/map/atcommand.c | grep -E '^-' | grep -vE '^---' | head
```
Expected: first empty; second empty (only additions).

- [ ] **Step 2: Boot smoke**

Run: `set +e; timeout 20 ./map-server_sql > /tmp/mk.log 2>&1; for p in $(pgrep -x map-server_sql); do kill -9 "$p"; done; grep -E "entries in 'quest_db.txt'|No memory leaks" /tmp/mk.log`
Expected: server boots, no leaks. (Live `@market` needs a client + an open vending shop — testers' phase.)

- [ ] **Step 3: Write `doc/market_chat_ui_changes.md`**

```markdown
# @market — что изменено и что проверять

## Что добавлено
- `@market <имя предмета>` — игрокам: резолв предмета по имени, затем перебор онлайн-вендоров
  (`map_foreachpc`, у кого `vender_id!=0`) → строки `<вендор> @ <карта> x,y: <цена>z x<кол-во> ("<лавка>")`.
  Кап 20 + «(+N more)»; нет продавцов → «No vendors selling that»; нет предмета → «Item not found».
- Read-only (`map_foreachpc` + чтение vending/cart); метки/имя предмета ASCII English; имена вендора/лавки —
  как есть (пользовательский текст). RU метки позже через msg_txt.
- Только добавления; существующие команды/механики не изменены.

## Что проверять (кластер: клиент)
1. Открыть лавку с предметом X; другим персонажем `@market X` → видна лавка (вендор/карта/цена/кол-во/заголовок).
2. Предмет, который никто не продаёт → «No vendors selling that».
3. Неизвестное имя предмета → «Item not found: <ввод>».
4. Много лавок с предметом → список обрезан до 20 + «(+N more)».
5. Действующие команды/лавки работают как раньше.

## Будущее (дорожная карта)
Достижения/титулы (нужен небольшой движок); отдельный SP — система наёмников (Mercenary).
```

- [ ] **Step 4: Commit + push**

```bash
git add doc/market_chat_ui_changes.md
git commit -m "doc: tester checklist for @market"
git push origin x64   # if rejected: git fetch origin x64 && git rebase origin/x64, re-verify, push
```

---

## Notes for the implementer
- `map_foreachpc` callback signature is `static int f(DBKey key, void* data, va_list ap)` with `data` = the player sd (cast it). Counters are passed by pointer through the varargs so they accumulate across players.
- `map_foreachpc` is va_copy-safe in this tree (x64 port fix); the sub uses a local `out[]` buffer (not the shared `atcmd_output`) to avoid clobbering the caller's buffer mid-iteration.
- Guard the cart slot (`0..MAX_CART`) before indexing `status.cart[]`.
- Only additions: no existing atcommand / vending behaviour changes.
```
