#include "../../src/common/showmsg.h"
#include "../../src/common/malloc.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int stdout_with_ansisequence = 0;
int msg_silent = 0;
char timestamp_format[20] = "";

static int vprint(FILE* stream, const char* prefix, const char* fmt, va_list ap)
{
        int written = 0;

        if (prefix != NULL && *prefix != '\0')
                written += fprintf(stream, "%s", prefix);

        written += vfprintf(stream, fmt, ap);
        return written;
}

static int print_message(FILE* stream, const char* prefix, const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stream, prefix, fmt, ap);
        va_end(ap);

        return result;
}

void ClearScreen(void)
{
        /* no-op in tests */
}

int ShowMessage(const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stdout, "", fmt, ap);
        va_end(ap);
        return result;
}

int ShowStatus(const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stdout, "[status] ", fmt, ap);
        va_end(ap);
        return result;
}

int ShowSQL(const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stdout, "[sql] ", fmt, ap);
        va_end(ap);
        return result;
}

int ShowInfo(const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stdout, "[info] ", fmt, ap);
        va_end(ap);
        return result;
}

int ShowNotice(const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stdout, "[notice] ", fmt, ap);
        va_end(ap);
        return result;
}

int ShowWarning(const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stderr, "[warning] ", fmt, ap);
        va_end(ap);
        return result;
}

int ShowDebug(const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stdout, "[debug] ", fmt, ap);
        va_end(ap);
        return result;
}

int ShowError(const char* fmt, ...)
{
        va_list ap;
        int result;

        va_start(ap, fmt);
        result = vprint(stderr, "[error] ", fmt, ap);
        va_end(ap);
        return result;
}

int ShowFatalError(const char* fmt, ...)
{
        va_list ap;

        va_start(ap, fmt);
        vprint(stderr, "[fatal] ", fmt, ap);
        va_end(ap);
        abort();
}

void* _mmalloc(size_t size, const char* file, int line, const char* func)
{
        (void)file;
        (void)line;
        (void)func;
        return malloc(size);
}

void* _mcalloc(size_t num, size_t size, const char* file, int line, const char* func)
{
        (void)file;
        (void)line;
        (void)func;
        return calloc(num, size);
}

void* _mrealloc(void* ptr, size_t size, const char* file, int line, const char* func)
{
        (void)file;
        (void)line;
        (void)func;
        return realloc(ptr, size);
}

char* _mstrdup(const char* src, const char* file, int line, const char* func)
{
        (void)file;
        (void)line;
        (void)func;
        if (src == NULL)
                return NULL;
        size_t len = strlen(src) + 1;
        char* copy = (char*)malloc(len);
        if (copy != NULL)
                memcpy(copy, src, len);
        return copy;
}

void _mfree(void* ptr, const char* file, int line, const char* func)
{
        (void)file;
        (void)line;
        (void)func;
        free(ptr);
}

unsigned int malloc_usage(void)
{
        return 0;
}

void malloc_init(void)
{
        /* nothing to initialize for the test stubs */
}
