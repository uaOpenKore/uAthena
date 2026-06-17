# Авто-запуск многомапного сервера (CPU-aware)

Система сама смотрит на число потоков CPU и поднимает нужное количество мап-серверов,
каждый — на своей паре ядер, со своим конфигом, портом, набором карт и логом. char-сервер
маршрутизирует игроков между ними (поддержка до `MAX_MAP_SERVERS = 30`, `src/char_sql/char.h`).

## Сколько мап-серверов и на каких ядрах

```
T = число потоков (nproc)
cpu_max  = (T < 4) ? 1 : ⌊T/2⌋ − 1
conf_max = число подряд идущих confN-папок (conf1, conf2, …); если conf1 нет → 1
K        = max(1, min(30, cpu_max, conf_max))
```

Раскладка ядер:

| Ядра | Назначение |
|------|-----------|
| 0–1 | map-сервер #1 |
| 2–3 | система / NIC softirq / login + char (резерв) |
| 2N..2N+1 | map-сервер #N (N ≥ 2) |

Пример: **24 потока → ⌊24/2⌋−1 = 11** мап-серверов (#1=0,1; #2=4,5; … #11=22,23).
Этот бокс (16 потоков) → максимум 7. При `T < 4` — один сервер, без пиннинга.

Проверить раскладку на конкретной машине, ничего не запуская:
```
scripts/ua-mapcount.sh info      # сводка: threads / cpu_max / conf_max / план по инстансам
UA_DRYRUN=1 scripts/ua-start.sh map sql   # точные команды запуска (taskset/конфиги/логи)
```

## Контракт confN (папки ведёшь ты — режим «только детект»)

- `confN/map_athena.conf` — **обязателен**, и в нём уникально на сервер:
  - свой `map_port` (напр. 5121, 5122, …);
  - свой `import:` со списком карт ЭТОГО сервера (в eAthena карта принадлежит **одному**
    мап-серверу — наборы карт между confN **не должны пересекаться**).
- Прочие конфиги в `confN/` (`battle_athena.conf`, `atcommand_athena.conf`,
  `charcommand_athena.conf`, `script_athena.conf`, `msg_athena.conf`, `grf-files.txt`):
  если файл лежит в `confN/` — берётся он, иначе общий из `conf/`.
- Правило количества:
  - `conf1`, `conf2` есть, `conf3` нет → не больше **2** серверов;
  - вообще нет `confN` → **1** сервер на `conf/` (как раньше).
- confN-папки должны идти **подряд** (conf1, conf2, conf3, …) — разрыв обрывает счёт.

Минимальный confN = `map_athena.conf` (уникальный `map_port` + `import:` своего списка карт)
+ файл со списком карт. Всё остальное наследуется из `conf/`.

## Скрипты

| Скрипт | Роль |
|--------|------|
| `ua-mapcount.sh` | единый источник истины: считает K и ядра (`count`/`cores N`/`appcpus`/`info`). Шарится start/stop; та же формула продублирована в rc.local. |
| `ua-start.sh map sql` | **мульти-супервизор**: считает K, поднимает каждый инстанс `taskset -c <ядра> map-server_sql --map_config confN/…`, со своим логом/PID/perf/креш-дампом; перезапускает упавший (с бэкоффом от краш-лупа); по SIGTERM гасит всех (do_final) и выходит. login/char — прежний одиночный путь. |
| `ua-stop.sh map` | находит супервизора по `PID-map.pid` и шлёт ему SIGTERM (он сам гасит детей — без гонки рестарта); фолбэк — гасит детей напрямую; SIGKILL по таймауту; чистит PID/lock. |
| `rc.local` | сетевой тюнинг по числу потоков: virtio combined=T, IRQ/RPS → ядра 2–3, XPS → все map-ядра, conntrack/somaxconn/backlog масштабируются от T. Авто-детект NIC. |
| `uAmap.service` | один сервис → `ua-start.sh map sql` (супервизор). **Без** `CPUAffinity` (пиннинг пер-инстанс делает taskset), `KillMode=mixed` (на стопе SIGTERM только супервизору). |
| `uAlogin/uAchar.service` | `CPUAffinity=2 3` — лёгкие, держатся на системных ядрах. |

## Раздельные логи

- `uAmapN.log` — игровой лог КАЖДОГО мап-сервера (N = номер инстанса), `$UA_LOG_DIR` (деф. `/opt/uathena/log`).
- `uAmap.log` — лог самого супервизора (через systemd `StandardOutput`).
- Креш-дампы: `crash/mapN-…txt`; perf: `perf/mapN-…` (UA_PERF=1).

## Тюнинг (env)

| Переменная | Назначение |
|-----------|-----------|
| `UA_FORCE_THREADS` | переопределить число потоков (ограничить count) |
| `UA_DRYRUN=1` | (map) только показать план, ничего не запускать |
| `UA_PERF` | perf-профиль; для map профилирует **каждый** инстанс — тяжело при многих, в проде `0` |
| `UA_STOP_GRACE` | сек ожидания graceful-стопа (деф. 120) |
| `UA_BIN_DIR` / `UA_LOG_DIR` | каталог бинарей+confN / каталог логов |

## Деплой

1. `make install` (копирует бинари + скрипты в `/opt/uathena/bin`), скрипты исполняемые.
2. Подготовить `confN/` (порты + непересекающиеся списки карт).
3. `rc.local` → `/etc/rc.local` (`chmod +x`, `systemctl enable rc-local`).
4. `systemctl daemon-reload && systemctl restart uAmap.service` (или `uAthena.target`).
5. Проверка: `scripts/ua-mapcount.sh info`, затем логи `uAmap1.log…uAmapK.log` («Map Server is now online»),
   и на char — строки «Map-Server N connected … port …».

## Проверено

- `ua-mapcount.sh`: юнит-тесты формулы/ядер/capping (24→11, 16→7, conf3-missing→cap 2, T<4→1, T=64→cap 30).
- `ua-start.sh`: DRYRUN K=2; реальный K=1 и **K=2** — два сервера на портах 5121/5122, пины ядер
  `0,1` и `4,5`, оба зарегистрированы char-сервером; раздельные `uAmap1/2.log`; graceful SIGTERM без
  рестарт-гонки.
- `ua-stop.sh map`: остановка по PID-файлу (без хрупкого pgrep по cmdline), оба инстанса гаснут, PID/lock чистятся.
- `rc.local`: раскладка ядер совпадает с `ua-mapcount.sh appcpus` для T=4/8/16/24/64.

## Замечания

- Наборы карт между confN **не должны пересекаться** (одна карта = один сервер).
- Перенос игрока между картами разных серверов делает char-сервер автоматически (inter-server).
- Гард двойного запуска супервизора — `flock` на `.ua-map.lock` (не зависит от cmdline).
