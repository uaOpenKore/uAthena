# Бэкпорт Buying Store (скупка через ларёк) для Мерчанта

Ветка: `x64`. Источник: eAthena (`/tmp/eathena-ref`), только не-renewal пути.

## Цель
Дать Мерчанту (и веткам) возможность открыть «ларёк скупки»: выставить
список предметов, которые он ГОТОВ КУПИТЬ за зени, а другие игроки ему их
продают. Зеркально обычному вендингу (продаже).

## Главный констрейнт
Клиент uAthena = `PACKETVER 7` (2007). Нативное окно Buying Store (пакеты
`0x810/0x814/0x818/0x811/0x817`) появилось в клиентах 2010+ (`#if PACKETVER >=
20100629/20110111`). В 2007-клиенте нет НИ окна владельца, НИ доски-вывески,
НИ диалога продажи. Поэтому весь UI — **через чат**, а нативные пакеты остаются
под `#if PACKETVER` (задел: при апгрейде клиента тот же движок отдаст и окно).

## Решения (утверждены)
1. Подход: **движок + чат-UI сейчас + нативные пакеты под #if PACKETVER**.
2. UI покупателя — **чат-паритет**: `@buymarket` (поиск) + `@sellto` (продажа).
3. **Слоты = `2 + уровень MC_VENDING`** (как у вендинга, `vending.c:24`).
4. `searchstore.c` (универсальный каталог) НЕ бэкпортим — его роль закрывает
   `@buymarket` (он тоже 2010+).
5. NPC-учитель — на загруженной карте (Альберта), не на `que_job01` (та не в
   `maps_athena.conf`).

## Компоненты и файлы
- `src/map/buyingstore.{c,h}` — ядро (адаптировано: лог-API uAthena, без
  searchstore). Функции: `buyingstore_setup/create/open/close/trade/search`.
- `src/map/map.h` — в `map_session_data`: бит `state.buyingstore`, поля
  `int buyer_id; struct s_buyingstore buyingstore;` рядом с вендингом.
- `src/map/itemdb.{c,h}` — флаг `flag.buyingstore` + чтение `db/item_buyingstore.txt`
  (белый список предметов, разрешённых к скупке).
- `src/map/battle.{c,h}` — `battle_config.feature_buying_store` (+ `buyingstore_max_price`).
- `src/map/skill.h` + `db/skill_db.txt` — скилл `ALL_BUYING_STORE` (id 2535,
  max lv1, self). `skill_castend_nodamage_id`: вызывает `buyingstore_setup`
  с лимитом `2 + pc_checkskill(MC_VENDING)`.
- `src/map/clif.{c,h}` — `clif_buyingstore_*`: натив под `#if PACKETVER>=20100629`,
  иначе no-op (фидбек на PV7 даёт atcommand). Натив-парсеры — dormant.
- `src/map/atcommand.c` + `conf/atcommand_athena.conf` — `@buystore`,
  `@buymarket`, `@sellto` (enum + таблица + conf согласованы).
- `db/item_buyingstore.txt` — список разрешённых к скупке (из эталона).
- `npc/merchants/buying_shops.txt` — NPC-учитель (адаптир., мерчант-онли).
- `src/map/Makefile{,.in}` — `buyingstore.o`.

## Чат-команды
Владелец: `@buystore add <id> <amount> <price>` / `list` / `remove <id>` /
`title <text>` / `open` / `close`.
Покупатель: `@buymarket` (список) / `@buymarket <storeid>` (детали) /
`@sellto <storeid> <itemID> <amount>`.

## Безопасность (дюп-критично)
Зеркало вендинга/трейда: атомарная транзакция (зени↔предмет одним блоком),
проверки бюджета/остатка/веса тележки владельца, запрет продажи себе,
дистанция/одна карта, нельзя торговать non-tradable/rental(expire_time)/
карточные/залоченные, дедуп позиций, защита от гонки и дисконнекта,
лог в picklog (`log_pick_pc(...,"B",...)`, `log_zeny`).

## Персистентность
Нет (в памяти, как вендинг). Скупка закрывается на logout/смену карты/смерть.

## Фазы
1. Движок + data-model + skill + battle_config + itemdb-флаг + Makefile + clif-stubs → компилится.
2. Чат-команды (@buystore/@buymarket/@sellto) + транзакция.
3. NPC-учитель + item_buyingstore.txt + дефолт battle conf.
4. Логирование + крайние случаи + регресс-сборка обоих серверов.

## Известные ограничения
- Нативный путь (PACKETVER≥20100629) пишется по эталону, но на этом ящике
  компиляционно проверяется только PV7-ветка (#else). 2010-сборка/рантайм — за
  будущим тестером при апгрейде клиента.
- Рантайм-тест скупки (клиент/кластер) — за тестерами (чек-лист в чате задачи).
