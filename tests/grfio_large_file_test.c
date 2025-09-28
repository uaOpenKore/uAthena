#include "../src/common/grfio.h"
#include "../src/common/malloc.h"

#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

static void create_directory(const char* path)
{
        if (mkdir(path, 0700) == -1 && errno != EEXIST) {
                perror("mkdir");
                exit(EXIT_FAILURE);
        }
}

static void join_path(char* dest, size_t dest_size, const char* base, const char* leaf)
{
        int written;

        written = snprintf(dest, dest_size, "%s/%s", base, leaf);
        if (written < 0 || (size_t)written >= dest_size) {
                fprintf(stderr, "path too long: %s/%s\n", base, leaf);
                exit(EXIT_FAILURE);
        }
}

static void remove_file(const char* path)
{
        if (unlink(path) == -1) {
                perror("unlink");
        }
}

static void remove_directory(const char* path)
{
        if (rmdir(path) == -1) {
                perror("rmdir");
        }
}

static void create_sparse_file(const char* path, uint64_t offset, const unsigned char* payload, size_t payload_size, int payload_at_offset)
{
        FILE* fp;

        fp = fopen(path, "wb");
        if (fp == NULL) {
                perror("fopen");
                exit(EXIT_FAILURE);
        }

        if (!payload_at_offset) {
                if (fwrite(payload, 1, payload_size, fp) != payload_size) {
                        perror("fwrite");
                        fclose(fp);
                        exit(EXIT_FAILURE);
                }
        }

        if (offset > (uint64_t)INT64_MAX) {
                fprintf(stderr, "offset %" PRIu64 " exceeds INT64_MAX\n", offset);
                fclose(fp);
                exit(EXIT_FAILURE);
        }

        if (fseeko(fp, (off_t)offset, SEEK_SET) != 0) {
                perror("fseeko");
                fclose(fp);
                exit(EXIT_FAILURE);
        }

        if (payload_at_offset) {
                if (fwrite(payload, 1, payload_size, fp) != payload_size) {
                        perror("fwrite");
                        fclose(fp);
                        exit(EXIT_FAILURE);
                }
        } else {
                unsigned char zero = 0;
                if (fwrite(&zero, 1, 1, fp) != 1) {
                        perror("fwrite");
                        fclose(fp);
                        exit(EXIT_FAILURE);
                }
        }

        if (fclose(fp) != 0) {
                perror("fclose");
                exit(EXIT_FAILURE);
        }
}

static void expect_equal_buffer(const unsigned char* lhs, const unsigned char* rhs, size_t len)
{
        assert(lhs != NULL);
        assert(rhs != NULL);
        assert(memcmp(lhs, rhs, len) == 0);
}

static void test_local_sparse_file(void)
{
        static const unsigned char payload[] = "SparseLocalPayload";
        const size_t payload_size = sizeof(payload) - 1;
        const uint64_t large_offset = (UINT64_C(1) << 32) + 4096;
        char tmp_template[] = "/tmp/grfio-local-XXXXXX";
        char data_dir_path[PATH_MAX];
        char data_path[PATH_MAX];
        char file_path[PATH_MAX];
        char* tmp_root;
        unsigned char* buffer;
        size_t size = 0;

        tmp_root = mkdtemp(tmp_template);
        if (tmp_root == NULL) {
                perror("mkdtemp");
                exit(EXIT_FAILURE);
        }

        join_path(data_dir_path, sizeof(data_dir_path), tmp_root, "");
        join_path(data_path, sizeof(data_path), tmp_root, "data");
        create_directory(data_path);

        join_path(file_path, sizeof(file_path), data_path, "large_local.bin");
        create_sparse_file(file_path, large_offset, payload, payload_size, 0);

        grfio_test_reset();
        grfio_test_set_data_dir(data_dir_path);
        assert(grfio_test_register_local("data\\large_local.bin", payload_size) == 0);

        printf("[test] reading local sparse file at >4GB offset\n");
        fflush(stdout);
        buffer = (unsigned char*)grfio_reads("data\\large_local.bin", &size);
        assert(buffer != NULL);
        assert(size == payload_size);
        expect_equal_buffer(buffer, payload, payload_size);
        aFree(buffer);
        grfio_final();

        remove_file(file_path);
        remove_directory(data_path);
        remove_directory(tmp_root);
}

static void test_grf_sparse_entry(void)
{
        static const unsigned char payload[] = "SparseGRFPayload";
        const size_t payload_size = sizeof(payload) - 1;
        const uint64_t large_offset = (UINT64_C(1) << 32) + 8192;
        char tmp_template[] = "/tmp/grfio-grf-XXXXXX";
        char grf_path[PATH_MAX];
        char entry_name[] = "data\\large_grf.bin";
        char* tmp_root;
        unsigned char* buffer;
        size_t size = 0;

        tmp_root = mkdtemp(tmp_template);
        if (tmp_root == NULL) {
                perror("mkdtemp");
                exit(EXIT_FAILURE);
        }

        join_path(grf_path, sizeof(grf_path), tmp_root, "large_test.grf");
        create_sparse_file(grf_path, large_offset, payload, payload_size, 1);

        grfio_test_reset();
        grfio_test_set_data_dir("");
        assert(grfio_test_register_grf(grf_path, entry_name, large_offset, payload_size,
                        payload_size, payload_size, 0) == 0);

        printf("[test] reading GRF entry at >4GB offset\n");
        fflush(stdout);
        buffer = (unsigned char*)grfio_reads(entry_name, &size);
        assert(buffer != NULL);
        assert(size == payload_size);
        expect_equal_buffer(buffer, payload, payload_size);
        aFree(buffer);
        grfio_final();

        remove_file(grf_path);
        remove_directory(tmp_root);
}

int main(void)
{
        test_local_sparse_file();
        test_grf_sparse_entry();
        puts("[result] large file and offset tests passed");
        fflush(stdout);
        return 0;
}
