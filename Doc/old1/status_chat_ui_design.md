# Дизайн: `@status` — баффы/дебаффы и кулдауны скиллов с остатком времени в чат

Дата: 2026-06-15. Ветка: `x64`. Пункт дорожной карты «обход клиента через chat» (клиент PV7 рисует иконки
баффов, но не секунды; точные кулдауны скиллов не показывает).

## Команда
`@status` (и алиас `@cd`) — игрокам (atcommand level 0). Две секции в чат:

### 1. Активные SC (баффы/дебаффы)
Перебор `sc->data[i]`, i в 1..SC_MAX. Активен, если `sc->data[i].timer != -1` (это и проверяет движок).
- Имя: `StatusSkillChangeTable[i]` (SC→скилл); если >0 — `skill_get_name(...)`, иначе `SC#<i>`.
- Остаток: `td = get_timer(sc->data[i].timer); rem = DIFF_TICK(td->tick, gettick())/1000` (сек). Guard `td!=NULL`.
- Строка: `[Status] <имя>: <Nс>`. Если активных нет (`sc->count==0`) — «No active status».

### 2. Кулдауны скиллов
Перебор `sd->blockskill[i] > 0`, i в 1..MAX_SKILL.
- Остаток: `rem = DIFF_TICK(sd->blockskill_tick[i], gettick())/1000`; показываем только при `rem > 0`.
- Строка: `[CD] <skill_get_name(i)>: <Nс>`. Если нет — «No cooldowns».

## Расширение движка (для точного кд)
`blockskill[MAX_SKILL]` хранит только флаг (0/1) без expiry. Добавляем:
- `unsigned int blockskill_tick[MAX_SKILL];` в `map_session_data` (map.h, рядом с `char blockskill[MAX_SKILL]`).
- В `skill_blockpc_start` (skill.c) после `sd->blockskill[skillid]=1;` — `sd->blockskill_tick[skillid]=gettick()+tick;`.
Аддитивно: читается только когда `blockskill[i]>0`; поведение кулдаунов не меняется. Кулдауны гомункула —
вне объёма (только `sd`).

## Детали
- **Имена** скиллов — `skill_get_name` (англ. из skill_db); не-скилловые SC (еда/итемы) → `SC#<номер>`
  (иконка в клиенте подсказывает; новое — точное время). Метки **ASCII English** (клиент 2007 докодовый;
  RU позже через `msg_txt`).
- **Регистрация:** enum `AtCommand_Status` (atcommand.h, перед `AtCommand_Unknown`); таблица —
  `{ AtCommand_Status, "@status", 1, atcommand_status }` и алиас `{ AtCommand_Status, "@cd", 1, atcommand_status }`;
  `conf/atcommand_athena.conf` — `status: 0` и `cd: 0`. Имя `@status`/`@cd`/`@buffs` — свободны (проверено).
- Буферы фикс. (`atcmd_output[200]`/локальный snprintf); только `sd` вызывающего.

## Безопасность/верификация
- Только добавления: новое поле сессии + одна строка в `skill_blockpc_start` + новая команда (+алиас).
  Существующее поведение/команды/движок не меняются.
- `make sql` чисто; boot-smoke; на кластере (тестировщики): бафф со скилла/еды → остаток; скилл на кд →
  остаток до готовности; без баффов/кд — «пусто»; действующие команды/механики целы.

## Вне объёма
Кулдауны гомункула; именованная таблица для не-скилловых SC (позже).
