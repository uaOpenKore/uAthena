# Renewal warps + town-NPC backport — изменения

Источник: rAthena `7f08087`. Ветка x64. **0 правок движка** (C). Изолированный вывод
генераторов, append-only подключение. Дизайн — `Doc/backport_renewal_warps_npc_design.md`,
план — `Doc/backport_renewal_warps_npc_plan.md`.

## Добавлено

**Статические варпы (139)** — `npc/warps/backport/re/{cities,fields,dungeons}/` (10 файлов).
- `warp2`→`warp`: 0 (в scope не встретились; конверсия — защитная мера).
- Конфликтов имён/тайлов: 0 (renewal-зоны greenfield).
- Boundary-skip: 2 (хаб dimensional-gap `dali`→bif_fild01/dic_fild02 — карта вне 6 зон,
  не в map_index; залогировано в `Doc/backport_renewal_warp_conflicts.md`).
- Генератор: `dumps/forge/backport-renewal-warps.py` (подключение `npc/scripts_warps.conf`).

**Town-NPC (6 зон + кафры)** — `npc/backport/re_cities/` (dewata, dicastes, eclage,
malangdo, malaya, mora + kafras). Вход: town `cities/` + non-warp из warp-файлов
(лифты Dicastes, Small Hole Mora, jeepney Malaya, hub Eclage).
- Кафры: 3 `duplicate(kaf_alberta)` (kaf_dewata, kaf_malaya1/2) из `npc/re/kafras/kafras.txt`.
- Генератор: `dumps/forge/backport-renewal-town-npcs.py` (подключение `npc/scripts_athena.conf`).

**Карты в load-list (43)** — `conf/maps_athena.conf` (append-only). Сервер грузит карты
отсюда, не из map_index. Без этого NPC/варпы на renewal-картах не материализуются.

**map_index**: 0 добавлений (все scope-карты уже зарегистрированы прошлой фазой).

## Адаптации синтаксиса (gap)

Токен-санитайзер (buildins) + boot-parse (операторы/синтаксис). Полный лог —
`Doc/backport_renewal_npc_gap.md`.

| Класс | Кол-во | Действие |
|-------|--------|----------|
| ADAPT consumeitem→delitem,1 | 6 | предмет удаляется (эквивалент) |
| ADAPT `=`→`set var,expr` | 2 | присваивание (uAthena нет `=`) |
| ADAPT for-init/`++`/`--`→`set` | 2 | циклы (uAthena нет `++`) |
| ADAPT `enablenpc()`→`enablenpc strnpcinfo(0)` | 4 | self-target (uAthena сигнатура `"s"`) |
| SITEFIX getargcount→getarg-sentinel | 1 | jeepney-транспорт Malaya |
| SITEFIX charat→compare-индекс | 1 | Small Hole транспорт Mora↔Bifrost |
| BOUNDARY (NPC вне scope-карт) | 4 | `Odgnalam#iz_*` на izlude-academy → закомментированы |
| COMMENT (функция теряется) | 118 | флейвор: 91 эмоция `ET_*`, 24 `getnpcid` unit-эмоут, 3 редкие (vip_status/is_party_leader/getgroupitem) |

**Кодировка**: town-файлы пишутся latin-1 (byte-preserving) — содержат 8-битные
(EUC-KR) байты в диалогах; UTF-8-перекодировка их бы удвоила.

**Известные потери флейвора** (залогированы, не блокируют): закомментированы 91 эмоция
`ET_*` (можно восстановить маппингом ET_→числовой emotion-id — follow-up) и 24 `getnpcid`
unit-эмоут-вызова. Диалоги/квесты/транспорт/кафры — целы.

## Верификация (выполнено)

- Оба генератора `--selftest` зелёные; `--verify` OK (имена/тайлы/endpoint/refs/braces/
  live-gap = чисто).
- Byte-preservation: `dicastes.txt` исходные EUC-KR байты идентичны (проверено).
- map-server `--run_once`: **0 script-error** на `backport/re*`, `Server is 'ready'`.
- maps_athena.conf: 43 scope-карты в load-list (boot подтверждает попытку загрузки).

## За тестерами (нужен клиент + GRF)

- **`.gat` renewal-карт в GRF** — без них сервер отбрасывает карты (`Removing map`),
  NPC/варпы не материализуются (на dev-боксе так; деплой-задача, как pre-renewal warps).
- Проходимость варпов, диалоги/транспорт NPC, баланс торговцев, заполнение
  `решение?` в `Doc/backport_renewal_warp_conflicts.md` (2 boundary-варпа `dali`).

## Регенерация

Из корня репо: `RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-warps.py`
и `… backport-renewal-town-npcs.py`. Идемпотентно. Подключения (`scripts_warps.conf`/
`scripts_athena.conf`/`maps_athena.conf`) — append-only вручную из `dumps/forge/*-includes.txt`
и `*-maps-athena.txt`.
