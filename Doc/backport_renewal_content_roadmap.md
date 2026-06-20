# Карта декомпозиции: бэкпорт renewal quests/NPC/shops (rAthena → uAthena)

Статус: КАРТА СОГЛАСОВАНА (brainstorming). Это роадмап серии под-проектов; каждый
получает свой цикл brainstorm→spec→plan→impl. Ветка x64. 0 правок движка (data + NPC).

Источник: rAthena `7f080871c8b3bbe7a79027194633201c63422ee1` (2026-06-18), `/tmp/rathena-ref`,
`npc/re/`. Продолжение серии: [[prerenewal-npc-backport]], [[backport-renewal-warps-npc]],
[[backport-renewal-mobs]].

## Цель

Бэкпортировать renewal-контент NPC из rAthena — **магазины, мелкие NPC, квесты** — в uAthena
(pre-renewal форк), адаптируя синтаксис скриптов под старый движок. Объём источника
`npc/re/` ≈ 270K строк → серия под-проектов, не один spec.

**Порядок реализации (решение пользователя): 1 → 3 → 2** (магазины, затем мелкие NPC,
затем квесты как самые объёмные).

## 1. Engine-границы (OUT — диктуется движком uAthena)

uAthena = pre-renewal форк; следующее **структурно недоступно** (нет движка/механики):

| Категория OUT | Объём | Причина |
|---|---|---|
| instances (`instances/`) + instance-квесты | 48 файлов | нет `instance.c` |
| квест-эпизоды 14.3–18 (`quests_14_3..18`) | 9 файлов, 64.6K | instance-gated |
| 3rd-job квесты (`jobs/` 3-1/3-2) | 19 файлов, 40K | нет 3rd-job классов (`JOB_RUNE_KNIGHT`=0) |
| doram (`spirit_handler`), academy/novice-tutorial | 3 файла, ~18K | нет doram/renewal-tutorial |
| barter-магазины | 16 `.yml` | нет `openbarter`/`barteropen` |
| `clans.txt` | 632 | нет clan-движка (`clan.c` absent) |
| `achievements.txt` | 543 | overlap — uAthena своя реализация (done) |
| `guides_woe_te`, BG | — | нет WoE:TE / battleground |
| cash-shop merchants (`cashmall`, `cash_trader`) + 2 3rd-job merchants | 4 файла | нет cash-points / 3rd-job |
| `marketshop`/`cashshop`/`pointshop` сущности | per-entity ~57 | npc.c не поддерживает → adapt→`shop` или skip+log |
| base-job квесты (acolyte/thief/mage/…) | — | дублируют существующие uAthena |

Остаётся: **town/field/collection/zone-контент на pre-renewal движке**.

## 2. Под-проекты (числа IN)

### SP-1 — Магазины (фаза 1) · ~23.8K строк · 55 файлов

55 IN из 59 merchant `.txt` (4 OUT: cash-shop ×2, 3rd-job ×2). Barter `.yml` (16,
в `merchants/barters/`) — отдельно OUT (§1).
- refiners: refine/hd/blessed/advanced/shadow/ticket
- enchanters: mora 1.8K, verus 1.4K, mal, ko, rockridge, illusion_dungeons, upg, edda, sage
- exchanges: coin, card, gld_mission, ghost_palace, moro_cav
- shops: eden_market 2K, malangdo_costume 1.5K, nightmare_biolab 2.1K, shops.txt, …
- **per-entity**: `marketshop`(44)/`cashshop`(13) → `shop` adapt или skip+log

### SP-3 — Мелкие NPC (фаза 2) · ~10K IN

- **guides**: 7 новых (dewata/dicastes/eclage/malangdo/malaya/mora/rockridge) + navigation;
  ~25 — дубли существующих городов (skip/merge по имени)
- **other IN**: adven_boards 3.3K, dimensional_gap 568 (хаб `dali` — закрывает boundary
  из [[backport-renewal-warps-npc]]), TrainingZone, resetskill, stone_change, item_merge,
  pvp, turbo_track, bulletin/global/mail
- **other OUT**: clans, achievements, CashShop_Functions, mercenary_rent (merc done)
- **jobs**: только `taekwon` (9 строк, expanded 2nd-class) — подобрать здесь; остальное OUT/дубли

### SP-2 — Квесты (фаза 3) · ~100K IN · дробится на 4 под-фазы

| Под-фаза | Содержимое | ~строк |
|---|---|---|
| 2a Zone-quests | eclage 17K, malangdo 11K, malaya 9K, dicastes 8K, rockridge 7K, mora 5K, dewata 2K | ~59K |
| 2b Eden Group | 16 файлов: hub (eden_quests 4.4K), tutorial, exp-цепочки по уровням | ~13.5K |
| 2c Dungeon/collection | illusion_dungeons 13K, juno_monster_society 4K, garden_of_time, homun_s, magic_books, dungeons_200, HelpMeShorty | ~25K |
| 2d Simple/misc | ninja_quests, cupet, cooking, pile_bunker, mrsmile, простые town-квесты | ~2K |

OUT (повтор из §1): 9 episode-файлов (14.3–18, 64.6K) — instance-gated.

## 3. Подход и зависимости

**Генератор-адаптер** (переиспользуется из [[backport-renewal-warps-npc]]): `adapt_text` с
синтаксис-классами `=→set` / `++`/`--` / `enablenpc()→strnpcinfo(0)` / `charat`/string-literal
guard / SITEFIX / BOUNDARY, byte-preserving latin-1, token-gap-санитайзер (gap=rAthena−uAthena
buildins), `collect_used_scope_maps`. На каждую категорию — свой генератор
(`dumps/forge/backport-renewal-{merchants,smallnpc,quests-XX}.py`) с category-спецификой:
- **merchants**: shop-семейство; `marketshop`/`cashshop`→`shop` adapt или skip
- **quests**: проверить потребность в новых записях `db/quest_db.txt` (renewal quest-ID)

**Изоляция**: `npc/backport/re_{merchants,other,quests}/`; append-only подключение в
`scripts_athena.conf` + `conf/maps_athena.conf` (урок: карты грузятся оттуда, не из map_index).

**Верификация (каждый под-проект)**: `--selftest`/`--verify` + **boot-parse `--run_once`**
(обязателен — выявляет операторные/синтаксис-gap, которые токен-санитайзер пропускает).
`.gat` renewal-карт в GRF = tester/deploy.

**Зависимости (обосновывают порядок 1→3→2):**
- SP-1 магазины — независимы.
- SP-3 мелкие — независимы (some other мягко ссылается на квесты).
- SP-2 квесты — зависят от quest-log (done) + ссылаются на торговцев (SP-1) и zone-NPC (done)
  → идут последними, чтобы награды/торговцы/NPC резолвились.

**Опора на готовое**: quest-log (SP2), 6 renewal town-зон, renewal `mob_db` (квест-цели),
achievements (done), `maps_athena.conf` урок.

## 4. Статус

- [x] Карта декомпозиции (этот документ)
- [ ] SP-1 Магазины
- [ ] SP-3 Мелкие NPC (guides + other + taekwon)
- [ ] SP-2a Zone-quests
- [ ] SP-2b Eden Group
- [ ] SP-2c Dungeon/collection
- [ ] SP-2d Simple/misc

Каждый под-проект: отдельный brainstorm→`Doc/backport_renewal_<sp>_design.md`→plan→impl→push.
