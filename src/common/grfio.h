// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef	_GRFIO_H_
#define	_GRFIO_H_

#include <stddef.h>
#include <stdint.h>

void grfio_init(char*);			// GRFIO Initialize
void grfio_final(void);			// GRFIO Finalize
void* grfio_reads(char*, size_t*);	// GRFIO data file read & size get
char *grfio_find_file(char *fname);

#define grfio_read(fn) grfio_reads(fn, NULL)

int grfio_size(char*);			// GRFIO data file size get
unsigned long grfio_crc32(const unsigned char *buf, unsigned int len);

int decode_zip(unsigned char *dest, unsigned long* destLen, const unsigned char* source, unsigned long sourceLen);
int encode_zip(unsigned char *dest, unsigned long* destLen, const unsigned char* source, unsigned long sourceLen);

#ifdef UA_TESTING
void grfio_test_reset(void);
void grfio_test_set_data_dir(const char* path);
int grfio_test_register_local(const char* fname, uint64_t declen);
int grfio_test_register_grf(const char* grfname, const char* fname, uint64_t srcpos,
                uint64_t srclen, uint64_t srclen_aligned, uint64_t declen, int type);
#endif

#endif /* _GRFIO_H_ */
