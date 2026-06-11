// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#include "../common/cbasetypes.h"
#include "../common/utils.h"
#include "showmsg.h"

#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>
#include <stdlib.h> // atexit

#include <unistd.h>

#ifdef DEBUGLOGMAP
	#define DEBUGLOGPATH "log/map-server.log"
#else
	#ifdef DEBUGLOGCHAR
		#define DEBUGLOGPATH "log/char-server.log"
	#else
		#ifdef DEBUGLOGLOGIN
			#define DEBUGLOGPATH "log/login-server.log"
		#endif
	#endif
#endif

///////////////////////////////////////////////////////////////////////////////
/// behavioral parameter.
/// when redirecting output:
/// if true prints escape sequences
/// if false removes the escape sequences
int stdout_with_ansisequence = 0;

int msg_silent = 0; //Specifies how silent the console is.

///////////////////////////////////////////////////////////////////////////////
/// static/dynamic buffer for the messages

#define SBUF_SIZE 2048 // never put less that what's required for the debug message

#define NEWBUF(buf)				\
	struct {					\
		char s_[SBUF_SIZE];		\
		struct StringBuf *d_;	\
		char *v_;				\
		int l_;					\
	} buf ={"",NULL,NULL,0};	\
//define NEWBUF

#define BUFVPRINTF(buf,fmt,args)						\
	buf.l_ = vsnprintf(buf.s_, SBUF_SIZE, fmt, args);	\
	if( buf.l_ >= 0 && buf.l_ < SBUF_SIZE )				\
	{/* static buffer */								\
		buf.v_ = buf.s_;								\
	}													\
	else												\
	{/* dynamic buffer */								\
		buf.d_ = StringBuf_Malloc();					\
		buf.l_ = StringBuf_Vprintf(buf.d_, fmt, args);	\
		buf.v_ = StringBuf_Value(buf.d_);				\
		ShowDebug("showmsg: dynamic buffer used, increase the static buffer size to %d or more.", buf.l_+1);\
	}													\
//define BUFVPRINTF

#define BUFVAL(buf) buf.v_
#define BUFLEN(buf) buf.l_

#define FREEBUF(buf)			\
	if( buf.d_ )				\
	{							\
		StringBuf_Free(buf.d_);	\
		buf.d_ = NULL;			\
	}							\
	buf.v_ = NULL;				\
//define FREEBUF

#define is_console(file) (0!=isatty(fileno(file)))


//#define VPRINTF	vprintf
//#define PRINTF	printf

#define is_console(file) (0!=isatty(fileno(file)))

//vprintf_without_ansiformats
int	VFPRINTF(FILE *file, const char *fmt, va_list argptr)
{
	char *p, *q;
	NEWBUF(tempbuf); // temporary buffer

	if(!fmt || !*fmt)
		return 0;

	if( is_console(file) || stdout_with_ansisequence )
	{
		vfprintf(file, fmt, argptr);
		return 0;
	}

	// Print everything to the buffer
	BUFVPRINTF(tempbuf,fmt,argptr);

	// start with processing
	p = BUFVAL(tempbuf);
	while ((q = strchr(p, 0x1b)) != NULL)
	{	// find the escape character
		fprintf(file, "%.*s", (int)(q-p), p); // write up to the escape
		if( q[1]!='[' )
		{	// write the escape char (whatever purpose it has)
			fprintf(file, "%.*s", 1, q);
			p=q+1;	//and start searching again
		}
		else
		{	// from here, we will skip the '\033['
			// we break at the first unprocessible position
			// assuming regular text is starting there

			// skip escape and bracket
			q=q+2;
			while(1)
			{
				if( ISDIGIT(*q) )
				{
					++q;
					// and next character
					continue;
				}
				else if( *q == ';' )
				{	// delimiter
					++q;
					// and next number
					continue;
				}
				else if( *q == 'm' )
				{	// \033[#;...;#m - Set Graphics Rendition (SGR)
					// set the attributes
				}
				else if( *q=='J' )
				{	// \033[#J - Erase Display (ED)
				}
				else if( *q=='K' )
				{	// \033[K  : clear line from actual position to end of the line
				}
				else if( *q == 'H' || *q == 'f' )
				{	// \033[#;#H - Cursor Position (CUP)
					// \033[#;#f - Horizontal & Vertical Position
				}
				else if( *q=='s' )
				{	// \033[s - Save Cursor Position (SCP)
				}
				else if( *q=='u' )
				{	// \033[u - Restore cursor position (RCP)
				}
				else if( *q == 'A' )
				{	// \033[#A - Cursor Up (CUU)
					// Moves the cursor UP # number of lines
				}
				else if( *q == 'B' )
				{	// \033[#B - Cursor Down (CUD)
					// Moves the cursor DOWN # number of lines
				}
				else if( *q == 'C' )
				{	// \033[#C - Cursor Forward (CUF)
					// Moves the cursor RIGHT # number of columns
				}
				else if( *q == 'D' )
				{	// \033[#D - Cursor Backward (CUB)
					// Moves the cursor LEFT # number of columns
				}
				else if( *q == 'E' )
				{	// \033[#E - Cursor Next Line (CNL)
					// Moves the cursor down the indicated # of rows, to column 1
				}
				else if( *q == 'F' )
				{	// \033[#F - Cursor Preceding Line (CPL)
					// Moves the cursor up the indicated # of rows, to column 1.
				}
				else if( *q == 'G' )
				{	// \033[#G - Cursor Horizontal Absolute (CHA)
					// Moves the cursor to indicated column in current row.
				}
				else if( *q == 'L' || *q == 'M' || *q == '@' || *q == 'P')
				{	// not implemented, just skip
				}
				else
				{	// no number nor valid sequencer
					// something is fishy, we break and give the current char free
					--q;
				}
				// skip the sequencer and search again
				p = q+1;
				break;
			}// end while
		}
	}
	if (*p)	// write the rest of the buffer
		fprintf(file, "%s", p);
	FREEBUF(tempbuf);
	return 0;
}
int	FPRINTF(FILE *file, const char *fmt, ...)
{
	int ret;
	va_list argptr;
	va_start(argptr, fmt);
	ret = VFPRINTF(file,fmt,argptr);
	va_end(argptr);
	return ret;
}

#define FFLUSH fflush

#define STDOUT stdout
#define STDERR stderr










char timestamp_format[20] = ""; //For displaying Timestamps

// by MC Cameri
int _vShowMessage(enum msg_type flag, const char *string, va_list ap)
{
	// _ShowMessage MUST be used instead of printf as of 10/24/2004.
	// Return: 0 = Successful, 1 = Failed.
//	int ret = 0;
	char prefix[100];
#if defined(DEBUGLOGMAP) || defined(DEBUGLOGCHAR) || defined(DEBUGLOGLOGIN)
	FILE *fp;
#endif

	if (!string || *string == '\0') {
		ShowError("Empty string passed to _vShowMessage().\n");
		return 1;
	}
	if ((flag == MSG_DEBUG && !SHOW_DEBUG_MSG) ||
	    (flag == MSG_INFORMATION && msg_silent&1) ||
	    (flag == MSG_STATUS && msg_silent&2) ||
	    (flag == MSG_NOTICE && msg_silent&4) ||
	    (flag == MSG_WARNING && msg_silent&8) ||
	    (flag == MSG_ERROR && msg_silent&16) ||
	    (flag == MSG_SQL && msg_silent&16))
		return 0; //Do not print it.

	if (timestamp_format[0])
	{	//Display time format. [Skotlex]
		time_t t = time(NULL);
		strftime(prefix, 80, timestamp_format, localtime(&t));
	} else prefix[0]='\0';

	switch (flag) {
		case MSG_NONE: // direct printf replacement
			break;
		case MSG_STATUS: //Bright Green (To inform about good things)
			strcat(prefix,CL_GREEN"[Status]"CL_RESET":");
			break;
		case MSG_SQL: //Bright Violet (For dumping out anything related with SQL) <- Actually, this is mostly used for SQL errors with the database, as successes can as well just be anything else... [Skotlex]
			strcat(prefix,CL_MAGENTA"[SQL]"CL_RESET":");
			break;
		case MSG_INFORMATION: //Bright White (Variable information)
			strcat(prefix,CL_WHITE"[Info]"CL_RESET":");
			break;
		case MSG_NOTICE: //Bright White (Less than a warning)
			strcat(prefix,CL_WHITE"[Notice]"CL_RESET":");
			break;
		case MSG_WARNING: //Bright Yellow
			strcat(prefix,CL_YELLOW"[Warning]"CL_RESET":");
			break;
		case MSG_DEBUG: //Bright Cyan, important stuff!
			strcat(prefix,CL_CYAN"[Debug]"CL_RESET":");
			break;
		case MSG_ERROR: //Bright Red  (Regular errors)
			strcat(prefix,CL_RED"[Error]"CL_RESET":");
			break;
		case MSG_FATALERROR: //Bright Red (Fatal errors, abort(); if possible)
			strcat(prefix,CL_RED"[Fatal Error]"CL_RESET":");
			break;
		default:
			ShowError("In function _vShowMessage() -> Invalid flag passed.\n");
			return 1;
	}

	if (flag == MSG_ERROR || flag == MSG_FATALERROR || flag == MSG_SQL)
	{	//Send Errors to StdErr [Skotlex]
		FPRINTF(STDERR, "%s ", prefix);
		VFPRINTF(STDERR, string, ap);
		FFLUSH(STDERR);
	} else {
		if (flag != MSG_NONE)
			FPRINTF(STDOUT, "%s ", prefix);
		VFPRINTF(STDOUT, string, ap);
		FFLUSH(STDOUT);
	}

#if defined(DEBUGLOGMAP) || defined(DEBUGLOGCHAR) || defined(DEBUGLOGLOGIN)
	if(strlen(DEBUGLOGPATH) > 0) {
		fp=fopen(DEBUGLOGPATH,"a");
		if (fp == NULL)	{
			FPRINTF(STDERR, CL_RED"[ERROR]"CL_RESET": Could not open '"CL_WHITE"%s"CL_RESET"', access denied.\n", DEBUGLOGPATH);
			FFLUSH(STDERR);
		} else {
			fprintf(fp,"%s ", prefix);
			vfprintf(fp,string,ap);
			fclose(fp);
		}
	} else {
		FPRINTF(STDERR, CL_RED"[ERROR]"CL_RESET": DEBUGLOGPATH not defined!\n");
		FFLUSH(STDERR);
	}
#endif

	va_end(ap);
	return 0;
}

void ClearScreen(void)
{
	ShowMessage(CL_CLS);	// to prevent empty string passed messages
}
int _ShowMessage(enum msg_type flag, const char *string, ...)
{
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(flag, string, ap);
	va_end(ap);
	return ret;
}

// direct printf replacement
int ShowMessage(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_NONE, string, ap);
	va_end(ap);
	return ret;
}
int ShowStatus(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_STATUS, string, ap);
	va_end(ap);
	return ret;
}
int ShowSQL(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_SQL, string, ap);
	va_end(ap);
	return ret;
}
int ShowInfo(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_INFORMATION, string, ap);
	va_end(ap);
	return ret;
}
int ShowNotice(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_NOTICE, string, ap);
	va_end(ap);
	return ret;
}
int ShowWarning(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_WARNING, string, ap);
	va_end(ap);
	return ret;
}
int ShowDebug(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_DEBUG, string, ap);
	va_end(ap);
	return ret;
}
int ShowError(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_ERROR, string, ap);
	va_end(ap);
	return ret;
}
int ShowFatalError(const char *string, ...) {
	int ret;
	va_list ap;
	va_start(ap, string);
	ret = _vShowMessage(MSG_FATALERROR, string, ap);
	va_end(ap);
	return ret;
}
