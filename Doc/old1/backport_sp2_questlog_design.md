# Дизайн SP2: движок quest-лога (порт подсистемы quest из eAthena)

Дата: 2026-06-15. Ветка: `x64`. Источник: `/tmp/eathena-ref`.

Второй под-проект NPC-бэкпорта — фундамент для квест-NPC (SP3). Точный порт подсистемы quest-лога eAthena
(map + char + межсервер + БД + clif-окно), адаптированный под фреймворк uAthena. **Главный инвариант:
существующий скрипт-API и действующие NPC не ломаются** (только добавляем).

## 1. Решение по клиентскому окну

Клиент тестировщиков (2007-05-07a) окна журнала квестов не имеет; PACKETVER сервера = 7. Поэтому:
**движок headless** — `clif_quest_*` портируются обёрнутыми в `#if PACKETVER >= ...` (как в eAthena) и под
текущим клиентом компилируются в пустышки (видимого журнала нет, нулевой риск). При будущем апгрейде клиента
окно заработает без доработок. **PACKETVER не меняем** (отдельное клиент-решение). NPC-логика SP3
(`checkquest`) от окна не зависит.

## 2. Архитектура и поток данных

Quest-лог — отдельная per-character сущность (аналог homunculus, `int_homun.c` — образец): грузится на
логине через межсервер, держится в памяти map-сервера (`sd->quest_log[]`), сохраняется диффом на
char-сервер (SQL). **Игровой тик не блокируется** (запись уходит в сокет char-серверу; SQL пишет char —
согласуется с async-DB архитектурой).

- **Логин:** `intif_request_questlog(char_id)` → `0x3061` (map→char) → `int_quest.c` читает таблицу
  `questlog` → `0x3860` (char→map) → map заполняет `sd->quest_log[]`/`num_quests`, ставит таймеры
  time-limit квестов (`quest_pc_login`).
- **Сохранение:** изменение квеста → `sd->save_quest = true`; в точках сохранения персонажа (рядом с
  существующим char-save) → `intif_quest_save(sd)` → `0x3060` (map→char) → char диффит против БД и пишет
  INSERT/UPDATE/DELETE → `0x3861` ack.
- **Охот-цели:** убийство моба игроком → `quest_update_objective(sd, mob_id)` инкрементит count активных
  hunt-квестов (хук в пути начисления килла, mob.c).

Свободные межсервер-пакеты подтверждены: `0x3060/0x3061` (map→char), `0x3860/0x3861` (char→map).

## 3. Компоненты (порт eAthena → адаптация под uAthena)

| Файл | Что |
|---|---|
| `src/common/mmo.h` | `struct quest`, `enum quest_state {Q_INACTIVE,Q_ACTIVE,Q_COMPLETE}`, `MAX_QUEST_DB=2000`, `MAX_QUEST_OBJECTIVES=3` |
| `src/map/pc.h` (map_session_data) | `int num_quests; struct quest quest_log[MAX_QUEST_DB]; bool save_quest;` (статич. массив; ~48 КБ/сессия — RAM-за-фичу приемлемо) |
| `src/map/quest.c` + `quest.h` (новые) | чтение `db/quest_db.txt`; `quest_add/delete/update/check`; `quest_pc_login`; `quest_update_objective` |
| `src/map/script.c` | 5 команд `setquest/erasequest/completequest/checkquest/changequest` (`BUILDIN_DEF` + реализация в стиле uAthena `int buildin_x(struct script_state*)`; существующие команды не трогаются) |
| `src/map/intif.c` + `chrif.c` | map-сторона межсервера: запрос на логине, save в точках char-save, парс `0x3860/0x3861` + packet_len |
| `src/char_sql/int_quest.c` + `int_quest.h` (новые) | char-сторона: SQL load + diff-save; регистрация в `inter.c` (inter_parse/inter_init) + `char.c` |
| `src/map/clif.c` + `clif.h` | `clif_quest_add/delete/send/update` под `#if PACKETVER >= ...` (спят под PV7) |
| `db/quest_db.txt` | порт списка квестов (формат: id, time, mob1,count1, mob2,count2, mob3,count3, "name") |
| `sql-files/quest.sql` + миграция | таблица `questlog` (state enum, time, mob1-3/count1-3, PK char_id+quest_id) |
| `src/map/mob.c` | хук `quest_update_objective` в пути смерти моба |
| Makefile/GNUmakefile (map+char) | `obj/quest.o`, `int_quest.o` |

## 4. Безопасность и корректность

- **x64:** межсервер-пакеты сериализуют `struct quest` (только int-поля, без указателей) → `memcpy` по
  проводу безопасен (в отличие от ранее найденных усечений указателей в SC/script). Длины пакетов считаются
  явно; буферы проверяются.
- **API-инвариант:** добавляются только новые команды/функции; ни одна существующая `BUILDIN_DEF` и её
  реализация не меняются → действующие NPC не ломаются.
- **Персистентность off-tick:** save уходит в сокет (char пишет SQL вне игрового тика). Дифф идемпотентен по
  PK `char_id+quest_id` → повторная запись/сбой не дюпают.
- **Загрузка БД:** `quest_db.txt` парсится на старте map; неизвестные строки — warn+skip (не фатально).

## 5. Верификация

- `make sql` чисто (map + char) под PACKETVER 7 (clif-окно → пустышки), без новых предупреждений.
- Standalone-юнит на парсер `quest_db.txt` (`-DQUEST_TEST`, как принято в проекте) + рассуждение о
  корректности diff-save.
- ASan smoke-boot обоих серверов (init/final сбалансированы, нет утечек на quest-структурах).
- На кластере (тестировщики): все 5 команд в тест-NPC; перезаход — квесты сохраняются/грузятся; убийство
  моба двигает hunt-счётчик; time-limit истекает; действующие NPC не затронуты.

## 6. Вне SP2

- Видимое окно журнала квестов (требует апгрейда клиента/PACKETVER) — отдельно.
- Квест-NPC нового контента (SP3, зависит от SP2).
- mercenary-скрипт-API (SP4).
- Авто-выдача наград/опыта за квест — логика конкретных NPC (SP3), не движок.
