cmake_minimum_required(VERSION 3.16)
project(uAthena C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

option(UA_ENABLE_SANITIZE "Enable address and undefined behaviour sanitizers" OFF)

set(UA_COMMON_COMPILE_FLAGS
    -m64
    -fPIC
    -O2
    -g3
    -Wall
    -Wextra
    -Wconversion
    -pipe
    -fomit-frame-pointer
    -ffast-math
    -fcommon
    -fstack-protector
    -Wno-sign-compare
    -Wno-unused-parameter
    -Wno-pointer-sign
    -Wno-switch
    -Wno-unused
    -Wno-parentheses
)
set(UA_SANITIZE_FLAGS)

if(UA_ENABLE_SANITIZE)
    list(REMOVE_ITEM UA_COMMON_COMPILE_FLAGS -fomit-frame-pointer)
    list(APPEND UA_COMMON_COMPILE_FLAGS -fno-omit-frame-pointer)
    set(UA_SANITIZE_FLAGS -fsanitize=address,undefined)
endif()

add_library(map_cache_serialization STATIC
    src/map/map_cache_serialization.c
)

target_include_directories(map_cache_serialization
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_compile_options(map_cache_serialization
    PRIVATE ${UA_COMMON_COMPILE_FLAGS}
)

if(UA_ENABLE_SANITIZE)
    target_compile_options(map_cache_serialization PRIVATE ${UA_SANITIZE_FLAGS})
    target_link_options(map_cache_serialization PRIVATE ${UA_SANITIZE_FLAGS})
endif()

add_executable(map_cache_serialization_test
    tests/map_cache_serialization_test.c
)

target_link_libraries(map_cache_serialization_test PRIVATE map_cache_serialization)

target_compile_options(map_cache_serialization_test
    PRIVATE ${UA_COMMON_COMPILE_FLAGS}
)

if(UA_ENABLE_SANITIZE)
    target_compile_options(map_cache_serialization_test PRIVATE ${UA_SANITIZE_FLAGS})
    target_link_options(map_cache_serialization_test PRIVATE ${UA_SANITIZE_FLAGS})
endif()

add_custom_target(run_tests
    COMMAND map_cache_serialization_test
    DEPENDS map_cache_serialization_test
    COMMENT "Run map cache serialization regression tests"
)

if(UA_ENABLE_SANITIZE)
    add_custom_target(sanitize
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR} --target map_cache_serialization_test
        COMMAND ${CMAKE_COMMAND} -E env ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=print_stacktrace=1 ./map_cache_serialization_test
        DEPENDS map_cache_serialization_test
        COMMENT "Build and run the map cache tests with sanitizers"
    )
endif()
