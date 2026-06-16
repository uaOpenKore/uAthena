# Mercenary M7d — изменения для тестировщиков

Подключение поведения merc-скиллов (8201-8240) поверх готового ядра наёмников (призыв/бой/AI/`@merc`).
План + полная карта порта: `doc/mercenary_m7d_plan.md`. Реализуется по фазам.

**Контекст:** у eAthena наёмники кастуют скиллы только по команде клиента, а под нашим PV7 merc-окна нет
→ скиллы будет кастовать наш кастомный AI (фаза M7d-5). Механика скиллов (фазы 1-4) подключается заранее.
Runtime-проверка (нужен клиент + кластер) — на тестировщиках.

---

## Фаза M7d-1 — Статус-фундамент (СДЕЛАНО)

**Что изменилось:**
- `src/map/skill.h` — добавлены enum-константы MER_* (8222-8240: MAGNIFICAT/QUICKEN/SIGHT/CRASH/REGAIN/
  TENDER/BENEDICTION/RECUPERATE/MENTALCURE/COMPRESS/PROVOKE/AUTOBERSERK/DECAGI/SCAPEGOAT/LEXDIVINA/
  ESTIMATION/KYRIE/BLESSING/INCAGI). Раньше были только MS_/MA_/ML_ (8201-8221).
- `src/map/status.c` `initChangeTables` — 21 маппинг merc-скилл→status-change (set_sc/add_sc), как в
  eAthena. Player-SC (SC_BERSERK/PROVOKE/AUTOGUARD/REFLECTSHIELD/DEFENDER/…) переиспользуют существующую
  логику. Иконки SI_MERC_* НЕ добавлялись (под PV7 косметика, не рисуются).
- `src/map/status.c` — **kill-bonus теперь рабочий**: 6 обработчиков SC_MERC_* (ранее `mercenary_killbonus`
  стартовал баф, но эффекта не было): FLEEUP→flee, ATKUP→watk, HITUP→hit (+15·tier); HPUP→maxhp, SPUP→maxsp
  (+5%·tier); QUICKEN→aspd. SCB-флаги + val2-расчёт (status_change_start) + BL_MER-гейт (баффы только для
  наёмников) + полный heal HP/SP при выдаче HPUP/SPUP.

**Что отложено** (дормант, пока скиллы некастуемы — включится в M7d-3/5): QUICKEN opt3/eligibility/cancel.

**Эффект для игры:** каждые 50 убийств наёмник получает случайный баф (FLEE/ATK/HP/SP/HIT, ~10 мин) —
теперь реально повышает стат (раньше был no-op). Прочие маппинги активируются, когда скиллы начнут
кастоваться (M7d-2/3 механика + M7d-5 AI).

**Верификация (здесь):** `make sql` EXIT=0, 0 новых ворнингов, бинарники линкуются. Геймплейная
проверка (наёмник на 50-м килле получает стат-баф) — на тестировщиках.

**Откат:** реверт коммита фазы.

<!-- M7d-2 (офенс-урон), M7d-3 (бафы/тогглы/cure), M7d-4 (ловушки), M7d-5 (AI-каст) — далее. -->
