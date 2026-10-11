# Running the uAthena server on Nintendo Switch — keeping the client's FPS up

When the **server and the game client run on the same Switch**, they fight over the same CPU.
The Switch has 4 CPU cores but the system keeps one, so only ~3 are free. If the server spreads
across every core, the client is left with almost nothing and drops to ~5 FPS.

This build lets you **pin the whole server to specific core(s)** so the client keeps a dedicated
core for rendering.

---

## 1. Prerequisites

The uAthena server is a normal **Linux** program. On the Switch it must run under **L4T Linux**
(Ubuntu for Switch, `aarch64`). It does **not** run on the stock Horizon OS directly.

> If your setup is different (e.g. the server is meant to run on Horizon natively), tell the
> developer — core pinning there uses a different OS call and is not covered here.

Install the build dependencies on the L4T system:

```sh
sudo apt update
sudo apt install build-essential libpcre2-dev zlib1g-dev
```

---

## 2. Build the server (TXT, no database)

Use the **`txt`** branch — it builds the no-MySQL server set, so you don't need a database on the
console.

```sh
git clone <repo-url> uAthena
cd uAthena
git checkout txt
make txt
```

This produces three executables in the repo root:

* `login-server`
* `char-server`
* `map-server`

Run all three (each in its own process, the usual uAthena way).

---

## 3. Configure the core pinning

Open **`conf/cpu_affinity.conf`** and set which cores the server may use. Cores are **0-based**.

```ini
# server uses cores 1 and 2; the client keeps core 0 free
cpu_cores: 1,2
```

* The setting applies to **all three** servers (login, char, map) — each reads this file on
  startup, before it creates any threads, so every server thread is confined to those cores.
* If the line stays commented out / the file is absent, nothing changes (the server may use every
  core, exactly as before).

**Alternative — environment variable** (overrides the file, handy from a launch script):

```sh
UATHENA_CPU_CORES=1,2 ./map-server
```

---

## 4. Limit the server to a SINGLE core

Put just one core number. For example, to run the **entire server on core 2 only** (leaving cores
0 and 1 for the client):

```ini
cpu_cores: 2
```

or

```sh
UATHENA_CPU_CORES=2 ./login-server
UATHENA_CPU_CORES=2 ./char-server
UATHENA_CPU_CORES=2 ./map-server
```

Recommended Switch layout: **client on core 0, server on core(s) 1–2** (core 3 is reserved by the
system). Start with the server on one core (`cpu_cores: 2`); if the server itself is too slow, give
it two (`cpu_cores: 1,2`).

---

## 5. Verify it worked

Each server prints a line at startup:

```
[Status]: CPU affinity: server pinned to 1 core(s) [2] (conf/cpu_affinity.conf)
```

* The number and the `[...]` show exactly which cores it was pinned to.
* Launch the servers **from the uAthena directory** so `conf/cpu_affinity.conf` is found. If you
  don't see the line, the setting wasn't picked up (wrong working directory, or the line is still
  commented out).

You can also confirm from another shell:

```sh
taskset -cp $(pgrep -f map-server)
# -> current affinity list: 2
```

---

## Notes

* **Linux only.** On any non-Linux build the setting is ignored (no effect, no error).
* All four Switch cores are the **same** (Cortex-A57) — there is no "slow" vs "fast" core, so it
  doesn't matter *which* cores you give the server; what matters is that they are **separate** from
  the core the client renders on.
* Set the affinity **once in the config** — you don't need to change any code.
