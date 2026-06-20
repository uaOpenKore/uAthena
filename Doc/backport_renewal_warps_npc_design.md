# Дизайн: бэкпорт renewal-варпов и town-NPC (rAthena → uAthena)

Статус: ДИЗАЙН СОГЛАСОВАН (brainstorming). Реализация — после плана (writing-plans).
Ветка: x64. Автор фиксации: Claude Opus 4.8.

## 1. Цель

Сделать 6 renewal-зон, уже зарегистрированных в `db/map_index.txt`, **функциональными**:
добавить статические варпы (проходимость) и town-NPC (транспорт, кафры, торговцы,
гиды, флейвор). Это продолжение многофазного порта renewal→pre-renewal контента
(локации/варпы из eAthena — DONE; мобы/карты из rAthena — DONE; NPC SP1-SP3 — DONE).

Принцип всех фаз: **additive, данные, без новых игровых механик; новый синтаксис
адаптируется под старый движок uAthena, существующий script-API не ломается.**

## 2. Источник

rAthena commit `7f080871c8b3bbe7a79027194633201c63422ee1` (2026-06-18), тот же,
что использован для мобов/карт. Доступ: `/tmp/rathena-ref` (blob:none + sparse).
`npc/re/` материализуется расширением sparse-checkout; тело blob'ов тянется сетью
через `git show HEAD:<path>` (проверено).

## 3. Scope (6 зон, уже в map_index)

| Зона        | Карты-города          | Файл варпов (cities)         | Файл town-NPC (cities) |
|-------------|-----------------------|------------------------------|------------------------|
| Dewata      | dewata                | warps/cities/dewata.txt      | cities/dewata.txt      |
| El Dicastes | dicastes01, dicastes02| warps/cities/dicastes.txt    | cities/dicastes.txt    |
| Eclage      | eclage, ecl_hub01     | warps/cities/eclage.txt      | cities/eclage.txt      |
| Malangdo    | malangdo              | warps/cities/malangdo.txt    | cities/malangdo.txt    |
| Malaya      | malaya                | warps/cities/malaya.txt      | cities/malaya.txt      |
| Mora/Bifrost| mora                  | warps/fields/bif_fild.txt    | cities/mora.txt        |

Плюс scope-поля/данжи варпов: `warps/fields/dic_fild.txt`,
`warps/dungeons/{dic_dun,ecl_dun,ecl_tdun}.txt`.
Генератор отбирает варпы по **scope-карте на любом конце** (как pre-renewal),
поэтому ручной перечень файлов не критичен — фильтр подберёт всё по картам.

### Объёмы (факт, сосчитано из источника)

- **Статические варпы**: **149** в 10 scope-файлах. **`warp2` = 0** (в scope нет).
- **Town-NPC (cities/)**: **156 script + 33 duplicate = 189 сущностей**, **4555**
  строк, 6 файлов (script/duplicate: dewata 47/3, dicastes 36/0, eclage 4/1,
  malangdo 8/15, malaya 23/11, mora 38/3). Все 33 duplicate-базы определены
  **внутри** этих же файлов; внешних callfunc-зависимостей у town-NPC нет.
- **Non-warp сущности ВНУТРИ warp-файлов** (≈20 script + 16 duplicate + 1 function):
  это **транспорт, критичный для проходимости**, который генератор только-варпов
  потерял бы. А именно:
  - `warps/cities/dicastes.txt`: `Elevator#main` + **13 duplicate** = лифты
    (связь уровней dicastes01↔dicastes02) + script `#eldicastes0016`.
  - `warps/fields/bif_fild.txt`: `bifrost_field0000` + **3 duplicate** =
    "Small Hole" порталы Mora↔Bifrost.
  - `warps/cities/malaya.txt`: 15 script (inn/ws/ts/shop/house + 9 jeepney
    `Town Warp#zif`) + `function F_Malaya_Warp` (определена в этом же файле).
  - `warps/cities/eclage.txt`: 2 script (hub-навигация).
  - **Все базы `duplicate` определены в тех же файлах** → порядок загрузки
    внутрифайловый, внешних duplicate-зависимостей нет.
- **Кафры scope-зон** живут в отдельном `npc/re/kafras/kafras.txt` (НЕ в town/warp
  файлах): `kaf_dewata`, `kaf_malaya1/2` и др. (sprite `4_F_KAFRA1`/`4_MAL_KAFRA`,
  новый `::kaf_*`-API). Нужны для функциональности (storage/save/teleport) →
  **R3-вход расширяется** на kafra-записи scope-карт из этого файла, адаптируемые
  через `kafra_duplicates()`→`duplicate(kaf_alberta)` (прецедент SP1).

### Измеренный token-gap (факт, не оценка)

uAthena buildins = 330, rAthena = 671. **Command-gap (parse-fatal) = 15 buildins**,
использованных в scope, большинство ≤3 раз. Классификация по стратегии §4.3:
- **Группа A (заглушка no-op, безвредно на PV7)**: `sit`, `stand`, `clear`,
  `cooking`, `transform`.
- **Группа B (adapt на старый API)**: `consumeitem <id>;`→`delitem <id>,1;`;
  `ET_*`-emotion-конст → числовой emotion-код (uAthena имеет те же id под `e_*`);
  `charat`/`floor`/`round`/`getargcount` — точечные замены.
- **Группа C (comment + log, функция теряется)**: `getnpcid` (24x, 2-арг
  `getnpcid(0,"name")` для unit-команд — самый тяжёлый; `unittalk`/`unitemote`/
  `unitwarp`/`donpcevent` в uAthena ЕСТЬ, отсутствует только `getnpcid`),
  `getgroupitem`, `vip_status`, `is_party_leader`, `kick` — по 1 разу.
`duplicate` (49x) — **не gap** (NPC-конструкция движка, uAthena поддерживает).
Генератор детектит gap токен-санитайзером (`script_is_safe`, прецедент
backport-renewal-cards.py), применяет дефолтную стратегию группы, логирует в
gap-лог; человек ревьюит лог и переопределяет при необходимости.

### Локации (фаза R1) — проверено: 0 добора

Все endpoint-карты scope-варпов и все 6 зон **уже присутствуют** в uAthena
`db/map_index.txt` (dicastes01/02, ecl_fild01, ma_scene01, ma_zif01-09, mora,
bif_fild01/02 и т.д.). Renewal-карты были добавлены в map_index прошлой фазой
(map_index-only). **R1 = верификационная фаза**: подтвердить endpoint-полноту,
добор только если генератор варпов выявит незарегистрированный конец, который
**сам является scope-картой** (=зона реально забыта в map_index).

**Boundary-исключение (эмпирически, dry-run):** один rAthena-хаб —
`dimensional_gap.txt` (карта `dali`, эпизод 14.3) — содержит варпы в scope-карты
(`dali→bif_fild01`, `dali→dic_fild02`), но сам `dali` **отсутствует** в uAthena
map_index. По концепции §3 «0 новых карт» такие варпы (незарегистрированный
endpoint ВНЕ 6 зон) **пропускаются + логируются** как boundary, а НЕ добавляются
и НЕ требуют добора. Подтверждено: 139 варсов добавляется, 2 boundary-skipped
(оба `dali`), 0 реальных незарегистрированных scope-концов. `dali`-хаб —
кандидат на отдельную будущую единицу (как Arunafeltz в pre-renewal), вне этой фазы.

## 4. Технические решения

### 4.1 warp2 → warp (адаптация, 0 правок движка)

Движок uAthena (`npc.c` диспетчер парса) знает только `warp`; `warp2`
(невидимый портал) упал бы в ошибку парса. Генератор конвертирует `warp2`→`warp`
(телепорт идентичен, портал становится видимым — косметика) и логирует.
В scope `warp2` = 0, поэтому это **защитная мера** на случай, если scope-фильтр
подберёт `warp2` из общего файла. Движок не трогаем (data-only линия порта).

### 4.2 Merge-правило варпов (как pre-renewal)

Варп rAthena, чьё **имя NPC ИЛИ исходный тайл (map,x,y)** уже есть в uAthena →
**сохраняем uAthena без изменений**, пишем конфликт; иначе **добавляем** в
изолированное дерево. Конфликты → `Doc/backport_renewal_warp_conflicts.md`
(схема `ВХОД/ВЫХОД … решение?`, тестеры заполняют) — **отдельный файл**, чтобы
не затирать pre-renewal `doc/backport_warp_conflicts.md`.

### 4.3 Адаптация синтаксиса town-NPC (приоритет b → a → c)

Gap-анализ токенов (как в card/NPC-фазах): токен валиден ⇔ в `const.txt` ∪
билдины `script.c` ∪ скиллы `skill_db.txt` ∪ keywords. Неизвестные токены →
адаптация по приоритету:

- **(b) рефактор на старый uAthena API** — предпочтительно. Пример: Kafra
  5-арг → 3-арг `duplicate(kaf_alberta)` (прецедент SP1).
- **(a) заглушка-buildin (no-op)** — если команда безвредна на клиенте PV7
  (прецедент SP3: `readbook`, `progressbar`).
- **(c) закомментировать NPC + лог** — крайний случай, если команда критична
  и аналога нет (faithful-порт; тестеры решают по логу).

Все адаптации/заглушки/комментирования → `Doc/backport_renewal_npc_gap.md`.
Предварительные кандидаты на gap (уточняется в реализации): `checkweight`,
`getgroupitem`, `vip_status`, `consumeitem`, Kafra-функции.
Уже поддерживается движком uAthena: `callfunc(...)`, `.@`-scope-vars, `warp`,
`setquest`/`completequest`, `strnpcinfo "v"`, `/* */`-комментарии,
`input` min/max, `setnpcdisplay`.

### 4.4 Разделение входов R2/R3 (warp-файлы содержат не только варпы)

Scope warp-файлы rAthena содержат `warp` + `script`/`function`/`duplicate`
(транспорт, см. §3). Поэтому входы фаз режут одни файлы по типу сущности:

- **R2 (варпы)** — `parse_warp` извлекает **только `\twarp\t`-строки** из всех
  scope warp-файлов → `npc/warps/backport/re/`.
- **R3 (NPC)** — обрабатывает town-файлы `cities/<zone>.txt` **ПЛЮС все non-warp
  сущности** (`script`/`function`/`duplicate`) из scope warp-файлов → gap-анализ
  и адаптация → `npc/backport/re_cities/`. Базы duplicate внутрифайловые, порядок
  сохраняется при портировании блока целиком.

**Проходимость**: в Malaya статические jeepney-варпы `ma_zif*` в rAthena
**закомментированы**; транспорт реализован скрипт-NPC `Town Warp#zifXX` через
`callfunc "F_Malaya_Warp"`. Лифты Dicastes и Small Hole Mora — тоже script/
duplicate, не варпы. То есть проходимость части зон обеспечивается town-NPC (R3),
а не варпами (R2). `parse_warp` корректно пропускает `//`-строки, так что
закомментированные `ma_zif`-варпы в R2 не попадут.

### 4.5 Изоляция (append-only, отдельные блоки от pre-renewal)

- Варпы → `npc/warps/backport/re/{cities,fields,dungeons}/<file>.txt`;
  include-блок в `npc/scripts_warps.conf`
  (`// ===== Backport renewal warps (GENERATED) =====`).
- Town-NPC → `npc/backport/re_cities/<зона>.txt` (+ извлечённые Kafra-дубликаты);
  include-блок в `npc/scripts_athena.conf`
  (`// ===== Backport renewal town-NPCs (GENERATED) =====`).
- Вывод генераторов — **UTF-8**, тело скриптов ASCII. cp1251-файлы (`Non-ISO`)
  не редактируются (Edit/Write их ломает — кириллица → U+FFFD).

## 5. Верификация (что доступно без клиента)

1. `--selftest` обоих генераторов (фикстуры merge-правил и санитайзера токенов).
2. `--verify` — уникальность имён варпов + отсутствие коллизий тайлов по всему
   `npc/` (включая оба backport-дерева).
3. **map_index endpoint-полнота** — каждый dstmap добавленного варпа и каждая
   карта-носитель town-NPC обязаны быть в `db/map_index.txt`.
4. **Парс-чистота** — локальная загрузка map-сервера (local-cluster-boot-test,
   GRF-symlink, `--run_once`): 0 script-error на добавленных файлах.
5. **Gap-лог** — полный список адаптированных/заглушенных/закомментированных
   команд.

За тестерами (нужен клиент): фактическая проходимость варпов, диалоги NPC,
транспорт, баланс торговцев. `.gat` новых карт — деплой-забота (карты читаются
из GRF; на dev-боксе `*.gat not found` для ВСЕХ карт — ожидаемо, не связано).

## 6. Декомпозиция на фазы (каждая — отдельный коммит, изолированно)

- **R1 — локации (фундамент, малый)**: sparse-checkout `npc/re/`; верификация
  endpoint-полноты всех scope-карт; добор map_index только если выявлен
  незарегистрированный конец (ожидается 0).
- **R2 — статические варпы**: генератор на базе `dumps/forge/backport-warps.py`
  (источник rAthena, **только `warp`-строки**, warp2→warp, merge-правило,
  конфликт-лог `Doc/backport_renewal_warp_conflicts.md`); вывод
  `npc/warps/backport/re/`; `--verify` + endpoint-полнота; локальный boot-парс.
- **R3 — town-NPC**: генератор town-NPC; вход = `cities/<zone>.txt` **ПЛЮС
  non-warp сущности из scope warp-файлов** (§4.4); gap-анализ → адаптация b/a/c,
  Kafra→`duplicate(kaf_alberta)`; вывод `npc/backport/re_cities/`; gap-лог
  `Doc/backport_renewal_npc_gap.md`; локальный boot-парс.

## 7. НЕ в scope (структурно исключено)

instances (`1@`/`2@`), Battlegrounds, WoE:TE (`te_*`), 3rd/4th-job, новые карты
(0 добавляется — только активация уже зарегистрированных зон). Движков
`instance.c`/`battleground.c` в uAthena нет (явно вне scope, как в pre-renewal).

## 8. Гочи и риски

- **Cline Bot** (`<bot@pechsoft.com>`) пушит x64 → перед push всегда fetch+rebase.
- Генератор пишет UTF-8; при индексации uAthena-варпов **исключать** `/backport/`
  (иначе self-collision на повторном прогоне).
- Shell здесь `set -e`+`pipefail` → `pgrep`/`pkill` с кодом 1 рушит скрипты
  (`set +e`); не `pgrep -f` по строке, совпадающей с собственным cmdline.
- map_index позиционный, append-only — существующие индексы НЕ сдвигать.
- Town-NPC могут ссылаться на quest/achievement, добавленные в SP2/SP3 — проверить,
  что зависимости уже в движке (иначе gap-комментирование).
