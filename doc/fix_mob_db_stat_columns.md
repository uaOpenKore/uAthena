# Фикс: импорт mob_db в SQL — «Out of range value for column 'DEX'»

## Симптом
При заливке mob_db в SQL (миграции `dumps/migrations/` через `dumps.sh update`,
либо `sql-files/mob_db*.sql`) MariaDB ругалась:

```
ERROR 1264 (22003): Out of range value for column 'DEX' at row 1
```

Падало на GvG-сундуках и кристаллах Эмпериум-комнаты из `db/mob_db2.txt`, у которых
`DEX = 999`: TREASURE_BOX41–49 (1938–1946), CRYSTAL_6–9 (1951–1954), TREASURE_BOX_I (1955).

## Причина
1. **Узкие колонки статов.** В SQL-схеме `mob_db` шесть базовых статов
   (`STR/AGI/VIT/INT/DEX/LUK`) были объявлены `tinyint(4) unsigned` — максимум **255**.
   Сервер же хранит их в `unsigned short` (0..65535 — `struct status_data`,
   `src/map/map.h:356`), поэтому `DEX=999` для движка штатен (TXT грузится без ошибок,
   `use_sql_db: no`), но в `tinyint`-колонку не влезал → ошибка/усечение до 255.
2. **Устаревший дамп.** `dumps/migrations/A-mob_db.sql` был сгенерирован из `mob_db.txt`
   ещё ДО разрешения мерж-конфликта по Maya(1147)/Medusa(1148) (коммит `455e631`), поэтому
   содержал **дублирующиеся** строки 1147 и 1148 → `ERROR 1062: Duplicate entry '1147'`.

## Что изменено
- Шесть стат-колонок расширены `tinyint(4) unsigned` → **`smallint(6) unsigned`**
  (точное соответствие `unsigned short`, 0..65535) в схемах:
  `dumps/migrations/1-mob_db.sql`, `dumps/tables/mob_db.sql`, `dumps/tables/mob_db2.sql`,
  `sql-files/mob_db.sql`, `sql-files/mob_db2.sql`.
- Добавлена идемпотентная миграция **`dumps/migrations/6-widen-mob-db-stats.sql`**
  (ALTER для патча «вживую» без переимпорта; рунер применяет её между `1-` и `A-`).
- **`dumps/migrations/A-mob_db.sql` перегенерирован** штатным генератором
  `dumps/forge/mob_db-to-sql.sh` из текущих `db/mob_db.txt` + `db/mob_db2.txt`
  (убраны 2 устаревшие дубль-строки 1147/1148; 1003→1001 INSERT).
- Регрессионный тест **`dumps/test_mob_db_stat_range.sh`**.

Значения статов мобов НЕ менялись — `DEX=999` сохраняется как есть. Это изменение только
схемы/дампа; механики не затронуты.

## Как применить
- Стенды на миграциях: `cd dumps && ./dumps.sh update` (таблица `mob_db` пересоздаётся
  широкой и наполняется заново — это справочные данные, потерь нет).
- Боевая БД без переимпорта: применить только ALTER —
  `mysql -u… -p… ragnarok < dumps/migrations/6-widen-mob-db-stats.sql`.
- Классический путь `sql-files/`: схемы уже исправлены; для уже залитой БД выполнить тот же
  ALTER по таблицам `mob_db` и (если используется отдельная) `mob_db2`.

> Замечание: боевой сервер сейчас читает TXT (`conf/inter_athena.conf: use_sql_db: no`),
> поэтому в живой игре баг не проявлялся. Фикс важен при переходе на SQL-mob_db и при любом
> импорте mob_db в СУБД.

## Проверка тестировщиками
1. **Регрессионный тест:** `./dumps/test_mob_db_stat_range.sh` → `PASS` (DEX=999 сохраняется).
2. **Полный импорт на чистой БД** (после `dumps.sh update` или вручную
   `1-mob_db.sql` → `6-widen-mob-db-stats.sql` → `A-mob_db.sql`):
   - импорт без `Out of range` и без `Duplicate entry`;
   - `SELECT COUNT(*) FROM mob_db` = **1001**;
   - `SELECT COUNT(*) FROM mob_db WHERE DEX=999` = **14**;
   - `SELECT MAX(DEX) FROM mob_db` = **999**;
   - `SHOW COLUMNS FROM mob_db LIKE 'DEX'` → `smallint(6) unsigned`;
   - `SELECT COUNT(*) FROM mob_db WHERE ID=1147` = **1** (дубля Maya нет).
3. **В игре (WoE/GvG):** сундуки сокровищ после WoE и кристаллы/барьеры Эмпериум-комнаты
   спавнятся и ведут себя как раньше (визуально без изменений — менялась только БД).
