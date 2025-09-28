# Centralized compiler and linker flags for the x64 port

# Toolchain configuration
UA_CC       ?= gcc
UA_ENABLE_NATIVE ?= 0

# Architecture and optimization
UA_ARCH_FLAGS    := -m64
UA_PIC_FLAGS     := -fPIC
UA_OPT_FLAGS     := -O2
UA_DEBUG_FLAGS   := -g3

# Warning policy
UA_WARN_FLAGS    := -Wall -Wextra -Wconversion

# Miscellaneous compile-time toggles and defines shared by all targets
UA_MISC_BASE_FLAGS := -pipe -fomit-frame-pointer -ffast-math -fcommon -fstack-protector
UA_MISC_BASE_FLAGS += -Wno-sign-compare -Wno-unused-parameter -Wno-pointer-sign \
                      -Wno-switch -Wno-unused -Wno-parentheses
UA_MISC_FLAGS      := $(UA_MISC_BASE_FLAGS)
UA_DEFINE_FLAGS  := -DCHRIF_OLDINFO -DBCHECK -DPCRE_SUPPORT -DHAVE_SETRLIMIT

# Dependency discovery
UA_PCRE_CFLAGS := $(shell pkg-config --cflags libpcre 2>/dev/null \
                   || pkg-config --cflags libpcre1 2>/dev/null)
UA_PCRE_LIBS   := $(shell pkg-config --libs libpcre 2>/dev/null \
                   || pkg-config --libs libpcre1 2>/dev/null)

# Ensure we still link PCRE even if pkg-config metadata is missing
ifeq ($(strip $(UA_PCRE_LIBS)),)
UA_PCRE_LIBS := -lpcre
endif

# Include directories
UA_INCLUDE_FLAGS := -I../common $(UA_PCRE_CFLAGS)

# Linker flags and libraries
UA_LINK_FLAGS    := -m64 -rdynamic
UA_LIBDIR_FLAGS  :=
UA_LIB_FLAGS     := $(UA_PCRE_LIBS) -ldl -lz -lm

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
