# Перф-оптимизации map-server — мастер-индекс (для тестировщиков)

Единая точка входа по поэтапной оптимизации CPU map-server. Цель: ~300 онлайн, pre-ep12 WoE/GvG,
клиент 2007/PV7. Этот файл — актуальный (этапы 1–7 завершены). Подробности каждого этапа — в его
`Doc/perf_stage*_changes.md`.

## Как это работает
- Каждая оптимизация — за своим конфиг-флагом (**same-binary A/B**): меряем `flag=0` vs `flag=1` в
  ОДНОЙ сборке на одинаковой нагрузке. Кросс-сборочные/кросс-ранные % сравнивать нельзя — только честный A/B.
- Любой этап откатывается флагом без пересборки (`@reloadbattleconf` где поддержано, иначе рестарт map).
- **Все флаги сейчас по умолчанию ВКЛ** (по решению владельца — чтобы тестировщики гоняли в бою).

## A/B-протокол (для каждого этапа)
1. Одинаковый сценарий нагрузки: N ботов в кучу на GvG/WoE-карте + наёмники, `mob_ai:0x20`.
2. Один бинарник, под `UA_PERF=1` (профайлер включён по умолчанию в `ua-start.sh`).
3. `flag 0` → снять профиль (perf) → `flag 1` → снять профиль → сравнить self% целевого хотспота.
4. Прогнать чек-лист корректности этапа (в его `Doc/perf_stage*_changes.md`).

## Как снять baseline-профиль (нужен ПЕРЕД дальнейшими решениями)
1. Поднять кластер, загнать ботов в типичную боевую кучу (WoE-замок), `mob_ai:0x20`, наёмники в обороте.
2. `UA_PERF=1` (уже дефолт). Дать поработать под нагрузкой, снять `perf`-профиль map-server.
3. Прислать топ функций по self% (game-thread И воркер-thread). Это покажет ДОМИНИРУЮЩИЙ расход
   (ожидание по прошлым замерам — сетевое ядро: `sendto`/qdisc) и продиктует, что делать дальше
   (в т.ч. оправдан ли крупный io_uring-проект).

## Статус этапов (всё СДЕЛАНО)
| Этап | Что | Флаг (файл) | Дефолт | Поведение | Док |
|------|-----|-------------|--------|-----------|-----|
| 1a | `SO_SNDBUF` (kernel send-буфер; меньше EAGAIN на WoE-бурсте) | `socket_sndbuf_size` (misc.conf) | **131072** | идентично | — |
| 1b | A* path-scratch gen-stamp (нет ~16КБ memset на fallback) | — (всегда) | — | идентично | — |
| 2a | live-индекс skill-units (вместо скана global objects[]) | `skill_unit_live_list` (skill.conf) | yes | идентично | perf_stage2a_… |
| 2b | пропуск AoE-скана юнита без игроков рядом | `skill_unit_skip_noplayer` (skill.conf) | yes | идентично | perf_stage2b_… |
| 2c | кеш LoS (path_search_long; неизменен на карту) | `skill_unit_los_cache` (skill.conf) | yes | идентично | perf_stage2c_… |
| 3 | recv parse-shortlist (парсить только fd с данными) | `recv_parse_shortlist` (misc.conf) | 1 | идентично | perf_stage3_… |
| 4a | AREA-broadcast пропускает блоки без игроков | `clif_bcast_pc_grid` (misc.conf) | 1 | идентично | perf_stage4_… |
| 5a | пул send-буферов воркера (вместо malloc/free на пакет) | `socket_send_pool` (misc.conf) | 1 | идентично (ASan+TSan ✓) | perf_stage5_… |
| 6 | кеш weapon-mastery в status_calc_pc | `weapon_mastery_cache` (misc.conf) | 1 | идентично | perf_stage6_… |
| 7 | отложенный (коалесц.) пересчёт status_calc_pc на equip-swap | `status_calc_defer` (misc.conf) | 1 | **МЕНЯЕТ поведение** ⚠ | perf_stage7_… |

⚠ **Этап 7 — единственный неидентичный.** OnEquip/OnUnequip-скрипты и проверка SignumCrucis ~1 тик
видят старые статы. Если хоть один предмет полагается на OnEquip-статы — ставить `status_calc_defer: 0`
(остальные этапы не затронуты). Детали — `Doc/perf_stage7_status_calc_defer_changes.md`.

## Уже в проде (НЕ переделывать — из прошлых пассов)
epoll event-loop; off-thread send-worker + коалесинг (`socket_async_send:1`, `socket_send_coalesce_ms:10`);
async SQL log writer + async_db; mob-AI 0x20 опты (livemob/mobgrid/skip-noplayer/active-maps/probe-cache);
natural-heal на map_foreachpc; центральный RNG (xoshiro256**).

## Что дальше (по решению — после baseline-профиля)
Все **код-сайд per-tick хотспоты устранены**. Этапы 6/7 по факту целились не в горячие места (анализ —
`Doc/perf_stage6_7_decision.md`). Реальный оставшийся рычаг — **сетевое ядро**:
- `socket_sndbuf_size` — поднят до 131072; на пробу до 262144 под тяжёлой WoE.
- **io_uring** для send-пути — единственный способ заметно срезать syscall/qdisc-оверхед. Крупный
  отдельный многосессионный проект; **начинать только если baseline-профиль подтвердит, что сеть-ядро
  доминирует.** Ядро 6.1 на боксе это поддерживает.
- Ops-сторона: многоочередь virtio-net + RPS/XPS, apparmor unconfined.
Принцип: дальше оптимизируем **измеренное**, а не предполагаемое → сначала профиль (см. выше).

## Все perf-флаги в одном месте (для быстрого A/B)
`conf/battle/misc.conf`: `socket_async_send`, `socket_send_coalesce_ms`, `socket_sndbuf_size`,
`socket_send_pool`, `recv_parse_shortlist`, `clif_bcast_pc_grid`, `weapon_mastery_cache`, `status_calc_defer`.
`conf/battle/skill.conf`: `skill_unit_live_list`, `skill_unit_skip_noplayer`, `skill_unit_los_cache`.
