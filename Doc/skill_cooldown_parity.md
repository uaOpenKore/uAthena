# Аудит полноты серверного кулдауна скиллов (uAthena vs eAthena)

Ветка: `x64`. Задача: проверить, что «откат скиллов после применения»
(серверный reuse-блок) навешан на все нужные скиллы, и добить недостающие.

## Что уже было (и работает)
Серверный кулдаун в uAthena полнофункционален:
- `skill_blockpc_start()` ставит `sd->blockskill[id]=1` + таймер снятия;
- блок enforced в `skillnotok()`: `if (sd->blockskill[i] > 0) return 1;` —
  recast запрещён, пока откат не истёк;
- `@cd`/`@status` показывает активные откаты в чате (PV7 не умеет нативно).

Это идентично eAthena. Бекпортировать сам механизм НЕ нужно.

## Аудит call-sites `skill_blockpc_start`
Сверка всех точек применения (по скиллам, не по номерам строк):

| Скилл | eAthena | uAthena (было) |
|-------|---------|----------------|
| SM_MAGNUM / MS_MAGNUM (splash + passive) | да | да |
| PF_SOULBURN | да | да |
| SM_ENDURE (Duration2) | да | да |
| MO_EXTREMITYFIST (via MO_BODYRELOCATION) | да | да |
| **AS_SPLASHER (Venom Splasher)** | **да** | **НЕТ** |
| **BD_ADAPTATION (после песни/танца)** | **да** | **НЕТ** |

## Бекпорт (2 пропуска, оба серверные, без клиентских пакетов)
`src/map/skill.c`:
1. **AS_SPLASHER** — после `sc_start4`/`clif_skill_nodamage`:
   `if (sd) skill_blockpc_start(sd, skillid, skill_get_time(skillid,skilllv)+3000);`
   (анти-спам бёрста; reuse = Duration1 + 3с).
2. **BD_ADAPTATION** — в `skill_castend_id`, в блоке очистки пред-каст состояний:
   `if(sc->data[SC_DANCING].timer != -1 && (skill_get_inf2(ud->skillid)&INF2_SONG_DANCE) && sd)`
   `   skill_blockpc_start(sd, BD_ADAPTATION, 3000);`
   (3с блок после любой песни/танца — анти-спам, как в eAthena).

Адаптация под uAthena: `sc->data[..].timer != -1` (массив значений), а не
`sc->data[..]` (указатель эталона).

## Не трогали
- Клиентский показ отката (`clif_skill_cooldown`, пакет `0x43d`) — он есть в
  eAthena, но требует клиент ≥ 2008-11-12; на PV7 мёртв, а `@cd` уже закрывает
  показ в чате. Отдельная история (как нативные пакеты скупки).
- Общий механизм (blockskill + skill_cast_db Duration1/2) — уже идентичен.

## Проверка
`make sql` собирается чисто (skill.c компилится, map-server линкуется). Рантайм
(спам Venom Splasher / песен на кластере) — за тестерами.
