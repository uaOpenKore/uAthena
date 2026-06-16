# Дизайн: `@whereis <моб>` — где водится и что дропает (обход поиска в клиенте PV7)

Дата: 2026-06-15. Ветка: `x64`. Пункт дорожной карты «обход клиента через chat» (клиент 2007 не умеет поиск мобов).

## Команда (игрокам, atcommand level 0)
`@whereis <имя моба>`:
1. Резолв: `id = mobdb_searchname(message)` (регистронезависимо, точное совпадение jname). `id<=0` → «Mob not found: <ввод>».
2. **Spawns** (где водится): перебор `m` в 0..`map_num`, `k` в 0..`MAX_MOB_LIST_PER_MAP`; если `map[m].moblist[k] && map[m].moblist[k]->class_ == id` → строка `map[m].name (<num>)`. Кап **20** карт, далее «(+N more)» (частые мобы — на многих картах, без флуда).
3. **Drops:** `mob_db(id)->dropitem[j]` (j<`MAX_MOB_DROP`, `nameid>0`) → `itemdb_jname(nameid)` + шанс `p/100.0`% (rate `p` в 0.01%).

Формат:
```
[Poring] (id 1002)
Spawns: prt_fild01 (20), prt_fild02 (15) ... (+N more)
Drops: Jellopy 70.00%, Apple 10.00%, Knife 1.00%
```

## Архитектура
- `src/map/atcommand.c` — `ACMD_FUNC(whereis)`: импл (mobdb_searchname → map[].moblist скан → mob_db dropitem),
  вывод `clif_displaymessage` построчно. `#include` уже есть (mob.h, map.h, itemdb.h).
- `src/map/atcommand.h` — `AtCommand_WhereIs` (перед `AtCommand_Unknown`).
- Таблица — `{ AtCommand_WhereIs, "@whereis", 1, atcommand_whereis }`; `conf/atcommand_athena.conf` — `whereis: 0`.
- Только чтение глобального `map[]`/`mob_db` вызывающего; ничего не меняется.

## Детали
- Метки/имена — **ASCII English** (имена мобов/итемов/карт английские из данных). RU позже через msg_txt.
- Скан moblist — редкая команда (~`map_num`×128 проверок указателей), приемлемо; буферы фикс. (snprintf,
  накопление через strncat с ограничением). `mob_db()`/`itemdb_search()` не возвращают NULL (dummy).
- Дефолты (зафиксированы): точное совпадение имени; кап спавн-карт 20; доступ игрокам.

## Безопасность/верификация
- Только добавления; существующие команды/механики не изменены.
- `make sql` чисто; boot-smoke; на кластере: `@whereis <известный моб>` → карты+дроп; неизвестный → сообщение.

## Вне объёма
Частичный поиск по имени (список кандидатов); MVP-дроп отдельной строкой (можно добавить позже).
