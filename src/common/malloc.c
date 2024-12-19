// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "malloc.h"
#include "../common/core.h"
#include "../common/showmsg.h"

#ifdef MINICORE
	#undef LOG_MEMMGR
#endif

void* aMalloc_ (size_t size, const char *file, int line, const char *func)
{
#ifndef MEMWATCH
	void *ret = MALLOC(size);
#else
	void *ret = mwMalloc(size, file, line);
#endif
	// ShowMessage("%s:%d: in func %s: malloc %d\n",file,line,func,size);
	if (ret == NULL){
		ShowFatalError("%s:%d: in func %s: malloc error out of memory!\n",file,line,func);
		exit(1);
	}

	return ret;
}
void* aMallocA_ (size_t size, const char *file, int line, const char *func)
{
#ifndef MEMWATCH
	void *ret = MALLOCA(size);
#else
	void *ret = mwMalloc(size, file, line);
#endif
	// ShowMessage("%s:%d: in func %s: malloc %d\n",file,line,func,size);
	if (ret == NULL){
		ShowFatalError("%s:%d: in func %s: malloc error out of memory!\n",file,line,func);
		exit(1);
	}

	return ret;
}
void* aCalloc_ (size_t num, size_t size, const char *file, int line, const char *func)
{
#ifndef MEMWATCH
	void *ret = CALLOC(num, size);
#else
	void *ret = mwCalloc(num, size, file, line);
#endif
	// ShowMessage("%s:%d: in func %s: calloc %d %d\n",file,line,func,num,size);
	if (ret == NULL){
		ShowFatalError("%s:%d: in func %s: calloc error out of memory!\n", file, line, func);
		exit(1);
	}
	return ret;
}
void* aCallocA_ (size_t num, size_t size, const char *file, int line, const char *func)
{
#ifndef MEMWATCH
	void *ret = CALLOCA(num, size);
#else
	void *ret = mwCalloc(num, size, file, line);
#endif
	// ShowMessage("%s:%d: in func %s: calloc %d %d\n",file,line,func,num,size);
	if (ret == NULL){
		ShowFatalError("%s:%d: in func %s: calloc error out of memory!\n",file,line,func);
		exit(1);
	}
	return ret;
}
void* aRealloc_ (void *p, size_t size, const char *file, int line, const char *func)
{
#ifndef MEMWATCH
	void *ret = REALLOC(p, size);
#else
	void *ret = mwRealloc(p, size, file, line);
#endif
	// ShowMessage("%s:%d: in func %s: realloc %p %d\n",file,line,func,p,size);
	if (ret == NULL){
		ShowFatalError("%s:%d: in func %s: realloc error out of memory!\n",file,line,func);
		exit(1);
	}
	return ret;
}
char* aStrdup_ (const char *p, const char *file, int line, const char *func)
{
#ifndef MEMWATCH
	char *ret = STRDUP(p);
#else
	char *ret = mwStrdup(p, file, line);
#endif
	// ShowMessage("%s:%d: in func %s: strdup %p\n",file,line,func,p);
	if (ret == NULL){
		ShowFatalError("%s:%d: in func %s: strdup error out of memory!\n", file, line, func);
		exit(1);
	}
	return ret;
}
void aFree_ (void *p, const char *file, int line, const char *func)
{
	// ShowMessage("%s:%d: in func %s: free %p\n",file,line,func,p);
	if (p)
	#ifndef MEMWATCH
		FREE(p);
	#else
		mwFree(p, file, line);
	#endif

	p = NULL;
}

#ifdef GCOLLECT

void* _bcallocA(size_t size, size_t cnt)
{
	void *ret = MALLOCA(size * cnt);
	if (ret) memset(ret, 0, size * cnt);
	return ret;
}
void* _bcalloc(size_t size, size_t cnt)
{
	void *ret = MALLOC(size * cnt);
	if (ret) memset(ret, 0, size * cnt);
	return ret;
}
char* _bstrdup(const char *chr)
{
	int len = strlen(chr);
	char *ret = (char*)MALLOC(len + 1);
	if (ret) memcpy(ret, chr, len + 1);
	return ret;
}

#endif

#ifdef USE_MEMMGR

/* USE_MEMMGR */

/*
 * �������}�l�[�W��
 *     malloc , free �̏����������I�ɏo����悤�ɂ������́B
 *     ���G�ȏ������s���Ă���̂ŁA�኱�d���Ȃ邩������܂���B
 *
 * �f�[�^�\���Ȃǁi��������ł����܂���^^; �j
 *     �E�������𕡐��́u�u���b�N�v�ɕ����āA����Ƀu���b�N�𕡐��́u���j�b�g�v
 *       �ɕ����Ă��܂��B���j�b�g�̃T�C�Y�́A�P�u���b�N�̗e�ʂ𕡐��ɋϓ��z��
 *       �������̂ł��B���Ƃ��΁A�P���j�b�g32KB�̏ꍇ�A�u���b�N�P��32Byte�̃�
 *       �j�b�g���A1024�W�܂��ďo���Ă�����A64Byte�̃��j�b�g�� 512�W�܂���
 *       �o���Ă����肵�܂��B�ipadding,unit_head �������j
 *
 *     �E�u���b�N���m�̓����N���X�g(block_prev,block_next) �łȂ���A�����T�C
 *       �Y�����u���b�N���m�������N���X�g(samesize_prev,samesize_nect) �ł�
 *       �����Ă��܂��B����ɂ��A�s�v�ƂȂ����������̍ė��p�������I�ɍs���܂��B
 */

/* �u���b�N�ɓ���f�[�^�� */
#define BLOCK_DATA_SIZE	80*1024

/* ��x�Ɋm�ۂ���u���b�N�̐��B */
#define BLOCK_ALLOC		32

/* �u���b�N�̃A���C�����g */
#define BLOCK_ALIGNMENT	64

/* �u���b�N */
struct block {
	int    block_no;		/* �u���b�N�ԍ� */
	struct block* block_prev;		/* �O�Ɋm�ۂ����̈� */
	struct block* block_next;		/* ���Ɋm�ۂ����̈� */
	int    samesize_no;     /* �����T�C�Y�̔ԍ� */
	struct block* samesize_prev;	/* �����T�C�Y�̑O�̗̈� */
	struct block* samesize_next;	/* �����T�C�Y�̎��̗̈� */
	size_t unit_size;		/* ���j�b�g�̃o�C�g�� 0=���g�p */
	size_t unit_hash;		/* ���j�b�g�̃n�b�V�� */
	int    unit_count;		/* ���j�b�g�̐� */
	int    unit_used;		/* �g�p�ς݃��j�b�g */
	char   data[BLOCK_DATA_SIZE];
};

struct unit_head {
	struct block* block;
	size_t size;
	const  char* file;
	int    line;
	unsigned int checksum;
};

struct chunk {
	char *block;
	struct chunk *next;
};

static struct block* block_first  = NULL;
static struct block* block_last   = NULL;
static struct block* block_unused = NULL;

/* ���j�b�g�ւ̃n�b�V���B80KB/64Byte = 1280�� */
static struct block* unit_first[BLOCK_DATA_SIZE/BLOCK_ALIGNMENT];		/* �ŏ� */
static struct block* unit_unfill[BLOCK_DATA_SIZE/BLOCK_ALIGNMENT];	/* ���܂��ĂȂ� */
static struct block* unit_last[BLOCK_DATA_SIZE/BLOCK_ALIGNMENT];		/* �Ō� */

/* ���������g���񂹂Ȃ��̈�p�̃f�[�^ */
struct unit_head_large {
	struct unit_head_large* prev;
	struct unit_head_large* next;
	struct unit_head        unit_head;
};
static struct unit_head_large *unit_head_large_first = NULL;

static struct chunk *chunk_first = NULL;

static struct block* block_malloc(void);
static void   block_free(struct block* p);
static void memmgr_info(void);
static unsigned int memmgr_usage_bytes = 0;

void* _mmalloc(size_t size, const char *file, int line, const char *func ) {
	int i;
	struct block *block;
	size_t size_hash;

	if (((long) size) < 0) {
		printf("_mmalloc: %d\n", size);
		return 0;
	}
	
	size_hash = (size+BLOCK_ALIGNMENT-1) / BLOCK_ALIGNMENT;
	if(size == 0) {
		return NULL;
	}
	memmgr_usage_bytes += size;

	/* �u���b�N���𒴂���̈�̊m�ۂɂ́Amalloc() ��p���� */
	/* ���̍ہAunit_head.block �� NULL �������ċ�ʂ��� */
	if(size_hash * BLOCK_ALIGNMENT > BLOCK_DATA_SIZE - sizeof(struct unit_head)) {
#ifdef MEMWATCH
		struct unit_head_large* p = (struct unit_head_large*)mwMalloc(sizeof(struct unit_head_large) + size,file,line);
#else
		struct unit_head_large* p = (struct unit_head_large*) MALLOC (sizeof(struct unit_head_large) + size);
#endif
		if(p != NULL) {
			p->unit_head.block = NULL;
			p->unit_head.size  = size;
			p->unit_head.file  = file;
			p->unit_head.line  = line;
			p->prev = NULL;
			if (unit_head_large_first == NULL)
				p->next = NULL;
			else {
				unit_head_large_first->prev = p;
				p->next = unit_head_large_first;
			}
			unit_head_large_first = p;
			*(int*)((char*)p + sizeof(struct unit_head_large) - sizeof(int) + size) = 0xdeadbeaf;
			return (char *)p + sizeof(struct unit_head_large) - sizeof(int);
		} else {
			ShowFatalError("Memory manager::memmgr_alloc failed (allocating %d+%d bytes at %s:%d).\n", sizeof(struct unit_head_large), size, file, line);
			exit(1);
		}
	}

	/* ����T�C�Y�̃u���b�N���m�ۂ���Ă��Ȃ����A�V���Ɋm�ۂ��� */
	if(unit_unfill[size_hash] == NULL) {
		block = block_malloc();
		if(unit_first[size_hash] == NULL) {
			/* ����m�� */
			unit_first[size_hash] = block;
			unit_last[size_hash] = block;
			block->samesize_no = 0;
			block->samesize_prev = NULL;
			block->samesize_next = NULL;
		} else {
			/* �A����� */
			unit_last[size_hash]->samesize_next = block;
			block->samesize_no   = unit_last[size_hash]->samesize_no + 1;
			block->samesize_prev = unit_last[size_hash];
			block->samesize_next = NULL;
			unit_last[size_hash] = block;
		}
		unit_unfill[size_hash] = block;
		block->unit_size  = size_hash * BLOCK_ALIGNMENT + sizeof(struct unit_head);
		block->unit_count = (int)(BLOCK_DATA_SIZE / block->unit_size);
		block->unit_used  = 0;
		block->unit_hash  = size_hash;
		/* ���g�pFlag�𗧂Ă� */
		for(i=0;i<block->unit_count;i++) {
			((struct unit_head*)(&block->data[block->unit_size * i]))->block = NULL;
		}
	}
	/* ���j�b�g�g�p�����Z */
	block = unit_unfill[size_hash];
	block->unit_used++;

	/* ���j�b�g����S�Ďg���ʂ����� */
	if(block->unit_count == block->unit_used) {
		do {
			unit_unfill[size_hash] = unit_unfill[size_hash]->samesize_next;
		} while(
			unit_unfill[size_hash] != NULL &&
			unit_unfill[size_hash]->unit_count == unit_unfill[size_hash]->unit_used
		);
	}

	/* �u���b�N�̒��̋󂫃��j�b�g�{�� */
	for(i=0;i<block->unit_count;i++) {
		struct unit_head *head = (struct unit_head*)(&block->data[block->unit_size * i]);
		if(head->block == NULL) {
			head->block = block;
			head->size  = size;
			head->line  = line;
			head->file  = file;
			*(int*)((char*)head + sizeof(struct unit_head) - sizeof(int) + size) = 0xdeadbeaf;
			return (char *)head + sizeof(struct unit_head) - sizeof(int);
		}
	}
	// �����ɗ��Ă͂����Ȃ��B
	ShowFatalError("Memory manager::memmgr_malloc() serious error (allocating %d+%d bytes at %s:%d)\n", sizeof(struct unit_head_large), size, file, line);
	memmgr_info();
	exit(1);
	return NULL;
};

void* _mcalloc(size_t num, size_t size, const char *file, int line, const char *func ) {
	void *p = _mmalloc(num * size,file,line,func);
	memset(p,0,num * size);
	return p;
}

void* _mrealloc(void *memblock, size_t size, const char *file, int line, const char *func ) {
	size_t old_size;
	if(memblock == NULL) {
		return _mmalloc(size,file,line,func);
	}

	old_size = ((struct unit_head *)((char *)memblock - sizeof(struct unit_head) + sizeof(int)))->size;
	if(old_size > size) {
		// �T�C�Y�k�� -> ���̂܂ܕԂ��i�蔲���j
		return memblock;
	}  else {
		// �T�C�Y�g��
		void *p = _mmalloc(size,file,line,func);
		if(p != NULL) {
			memcpy(p,memblock,old_size);
		}
		_mfree(memblock,file,line,func);
		return p;
	}
}

char* _mstrdup(const char *p, const char *file, int line, const char *func ) {
	if(p == NULL) {
		return NULL;
	} else {
		size_t len = strlen(p);
		char *string  = (char *)_mmalloc(len + 1,file,line,func);
		memcpy(string,p,len+1);
		return string;
	}
}

void _mfree(void *ptr, const char *file, int line, const char *func ) {
	struct unit_head *head;
	size_t size_hash;

	if (ptr == NULL)
		return; 

	head = (struct unit_head *)((char *)ptr - sizeof(struct unit_head) + sizeof(int));
	size_hash = (head->size+BLOCK_ALIGNMENT-1) / BLOCK_ALIGNMENT;

	if(head->block == NULL) {
		if(size_hash * BLOCK_ALIGNMENT > BLOCK_DATA_SIZE - sizeof(struct unit_head)) {
			/* malloc() �Œ��Ɋm�ۂ��ꂽ�̈� */
			struct unit_head_large *head_large = (struct unit_head_large *)((char *)ptr - sizeof(struct unit_head_large) + sizeof(int));
			if(
				*(int*)((char*)head_large + sizeof(struct unit_head_large) - sizeof(int) + head->size)
				!= 0xdeadbeaf)
			{
				ShowError("Memory manager: args of aFree is overflowed pointer %s line %d\n", file, line);
			}
			if(head_large->prev) {
				head_large->prev->next = head_large->next;
			} else {
				unit_head_large_first  = head_large->next;
			}
			if(head_large->next) {
				head_large->next->prev = head_large->prev;
			}
			head->block = NULL;
			memmgr_usage_bytes -= head->size;
			FREE (head_large);			
		} else {
			ShowError("Memory manager: args of aFree is freed pointer %s line %d\n", file, line);
		}
		ptr = NULL;
		return;
	} else {
		/* ���j�b�g��� */
		struct block *block = head->block;
		if((unsigned long)block % sizeof(struct block) != 0) {
			ShowError("Memory manager: args of aFree is not valid pointer %s line %d\n", file, line);
		} else if(*(int*)((char*)head + sizeof(struct unit_head) - sizeof(int) + head->size) != 0xdeadbeaf) {
			ShowError("Memory manager: args of aFree is overflowed pointer %s line %d\n", file, line);
		} else {
			head->block = NULL;
			memmgr_usage_bytes -= head->size;
			if(--block->unit_used == 0) {
				/* �u���b�N�̉�� */
				if(unit_unfill[block->unit_hash] == block) {
					/* �󂫃��j�b�g�Ɏw�肳��Ă��� */
					do {
						unit_unfill[block->unit_hash] = unit_unfill[block->unit_hash]->samesize_next;
					} while(
						unit_unfill[block->unit_hash] != NULL &&
						unit_unfill[block->unit_hash]->unit_count == unit_unfill[block->unit_hash]->unit_used
					);
				}
				if(block->samesize_prev == NULL && block->samesize_next == NULL) {
					/* �Ɨ��u���b�N�̉�� */
					unit_first[block->unit_hash]  = NULL;
					unit_last[block->unit_hash]   = NULL;
					unit_unfill[block->unit_hash] = NULL;
				} else if(block->samesize_prev == NULL) {
					/* �擪�u���b�N�̉�� */
					unit_first[block->unit_hash] = block->samesize_next;
					(block->samesize_next)->samesize_prev = NULL;
				} else if(block->samesize_next == NULL) {
					/* ���[�u���b�N�̉�� */
					unit_last[block->unit_hash] = block->samesize_prev; 
					(block->samesize_prev)->samesize_next = NULL;
				} else {
					/* ���ԃu���b�N�̉�� */
					(block->samesize_next)->samesize_prev = block->samesize_prev;
					(block->samesize_prev)->samesize_next = block->samesize_next;
				}
				block_free(block);
			} else {
				/* �󂫃��j�b�g�̍Đݒ� */
				if(
					unit_unfill[block->unit_hash] == NULL ||
					unit_unfill[block->unit_hash]->samesize_no > block->samesize_no
				) {
					unit_unfill[block->unit_hash] = block;
				}
			}
			ptr = NULL;
		}
	}
}

/* ���݂̏󋵂�\������ */
static void memmgr_info(void) {
	int i;
	struct block *p;
	ShowInfo("** Memory Manager Information **\n");
	if(block_first == NULL) {
		ShowMessage("Uninitialized.\n");
		return;
	}
	ShowMessage(
		"Blocks: %04u , BlockSize: %06u Byte , Used: %08uKB\n",
		block_last->block_no+1,sizeof(struct block),
		(block_last->block_no+1) * sizeof(struct block) / 1024
	);
	p = block_first;
	for(i=0;i<=block_last->block_no;i++) {
		ShowMessage("    Block #%04u : ",p->block_no);
		if(p->unit_size == 0) {
			ShowMessage("unused.\n");
		} else {
			ShowMessage(
				"size: %05u byte. used: %04u/%04u prev:",
				p->unit_size - sizeof(struct unit_head),p->unit_used,p->unit_count
			);
			if(p->samesize_prev == NULL) {
				ShowMessage("NULL");
			} else {
				ShowMessage("%04u",(p->samesize_prev)->block_no);
			}
			ShowMessage(" next:");
			if(p->samesize_next == NULL) {
				ShowMessage("NULL");
			} else {
				ShowMessage("%04u",(p->samesize_next)->block_no);
			}
			ShowMessage("\n");
		}
		p = p->block_next;
	}
}

/* �u���b�N���m�ۂ��� */
static struct block* block_malloc(void) {
	if(block_unused != NULL) {
		/* �u���b�N�p�̗̈�͊m�ۍς� */
		struct block* ret = block_unused;
		do {
			block_unused = block_unused->block_next;
		} while(block_unused != NULL && block_unused->unit_size != 0);
		return ret;
	} else {
		/* �u���b�N�p�̗̈��V���Ɋm�ۂ��� */
		int i;
		int block_no;
		struct block* p;
		struct chunk* chunk;
		char *pb = (char *) CALLOC (sizeof(struct block),BLOCK_ALLOC + 1);
		if(pb == NULL) {
			ShowFatalError("Memory manager::block_alloc failed.\n");
			exit(1);
		}

		// store original block address in chunk
		chunk = (struct chunk *) MALLOC (sizeof(struct chunk));
		if (chunk == NULL) {
			ShowFatalError("Memory manager::block_alloc failed.\n");
			exit(1);
		}
		chunk->block = pb;
		chunk->next = (chunk_first) ? chunk_first : NULL;
		chunk_first = chunk;

		// �u���b�N�̃|�C���^�̐擪��sizeof(block) �A���C�����g�ɑ�����
		// ���̃A�h���X��free() ���邱�Ƃ͂Ȃ��̂ŁA���ڃ|�C���^��ύX���Ă���B
		pb += sizeof(struct block) - ((unsigned long)pb % sizeof(struct block));
		p   = (struct block*)pb;
		if(block_first == NULL) {
			/* ����m�� */
			block_no     = 0;
			block_first  = p;
		} else {
			block_no      = block_last->block_no + 1;
			block_last->block_next = p;
			p->block_prev = block_last;
		}
		block_last = &p[BLOCK_ALLOC - 1];
		/* �u���b�N��A�������� */
		for(i=0;i<BLOCK_ALLOC;i++) {
			if(i != 0) {
				p[i].block_prev = &p[i-1];
			}
			if(i != BLOCK_ALLOC -1) {
				p[i].block_next = &p[i+1];
			}
			p[i].block_no = block_no + i;
		}

		/* ���g�p�u���b�N�ւ̃|�C���^���X�V */
		block_unused = &p[1];
		p->unit_size = 1;
		return p;
	}
}

static void block_free(struct block* p) {
	/* free() �����ɁA���g�p�t���O��t���邾�� */
	p->unit_size = 0;
	/* ���g�p�|�C���^�[���X�V���� */
	if(block_unused == NULL) {
		block_unused = p;
	} else if(block_unused->block_no > p->block_no) {
		block_unused = p;
	}
}

unsigned int memmgr_usage (void)
{
	return memmgr_usage_bytes / 1024;
}

#ifdef LOG_MEMMGR
static char memmer_logfile[128];
static FILE *log_fp;

static void memmgr_log (char *buf)
{
	if (!log_fp) {
		log_fp = fopen(memmer_logfile,"w");
		if (!log_fp) log_fp = stdout;
		fprintf(log_fp, "Memory manager: Memory leaks found.\n");
	}
	fprintf(log_fp, buf);
	return;
}
#endif

static void memmgr_final (void)
{
	struct block *block = block_first;
	struct chunk *chunk = chunk_first, *chunk2;
	struct unit_head_large *large = unit_head_large_first, *large2;
	int i;

#ifdef LOG_MEMMGR
	int count = 0;
	char buf[128];
#endif
	
	while (block) {
		if (block->unit_size) {
			for (i = 0; i < block->unit_count; i++) {
				struct unit_head *head = (struct unit_head*)(&block->data[block->unit_size * i]);
				if(head->block != NULL)
				{
				#ifdef LOG_MEMMGR
					sprintf (buf,
						"%04d : %s line %d size %d\n", ++count,
						head->file, head->line, head->size);
					memmgr_log (buf);
				#endif
					// get block pointer and free it [celest]
					_mfree ((char *)head + sizeof(struct unit_head) - sizeof(int), ALC_MARK);
				}
			}
		}
		//if (block->block_no >= block2->block_no + BLOCK_ALLOC - 1) {
			// reached a new block array
			//block = block->block_next;

		/* Okay wise guys... this is how block2 was allocated: [Skotlex]
		struct block* p;
		char *pb = (char *) CALLOC (sizeof(struct block),BLOCK_ALLOC + 1);
		pb += sizeof(struct block) - ((unsigned long)pb % sizeof(struct block));
		p   = (struct block*)pb;
		
		The reason we get an invalid pointer is that we allocated pb, not p.
		So how do you get pb when you only have p? 
		The answer is, you can't, because the original pointer was lost when
		memory-aligning the block. So we either forget this FREE or use a
		self-reference...
		Since we are already quitting, it might be ok to just not free the block
		as it is. 
		 */
		// didn't realise that before o.o -- block chunks are now freed below [celest]
		//	FREE(block2);
			//block2 = block;
			//continue;
		//}
		block = block->block_next;
	}

	// free the allocated block chunks
	chunk = chunk_first;
	while (chunk) {
		chunk2 = chunk->next;
		FREE(chunk->block);
		FREE(chunk);
		chunk = chunk2;
	}

	while(large) {
		large2 = large->next;
	#ifdef LOG_MEMMGR
		sprintf (buf,
			"%04d : %s line %d size %d\n", ++count,
			large->unit_head.file, large->unit_head.line, large->unit_head.size);
		memmgr_log (buf);
	#endif
		FREE (large);
		large = large2;
	}
#ifdef LOG_MEMMGR
	if(count == 0) {
		ShowInfo("Memory manager: No memory leaks found.\n");
	} else {
		ShowWarning("Memory manager: Memory leaks found and fixed.\n");
		fclose(log_fp);
	}
#endif
	return;
}

static void memmgr_init (void)
{
	#ifdef LOG_MEMMGR
		sprintf(memmer_logfile, "log/%s.leaks", SERVER_NAME);
		ShowStatus("Memory manager initialised: "CL_WHITE"%s"CL_RESET"\n", memmer_logfile);
	#endif
	return;
}
#endif


/*======================================
 * Initialise
 *--------------------------------------
 */

unsigned int malloc_usage (void)
{
#ifdef USE_MEMMGR
	return memmgr_usage ();
#else
	return 0;
#endif
}

void malloc_final (void)
{
#ifdef USE_MEMMGR
	memmgr_final ();
#endif
	return;
}

void malloc_init (void)
{
#ifdef USE_MEMMGR
	memmgr_init ();
#endif
	return;
}
