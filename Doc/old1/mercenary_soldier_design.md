# Mercenary Soldier (наёмник-солдат) — дизайн порта в uAthena

Порт системы наёмных солдат (свитки призыва → временный боевой союзник) из eAthena pre-renewal
(`/tmp/eathena-ref`). uAthena этой системы НЕ имеет: её `mercenary.c` — это ГОМУНКУЛ (`merc_hom_*`).
Источник порта: `src/map/mercenary.c|.h`, `src/char_sql/int_mercenary.c|.h`, `db/mercenary_db.txt`,
`db/mercenary_skill_db.txt`, item-свитки, `clif_mercenary_*`, BUILDIN `mercenary_*`.

Это самая инвазивная фаза проекта: вводится **новый тип block-list `BL_MER`** в горячих боевых путях.
Объём по решению пользователя — **полный порт, включая 21 активный скилл наёмника**.

## Ключевые отклонения от eAthena (uAthena-специфика)

1. **`BL_MER = 0x100`, НЕ `0x010`.** У eAthena `BL_MER = 0x010`, но в uAthena этот бит занят под
   `BL_ITEM`. Беру свободный бит `0x100`. `BL_CHAR = (BL_PC|BL_MOB|BL_HOM|BL_MER)`. Коллизий нет.
2. **Новые файлы `mercenary_soldier.c|.h`** — имя `mercenary.c` занято гомункулом. Символы
   (`merc_create`, `mercenary_*`, `struct mercenary_data`, `struct s_mercenary`) с `merc_hom_*`/
   `homun_data`/`s_homunculus` НЕ конфликтуют (проверено).
3. **Нет `sv_readdb`** — пишу ручной парсер запятых (как для quest/achievement loader).
4. **Char-сторона на сыром mysql** — char_sql uAthena не имеет `Sql_*` API; `int_mercenary.c`
   переписывается под идиому `int_quest.c`/`int_achievement.c` (raw `mysql_query`/`mysql_fetch_row`).
5. **Окно статуса наёмника спит под PV7** — `clif_mercenary_*` гард `PACKETVER>=20080102`. Наёмник
   виден и дерётся как юнит; окно покажем чатом `@merc` (MSP3), как quest/@status/@achievements.
6. **Скилл-ремап `MC_SKILLBASE 8201` → `MERC_SKILLRANGEMIN 1000`** (массив `skill_db[1100]`,
   гомункул 800-816, гильдия 900-915 → мерк 1000-1040 свободно). Вставка мерк-ветки на каждом
   из ~12 инлайн-сайтов ремапа в `skill.c`, ПОРЯДОК: `GD(10000) → MC(8201) → HM(8001)`.

## Модель данных

- `struct s_mercenary` (mmo.h): `int mercenary_id, char_id; short class_; int hp, sp;
  unsigned int kill_count, life_time;` — пересылается memcpy по wire, держать packed-стабильным.
- `mmo_charstatus` (+7 полей): `int mer_id; int arch_faith, arch_calls, spear_faith, spear_calls,
  sword_faith, sword_calls;` — сохраняются в таблице `mercenary_owner` (грузятся при загрузке перса).
- `struct mercenary_data` (mercenary_soldier.h): `bl, ud, *vd, base/battle_status, sc, regen, *db,
  mercenary, blockskill[MAX_SKILL], *master, contract_timer, devotion_flag:1`.
- `struct s_mercenary_db`: class_, sprite/name, lv, range2/3, status_data, view_data,
  skill[MAX_MERCSKILL].
- map_session_data: `+ struct mercenary_data *md;` (рядом с `*hd`).
- Константы (mmo.h): `MAX_MERCENARY_CLASS 100`, `MAX_MERCSKILL 40`, `MC_SKILLBASE 8201`.
- enum (status.h): `SC_MERC_FLEEUP, SC_MERC_ATKUP, SC_MERC_HPUP, SC_MERC_SPUP, SC_MERC_HITUP,
  SC_MERC_QUICKEN` — append перед `SC_MAX` (значения внутренние, с eAthena не обязаны совпадать).
- enum (map.h): `SP_MERCFLEE=165, SP_MERCKILLS=189, SP_MERCFAITH=190` в SP_-enum.
- skill.h: 21 скилл `MS_BASH=8201 … ML_DEVOTION` (MS_ 6 + MA_ 9 + ML_ 6).
- Таблицы (миграция 9): `mercenary` (инстанс) + `mercenary_owner` (faith/calls per char).
- intif map↔char: `0x3070 create / 0x3071 load / 0x3072 delete / 0x3073 save`
  ↔ `0x3870/0x3871/0x3872` (СВОБОДНЫ в uAthena).

## Фазы

**MSP1 — ядро + скиллы (эта фаза).** Делается по компилируемым вехам, каждая = коммит + сборка:

- **M1 — константы и структуры.** mmo.h (s_mercenary + charstatus + константы), map.h (BL_MER,
  BL_CHAR, TBL_MER, SP_MERC*, sd->md), status.h (SC_MERC_*), skill.h (21 enum + MERC range defs).
  Плюс копия `db/mercenary_db.txt` (47) + `db/mercenary_skill_db.txt` (164). Компилируется (ничего
  ещё не ссылается на новое).
- **M2 — boil-up зависимостей:** `clif_mercenary_*` (clif.c, PV7-гард) + intif `0x3070-3` (map-side)
  + `status_calc_mercenary`/`status_set_viewdata(BL_MER)` (status.c).
- **M3 — движок `mercenary_soldier.c|.h`:** порт mercenary.c (create/data_received/faith/calls/save/
  delete/contract-timer/heal/damage/dead/kills/killbonus/checkskill) + ручные db-парсеры + do_init
  в map.c.
- **M4 — нити BL_MER по боевым файлам** (зеркало BL_HOM, поведение существующих типов НЕ меняем):
  status.c, battle.c, skill.c, unit.c (AI/walk/free/remove), mob.c, map.c, pc.c, script.c.
- **M5 — char-сторона:** `int_mercenary.c` (raw mysql, 2 таблицы) + хуки в char-load/save/delete +
  inter.c + миграция 9 + char Makefile/GNUmakefile.
- **M6 — boot ядра:** оба сервера линкуются, db грузится ("Done reading 47/164"), boot с картами чист.
- **M7 — скиллы:** skill.h enum (M1) + `MERC_SKILLRANGEMIN 1000` + мерк-ветка ремапа на всех ~12
  сайтах skill.c + `MAX_SKILL_DB`/`MAX_SKILL` при необходимости + записи skill_db/cast/require для
  21 скилла + поведение (пассивы через статус, активки через AI). Boot-проверка.

**MSP2 — призыв.** Свитки-предметы (item_db 12153+), скрипт `{ mercenary_create <class>,<ms>; }`,
BUILDIN `mercenary_create/heal/sc_start/get_calls/set_calls/get_faith/set_faith`. Мерк-скрипты гильдий.

**MSP3 — `@merc` чат-UI.** Статус/скиллы/контракт наёмника текстом (PV7 без окна).

## Инварианты

- **Аддитивность к существующим типам.** Добавление `BL_MER` НЕ меняет поведение BL_PC/MOB/HOM/PET.
  В каждом боевом сайте — зеркало уже работающей BL_HOM-ветки, без правки соседних веток.
- **Worker/сейв off-tick** — char-сторона пишет асинхронно через сокет (как quest/achievement).
- **Идемпотентность** — повторная загрузка/релог не плодит наёмников (`sd->status.mer_id` гард).
- **PV7-headless** — окно наёмника не требуется; всё критичное доступно без клиентского окна.
- **Скиллы — последними** — ремап-хирургию skill.c делаю после того, как ядро забутилось.

## Тестирование

- Пер-веха: чистая `make sql` (0 новых ворнингов) + рассуждение о корректности.
- Boot: оба сервера, межсерверный хендшейк, загрузка карт `--run_once`.
- Кластер (тестировщики): свиток → призыв; следование за хозяином; авто-бой; faith/calls растут;
  таймер контракта истекает → наёмник уходит; релог в пределах life_time → наёмник возвращается;
  смерть наёмника; (M7) скиллы; идемпотентность (нет дублей).
