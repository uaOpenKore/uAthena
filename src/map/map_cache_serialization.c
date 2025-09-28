#include "map_cache_serialization.h"

#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#  include <io.h>
#endif

struct map_cache_disk_header_v1 {
    uint32_t sizeof_header;
    uint32_t sizeof_map;
    uint32_t nmaps;
    uint32_t filesize;
};

struct map_cache_disk_entry_v1 {
    char fn[32];
    uint32_t xs;
    uint32_t ys;
    int32_t water_height;
    uint32_t pos;
    uint32_t compressed;
    uint32_t compressed_len;
};

struct map_cache_disk_header_v2 {
    uint32_t magic;
    uint32_t version;
    uint32_t header_size;
    uint32_t entry_size;
    uint32_t entry_count;
    uint32_t reserved;
    uint64_t filesize;
};

struct map_cache_disk_entry_v2 {
    char fn[32];
    uint32_t xs;
    uint32_t ys;
    int32_t water_height;
    uint32_t compressed;
    uint64_t pos;
    uint64_t compressed_len;
};

/* compile-time layout checks */
typedef char map_cache_header_v1_size_check[(sizeof(struct map_cache_disk_header_v1) == 16u) ? 1 : -1];
typedef char map_cache_entry_v1_size_check[(sizeof(struct map_cache_disk_entry_v1) == 56u) ? 1 : -1];
typedef char map_cache_header_v2_size_check[(sizeof(struct map_cache_disk_header_v2) == 32u) ? 1 : -1];
typedef char map_cache_entry_v2_size_check[(sizeof(struct map_cache_disk_entry_v2) == 64u) ? 1 : -1];

static bool map_cache_read_bytes(FILE *fp, void *buffer, size_t length) {
    if (length == 0) {
        return true;
    }
    return fread(buffer, 1, length, fp) == length;
}

static bool map_cache_write_bytes(FILE *fp, const void *buffer, size_t length) {
    if (length == 0) {
        return true;
    }
    return fwrite(buffer, 1, length, fp) == length;
}

static bool map_cache_read_u32(FILE *fp, uint32_t *value) {
    return map_cache_read_bytes(fp, value, sizeof(*value));
}

static bool map_cache_read_u64(FILE *fp, uint64_t *value) {
    return map_cache_read_bytes(fp, value, sizeof(*value));
}

static bool map_cache_read_i32(FILE *fp, int32_t *value) {
    return map_cache_read_bytes(fp, value, sizeof(*value));
}

static bool map_cache_write_u32(FILE *fp, uint32_t value) {
    return map_cache_write_bytes(fp, &value, sizeof(value));
}

static bool map_cache_write_u64(FILE *fp, uint64_t value) {
    return map_cache_write_bytes(fp, &value, sizeof(value));
}

static bool map_cache_write_i32(FILE *fp, int32_t value) {
    return map_cache_write_bytes(fp, &value, sizeof(value));
}

static int map_cache_seek64(FILE *fp, uint64_t offset, int whence) {
#if defined(_WIN32)
    return _fseeki64(fp, (long long)offset, whence);
#elif defined(HAVE_FSEEKO) || defined(__USE_LARGEFILE64)
    return fseeko(fp, (off_t)offset, whence);
#else
    if (offset > LONG_MAX) {
        errno = EOVERFLOW;
        return -1;
    }
    return fseek(fp, (long)offset, whence);
#endif
}

static uint64_t map_cache_entry_payload_size(const struct map_cache_entry *entry) {
    if (!entry) {
        return 0;
    }

    if (entry->compressed) {
        return entry->compressed_len;
    }

    return (uint64_t)entry->xs * (uint64_t)entry->ys;
}

uint64_t map_cache_directory_size(const struct map_cache_head *head) {
    if (!head) {
        return 0;
    }
    return (uint64_t)head->header_size + (uint64_t)head->entry_size * (uint64_t)head->entry_count;
}

bool map_cache_read_header(FILE *fp, struct map_cache_head *head, enum map_cache_format *format) {
    if (!fp || !head || !format) {
        return false;
    }

    if (map_cache_seek64(fp, 0, SEEK_SET) != 0) {
        return false;
    }

    uint32_t first_word = 0;
    if (fread(&first_word, sizeof(first_word), 1, fp) != 1) {
        return false;
    }

    if (first_word == MAP_CACHE_MAGIC) {
        uint32_t disk_version = 0;
        uint32_t disk_header_size = 0;
        uint32_t disk_entry_size = 0;
        uint32_t disk_entry_count = 0;
        uint32_t disk_reserved = 0;
        uint64_t disk_filesize = 0;

        if (!map_cache_read_u32(fp, &disk_version) || !map_cache_read_u32(fp, &disk_header_size) ||
            !map_cache_read_u32(fp, &disk_entry_size) || !map_cache_read_u32(fp, &disk_entry_count) ||
            !map_cache_read_u32(fp, &disk_reserved) || !map_cache_read_u64(fp, &disk_filesize)) {
            return false;
        }

        (void)disk_reserved;

        if (disk_version != MAP_CACHE_FORMAT_VERSION) {
            return false;
        }

        if (disk_header_size != sizeof(struct map_cache_disk_header_v2) ||
            disk_entry_size != sizeof(struct map_cache_disk_entry_v2)) {
            return false;
        }

        head->version = disk_version;
        head->header_size = disk_header_size;
        head->entry_size = disk_entry_size;
        head->entry_count = disk_entry_count;
        head->filesize = disk_filesize;
        *format = MAP_CACHE_FORMAT_V2;
        return true;
    }

    uint32_t legacy_sizeof_map = 0;
    uint32_t legacy_nmaps = 0;
    uint32_t legacy_filesize = 0;

    if (!map_cache_read_u32(fp, &legacy_sizeof_map) || !map_cache_read_u32(fp, &legacy_nmaps) ||
        !map_cache_read_u32(fp, &legacy_filesize)) {
        return false;
    }

    if (first_word != sizeof(struct map_cache_disk_header_v1) ||
        legacy_sizeof_map != sizeof(struct map_cache_disk_entry_v1)) {
        return false;
    }

    head->version = MAP_CACHE_FORMAT_V1;
    head->header_size = first_word;
    head->entry_size = legacy_sizeof_map;
    head->entry_count = legacy_nmaps;
    head->filesize = legacy_filesize;
    *format = MAP_CACHE_FORMAT_V1;
    return true;
}

bool map_cache_read_entries(FILE *fp, const struct map_cache_head *head, enum map_cache_format format, struct map_cache_entry *entries, size_t entry_capacity) {
    if (!fp || !head || !entries) {
        return false;
    }

    if ((uint64_t)entry_capacity < (uint64_t)head->entry_count) {
        return false;
    }

    if (map_cache_seek64(fp, head->header_size, SEEK_SET) != 0) {
        return false;
    }

    size_t i;
    if (format == MAP_CACHE_FORMAT_V2) {
        for (i = 0; i < head->entry_count; ++i) {
            char fn[sizeof(entries[i].fn)];
            uint32_t xs = 0;
            uint32_t ys = 0;
            int32_t water_height = 0;
            uint32_t compressed = 0;
            uint64_t pos = 0;
            uint64_t compressed_len = 0;

            if (!map_cache_read_bytes(fp, fn, sizeof(fn)) || !map_cache_read_u32(fp, &xs) ||
                !map_cache_read_u32(fp, &ys) || !map_cache_read_i32(fp, &water_height) ||
                !map_cache_read_u32(fp, &compressed) || !map_cache_read_u64(fp, &pos) ||
                !map_cache_read_u64(fp, &compressed_len)) {
                return false;
            }

            memcpy(entries[i].fn, fn, sizeof(entries[i].fn));
            entries[i].xs = xs;
            entries[i].ys = ys;
            entries[i].water_height = water_height;
            entries[i].compressed = compressed;
            entries[i].pos = pos;
            entries[i].compressed_len = compressed_len;
        }
        return true;
    }

    if (format != MAP_CACHE_FORMAT_V1) {
        return false;
    }

    for (i = 0; i < head->entry_count; ++i) {
        char fn[sizeof(entries[i].fn)];
        uint32_t xs = 0;
        uint32_t ys = 0;
        int32_t water_height = 0;
        uint32_t pos = 0;
        uint32_t compressed = 0;
        uint32_t compressed_len = 0;

        if (!map_cache_read_bytes(fp, fn, sizeof(fn)) || !map_cache_read_u32(fp, &xs) ||
            !map_cache_read_u32(fp, &ys) || !map_cache_read_i32(fp, &water_height) ||
            !map_cache_read_u32(fp, &pos) || !map_cache_read_u32(fp, &compressed) ||
            !map_cache_read_u32(fp, &compressed_len)) {
            return false;
        }

        memcpy(entries[i].fn, fn, sizeof(entries[i].fn));
        entries[i].xs = xs;
        entries[i].ys = ys;
        entries[i].water_height = water_height;
        entries[i].compressed = compressed;
        entries[i].pos = pos;
        entries[i].compressed_len = compressed ? compressed_len : 0;
    }
    return true;
}

bool map_cache_write_v2(FILE *fp, const struct map_cache_head *head, const struct map_cache_entry *entries) {
    if (!fp || !head || !entries) {
        return false;
    }

    struct map_cache_head local = *head;
    local.version = MAP_CACHE_FORMAT_VERSION;
    local.header_size = sizeof(struct map_cache_disk_header_v2);
    local.entry_size = sizeof(struct map_cache_disk_entry_v2);

    if (map_cache_seek64(fp, 0, SEEK_SET) != 0) {
        return false;
    }

    struct map_cache_disk_header_v2 disk_header;
    memset(&disk_header, 0, sizeof(disk_header));
    disk_header.magic = MAP_CACHE_MAGIC;
    disk_header.version = MAP_CACHE_FORMAT_VERSION;
    disk_header.header_size = local.header_size;
    disk_header.entry_size = local.entry_size;
    disk_header.entry_count = local.entry_count;
    disk_header.filesize = local.filesize;

    if (!map_cache_write_u32(fp, disk_header.magic) || !map_cache_write_u32(fp, disk_header.version) ||
        !map_cache_write_u32(fp, disk_header.header_size) || !map_cache_write_u32(fp, disk_header.entry_size) ||
        !map_cache_write_u32(fp, disk_header.entry_count) || !map_cache_write_u32(fp, disk_header.reserved) ||
        !map_cache_write_u64(fp, disk_header.filesize)) {
        return false;
    }

    if (map_cache_seek64(fp, local.header_size, SEEK_SET) != 0) {
        return false;
    }

    size_t i;
    for (i = 0; i < local.entry_count; ++i) {
        char fn[sizeof(entries[i].fn)] = {0};
        memcpy(fn, entries[i].fn, sizeof(fn));

        if (!map_cache_write_bytes(fp, fn, sizeof(fn)) || !map_cache_write_u32(fp, entries[i].xs) ||
            !map_cache_write_u32(fp, entries[i].ys) || !map_cache_write_i32(fp, entries[i].water_height) ||
            !map_cache_write_u32(fp, entries[i].compressed) || !map_cache_write_u64(fp, entries[i].pos) ||
            !map_cache_write_u64(fp, entries[i].compressed_len)) {
            return false;
        }
    }

    return fflush(fp) == 0;
}

static bool map_cache_copy_payload(FILE *dst, uint64_t dst_offset, FILE *src, uint64_t src_offset, uint64_t length) {
    if (length == 0) {
        return true;
    }

    if (map_cache_seek64(src, src_offset, SEEK_SET) != 0) {
        return false;
    }

    if (map_cache_seek64(dst, dst_offset, SEEK_SET) != 0) {
        return false;
    }

    if (length > SIZE_MAX) {
        errno = EOVERFLOW;
        return false;
    }

    size_t chunk_size = (size_t)length;
    unsigned char *buffer = (unsigned char *)malloc(chunk_size);
    if (!buffer) {
        return false;
    }

    size_t read_bytes = fread(buffer, 1, chunk_size, src);
    if (read_bytes != chunk_size) {
        free(buffer);
        return false;
    }

    size_t written = fwrite(buffer, 1, chunk_size, dst);
    free(buffer);
    return written == chunk_size;
}

static int map_cache_replace_file(const char *src, const char *dst) {
#if defined(_WIN32)
    if (_unlink(dst) != 0 && errno != ENOENT) {
        return -1;
    }
    return rename(src, dst);
#else
    return rename(src, dst);
#endif
}

bool map_cache_upgrade_v1_to_v2(const char *path, const struct map_cache_head *legacy_head, struct map_cache_entry *entries) {
    if (!path || !legacy_head || !entries || legacy_head->version != MAP_CACHE_FORMAT_V1) {
        return false;
    }

    FILE *legacy_fp = fopen(path, "rb");
    if (!legacy_fp) {
        return false;
    }

    size_t path_len = strlen(path);
    const char *suffix = ".tmp";
    size_t suffix_len = strlen(suffix);
    char *tmp_path = (char *)malloc(path_len + suffix_len + 1);
    if (!tmp_path) {
        fclose(legacy_fp);
        return false;
    }
    memcpy(tmp_path, path, path_len);
    memcpy(tmp_path + path_len, suffix, suffix_len + 1);

    FILE *tmp_fp = fopen(tmp_path, "wb+");
    if (!tmp_fp) {
        free(tmp_path);
        fclose(legacy_fp);
        return false;
    }

    struct map_cache_head new_head;
    new_head.version = MAP_CACHE_FORMAT_VERSION;
    new_head.header_size = sizeof(struct map_cache_disk_header_v2);
    new_head.entry_size = sizeof(struct map_cache_disk_entry_v2);
    new_head.entry_count = legacy_head->entry_count;
    new_head.filesize = map_cache_directory_size(&new_head);

    uint64_t write_cursor = map_cache_directory_size(&new_head);
    uint64_t max_written = write_cursor;

    for (uint32_t i = 0; i < legacy_head->entry_count; ++i) {
        struct map_cache_entry *entry = &entries[i];
        uint64_t payload = map_cache_entry_payload_size(entry);
        uint64_t new_pos = 0;

        if (entry->fn[0] == '\0' || payload == 0) {
            entry->pos = 0;
            if (!entry->compressed) {
                entry->compressed_len = 0;
            }
            continue;
        }

        uint64_t old_pos = entry->pos;
        if (!map_cache_copy_payload(tmp_fp, write_cursor, legacy_fp, old_pos, payload)) {
            fclose(tmp_fp);
            fclose(legacy_fp);
            free(tmp_path);
            return false;
        }

        new_pos = write_cursor;
        write_cursor += payload;
        if (write_cursor > max_written) {
            max_written = write_cursor;
        }

        entry->pos = new_pos;
        if (!entry->compressed) {
            entry->compressed_len = 0;
        }
    }

    new_head.filesize = max_written;

    if (!map_cache_write_v2(tmp_fp, &new_head, entries)) {
        fclose(tmp_fp);
        fclose(legacy_fp);
        free(tmp_path);
        return false;
    }

    if (fflush(tmp_fp) != 0) {
        fclose(tmp_fp);
        fclose(legacy_fp);
        free(tmp_path);
        return false;
    }

    fclose(tmp_fp);
    fclose(legacy_fp);

    if (map_cache_replace_file(tmp_path, path) != 0) {
        free(tmp_path);
        return false;
    }

    free(tmp_path);
    return true;
}
