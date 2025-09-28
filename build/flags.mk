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
UA_MISC_FLAGS    := -pipe -fomit-frame-pointer -ffast-math -fcommon -fstack-protector
UA_MISC_FLAGS    += -Wno-sign-compare -Wno-unused-parameter -Wno-pointer-sign \
                    -Wno-switch -Wno-unused -Wno-parentheses
UA_DEFINE_FLAGS  := -DCHRIF_OLDINFO -DBCHECK -DPCRE_SUPPORT -DHAVE_SETRLIMIT

# Include directories
UA_INCLUDE_FLAGS := -I../common -I/usr/include -I/usr/include/mysql

# Linker flags and libraries
UA_LINK_FLAGS    := -m64 -rdynamic
UA_LIBDIR_FLAGS  := -L/usr/lib64 -L/usr/lib -L/usr/lib64/mysql -L/usr/lib/mysql
UA_LIB_FLAGS     := -lpcre -lmysqlclient -ldl -lz -lm

# Allow opting-in to native tuning locally while keeping release builds portable
ifeq ($(UA_ENABLE_NATIVE),1)
UA_OPT_FLAGS += -march=native -mtune=native
endif

# Aggregate flag helpers
UA_CFLAGS := $(UA_ARCH_FLAGS) $(UA_PIC_FLAGS) $(UA_OPT_FLAGS) $(UA_DEBUG_FLAGS) \
             $(UA_WARN_FLAGS) $(UA_MISC_FLAGS) $(UA_DEFINE_FLAGS) \
             $(UA_INCLUDE_FLAGS)
UA_LDFLAGS := $(UA_LINK_FLAGS)
UA_LDLIBS  := $(UA_LIBDIR_FLAGS) $(UA_LIB_FLAGS)
