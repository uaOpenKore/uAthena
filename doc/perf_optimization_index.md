# Перф-оптимизации map-server — мастер-индекс (для тестировщиков)

Единая точка входа по поэтапной оптимизации CPU map-server. Полный план: `doc/perf_subsystem_optimization_plan.md`
(+ секция «Сверка с rental/merc» в его конце). Цель: ~300 онлайн, pre-ep12 WoE/GvG, клиент 2007/PV7.

## Как это работает
- Каждая оптимизация — за своим конфиг-флагом (same-binary A/B): меряем `flag=0` vs `flag=1` в ОДНОЙ
  сборке на одинаковой нагрузке. Кросс-ранные % сравнения «рыхлые» — нужен честный A/B.
- Рисковые фазы едут дефолтом `0` (валидация тестировщиками → отдельный «flip default» коммит).
- Любой этап откатывается флагом=0 без пересборки.

## A/B-протокол (для каждой поведенческой фазы)
1. Одинаковый сценарий нагрузки (N ботов в кучу на GvG-карте + наёмники, `mob_ai:0x20`).
2. Один бинарник, под `UA_PERF=1` (профайлер уже включён по умолчанию).
3. `flag 0` → снять профиль → `flag 1` → снять профиль → сравнить self% целевого хотспота.
4. Проверить чек-лист корректности фазы (в её `doc/perf_stage*_changes.md`).

## Статус фаз
| Этап | Что | Флаг | Дефолт | Статус |
|------|-----|------|--------|--------|
| 0 | Харнесс: профайлер + рестарт-лимит + этот индекс | — | — | ✅ **СДЕЛАНО** (UA_PERF=1 в ua-start.sh; StartLimitIntervalSec=0 в .service; индекс — этот файл) |
| 1a | `SO_SNDBUF` (kernel send-буфер, против EAGAIN на WoE-бурсте) | `socket_sndbuf_size` | 0 | ✅ **СДЕЛАНО**: misc.conf `socket_sndbuf_size` (0=дефолт ОС; пробовать 131072–262144). Применяется на всех сокетах в setsocketopts. Замер: A/B 0 vs 262144 под WoE-бурстом (меньше EAGAIN-дрейнов в send-worker) |
| 1b | path_search scratch без 12КБ memset/вызов | `path_scratch_reuse` | 1 | план |
| 1c | `packet_db` hot/cold split + hoist len-лука | — | — | план |
| 2 | **skill_unit AoE**: per-map список + presence-гейт + LoS-кеш (главный пропущенный хотспот) | `skill_unit_active_maps_only`/`skill_unit_skip_noplayer`/`skill_unit_los_cache` | 1 | план |
| 3 | parse-shortlist (приём только по fd с данными) | `recv_parse_shortlist` | 1 | план |
| 4 | broadcast-кеши: зрители AREA / spawn-пакет / cloth_color | `clif_area_viewer_cache`/`clif_spawn_packet_cache`/`clif_clothcolor_inline` | 0→1 | план |
| 5 | send-структура: freelist чанков / writev / refcount-буфер | `send_chunk_freelist`/`send_worker_writev`/`send_refcount_broadcast` | 0→1 | план |
| 6 | battle per-hit кеш mastery/base-damage | `battle_mastery_cache` | 0→1 | план |
| 7 (отл.) | delta-пересчёт `status_calc_pc` на свапе экипа | `status_calc_pc_delta` | 0 | отложен (high risk) |
| доп. | throttle merc-AI auto-aggro / live-merc список | (TBD) | — | низкий приоритет (только если профиль покажет merc-AI заметным) |

Рекомендуемый порядок: 0 → 1 → 2 → 3 → 4 → 5 → 6. Перед рисковыми (4/5/6) — baseline-профиль тестировщиков.

## Уже в проде (НЕ переделывать — из прошлых пассов)
epoll event-loop; off-thread send-worker + коалесинг (`socket_async_send:1`, `socket_send_coalesce_ms:10`
в misc.conf); async SQL log writer + async_db; mob-AI 0x20 опты (livemob/mobgrid/skip-noplayer/active-maps/
probe-cache); natural-heal на map_foreachpc; RNG-модуль. Подробности — в плане.

## Перед стартом фаз 1+
Желательно: тестировщики снимают **baseline-профиль** (0x20 + игроки + наёмники + rental в обороте),
чтобы (а) измерять эффект честно и (б) увидеть, не доминирует ли что-то неожиданное после rental/merc
доделок. Заодно — live-верификация rental + merc-ядра + merc-скиллов (всё это пока проверено только сборкой).
