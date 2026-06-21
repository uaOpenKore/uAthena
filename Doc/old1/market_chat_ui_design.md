# Дизайн: `@market <item>` — поиск товара по вендорам (обход отсутствия searchstores в PV7)

Дата: 2026-06-15. Ветка: `x64`. Пункт дорожной карты «обход клиента через chat» (клиент 2007 не умеет поиск по лавкам).

## Команда (игрокам, atcommand level 0)
`@market <имя предмета>`:
1. Резолв: `id = itemdb_searchname(message)` (item_data*); нет → «Item not found: <ввод>».
2. Перебор онлайн-игроков через `map_foreachpc(atcommand_market_sub, fd, nameid, &total, &printed)`:
   sub-callback для каждого `vsd`: если `vsd->vender_id != 0`, скан `vsd->vending[i]` (i<`vsd->vend_num`),
   где `vsd->status.cart[ vsd->vending[i].index ].nameid == nameid` → строка
   `  <vsd->status.name> @ <map[vsd->bl.m].name> <bl.x>,<bl.y>: <value>z x<amount> ("<vsd->message>")`.
   Счётчики `total`/`printed` по указателю (va), кап **20** + «(+N more)».

Формат:
```
Vendors selling Apple:
  Alice @ prontera 150,100: 500z x30 ("Cheap food")
  ...(+N more)
```
Нет продавцов → «No vendors selling that».

## Архитектура
- `src/map/atcommand.c` — `ACMD_FUNC(market)` + статический `atcommand_market_sub(DBKey,void*,va_list)`.
- enum `AtCommand_Market` (перед `AtCommand_Unknown`); таблица `{ AtCommand_Market, "@market", 1, atcommand_market }`;
  `conf/atcommand_athena.conf` — `market: 0`.
- Read-only. `map_foreachpc` va-safe (va_copy-фикс из x64-порта — см. [[x64-valist-reuse-map-crash]]).

## Детали
- Имена вендора (`status.name`) и заголовок лавки (`message`) — пользовательский текст, печатаю как есть
  (клиент рендерит в своей кодировке). Мои метки + имя предмета (`itemdb` jname) — **ASCII English**.
- Буферы фикс. (snprintf); `itemdb_searchname` NULL → «not found». `map[vsd->bl.m].name` валиден (онлайн на карте).
- Дефолты (зафиксированы): точное имя предмета; кап 20 вендоров; доступ игрокам.

## Безопасность/верификация
- Только добавления; существующие команды/механики не изменены.
- `make sql` чисто; boot-smoke; на кластере: открыть лавку с предметом → `@market <item>` находит её
  (вендор/карта/цена/кол-во/заголовок); неизвестный предмет → сообщение; нет лавок → «No vendors».

## Вне объёма
Частичный поиск по имени; фильтр по цене/слотам/рефайну; закупочные лавки (buyingstore — в PV7 нет) — позже.
