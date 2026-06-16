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

<!-- Следующие фазы (2: движок+buildin+пакеты, 3: bind-семантика, 4: восстановление 98 предметов)
     будут дописаны сюда по мере реализации. -->
