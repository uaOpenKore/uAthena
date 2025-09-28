#ifndef MAP_CACHE_SERIALIZATION_H
#define MAP_CACHE_SERIALIZATION_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define MAP_CACHE_MAGIC 0x4d434143u /* 'MCAC' */
#define MAP_CACHE_FORMAT_VERSION 2u
#define MAP_CACHE_HEADER_SIZE_V2 32u
#define MAP_CACHE_ENTRY_SIZE_V2 64u

struct map_cache_head {
    uint32_t version;
    uint32_t header_size;
    uint32_t entry_size;
    uint32_t entry_count;
    uint64_t filesize;
};

struct map_cache_entry {
    char fn[32];
    uint32_t xs;
    uint32_t ys;
    int32_t water_height;
    uint32_t compressed;
    uint64_t pos;
    uint64_t compressed_len;
};

enum map_cache_format {
    MAP_CACHE_FORMAT_UNKNOWN = 0,
    MAP_CACHE_FORMAT_V1 = 1,
    MAP_CACHE_FORMAT_V2 = 2,
};

#ifdef __cplusplus
extern "C" {
#endif

bool map_cache_read_header(FILE *fp, struct map_cache_head *head, enum map_cache_format *format);
bool map_cache_read_entries(FILE *fp, const struct map_cache_head *head, enum map_cache_format format, struct map_cache_entry *entries, size_t entry_capacity);
bool map_cache_write_v2(FILE *fp, const struct map_cache_head *head, const struct map_cache_entry *entries);
bool map_cache_upgrade_v1_to_v2(const char *path, const struct map_cache_head *legacy_head, struct map_cache_entry *entries);
uint64_t map_cache_directory_size(const struct map_cache_head *head);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* MAP_CACHE_SERIALIZATION_H */
