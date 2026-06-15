# SP3 группы D/E — выборочный апгрейд (только quest-log контент)

Финальная под-фаза SP3. Разведка показала: **подавляющее большинство тематических и job-квестов
(Kiel/Sign/Bard/cooking/gunslinger/ninja/doomed_swords/thana/Lvl4/Dandelion/2007_relay + first_class/
skills/newgears/quiz) НЕ используют quest-log даже в eathena** (0 setquest) — и uAthena их уже имеет.
Апгрейд таких = замена рабочих версий без выгоды для журнала → НЕ делаем.

Quest-log в D/E используют только два, их и берём:

## Что сделано

- **`collection/`** — 15 файлов, **новые для uAthena** (аддитивно) → `npc/backport/quests/collection/` +
  регистрация в `scripts_athena.conf`. Это **iRO Repeatable EXP Quests** (повторяемые квесты на убийство
  мобов за опыт): alligator, caramel, coco, creamy, demonpungus, dokebi, dryad, fabre, frilldora, goat,
  golem, hode, leafcat, pecopeco, pupa. Квест-NPC на классических полевых картах. 45 setquest → наполняют `@quests`.
- **`quests_airship`** — **АПГРЕЙД** на eathena-версию с quest-log (25 setquest). Старая регистрация
  `npc/quests/quests_airship.txt` отключена; активна `npc/backport/quests/quests_airship.txt`.

Покрытие quest_id: 66/66 в `quest_db.txt`. API-разрывов нет (движковые фиксы из B/A/C достаточны).

## Что НЕ трогали (осознанно)

Все прочие тематические/job-квесты остаются версиями uAthena (работают, quest-log им не нужен):
Kiel_Hyre, The_Sign_Quest, Bard_Quest, cooking_quest, gunslinger/ninja_quests, doomed_swords(_quest),
thana_quest, eye_of_hellion, Lvl4_weapon_quest, Dandelion_Request, 2007_relay, monstertamers, obb_quest,
counteragent_mixture, juice_maker, mrsmile, bunnyband + first_class/skills/newgears/quiz. F (seals/okolnir/
guildrelay = god-item/WoE:SE) — исключены.

## Валидация (dev-бокс с GRF)

`./map-server_sql --run_once`: сборка 0 ошибок; **Scripts +15** (все 15 collection-NPC загрузились),
0 `script error`, 0 «Could not parse», 0 `Duplicate user function`, 0 undefined-function. airship-карты
(airplane/airplane_01/einbech/ein_in01) присутствуют.

## Что проверять тестировщикам

1. `collection/`: найти квест-NPC на полевых картах (напр. «Langry#Fabre_Hunt» на gef_fild07), взять квест →
   `@quests` показывает; убить нужных мобов → награда (опыт) выдаётся; квест **повторяемый**.
2. **Баланс:** collection — повторяемый фарм опыта; оценить влияние на экономику опыта пре-12 сервера.
3. `quests_airship`: квестовая часть воздушного корабля (доступ/перелёты) работает; `@quests` отражает прогресс.
4. Перекрёстные ссылки на airship-NPC (другие NPC/варпы) — не сломаны апгрейдом (рантайм).

## Итог SP3

После D/E **весь quest-log контент пре-реневала перенесён**: классика+ep11-13 (апгрейд), Новый Мир (новое),
airship (апгрейд), collection (новое). Остаток квестов — рабочие версии uAthena без журнала (по дизайну).
