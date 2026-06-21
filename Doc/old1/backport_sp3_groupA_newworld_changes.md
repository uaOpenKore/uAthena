# SP3 группа A — бэкпорт квестовых NPC «Нового Мира»

Вторая под-фаза SP3 (после группы B — классические города). Группа A = регионы Нового Мира,
под которые мы уже сделали карты/варпы (бэкпорт карт) и базовые town-NPC (SP1).
Источник — `/tmp/eathena-ref/npc/quests/`.

## Что добавлено (контент)

3 файла дословно → `npc/backport/quests/` + регистрация в `npc/scripts_athena.conf` (блок «SP3 group A»):

- `quests_moscovia.txt` (16.5k строк, на переменных)
- `quests_brasilis.txt` (4.6k, 57 `setquest` → журнал)
- `quests_nameless.txt` (13.2k, 57 `setquest` → журнал; Nameless Island / Thanatos)

Все `quest_id` (65 шт.) покрыты `db/quest_db.txt`. Коллизий имён NPC с существующим контентом нет.

## Изменения движка (аддитивные)

- **`setnpcdisplay("<name>", <class>|<newname>{,<class>{,<size>}})`** — смена спрайта/имени NPC в рантайме
  (brasilis: квестовый Poring). Инлайн смены `class_` + refresh (`clif_clearunit_area`+`clif_spawn`).
  Аргумент size принимается, но игнорируется (у `npc_data` в uAthena нет поля size).
- **`readbook(<id>,<page>)`** — **no-op**: в клиенте 2007 нет окна книги; команда компилируется,
  квест продолжается через идущий следом `getitem` (nameless). Аддитивно, существующее не меняется.

## map_index

- Добавлен `mosk_que` (Moscovia quest-карта) — **append-only** (в конец, существующие индексы не сдвинуты).
  Раньше скрипт ссылался на неё → «Invalid map». Теперь зарегистрирована.

## Зависимость по доступу (важно)

**Доступ в Manuk/Splendide (ep14.1, Ash Vacuum) лежит в `quests_13_1.txt`/`quests_13_2.txt` — это группа C.**
Группа A даёт квесты Moscovia/Brasilis/Nameless; полный гейт входа в Manuk/Splendide появится с группой C.
Сами города Manuk/Splendide (town-NPC) уже есть из SP1.

## Валидация (dev-бокс с GRF /root/uAthenaGRF)

`./map-server_sql --run_once`: сборка 0 ошибок; **16210 NPC**, 0 `script error`, 0 «Could not parse»,
0 коллизий; покрытие quest_id полное.

> Ограничение dev-бокса: карты `mosk_que` НЕТ в .gat этого GRF → 7 NPC Moscovia на ней тихо пропускаются.
> На проде/у тестировщиков с полным клиентом (карта + mapindex синхронизированы) они загрузятся.
> Прочие карты Нового Мира грузятся.

## Что проверять тестировщикам (кластер + клиент)

1. Moscovia/Brasilis/Nameless: найти квест-NPC, пройти диалоги — без крашей.
2. Brasilis/Nameless: квест → `@quests` показывает; завершение → награда/статус корректны.
3. Brasilis: квестовый Poring (`setnpcdisplay`) меняет спрайт по ходу квеста.
4. Nameless: NPC с «книгой» (`readbook`) — окна нет (норм), но `getitem` (Research Note) срабатывает, квест идёт.
5. **mosk_que**: убедиться, что карта есть в клиентском GRF и mapindex синхронизирован → NPC на ней работают.
6. Регрессий по существующим NPC/квестам нет.

## Дальше по плану

Группа C (эпизоды 11-13, включая гейт доступа Manuk/Splendide) → D/E (тематические/job-линейки).
F (god-item/seals/okolnir + instance/BG) — исключены.
