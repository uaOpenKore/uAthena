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

