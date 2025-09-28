# x64 Port Documentation

## 64-bit Dependency Matrix

The uAthena server and its tooling depend on the libraries below. Install the
native 64-bit development packages before building; no multilib (`:i386`
packages) are required.

| Component | Purpose | Ubuntu 22.04 LTS (amd64) | Fedora 39 (x86_64) |
|-----------|---------|--------------------------|---------------------|
| Toolchain | GCC/Clang, make, and headers | `build-essential`, `clang`, `clang-format`, `clang-tidy`, `cmake`, `pkg-config` | `@development-tools`, `clang`, `clang-tools-extra`, `cmake`, `pkgconf-pkg-config` |
| Cache     | Optional compiler cache | `ccache` | `ccache` |
| Compression | GRF compression support | `zlib1g-dev` | `zlib-devel` |
| Regex     | Script engine and parser | `libpcre3-dev` | `pcre-devel` |
| Database  | MySQL/MariaDB client API | `libmariadb-dev`, `libmariadb-dev-compat` | `mariadb-connector-c-devel` |
| Crypto    | SSL/TLS helpers | `libssl-dev` | `openssl-devel` |
| Readline  | Console utilities | `libreadline-dev` | `readline-devel` |

## Installation Notes

### Ubuntu 22.04 LTS (amd64)

```bash
sudo apt update
sudo apt install build-essential clang clang-format clang-tidy cmake pkg-config \
    ccache zlib1g-dev libpcre3-dev libmariadb-dev libmariadb-dev-compat \
    libssl-dev libreadline-dev
```

The command above was validated on a fresh Ubuntu 22.04.4 LTS amd64 image using
`apt install --simulate` to confirm all packages resolve to 64-bit builds with
no `:i386` pulls.

### Fedora 39 (x86_64)

```bash
sudo dnf install @development-tools clang clang-tools-extra cmake pkgconf-pkg-config \
    ccache zlib-devel pcre-devel mariadb-connector-c-devel openssl-devel readline-devel
```

Tested on Fedora 39 Workstation (x86_64) via `dnf install --assumeno` to verify
that only native 64-bit RPMs are selected.

## Verification Checklist

* Run `clang --version` and `gcc --version` to confirm the host compilers report
  `x86_64` targets.
* Build with `make common` or the sanitizer profile to ensure the toolchain
  links cleanly against the 64-bit libraries listed above.

## Release Optimization Profile

The default make and CMake recipes now centralize their optimization knobs via
`UA_OPT_LEVEL`/`UA_RELEASE_OPT_LEVEL` and `UA_ENABLE_LTO`.  Profiling on the map
cache and GRF regression tests showed that sticking with `-O2` keeps runtimes
predictable, while `-flto` can be enabled selectively for CPU-bound binaries
that benefit from the extra inlining headroom.【F:docs/x64/release_profile.md†L1-L36】

## Eliminating Legacy 32-bit Dependencies

Recent makefile changes remove every `-m32` and `/usr/lib32` reference from the
default build. Library paths are now discovered dynamically:

* PCRE headers and linker flags are pulled from `pkg-config libpcre` when
  available, with an automatic fallback to the system `-lpcre` symbol. This lets
  the build follow whichever 64-bit package your distribution ships without
  hard-coding `/usr/lib32` lookups.
* When SQL support is enabled (`SQLFLAG=1`), the build prefers `mysql_config`
  but falls back to `mariadb_config` automatically so that MariaDB Connector/C
  installations satisfy the dependency without installing legacy MySQL 5.x i686
  RPMs.

For older distributions that still lack 64-bit development RPMs/DEBs, install a
modern MariaDB Connector/C release and rebuild PCRE from source in 64-bit mode:

```bash
# Example for RHEL/CentOS 7+ hosts
curl -LO https://downloads.mariadb.org/interstitial/connector-c-3.3.8/mariadb-connector-c-3.3.8-linux-system.tar.gz
sudo tar -C /usr/local -xzvf mariadb-connector-c-3.3.8-linux-system.tar.gz
sudo ln -s /usr/local/mariadb-connector-c-3.3.8-linux-system/bin/mariadb_config /usr/local/bin/mariadb_config

curl -LO https://downloads.sourceforge.net/pcre/pcre-8.45.tar.gz
tar -xzvf pcre-8.45.tar.gz
cd pcre-8.45
./configure --enable-utf --enable-unicode-properties
make -j$(nproc)
sudo make install
```

Both projects install to `/usr/local` by default, avoiding any multilib
conflicts while satisfying the 64-bit linker checks performed by the makefiles.

