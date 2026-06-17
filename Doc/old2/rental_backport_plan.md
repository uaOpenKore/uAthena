# План: бекпорт rental-предметов (eAthena → uAthena)

**Цель:** воскресить 98 out-of-era box-предметов, зовущих `rentitem`, полноценным бекпортом
аренды из pre-RE eAthena. Аренда = предмет с абсолютным временем истечения (`expire_time`), по
истечении удаляется; привязан к персонажу (нельзя торговать/продать/дропнуть/в склад/вендинг).

**Согласовано с пользователем (2026-06-16):** делаем; клиент НЕ обновляем (`0x0298/0x0299` уже в
`packet_db.txt` 2007-клиента); `rentitem2` НЕ нужен (rAthena-only, 0 предметов его зовут); запрет
аренды и в обычном складе (rAthena, против эксплойта «парковки» аренды); под PV7 — функциональная
аренда без per-item оверлея в инвентаре (поля list-пакетов загейчены `PACKETVER>20061218`).

**Эталон:** pre-RE eAthena (порт-карта снята). **БЕЗ RENEWAL-кода, БЕЗ battle_config.** Откат =
реверт коммитов фазы (поле/колонка остаются — безвредны, default 0).

---

## Инварианты / ключевые находки uAthena

- `struct item` (`src/common/mmo.h:147-156`) += `unsigned int expire_time;` (в конец). `expire_time==0`
  = НЕ аренда (отдельного флага нет). Это кросс-серверная структура.
- **`struct itemtmp` (`src/char_sql/char.h:27-37`)** — staging для всех save-путей; ТОЖЕ += `expire_time`,
  иначе значение не дойдёт до SQL.
- Одна общая save-функция **`memitemdata_to_sql` (`char.c:772-895`)**: 3 SQL — SELECT(791), UPDATE(840),
  INSERT(874) — каждая += `expire_time`. 4 copy-loop'а: inventory(char.c:466), cart(char.c:493),
  storage(int_storage.c:37), guild(int_storage.c:111). 4 load'а: inventory(char.c:1010), cart(char.c:1040),
  storage(int_storage.c:70), guild(int_storage.c:145) — row-index `7+MAX_SLOTS` после карт.
- char-сторона использует raw-mysql (НЕ Sql_ API). Парсить `(unsigned int)strtoul(sql_row[7+MAX_SLOTS],NULL,10)`.
- `compare_item` (char-сторона, save-diff триггер) — добавить сравнение `expire_time` (корректность save;
  expire_time set-once, но для строгости как в eAthena).
- Миграция: следующий номер **10**; `dumps.sh update` пере-применяет ВСЕ миграции (drop `migrations`)
  → ALTER должен быть **`ADD COLUMN IF NOT EXISTS`** (MariaDB 11.8 поддерживает) для re-run-safety.
  Плюс правка CREATE в `dumps/tables/{inventory,cart_inventory,storage,guild_storage}.sql` (fresh install).
- `INVALID_TIMER == -1` (`timer.h:19`). `time(NULL)` доступен (`#include <time.h>` проектно).
- 98 предметов — в `db/item_db.txt` (~5932+), сейчас `{}`. Оригиналы: `git show 25f3be3:db/item_db2.txt
  | grep rentitem` (формат `{ rentitem <id>,<seconds>; }`, 604800=7д / 2592000=30д).

---

## Фаза 1 — Фундамент: поле `struct item` + char-персистентность + схема БД

**Цель:** `expire_time` существует, грузится/сохраняется, default 0. Без изменения геймплея. Boots clean.

**Правки:**
- `mmo.h:147-156` — `struct item` += `unsigned int expire_time;`.
- `char.h:27-37` — `struct itemtmp` += `unsigned int expire_time;`.
- `char.c` — `memitemdata_to_sql`: добавить `expire_time` в SELECT(791) / UPDATE(840) / INSERT(874).
  Copy-loop'ы inventory(466)+cart(493): `mapitem[count].expire_time = p->{inventory,cart}[i].expire_time;`.
  Load'ы inventory(1010)+cart(1040): добавить ``, `expire_time`` в SELECT + парс
  `p->X[i].expire_time = (unsigned int)strtoul(sql_row[7+MAX_SLOTS],NULL,10);`.
  Найти char-сторонний `compare_item` → добавить `a->expire_time == b->expire_time`.
- `int_storage.c` — copy-loop'ы storage(37)+guild(111) + load'ы storage(70)+guild(145): то же.
  (guild-load: при желании занулять как eAthena — но раз храним, оставляем как есть; mail/auction не трогаем.)
- `dumps/tables/{inventory,cart_inventory,storage,guild_storage}.sql` — в CREATE после `card3`
  (для cart — после `broken`): `` `expire_time` int(11) unsigned NOT NULL DEFAULT '0', ``.
- `dumps/migrations/10-add-item-expire-time.sql` — 4× `ALTER TABLE \`X\` ADD COLUMN IF NOT EXISTS
  \`expire_time\` int(11) unsigned NOT NULL DEFAULT '0';`.
- Проверить `sql-files/main.sql` — если используется, синхронно; если мёртв (активен dumps/) — пропустить.

**Верификация:** `make sql` без новых ворнингов; boot-clean (логин чара не происходит в boot-smoke,
SELECT с expire_time не триггерится без логина — но схема консистентна в одном коммите).
**Отчёт:** создать `doc/rental_backport_changes.md` — секция Фаза 1 + **CRITICAL: миграция БД обязательна**.
**Коммит** (fetch+rebase перед push — Cline Bot).

## Фаза 2 — Движок аренды + buildin + пакеты

**Цель:** аренда функциональна (buildin работает, предметы истекают, клиент получает 0x298/0x299).

**Правки:**
- `map.h:~650` — `map_session_data` += `int rental_timer;`.
- `pc.h` — декларации `pc_inventory_rentals`, `pc_inventory_rental_clear`, `pc_inventory_rental_add`.
- `pc.c` — 4 функции (static callback `pc_inventory_rental_end`, `_clear`, `pc_inventory_rentals` скан,
  `_add`); init `sd->rental_timer = INVALID_TIMER` (pc_authok ~667/755); вызов `pc_inventory_rentals(sd)`
  в конце `pc_authok` (~748-757, до return 825); `add_timer_func_list(pc_inventory_rental_end,...)` в
  `do_init_pc` (~7894); guard `&& item_data->expire_time==0` в стакинге `pc_additem` (~3095) — аренда
  свой слот; guard в `pc_useitem` (~3386) — rental-usable не расходуется до истечения; `pc_candrop`
  (~6168) `if(item && item->expire_time) return 0;`.
- `clif.c` (рядом с merc-блоком ~1470) + `clif.h` (~389) — `clif_rental_time(fd,nameid,seconds)` (0x298,
  len8: W0=0x298,W2=nameid,L4=seconds) + `clif_rental_expired(fd,index,nameid)` (0x299, len6: W0=0x299,
  W2=index+2,W4=nameid).
- `script.c` — forward `BUILDIN_FUNC(rentitem)` (~3610); `BUILDIN_DEF(rentitem,"vi")` (~3951); тело по
  идиоме `getitem` (5922): memset item, identify=1, `it.expire_time=(unsigned int)(time(NULL)+seconds)`,
  `pc_additem`, при ошибке `clif_additem`, иначе `clif_rental_time` + `pc_inventory_rental_add`.

**Верификация:** make sql clean; boot clean. **Отчёт:** секция Фаза 2 (как тестировать: дать предмет
с rentitem-скриптом, проверить таймер/истечение/сообщение).

## Фаза 3 — Bind-семантика (привязка аренды)

**Цель:** аренду нельзя торговать/продать NPC/дропнуть/в склад(оба)/вендинг; не стакается/не мержится.

**Правки (вставить `expire_time`-блок):**
- `trade.c` — `trade_tradeadditem` (~355-365): отказ при `item->expire_time` (msg + clif_tradeitemok(...,1)).
- `clif.c` — `clif_selllist` (~1894): `|| sd->status.inventory[i].expire_time` → continue.
- `storage.c` — `storage_additem` (~194) И `guild_storage_additem` (~550): отказ при `item_data->expire_time`
  (msg_txt(264)); `compare_item` (~164) += `a->expire_time==b->expire_time` (не мержить разные аренды).
- `vending.c` — `vending_openvending` (~235-240): `|| sd->status.cart[...].expire_time` → skip.
- (Refine — НЕ гардим, как eAthena. Skill-реагент — опционально, большинство rental-usable не реагенты;
  основной use-guard уже в pc_useitem.)

**Верификация:** make sql clean; boot clean. **Отчёт:** секция Фаза 3 (чек-лист bind: попытка
trade/sell/drop/storage/vend аренды — отказ).

## Фаза 4 — Восстановить скрипты 98 предметов + регенерация item-SQL

**Цель:** 98 box-предметов снова выдают аренду.

**Правки:**
- `db/item_db.txt` — каждому из 98 ID вернуть `{ rentitem <id>,<seconds>; }` (из 25f3be3). Скриптом-
  ресторером (как backport-конвертеры): извлечь (id→script) из `git show 25f3be3:db/item_db2.txt`,
  применить к строкам item_db.txt по ID (заменить первый `{}`).
- Регенерация `dumps/migrations/A-item_db.sql` через `dumps/forge/items_db-to-sql.sh`.

**Верификация:** boot clean, **0 script error** (был риск возврата ошибок — buildin из Фазы 2 их
снимает); spot-check 2-3 предмета. **Отчёт:** секция Фаза 4 + итог (98 предметов, in/out-of-scope).

---

## Что СОЗНАТЕЛЬНО не делаем
- `rentitem2` (rAthena-only, 0 предметов).
- Per-item expire-оверлей в list-пакетах (загейчен `PACKETVER>20061218`, дормант под PV7 — косметика).
- setfont / searchstore / buyingstore (вне концепции — нужен клиент 2008/2010+; остаются `{}`).
- Refine-guard для аренды (eAthena не гардит).
- battle_config-флаг (eAthena не имеет; аренда opt-in через item-скрипты; откат = реверт фазы).

## Документация для тестировщиков
`doc/rental_backport_changes.md` — кумулятивно по фазам: фича, **обязательная миграция БД**, как тестировать
каждую фазу, in/out-of-scope, откат. Обновлять после каждой фазы.
