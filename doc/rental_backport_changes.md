# Бекпорт rental-предметов — изменения для тестировщиков

Воскрешение аренды (rental) из pre-RE eAthena: предмет с абсолютным временем истечения
(`expire_time`), по истечении удаляется; привязан к персонажу. Возвращает к жизни 98 box-предметов,
которые звали `rentitem` и были нейтрализованы в `{}` (коммит b0d885b). План: `doc/rental_backport_plan.md`.

## ⚠️ Деплой (ОБЯЗАТЕЛЬНО)

1. **Применить миграцию БД** `dumps/migrations/10-add-item-expire-time.sql` — добавляет колонку
   `expire_time` в `inventory`, `cart_inventory`, `storage`, `guild_storage`. `IF NOT EXISTS` →
   безопасно при повторном `dumps.sh update`. На существующих сейвах default `0` = НЕ аренда (никаких
   изменений у игроков).
2. **Пересобрать ОБА сервера вместе** (`make sql`): в `struct item` добавлено поле `expire_time` —
   это кросс-серверная структура (char↔map). Старый map против нового char (или наоборот) =
   рассинхрон протокола. Всегда деплоить map+char одной сборкой.
3. Легаси `sql-files/main.sql` НЕ обновлялся (он мёртв — `TYPE=MyISAM` не работает в MariaDB 11.8).
   Активна схема `dumps/`.

---

## Фаза 1 — Фундамент: поле `expire_time` + персистентность + схема (СДЕЛАНО)

**Что изменилось (без изменения геймплея — поле всегда 0, пока аренда не выдана):**
- `src/common/mmo.h` — `struct item` += `unsigned int expire_time` (0 = не аренда).
- `src/char_sql/char.h` — `struct itemtmp` (staging для всех save-путей) += `expire_time`.
- `src/char_sql/char.c` — `compare_item` сравнивает `expire_time`; inventory/cart copy-loop'ы и
  load'ы + `memitemdata_to_sql` (SELECT/matcher/UPDATE/INSERT) переносят `expire_time`. **Важно:**
  matcher теперь сравнивает `expire_time`, иначе две разные аренды одного nameid могли перепутаться
  при сохранении.
- `src/char_sql/int_storage.c` — storage и guild-storage copy-loop'ы + load'ы += `expire_time`.
- `dumps/tables/{inventory,cart_inventory,storage,guild_storage}.sql` — колонка в CREATE (fresh install).
- `dumps/migrations/10-add-item-expire-time.sql` — ALTER для существующих БД.

**Верификация (здесь):** `make sql` — 0 новых ворнингов, все 3 бинарника собраны/линкуются.
Runtime-логин-тест невозможен без клиента → **на тестировщиках**:

**Как протестировать Фазу 1 (тестировщики):**
1. Применить миграцию, пересобрать оба сервера, запустить кластер.
2. Залогиниться персонажем со старыми сейвами → инвентарь/карт/склад грузятся как раньше (ничего
   не сломалось, `expire_time`=0 у всех существующих предметов).
3. (Полный тест аренды — после Фазы 2, когда появится buildin `rentitem`.)

**Откат:** реверт коммита фазы; колонка `expire_time` может остаться (default 0, безвредна).

## Фаза 2 — Движок аренды + buildin `rentitem` + пакеты (СДЕЛАНО)

**Что изменилось:**
- `src/map/map.h` — `map_session_data` += `int rental_timer`.
- `src/map/pc.c` + `pc.h` — движок аренды: `pc_inventory_rentals` (скан инвентаря: истёкшие удаляет
  + шлёт 0x299, активным шлёт 0x298 и ставит таймер), `pc_inventory_rental_clear`,
  `pc_inventory_rental_add`, callback `pc_inventory_rental_end`. Хуки: init `rental_timer` и вызов
  `pc_inventory_rentals` в `pc_authok` (логин), регистрация callback в `do_init_pc`. Аренда **не
  стакается** (свой слот), rental-usable **не расходуется** при использовании (эффект применяется,
  предмет остаётся до истечения), аренду **нельзя дропнуть** (`pc_candrop`).
- `src/map/clif.c` + `clif.h` — `clif_rental_time` (0x298: «предмет исчезнет через N сек») +
  `clif_rental_expired` (0x299: удаление из инвентаря). Без PACKETVER-гейта; длины уже в `packet_db.txt`.
- `src/map/script.c` — buildin `rentitem <id|"name">,<seconds>` (`"vi"`): выдаёт предмет с
  `expire_time = time(NULL)+seconds`, шлёт 0x298, ставит таймер.

**Верификация (здесь):** `make sql` EXIT=0, все бинарники линкуются; **0 ворнингов** на rental-строках
(прочий warning-шум — пред-существующий x64 int↔pointer/strncpy). Runtime — на тестировщиках.

**Как протестировать Фазу 2 (тестировщики, нужен клиент):**
1. NPC/`@`-скриптом или предметом вызвать `rentitem <id>,60` (1 минута) → предмет появляется,
   приходит сообщение об оставшемся времени.
2. Подождать минуту → предмет удаляется автоматически, приходит уведомление.
3. Релог во время аренды → таймер восстанавливается (благодаря Фазе 1), остаток времени корректен.
4. Rental-экип можно надеть; rental-usable при использовании даёт эффект, но не расходуется.

**Откат:** реверт коммита фазы.

<!-- Следующая фаза (3: bind-семантика, 4: восстановление 98 предметов) будет дописана по мере реализации. -->

