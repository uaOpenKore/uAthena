# Достижения и титулы — дизайн (спека)

Фича «с нуля» (в eAthena пре-реневала нет; achievements — реневал+). Архитектура **зеркалит движок
quest-log (SP2)** — проверенный паттерн per-character сущности с off-tick сохранением на char-сервер.
Клиент 2007 (PV7) не имеет окна достижений/титулов → весь вывод через чат (`@achievements`, `@title`),
как остальные client-workarounds.

## Объём (одобрено): движок + трекинг + @achievements + титулы + материальные награды.

## Структуры данных

`src/common/mmo.h`:
```c
#define MAX_ACHIEVEMENT_DB 500      // определений в db
#define MAX_ACHIEVEMENT     256     // на персонажа (активные/в процессе)

struct achievement {                // per-character прогресс (как struct quest, all-int → memcpy x64-safe)
    int achievement_id;
    int count;                      // прогресс к цели
    unsigned int completed;         // время завершения (0 = не завершено)
    int rewarded;                   // 1 = награда выдана
};
```

`src/map/map.h` (map_session_data, после quest-полей):
```c
int num_achievements;
struct achievement achievement_log[MAX_ACHIEVEMENT];
int achievement_index[MAX_ACHIEVEMENT];
bool save_achievement;
int active_title;                   // id достижения, чей титул активен (0 = нет)
```

## db/achievement_db.txt (определения)

Формат: `ID,Group,TargetID,TargetCount,"Name","Title",RewardItem,RewardAmount,RewardZeny,RewardExp`
- **Group** (тип условия): `AG_KILL`(убить TargetCount моба TargetID; 0=любой), `AG_BASELEVEL`,
  `AG_JOBLEVEL`(достичь TargetCount), `AG_JOBCHANGE`(сменить на джоб TargetID),
  `AG_QUEST`(завершить TargetCount квестов; либо конкретный TargetID), `AG_ZENY`(накопить TargetCount).
- **Title** — строка титула ("" = достижение без титула).
- Reward* — 0 = нет. RewardItem/Amount, RewardZeny, RewardExp (base exp).

s_achievement_db в `achievement.c` парсит это (как quest_read_db).

## Движок `src/map/achievement.c` + `achievement.h`

- `achievement_read_db()` — парс db (do_init).
- `achievement_search(id)` → определение.
- `achievement_get_index(sd,id)` / создать запись прогресса.
- `achievement_progress(sd, group, target_id, add)` — найти подходящие незавершённые достижения, инкрементить
  count, при достижении цели → `achievement_complete()`.
- `achievement_complete(sd, id)` — пометить completed=time, выдать награду (item/zeny/exp), показать титул-доступ,
  чат-уведомление, `save_achievement=true`.
- `achievement_check_title(sd, id)` — можно ли активировать титул (достижение завершено).
- load/save через intif (как quest).

## char-сторона `src/char_sql/int_achievement.c` (raw mysql, зеркало int_quest.c)

- Таблица `achievement` (migration 8): `char_id, achievement_id, count, completed, rewarded`, PK(char_id,achievement_id).
  + `char_titles` ИЛИ поле `active_title` в `char` (см. ниже) — храним активный титул.
- `mapif_parse_achievement_load` (0x3062→0x3862), `..._save` (0x3063→0x3863). Зеркало int_quest идиомы
  (mysql_query/tmp_sql/sql_res).

## intif (map↔char)

- `intif_request_achievements(char_id)` → 0x3062; парс ответа 0x3862 (-1, переменная длина).
- `intif_achievement_save(sd)` → 0x3063 (полный diff-набор, как quest); подтверждение 0x3863.
- Длины в char.c/inter.c packet_len; цепочка inter_achievement_parse_frommap.

## Трекинг (хуки)

- `mob_dead` (mob.c) → `achievement_progress(sd, AG_KILL, md->class_, 1)` для каждого игрока-добытчика
  (рядом с quest-хуком mob_dead).
- `pc_checkbaselevelup` → `achievement_progress(sd, AG_BASELEVEL, 0, 0)` (проверка по текущему уровню).
- `pc_checkjoblevelup` → AG_JOBLEVEL.
- `pc_jobchange` → `achievement_progress(sd, AG_JOBCHANGE, job, 1)`.
- quest_update_status (complete) → AG_QUEST.
- zeny: проверять при изменении (pc_payzeny/getzeny) или периодически/при @achievements (дёшево).
- Хук в `pc_authok` → `intif_request_achievements`; `chrif_save` → achievement_save (off-tick).

## Чат-UI (PV7)

- **`@achievements`** [`@ach`] — список: завершённые сверху/в процессе снизу (как @quests), строка
  `[N] "<Name>" - DONE|<count>/<target>[ +title]`.
- **`@title`** — список доступных титулов (из завершённых достижений с непустым Title) + `@title <N>` выбрать
  активный, `@title off` снять. Активный титул показывается в `@achievements`/`@title` и в самопредставлении.
  (Имя-префикс над головой НЕ делаем: PV7 не имеет поля титула, хак рискован.)

## Награды

В `achievement_complete`: `pc_getitem`/`pc_getzeny`/`pc_gainexp` по полям db; `rewarded=1` (идемпотентно —
не выдавать повторно при рело́де). Балансные значения — скромные (стартовый набор), тестировщики калибруют.

## Стартовый контент (~15-20)

Киллы (Poring x100, Fabre x100, любой моб x1000), база-уровень (10/30/50/70/99), джоб-уровень (10/50),
джоб-чейндж (на 2-1/2-2), квесты (1/10/50 завершено), зени (1m/10m/100m). Часть с титулами
(«Novice Slayer», «Veteran», «Millionaire»...). ASCII-метки (кодировка клиента; RU позже через msg_txt).

## Фазы реализации (инкрементальные коммиты)

1. Данные: mmo.h struct/const + db/achievement_db.txt (формат+стартовый набор) + achievement.c парсер + read в do_init. Build.
2. Движок прогресса/complete/награды + map.h поля. Build.
3. char-сторона: int_achievement.c + таблица + migration 8 + Makefile. Build (оба сервера).
4. intif протокол (0x3062/3) + load/save хуки (pc_authok/chrif_save). Build.
5. Трекинг-хуки (mob_dead/levelup/jobchange/quest/zeny). Build.
6. @achievements + @title atcommands. Build + boot.
7. Доки тестировщикам + память.

## Инварианты/риски

- Не менять существующий API (только добавления; как quest-log).
- struct achievement all-int → inter-server memcpy x64-safe (урок SP2).
- char_sql = raw mysql (НЕ Sql_ API) — зеркалить int_homun/int_quest.
- clif-окна нет → никаких PACKETVER-гейтов нужных пакетов; всё headless+чат.
- Награды идемпотентны (rewarded-флаг) — нет дюпа при реконнекте/релоаде.

## Верификация

Per-фаза: `make sql` 0 новых ворнингов. Boot с GRF: чтение achievement_db, без ошибок. End-to-end
(тестировщики на кластере): убить мобов→прогресс в @achievements; достичь уровня→разблокировка+награда+титул;
@title выбор; реконнект→прогресс/награды сохранены (без повторной выдачи).
