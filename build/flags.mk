# Centralized compiler and linker flags for the x64 port

# Toolchain configuration
UA_CC       ?= gcc
UA_ENABLE_NATIVE ?= 0

# Architecture and optimization
UA_ARCH_FLAGS    := -m64
UA_PIC_FLAGS     := -fPIC

# Allow the optimization level to be tuned per build while defaulting to -O2.
UA_OPT_LEVEL     ?= 2
UA_OPT_FLAGS     := -O$(UA_OPT_LEVEL)
UA_DEBUG_FLAGS   := -g3

# Warning policy
UA_WARN_FLAGS    := -Wall -Wextra -Wconversion

# Miscellaneous compile-time toggles and defines shared by all targets
UA_MISC_BASE_FLAGS := -pipe -fomit-frame-pointer -ffast-math -fcommon -fstack-protector
UA_MISC_BASE_FLAGS += -Wno-sign-compare -Wno-unused-parameter -Wno-pointer-sign \
                      -Wno-switch -Wno-unused -Wno-parentheses
UA_MISC_FLAGS      := $(UA_MISC_BASE_FLAGS)
UA_DEFINE_FLAGS  := -DCHRIF_OLDINFO -DBCHECK -DHAVE_SETRLIMIT
UA_PCRE_DEFINE   := -DPCRE_SUPPORT

# Dependency discovery
UA_PCRE_CFLAGS := $(shell pkg-config --cflags libpcre 2>/dev/null \
                   || pkg-config --cflags libpcre1 2>/dev/null)
UA_PCRE_LIBS   := $(shell pkg-config --libs libpcre 2>/dev/null \
                   || pkg-config --libs libpcre1 2>/dev/null)

# Fall back to pcre-config if pkg-config metadata is unavailable
ifeq ($(strip $(UA_PCRE_LIBS)),)
UA_PCRE_CFLAGS := $(shell pcre-config --cflags 2>/dev/null)
UA_PCRE_LIBS   := $(shell pcre-config --libs 2>/dev/null)
endif

# Only enable PCRE integration when the library is available.
ifneq ($(strip $(UA_PCRE_LIBS)),)
UA_DEFINE_FLAGS += $(UA_PCRE_DEFINE)
else
UA_PCRE_CFLAGS :=
endif

# Include directories
UA_INCLUDE_FLAGS := -I../common $(UA_PCRE_CFLAGS)

# Linker flags and libraries
UA_LINK_FLAGS    := -m64 -rdynamic
UA_LIBDIR_FLAGS  :=
UA_LIB_FLAGS     := $(UA_PCRE_LIBS) -ldl -lz -lm

# Enable link-time optimization when explicitly requested.
UA_ENABLE_LTO    ?= 0

ifeq ($(UA_ENABLE_LTO),1)
UA_OPT_FLAGS  += -flto
UA_LINK_FLAGS += -flto
endif

# Allow opting-in to native tuning locally while keeping release builds portable
ifeq ($(UA_ENABLE_NATIVE),1)
UA_OPT_FLAGS += -march=native -mtune=native
endif

# Address/UndefinedBehavior sanitizer profile
UA_ENABLE_SANITIZE ?= 0
UA_SANITIZE_MODES  := address,undefined
UA_SANITIZE_CFLAGS :=
UA_SANITIZE_LDFLAGS :=

ifeq ($(UA_ENABLE_SANITIZE),1)
# Drop the release-oriented frame-pointer omission when sanitizers are active
UA_MISC_FLAGS := $(filter-out -fomit-frame-pointer,$(UA_MISC_FLAGS))
UA_MISC_FLAGS += -fno-omit-frame-pointer

UA_SANITIZE_CFLAGS  += -fsanitize=$(UA_SANITIZE_MODES)
UA_SANITIZE_LDFLAGS += -fsanitize=$(UA_SANITIZE_MODES)
endif

# Aggregate flag helpers
UA_CFLAGS := $(UA_ARCH_FLAGS) $(UA_PIC_FLAGS) $(UA_OPT_FLAGS) $(UA_DEBUG_FLAGS) \
             $(UA_WARN_FLAGS) $(UA_MISC_FLAGS) $(UA_DEFINE_FLAGS) \
             $(UA_INCLUDE_FLAGS) $(UA_SANITIZE_CFLAGS)
UA_LDFLAGS := $(UA_LINK_FLAGS) $(UA_SANITIZE_LDFLAGS)
UA_LDLIBS  := $(UA_LIBDIR_FLAGS) $(UA_LIB_FLAGS)
