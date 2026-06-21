// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#include "../common/cbasetypes.h"
#include "../common/showmsg.h"
#include "lock.h"

#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>

#define exists(filename) (!access(filename, F_OK))

// �������݃t�@�C���̕ی쏈��
// �i�������݂��I���܂ŁA���t�@�C����ۊǂ��Ă����j

// �V�����t�@�C���̏������݊J�n
FILE* lock_fopen (const char* filename, int *info) {
	char newfile[512];
	FILE *fp;
	int no = 0;

	// ���S�ȃt�@�C�����𓾂�i�蔲���j
	do {
		sprintf(newfile, "%s_%04d.tmp", filename, ++no);
	} while((fp = fopen(newfile,"r")) && (fclose(fp), no < 9999));
	*info = no;
	return fopen(newfile,"w");
}

// ���t�@�C�����폜���V�t�@�C�������l�[��
int lock_fclose (FILE *fp, const char* filename, int *info) {
	int ret = 1;
	char newfile[512];
	char oldfile[512];
	if (fp != NULL) {
		ret = fclose(fp);
		sprintf(newfile, "%s_%04d.tmp", filename, *info);
		sprintf(oldfile, "%s.bak", filename);	// old backup file

		if (exists(oldfile)) remove(oldfile);	// remove backup file if it already exists
		rename (filename, oldfile);				// backup our older data instead of deleting it

		// ���̃^�C�~���O�ŗ�����ƍň��B
		if ((ret = rename(newfile,filename)) != 0) {	// rename our temporary file to its correct name
			char ebuf[255];
			ebuf[0] = '\0';
			if (strerror_r(errno, ebuf, sizeof(ebuf)) != 0 || ebuf[0] == '\0')
				snprintf(ebuf, sizeof(ebuf), "errno %d", errno);
			ShowError("%s - '"CL_WHITE"%s"CL_RESET"'\n", ebuf, newfile);
		}
	}

	return ret;
}
