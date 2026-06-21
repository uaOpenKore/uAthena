# SP-3 Small renewal NPC — изменения

Источник: rAthena `7f08087`. Ветка x64. 0 правок движка. Под-проект 3 роадмапа
`Doc/backport_renewal_content_roadmap.md` (порядок 1→3→2). Переиспользует SP-1 активы.

## Добавлено

`npc/backport/re_other/` (20 файлов), генератор `dumps/forge/backport-renewal-smallnpc.py`
(собран = town-npcs adapt_text + merchant block_filter/orphan/existing-index + small-NPC tail).
Подключение: `npc/scripts_athena.conf` (20 includes) + `conf/maps_athena.conf` (scope-карты).

- **guides** (7 новых зон): dewata, dicastes, eclage, malangdo, malaya, mora, rockridge.
- **other** (12 IN): TrainingZone123, adven_boards, dimensional_gap, item_merge, kachua_key,
  mail, pvp, resetskill, stone_change, turbo_track, bulletin_boards, global_npcs.
- **taekwon** (expanded 2nd-class).

## События адаптации

ADAPT 37 (синтаксис-классы), BOUNDARY 56 (NPC на картах вне map_index — `dali`/renewal-данжи),
DEDUP 72 (дубли существующих uAthena-NPC → skip), UNRESOLVED 4 + ORPHAN 4 + MANUAL/COMMENT
(renewal-функции/broken-синтаксис закомментированы). Полный лог — `Doc/backport_renewal_smallnpc_gap.md`.

**dimensional_gap**: NPC на карте `dali` → BOUNDARY-comment. Завершает оставленный dali-boundary
из [[backport-renewal-warps-npc]] (dali-хаб остаётся отдельной будущей единицей).

**adven_boards** (3335, adventure-board renewal): многострочные `= callfunc("F_AvenBoard",`
+ undefined F_AvenBoard → block-comment (multiline-call BROKEN). Глубоко renewal, faithful-выпал.

## Известные ссылки (informational, не parse-error)

- `pvp.txt` → `callfunc "F_PVP_FSRS"` (PVP-ladder функция, отсутствует в uAthena) — runtime-ref,
  не ломает парс; для будущего порта Global_Functions (под-проект уровня other).
- `charat`/`mergeitem`/`mesitemlink`/`mail` — нет аналога → затронутые блоки закомментированы.

## Верификация

- Генератор `--selftest`/`--verify` **OK** (0 live-gap/unreg/brace).
- Merchant re-gen после общего block_filter-улучшения (multiline-call) — verify OK, 0 регрессии.
- Финальный boot `--run_once`: **0 total script errors**, 16408 NPCs, Server ready.

## За тестерами (нужен клиент + GRF)

`.gat` renewal-карт guides (новые зоны) + `dali` (dimensional_gap) в GRF; достижимость,
диалоги. F_PVP_FSRS + adven_boards/charat-блоки — для будущего движкового/Global_Functions порта.
