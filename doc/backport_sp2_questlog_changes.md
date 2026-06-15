# SP2 quest-лог: что изменено и что проверять

Серия коммитов в `x64` (T1 типы → T2 clif → T3 map-движок → T4 char-хранение → T5 хуки → T6 данные).
Дизайн — `doc/backport_sp2_questlog_design.md`, план — `doc/backport_sp2_questlog_plan.md`.

## Что добавлено
- **Движок quest-лога** (порт подсистемы eAthena): `src/map/quest.c` + 5 скрипт-команд
  (`setquest/erasequest/completequest/changequest/checkquest`); хранение на char-сервере
  (`src/char_sql/int_quest.c`, таблица `quest`); межсервер `0x3060/0x3061`↔`0x3860/0x3861`;
  `db/quest_db.txt` (1703 квеста).
- **Хуки:** загрузка квестов на логине (`pc_authok`), сохранение с персонажем (`chrif_save`, off-tick),
  обновление hunt-счётчиков при убийстве моба (`mob_dead`).
- **Окно журнала квестов** (`clif_quest_*`) портировано, но под `#if PACKETVER >= 20080000` — при текущем
  `PACKETVER 7` (клиент 2007-05-07a) оно **спит**: видимого журнала нет, пакеты старому клиенту не шлются,
  движок работает headless. NPC-логика (`checkquest`) от окна не зависит.
- **API не менялся:** добавлены только новые команды/функции; ни одна существующая `BUILDIN_DEF` и её
  реализация не тронуты → действующие NPC не ломаются (проверено diff'ом).

## Ключевые адаптации под uAthena (старый API)
- `int_quest.c` переписан под **raw-mysql** идиому char-сервера uAthena (`mysql_handle`/`tmp_sql`/
  `sql_res`, как `int_homun.c`) — у uAthena нет нового `Sql_/SqlStmt_` API из eAthena.
- `clif_quest_*` обёрнуты в `#if PACKETVER` (в eAthena они без обёртки — там клиенты новее).

## Перед запуском (БД)
- Применить **`sql-files/quest.sql`** (или миграцию `dumps/migrations/7-add-quest-table.sql`) — создаёт
  таблицу `quest`. Без неё load/save квестов будут давать SQL-ошибку в логе char-сервера.

## Что проверять (кластер: char+map, текущий клиент)
1. Тест-NPC с командами: `setquest <id>`, `checkquest <id>` (без арга=HAVEQUEST; арг 0=HAVEQUEST/PLAYTIME/
   HUNTING — см. enum), `changequest <id1>,<id2>`, `completequest <id>`, `erasequest <id>` — состояния
   меняются как ожидается, без ошибок скрипта в логе.
2. **Перезаход персонажа** — активные/выполненные квесты сохранились и загрузились (строка
   `intif_parse_questlog` на map; строки SQL на char).
3. **Hunt-квест** (квест с mob/count в `db/quest_db.txt`): убийство нужного моба двигает счётчик;
   `checkquest(id, HUNTING)` == 2 при достижении.
4. **Time-limit квест**: по истечении `time` `checkquest(id, PLAYTIME)` == 2.
5. Действующие NPC/команды не сломаны (выборочно: кафры, варпы, лавки, диалоги).
6. Окно журнала в клиенте НЕ появляется — это ожидаемо под текущим клиентом.

## Известные/вне SP2
- Warning при старте `Unknown setting 'quest_exp_rate' in conf/battle/exp.conf` — **pre-existing**
  (не из SP2): это реневал-настройка множителя exp-награды за квест; награды — логика квест-NPC (SP3),
  а не движка quest-лога. Можно проигнорировать / вычистить отдельно.
- Видимое окно журнала — требует апгрейда клиента и `PACKETVER >= 20080000` (тогда `clif_quest_*`
  включатся без правок кода).
- Квест-NPC нового контента — **SP3** (зависит от этого движка). Вход в Новый Мир (Manuk/Splendide) — там же.

## Воспроизведение/проверки
Boot-smoke подтвердил: map-сервер на старте читает `quest_db.txt` (`Done reading '1703' entries`),
утечек нет. Полный игровой прогон квестов — фаза тестировщиков (нужны char-сервер + клиент).
