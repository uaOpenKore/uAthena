# Конфликты renewal-варпов бэкпорта (отвергнутые точки)

Тестировщики: замените `решение?` корректирующими данными.
Схема — Doc/backport_renewal_warps_npc_design.md §4.2.

## Пропущенные boundary-варпы (незарегистрированный endpoint вне scope)
# Концепция «0 новых карт» (§3): варп в карту вне 6 зон, которой нет в
# map_index (напр. dimensional-gap хаб 'dali'), пропущен. решение?
dali,34,139 -> dic_fild02 (dg004) | unregistered out-of-scope endpoint ['dali'] | SKIPPED
dali,38,87 -> bif_fild01 (dg003) | unregistered out-of-scope endpoint ['dali'] | SKIPPED
