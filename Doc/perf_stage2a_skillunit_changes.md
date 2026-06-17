# Perf Этап 2a — live skill-unit индекс для skill_unit_timer

## Что изменилось
`skill_unit_timer` (тик наземных AoE/ловушек/стен, раз в 100мс) раньше звал
`map_foreachobject(BL_SKILL)`, который **сканирует весь глобальный массив `objects[]`**
(floor-items + skill-units + …, до `last_object_id`) каждый тик, фильтруя по типу. Под WoE
там сотни floor-items и AoE-клеток → дорогой полный проход 10 раз/сек.

Теперь поддерживается **плоский индекс живых skill-units** (`liveskillunit.c`, зеркало
`livemob.c`): непрерывный массив указателей, O(1) swap-remove, слот кешится в самом юните
(`skill_unit.liveskillunit_idx`). `skill_unit_timer` итерирует **только живые юниты**, а не весь
`objects[]`.

**Поведение идентично** — те же юниты, тот же `skill_unit_timer_sub`, тот же порядок;
снапшот под `map_freeblock_lock` (фри `group->unit` отложен туда же → указатели снапшота живут
весь проход), `idx<0` skip при удалении в процессе прохода. Регистрация — в `skill_initunit`
(после `map_addblock`, по переходу dead→alive), снятие — в `skill_delunit` (по `alive=0`).

## Флаг
`conf/battle/skill.conf`:
```
skill_unit_live_list: yes   // yes (деф.) = live-индекс; no = старый map_foreachobject скан
```
Меняется на лету через `@reloadbattleconf`. Это **A/B-переключатель производительности** в одном
бинарнике (поведение одинаковое, меняется только способ обхода).

## Как замерить (A/B)
Одинаковая нагрузка (боты в куче, AoE-спам / WoE) под `UA_PERF=1`:
1. `skill_unit_live_list: no` + `@reloadbattleconf` → снять профиль → доля `map_foreachobject` /
   `skill_unit_timer`.
2. `skill_unit_live_list: yes` + `@reloadbattleconf` → снять профиль.
3. Сравнить self% `skill_unit_timer` / исчезновение `map_foreachobject` из горячих.
Ожидание: проседает проход по `objects[]` (тем сильнее, чем больше floor-items/юнитов на картах).

## Чек-лист корректности
- [ ] Наземные AoE тикают как раньше (Storm Gust / Lord of Vermillion / Heaven's Drive наносят урон).
- [ ] Ловушки срабатывают и исчезают по таймеру; предмет-ловушка возвращается (PC, не into_abyss).
- [ ] Стены/зоны живут и истекают: Safety Wall, Pneuma, Land Protector, Ice Wall, Basilica.
- [ ] Песни/танцы (dance overlap) корректны.
- [ ] Массовая смерть юнитов в один тик (AoE накрывает кучу) не крашит.
- [ ] Смена карты/выход игрока — юниты живут штатно; `no` и `yes` дают одинаковый игровой результат.

## Откат
`skill_unit_live_list: no` + `@reloadbattleconf` (или в conf) — мгновенно вернуться к
`map_foreachobject`, без пересборки.

## Тест
Standalone ASan/UBSan: `test_liveskillunit.c` (swap-remove, foreach, удаление в проходе, varargs
tick). Не входит в `make sql`. Сборка/прогон:
```
gcc -DLIVESKILLUNIT_TEST -fsanitize=address,undefined -I src/map -o /tmp/test_liveskillunit \
    src/map/liveskillunit.c src/map/test_liveskillunit.c && /tmp/test_liveskillunit
```
→ `test_liveskillunit: ALL PASS`. Сборка `make` чистая, локальный буст кластера чистый (без утечек).

## Дальше (Этап 2b/2c)
- 2b: player-presence гейт (`block_pc_count` грид) — пропуск AoE-скана юнита, если рядом нет PC.
- 2c: LoS-мемоизация `path_search_long` в `map_foreachinshootrange` — главный WoE-выигрыш.
