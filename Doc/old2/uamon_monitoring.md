# Мониторинг нагрузки мап-серверов (uamon)

Поминутно снимает нагрузку каждого мап-сервера в **MongoDB 7**, агрегирует в 10-минутные и
часовые срезы, чистит по ретеншну. Скрипты — только bash, в `scripts/cron/`.

## Источники данных (и их точность)
- **CPU** — самый нагруженный **поток** мап-сервера, **дельтой двух замеров** (`/proc/<pid>/task/<tid>/stat`,
  utime+stime в clock-ticks, окно `CPU_SAMPLE_SECS` сек) → текущая `%CPU` (0–100 одного ядра). Это
  насыщение game-loop. (Сырой `ps %CPU` — среднее за всё время жизни процесса, не текущая нагрузка, —
  НЕ используется.)
- **RAM** — `RSS` процесса в целых МБ (`ps -o rss`, /1024).
- **Игроки по картам** — SQL: `SELECT REPLACE(last_map,'.gat',''),COUNT(*) FROM char WHERE online=1
  GROUP BY last_map`. **Каузат:** `last_map` обновляется при сейве (автосейв/смена карты), поэтому
  данные **отстают на интервал автосейва** (выбор A — чистый bash без правок сервера). Карта→сервер —
  по спискам `map:` в `confN`. Карты с 0 игроков не пишем.
- **Номер инстанса** — из `PID-mapN.pid` (пишет супервизор мульти-мапа); карта→инстанс — из `confN`.

## Коллекции и документы (строка на запись; все поля индексируются)
`stat_min` (сырое поминутное):
```
{ ts:ISODate(минута,UTC), server:N, type:"server", cpu:Int, ram_mb:Int }
{ ts:ISODate(минута,UTC), server:N, type:"map", map:"prontera", players:Int }
```
`stat_10min` / `stat_hour` (агрегат — среднее + пик):
```
{ ts:ISODate(10м|час), server:N, type:"server", cpu_avg, cpu_max, ram_avg, ram_max, samples }
{ ts:ISODate(10м|час), server:N, type:"map", map, players_avg, players_max }
```
- `ts` обрезается до минуты / 10 минут / часа (UTC), маркирует **начало** интервала.
- `players_avg` = **среднее одновременное** = `sum(players)/число минутных снимков сервера в окне`
  (минуты с 0 игроков на карте тянут среднее вниз). `*_max` — точные пики.
- Индексы на **каждое поле** + компаунд `{ts,type,server}` (создаёт `uamon-init.sh`).

## Скрипты (`scripts/cron/`)
| Скрипт | Когда | Что |
|--------|-------|-----|
| `uamon-init.sh` | один раз | создаёт коллекции + индексы (идемпотентно) |
| `uamon-minute.sh` | каждую минуту | CPU-дельта + RAM + игроки/карты → `stat_min` |
| `uamon-10min.sh` | каждые 10 мин | агрегирует последние 10 мин `stat_min` → `stat_10min` |
| `uamon-hour.sh` | каждый час | агрегирует последние 60 мин `stat_min` → `stat_hour` |
| `uamon-cleanup.sh` | раз в месяц | удаляет старше ретеншна |
| `uamon.conf` | — | конфиг (Mongo, SQL, ретеншн, окно CPU) |
| `uamon-lib.sh` | — | общие функции |
| `crontab.example` | — | готовый кронтаб |

Ретеншн (дни, в `uamon.conf`): `stat_min` 62 (~2 мес), `stat_10min` 183 (~6 мес), `stat_hour` 730 (~2 года).

## Деплой
1. Поставить **MongoDB 7 + mongosh** и клиент `mysql`/`mariadb`.
2. `make install` (копирует `scripts/cron` → `/opt/uathena/bin/cron/`).
3. Отредактировать `/opt/uathena/bin/cron/uamon.conf` (Mongo URI/БД, SQL-креды = `inter_athena.conf`
   `char_server_*`, ретеншн, `CPU_SAMPLE_SECS`).
4. Один раз: `/opt/uathena/bin/cron/uamon-init.sh`.
5. Установить кронтаб из `crontab.example` (`crontab -e`).

Проверка без mongosh: `UAMON_DRYRUN=1 ./uamon-minute.sh` (печатает JS, ничего не пишет).

## Примеры выборки
```js
// пик CPU мап-сервера 2 за сутки (поминутно)
db.stat_min.find({server:2,type:"server"}).sort({cpu:-1}).limit(1)
// самые populated карты за последний час (по пику)
db.stat_hour.find({type:"map"},{map:1,server:1,players_max:1,players_avg:1}).sort({players_max:-1}).limit(10)
// средняя загрузка сервера 1 по 10-минуткам за день
db.stat_10min.find({server:1,type:"server"},{ts:1,cpu_avg:1,cpu_max:1,ram_avg:1})
```

## Тюнинг (env / uamon.conf)
`MONGO_URI`,`MONGO_DB`; `SQL_HOST/PORT/USER/PASS/DB`,`CHAR_TABLE`; `UA_BIN_DIR`; `CPU_SAMPLE_SECS`
(окно дельты, деф. 4с — столько работает ежеминутный скрипт); `RET_*_DAYS`; `UAMON_DRYRUN=1` (печать JS).

## Замечания
- Точность игроков по картам ограничена интервалом автосейва (выбор A). Нужна live-точность —
  потребуется маленький C-экспорт `map[m].users` (вариант B, отложен).
- Время хранится в UTC (ISODate). При выборке конвертируй в локаль при необходимости.
- Карта без владельца в `confN` пишется с `server:0` (не теряем игроков; сигнал «не привязано»).
