# SP3 группа C — бэкпорт квестовых NPC эпизодов 11-13

Третья под-фаза SP3 (после B классические города, A Новый Мир). Группа C = средние эпизоды 11-13
(Schwarzwald/Arunafeltz + переход в Новый Мир). Источник — `/tmp/eathena-ref/npc/quests/`.

## Что добавлено (контент)

8 файлов дословно → `npc/backport/quests/` + регистрация в `scripts_athena.conf` (блок «SP3 group C»):

| файл | строк | setquest |
|------|------:|---------:|
| quests_lighthalzen | 11818 | 13 |
| quests_hugel | 10942 | 9 |
| quests_rachel | 7698 | 9 |
| quests_veins | 7430 | 38 |
| quests_ein | 7345 | 25 |
| quests_juperos | 5116 | 0 |
| **quests_13_1** | 18065 | **203** |
| **quests_13_2** | 13702 | **86** |

**`quests_13_1`/`quests_13_2` несут цепочку доступа в Manuk/Splendide (ep14.1, Ash Vacuum)** — то, чего
ждал Новый Мир из группы A. Покрытие quest_id: 247/249 в `quest_db.txt` (2 исключения ниже).

## Изменение движка (аддитивное)

- **`progressbar("<color>",<seconds>)`** — в eathena под `#if PACKETVER >= 20080318`, т.е. на клиенте 2007
  (PV7) сам eathena компилит её в **no-op**. Делаю так же: аргументы принимаются, выполнение продолжается
  сразу (без полосы прогресса и ожидания). Нужна `quests_13_1`. Поведение идентично eathena-на-PV7.

## map_index (append-only)

Добавлены `nyd_dun01`, `nyd_dun02` (Нидхёгг, в 13_2), `que_dan01`, `que_dan02` (quest-карты, в 13_1) —
раньше «Invalid map». **На dev-боксе их .gat нет** → NPC на них тихо пропускаются; на проде с полным
клиентом (карта + mapindex синхронизированы) загрузятся.

## Родное eathena-поведение (НЕ баги порта; quest_db идентичен eathena)

- `completequest 60213` (rachel) — квеста 60213 нет в quest_db (и в eathena нет) → завершение
  несуществующего/неактивного квеста = безвредный no-op, диалог продолжается.
- camel-цепочка (veins): `changequest 3059+rachel_camel,3060+rachel_camel` — 3060-3072 есть, **3059
  (camel=0) отсутствует** (как в eathena). Проверить прохождение camel-квеста в игре.

## Валидация (dev-бокс с GRF)

`./map-server_sql --run_once`: сборка 0 ошибок; **16858 NPC**, 0 `script error`, 0 «Could not parse»,
0 «Invalid map», 0 коллизий. Игровой процесс (диалоги/награды/прогресс) — тестировщики на клиенте.

## Что проверять тестировщикам

1. Lighthalzen (био-этика/Friendship), Hugel, Rachel/Veins (Arunafeltz), Einbroch, Juperos — квест-NPC, диалоги, награды.
2. **Доступ в Новый Мир:** пройти цепочку `13_1`/`13_2` → открывается вход в Manuk/Splendide (свести с town-NPC из SP1 и картами).
3. Квесты с журналом (`@quests`): veins (38), ein (25), lighthalzen (13) — статус/прогресс корректны.
4. camel-квест (veins) — проходится ли (см. заметку про 3059).
5. Карты `nyd_dun01/02`, `que_dan01/02` есть в клиентском GRF + mapindex синхронизирован.
6. Регрессий по существующим NPC нет.

## Дальше

Группы D/E (тематические/job-линейки: Sign/Kiel/Lvl4-weapon/headgears/skills/...). F (god-item/instance/BG) — исключены.
