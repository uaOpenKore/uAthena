# Ops-тюнинг производительности сервера (VM/ядро/host)

Дополняет код-оптимизации (перф-этапы 1–6) слоем настроек ОС/виртуализации.
Основано на `perf record` map-сервера при ~190 онлайн (профиль map2, 99 Гц).

## Что показал профиль (self CPU, стабильный геймплей)
| % | символ | вывод |
|---|--------|-------|
| ~21% (incl.) | `tcp_sendmsg`/`sendto`/`ip_queue_xmit` | сеть-send — доминирующий syscall-путь |
| 11% | `map_foreachinmovearea` | рассылка «вошёл/вышел из вида» при движении (код, inherent) |
| 6.6% | `mobgrid_any` | проверка присутствия игроков в AI мобов |
| **2.3%** | **`srso_alias_safe_ret`** (ядро) | **CPU-митигации Spectre/SRSO — чистые накладные** |
| **1.2%** | **`aa_sk_perm`** (ядро) | **AppArmor-проверка на КАЖДОМ сокет-send** |
| ~10% | `futex`/`schedule` | синхронизация воркеров + qdisc-контеншн |

Строки ядра (митигации, apparmor) — это «бесплатный» CPU, который можно вернуть
без единой правки кода. Ниже — что автоматизировано и что руками.

---

## Автоматизировано (в `scripts/rc.local`, гость)
Копия → `/etc/rc.local` на гостевой VM (`chmod +x` + `systemctl enable rc-local`):
- **virtio-net multiqueue** (`ethtool -L combined = vCPU`), GRO/TSO/GSO.
- **IRQ-affinity** очередей NIC → CPU 2–3 (в стороне от game-loop ядер), **RPS/XPS**.
- **irqbalance off** (чтобы не перебивал ручную affinity).
- **sysctl** сети: `somaxconn/netdev_max_backlog/rmem/wmem/tcp_rmem/tcp_wmem/tcp_mtu_probing`, conntrack.
- **[новое] CPU governor = performance** — no-op внутри KVM-гостя без cpufreq (обычно так; см. host-раздел ниже).
- **[новое] `tcp_notsent_lowat=16384`** — мелкие пакеты движения/действий уходят на своём тике (меньше rubber-banding).

## ВРУЧНУЮ (host / GRUB / apparmor — rc.local это не покрывает)

### 1. CPU-митигации off — вернуть ~2–4% (доверенный игровой хост)
Профиль: `srso_alias_safe_ret` и родственные митигации. На выделенном игровом
сервере (не мультитенант, нет чужого недоверенного кода) их можно снять.

**На HOST (и/или в гостевой VM), в GRUB:**
```
# /etc/default/grub -> GRUB_CMDLINE_LINUX_DEFAULT="... mitigations=off"
update-grub && reboot
```
Проверка после ребута: `cat /sys/devices/system/cpu/vulnerabilities/*` → «Mitigation off/Vulnerable».
⚠️ Осознанный размен безопасность↔производительность. Оправдан для изолированного игрового хоста.

### 2. CPU governor = performance на HOST — держать частоту ядер
Внутри KVM-гостя cpufreq обычно НЕ проброшен → governor решается на **host**.
```
cpupower frequency-set -g performance          # или:
for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > "$g"; done
```
(rc.local гостя тоже пытается — сработает, только если cpufreq проброшен в гость.)

### 3. AppArmor unconfined для серверов — вернуть ~1–2%
Профиль: `aa_sk_perm` дергается на каждый `send()`. Если серверы под apparmor-профилем:
```
aa-status                                   # увидеть профиль(и) map/char/login-server_sql
aa-complain /path/to/profile                # мягко: логировать, не проверять; ИЛИ
aa-disable  /path/to/profile                # снять профиль для этого бинаря
# либо целиком (если apparmor нужен только под эти серверы):
systemctl disable --now apparmor
```
⚠️ Тоже размен на безопасность — снимать только осознанно, лучше точечно (`aa-disable` конкретного профиля), а не весь apparmor.

### 4. virtio на HOST (XML домена) — если ещё не так
`ethtool -L combined` в гостевом rc.local сработает, только если у vNIC **несколько
очередей**. Проверь домен на host:
```xml
<interface type='...'>
  <model type='virtio'/>
  <driver name='vhost' queues='N'/>   <!-- N = число vCPU -->
</interface>
```
Без `queues=N` multiqueue в госте не включится (одна очередь).

---

## Config-рычаг (геймплейное решение, НЕ трогал)
`conf/battle/monster.conf`: **`monster_ai: 0x020`** заметно раздувает mob-AI и
движение мобов → это виновник `map_foreachinmovearea` (11%) и `mob_ai_*`.
Митигации `mob_ai_*_skip_*` уже включены, но сам режим 0x20 — самый большой
CPU-рычаг на карте. Если 0x20 не нужен геймплейно — дефолт (0) даёт крупное
падение CPU (дальние мобы простаивают). **Решение за владельцем** (влияет на
поведение мобов), поэтому не менял.

## Ожидаемый суммарный эффект ops-слоя
mitigations off (~2–4%) + apparmor unconfined (~1–2%) + governor performance
(частота под нагрузкой) ≈ **5–8% CPU map-сервера возвращается**, плюс меньше
джиттера в send-пути. Всё — без правок игрового кода.

## Проверка
После применения снять свежий `UA_PERF=1` профиль: `srso_alias_safe_ret` и
`aa_sk_perm` должны исчезнуть/просесть; частота ядер — на максимуме под нагрузкой.
