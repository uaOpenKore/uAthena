// Unit test of onlinestat_rules.h (S. 2026-11-21). Build and run:
//   gcc -O1 -Wall -o /tmp/test_onlinestat src/char_sql/test_onlinestat.c && /tmp/test_onlinestat [cp1251.txt]
// cp1251.txt (optional): 128 lines "<byte hex> <code point hex>" for 0x80..0xFF from Python's cp1251 codec
// (0 for a byte it has no character for), to compare the table with.
#include "onlinestat_rules.h"

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(int argc, char** argv)
{
	char buf[1024], utf[OS_NAME_UTF8];
	struct os_line a, b;

	// cp1251 -> UTF-8
	os_name_utf8("\xCF\xF0\xE8\xE2\xB3\xF2 \xAF\xBF", utf, sizeof(utf)); // "Привіт Її"
	CHECK(strcmp(utf, "\xD0\x9F\xD1\x80\xD0\xB8\xD0\xB2\xD1\x96\xD1\x82 \xD0\x87\xD1\x97") == 0, "utf8 Привіт Її: %s", utf);
	os_name_utf8("Abc_09", utf, sizeof(utf));
	CHECK(strcmp(utf, "Abc_09") == 0, "ascii kept");
	os_name_utf8("\x98x", utf, sizeof(utf));
	CHECK(strcmp(utf, "?x") == 0, "0x98 has no character: %s", utf);
	os_name_utf8("\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF", utf, sizeof(utf));
	CHECK(strlen(utf) == 46, "23 Cyrillic letters = 46 bytes: %zu", strlen(utf));
	os_name_utf8("\x88\xB9", utf, sizeof(utf)); // € №
	CHECK(strcmp(utf, "\xE2\x82\xAC\xE2\x84\x96") == 0, "3-byte characters");
	if (argc > 1) {
		FILE* f = fopen(argv[1], "r");
		unsigned int c, u, n = 0;
		while (f && fscanf(f, "%x %x", &c, &u) == 2) {
			CHECK(os_cp1251((unsigned char)c) == u, "cp1251 0x%02X: table 0x%04X, Python 0x%04X", c, os_cp1251((unsigned char)c), u);
			n++;
		}
		CHECK(n == 128, "the Python table has %u lines", n);
		if (f)
			fclose(f);
	}

	// a line and back
	memset(&a, 0, sizeof(a));
	a.date = 20261121; a.char_id = 150001; a.account_id = 2000001; a.online = 10; a.paid_buy = 3; a.paid_auto = 7;
	strcpy(a.name, "Na\"me\\\x01\xD0\x9F");
	os_line_format(&a, buf, sizeof(buf));
	CHECK(strcmp(buf, "{\"d\":20261121,\"c\":150001,\"a\":2000001,\"n\":\"Na\\\"me\\\\\\u0001\xD0\x9F\",\"o\":10,\"b\":3,\"p\":7}\n") == 0, "format: %s", buf);
	CHECK(os_line_parse(buf, &b) == 1, "parse");
	CHECK(b.date == a.date && b.char_id == a.char_id && b.account_id == a.account_id, "ids back");
	CHECK(strcmp(b.name, a.name) == 0, "name back: %s", b.name);
	CHECK(b.online == 10 && b.paid_buy == 3 && b.paid_auto == 7, "minutes back");
	CHECK(os_line_parse("{\"d\":20261121,\"c\":1,\"a\":2,\"n\":\"x", &b) == 0, "a cut line is skipped");
	CHECK(os_line_parse("garbage", &b) == 0, "garbage is skipped");
	CHECK(os_line_parse("", &b) == 0, "empty is skipped");

	// dates
	os_date_text(20260105, utf, sizeof(utf));
	CHECK(strcmp(utf, "2026-01-05") == 0, "date text %s", utf);
	{
		long long ms = os_date_ms(20261121), ms2 = os_date_ms(20261122);
		time_t t = (time_t)(ms / 1000);
		struct tm tm;
		localtime_r(&t, &tm);
		CHECK(tm.tm_hour == 0 && tm.tm_min == 0 && tm.tm_mday == 21 && tm.tm_mon == 10, "local midnight");
		CHECK(ms2 - ms == 86400000LL, "a day later");
	}
	printf(fails ? "%d FAILED\n" : "ALL PASSED\n", fails);
	return fails != 0;
}
