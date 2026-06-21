# Renewal-бэкпорт: известные runtime-ограничения (для тестеров)

Серия бэкпорта renewal-контента (SP-1 merchants / SP-3 small-NPC / SP-2 quests 2a-2d)
ЗАВЕРШЕНА. Boot parse-чист (0 ошибок парсинга по всем `npc/backport/re_*`). Ниже —
известные **runtime**-ограничения: NPC грузятся, но отдельная функциональность деградирует.
Это НЕ parse-ошибки и НЕ блокируют сервер. Решение по каждому — «оставить + документировать»
(одобрено 2026-06-21).

## 1. NAME_LENGTH=24 — 7 NPC с длинным base-именем не спавнятся через duplicate

`src/common/mmo.h NAME_LENGTH 24` (23 символа + null). NPC-имя длиннее обрезается при
регистрации, а `duplicate(полное_имя)` ищет необрезанное → `bad duplicate name (not exist)`.
На проде та же ситуация (НЕ deploy-артефакт).

| Base-NPC | Где | Эффект |
|---|---|---|
| `Carbonated Water Vending Machine#ra` | `re_collections/juno_monster_society.txt` | 6 duplicate-копий (содовые автоматы в prontera/alberta/einbroch/geffen/yuno/veins/lighthalzen) не спавнятся |
| `Equipment Reform PR Agent#it01` | `re_merchants/` | 1 duplicate не спавнится |

Базовый NPC (на rachel / itemmall соответственно) работает; не спавнятся только его
duplicate-копии в других городах. 167 длинных имён всего, но остальные работают (одиночные
NPC обрезаются лишь в отображаемом имени; duplicate-пары с обеих сторон обрезаются согласованно).

**Если решат починить позже:** генератор-укорачивание (укоротить base + все его duplicate-ссылки
консистентно до ≤23) ИЛИ engine ↑NAME_LENGTH (рискованно — затрагивает DB-схему char/npc,
сетевые пакеты clif, inter-server протокол; нужен анализ wire/DB-совместимости).

## 2. Renewal Global_Functions не портированы (runtime-ссылки)

Эти `function script`-функции из renewal Global_Functions отсутствуют в uAthena. Вызовы
`callfunc` к ним сработают только при триггере игроком (runtime), не при загрузке:

| Функция | Где используется | Что деградирует |
|---|---|---|
| `F_GM_NPC` | `re_eden/eden_quests.txt` (2), `re_quests/` | GM-проверка в NPC |
| `F_Malaya_Nurse` | `re_quests/quests_malaya.txt` | диалог медсестры Malaya |
| `F_PVP_FSRS` | `re_other/pvp.txt` | PvP-функция |

## 3. Renewal-спрайты NPC без viewdata (косметика)

`status_set_viewdata (NPC): No view data for class N` при загрузке — renewal-классы спрайтов
(4, 401, 449, 553, ...) отсутствуют в pre-renewal `db/`. NPC грузится и работает; спрайт
может отображаться неверно. Чисто косметическое, зависит от клиентского GRF.

## 4. Закомментированные renewal-feature строки (адаптация)

Отдельные строки скриптов с renewal-only buildins (`clear`/`sit`/`delequip`/`questinfo`/
`setunittitle`/`getnpcid`/`mesitemlink` и др.) закомментированы как `//[BACKPORT-GAP:...]` /
`//[BACKPORT-UNRESOLVED:...]`. NPC грузится, но конкретная фича внутри деградирует (логировано
в `Doc/backport_renewal_*_gap.md` по фазам). Для будущего движкового/Global_Functions порта.

## Не бэкпортировано (вне концепции, по решению)

- **Эпизоды 14.3-18** — instance-gated, нет `instance.c` (engine-OUT).
- **episode/town-quests** (`quests_13_1..18`, `quests_lighthalzen`/`morocc`/`aldebaran`/`izlude`/
  `nameless`/`niflheim`/`veins`/`glastheim`/`payon`) — не входили в roadmap; решение «оставить OUT,
  серия закрыта» (2026-06-21).
- **instances / 3rd-job квесты / barter / clan / cash-marketshop** — нет движковой поддержки.
