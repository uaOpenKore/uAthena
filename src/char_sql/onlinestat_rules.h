// Online statistics (S. 2026-11-21): the pure rules of onlinestat.c, unit tested by test_onlinestat.c.
// The spool file holds one JSON object a line, the minutes of one character on one day:
//   {"d":20261121,"c":150001,"a":2000001,"n":"Name","o":10,"b":0,"p":0}
// d = server date YYYYMMDD, c = char_id, a = account_id, n = name (UTF-8), o = minutes online,
// b = minutes bought with @buyplaytime, p = minutes paid by @autopay.
#ifndef _ONLINESTAT_RULES_H_
#define _ONLINESTAT_RULES_H_

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define OS_NAME_UTF8 80 // a 24-byte name is at most 3 UTF-8 bytes a character, plus the end

struct os_line {
	int date, char_id, account_id;
	char name[OS_NAME_UTF8];
	int online, paid_buy, paid_auto;
};

// The Unicode code point of a cp1251 byte (the character names are stored in cp1251, like `char`); 0 = none.
static inline unsigned int os_cp1251(unsigned char c)
{
	static const unsigned short hi[64] = {
		0x0402, 0x0403, 0x201A, 0x0453, 0x201E, 0x2026, 0x2020, 0x2021, 0x20AC, 0x2030, 0x0409, 0x2039, 0x040A, 0x040C, 0x040B, 0x040F,
		0x0452, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014, 0x0000, 0x2122, 0x0459, 0x203A, 0x045A, 0x045C, 0x045B, 0x045F,
		0x00A0, 0x040E, 0x045E, 0x0408, 0x00A4, 0x0490, 0x00A6, 0x00A7, 0x0401, 0x00A9, 0x0404, 0x00AB, 0x00AC, 0x00AD, 0x00AE, 0x0407,
		0x00B0, 0x00B1, 0x0406, 0x0456, 0x0491, 0x00B5, 0x00B6, 0x00B7, 0x0451, 0x2116, 0x0454, 0x00BB, 0x0458, 0x0405, 0x0455, 0x0457,
	};
	if (c < 0x80)
		return c;
	if (c >= 0xC0)
		return 0x0410 + (c - 0xC0);
	return hi[c - 0x80];
}

// A cp1251 name as UTF-8 (Mongo takes UTF-8 only); a byte with no character becomes '?'.
static inline void os_name_utf8(const char* in, char* out, size_t size)
{
	size_t n = 0;
	for (; *in && n + 4 < size; in++) {
		unsigned int u = os_cp1251((unsigned char)*in);
		if (u == 0)
			u = '?';
		if (u < 0x80)
			out[n++] = (char)u;
		else if (u < 0x800) {
			out[n++] = (char)(0xC0 | (u >> 6));
			out[n++] = (char)(0x80 | (u & 0x3F));
		} else {
			out[n++] = (char)(0xE0 | (u >> 12));
			out[n++] = (char)(0x80 | ((u >> 6) & 0x3F));
			out[n++] = (char)(0x80 | (u & 0x3F));
		}
	}
	out[n] = '\0';
}

// One spool line (with the '\n'); the name is escaped for JSON.
static inline int os_line_format(const struct os_line* l, char* out, size_t size)
{
	char esc[OS_NAME_UTF8 * 6 + 1];
	size_t n = 0;
	const unsigned char* p;
	for (p = (const unsigned char*)l->name; *p && n + 7 < sizeof(esc); p++) {
		if (*p == '"' || *p == '\\') {
			esc[n++] = '\\';
			esc[n++] = (char)*p;
		} else if (*p < 0x20)
			n += snprintf(esc + n, sizeof(esc) - n, "\\u%04x", *p);
		else
			esc[n++] = (char)*p;
	}
	esc[n] = '\0';
	return snprintf(out, size, "{\"d\":%d,\"c\":%d,\"a\":%d,\"n\":\"%s\",\"o\":%d,\"b\":%d,\"p\":%d}\n",
		l->date, l->char_id, l->account_id, esc, l->online, l->paid_buy, l->paid_auto);
}

// A line written by os_line_format back into its fields; 0 = not such a line (it is skipped).
static inline int os_line_parse(const char* s, struct os_line* l)
{
	const char* p;
	size_t n = 0;
	memset(l, 0, sizeof(*l));
	if (sscanf(s, "{\"d\":%d,\"c\":%d,\"a\":%d,\"n\":\"", &l->date, &l->char_id, &l->account_id) != 3)
		return 0;
	if ((p = strstr(s, "\"n\":\"")) == NULL)
		return 0;
	for (p += 5; *p && *p != '"'; p++) {
		char c = *p;
		if (c == '\\') {
			p++;
			if (*p == 'u') {
				unsigned int u = 0;
				if (sscanf(p + 1, "%4x", &u) != 1)
					return 0;
				c = (char)u;
				p += 4;
			} else if (*p)
				c = *p;
			else
				return 0;
		}
		if (n + 1 < sizeof(l->name))
			l->name[n++] = c;
	}
	l->name[n] = '\0';
	if (*p != '"' || sscanf(p, "\",\"o\":%d,\"b\":%d,\"p\":%d}", &l->online, &l->paid_buy, &l->paid_auto) != 3)
		return 0;
	return l->date > 0 && l->char_id > 0;
}

// YYYYMMDD as "YYYY-MM-DD".
static inline void os_date_text(int date, char* out, size_t size)
{
	snprintf(out, size, "%04d-%02d-%02d", date / 10000, date / 100 % 100, date % 100);
}

// The server's local midnight starting the day YYYYMMDD, in ms since the epoch (the Date the TTL counts from).
static inline long long os_date_ms(int date)
{
	struct tm tm;
	memset(&tm, 0, sizeof(tm));
	tm.tm_year = date / 10000 - 1900;
	tm.tm_mon = date / 100 % 100 - 1;
	tm.tm_mday = date % 100;
	tm.tm_isdst = -1;
	return (long long)mktime(&tm) * 1000;
}

#endif /* _ONLINESTAT_RULES_H_ */
