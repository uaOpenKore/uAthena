#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>

#if defined(_WIN32)
#include <io.h>
#endif

#include "../src/map/map_cache_serialization.h"

static int test_seek(FILE *fp, uint64_t offset)
{
#if defined(_WIN32)
        return _fseeki64(fp, (long long)offset, SEEK_SET);
#elif defined(HAVE_FSEEKO) || defined(__USE_LARGEFILE64)
        return fseeko(fp, (off_t)offset, SEEK_SET);
#else
        if (offset > LONG_MAX)
                return -1;
        return fseek(fp, (long)offset, SEEK_SET);
#endif
}

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

static void write_v1_fixture(const char *path)
{
        FILE *fp = fopen(path, "wb");
        struct map_cache_disk_header_v1 header;
        struct map_cache_disk_entry_v1 entries[2];
        uint8_t payload[4] = {1, 2, 3, 4};
        uint32_t offset;

        assert(fp != NULL);

        memset(&header, 0, sizeof(header));
        header.sizeof_header = sizeof(header);
        header.sizeof_map = sizeof(entries[0]);
        header.nmaps = 2;
        header.filesize = sizeof(header) + sizeof(entries);

        memset(entries, 0, sizeof(entries));
        strncpy(entries[0].fn, "sample", sizeof(entries[0].fn) - 1);
        entries[0].xs = 2;
        entries[0].ys = 2;
        entries[0].water_height = 10;
        entries[0].compressed = 0;
        entries[0].compressed_len = 0;
        offset = header.sizeof_header + header.sizeof_map * header.nmaps;
        entries[0].pos = offset;
        header.filesize += sizeof(payload);

        fwrite(&header, sizeof(header), 1, fp);
        fwrite(entries, sizeof(entries), 1, fp);
        fwrite(payload, sizeof(payload), 1, fp);
        fclose(fp);
}

static void verify_payload(FILE *fp, uint64_t pos)
{
        uint8_t buffer[4];
        assert(test_seek(fp, pos) == 0);
        assert(fread(buffer, 1, sizeof(buffer), fp) == sizeof(buffer));
        assert(buffer[0] == 1 && buffer[1] == 2 && buffer[2] == 3 && buffer[3] == 4);
}

static void test_upgrade_and_read(const char *path)
{
        FILE *fp;
        struct map_cache_head head;
        struct map_cache_entry *entries;
        enum map_cache_format format;

        fp = fopen(path, "r+b");
        assert(fp != NULL);
        assert(map_cache_read_header(fp, &head, &format));
        assert(format == MAP_CACHE_FORMAT_V1);

        entries = calloc(head.entry_count, sizeof(*entries));
        assert(entries != NULL);
        assert(map_cache_read_entries(fp, &head, format, entries, head.entry_count));
        fclose(fp);

        assert(map_cache_upgrade_v1_to_v2(path, &head, entries));
        free(entries);

        fp = fopen(path, "r+b");
        assert(fp != NULL);
        assert(map_cache_read_header(fp, &head, &format));
        assert(format == MAP_CACHE_FORMAT_V2);
        assert(head.version == MAP_CACHE_FORMAT_VERSION);
        assert(head.header_size == MAP_CACHE_HEADER_SIZE_V2);
        assert(head.entry_size == MAP_CACHE_ENTRY_SIZE_V2);

        entries = calloc(head.entry_count, sizeof(*entries));
        assert(entries != NULL);
        assert(map_cache_read_entries(fp, &head, format, entries, head.entry_count));
        verify_payload(fp, entries[0].pos);
        assert(entries[0].xs == 2);
        assert(entries[0].ys == 2);
        assert(entries[0].water_height == 10);
        free(entries);
        fclose(fp);
}

static void test_write_new(const char *path)
{
        FILE *fp = fopen(path, "wb+");
        struct map_cache_head head;
        struct map_cache_entry entries[1];

        assert(fp != NULL);
        memset(&head, 0, sizeof(head));
        head.version = MAP_CACHE_FORMAT_VERSION;
        head.header_size = MAP_CACHE_HEADER_SIZE_V2;
        head.entry_size = MAP_CACHE_ENTRY_SIZE_V2;
        head.entry_count = 1;
        head.filesize = map_cache_directory_size(&head);

        memset(entries, 0, sizeof(entries));
        strncpy(entries[0].fn, "new", sizeof(entries[0].fn) - 1);
        entries[0].xs = 1;
        entries[0].ys = 1;
        entries[0].compressed = 0;
        entries[0].compressed_len = 0;
        entries[0].pos = head.filesize;
        head.filesize += 1;

        assert(map_cache_write_v2(fp, &head, entries));
        assert(fwrite("Z", 1, 1, fp) == 1);
        assert(fflush(fp) == 0);
        fclose(fp);

        {
                enum map_cache_format dummy;
                fp = fopen(path, "rb");
                assert(fp != NULL);
                assert(map_cache_read_header(fp, &head, &dummy));
                fclose(fp);
        }
}

int main(void)
{
        char tmpl[] = "/tmp/mapcache_testXXXXXX";
        int fd = mkstemp(tmpl);
        close(fd);
        unlink(tmpl);

        write_v1_fixture(tmpl);
        test_upgrade_and_read(tmpl);
        test_write_new(tmpl);

        unlink(tmpl);
        return 0;
}
