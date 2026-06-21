// Standalone unit test for the player-presence grid (mobgrid.c).
//
// Not part of `make sql`. Build & run with:
//   gcc -DMOBGRID_TEST -I src/map -o /tmp/test_mobgrid src/map/mobgrid.c src/map/test_mobgrid.c
//   /tmp/test_mobgrid
//
// Locks down the two correctness-critical properties:
//   * mobgrid_any never returns a false negative (it must cover every block the
//     real map_foreachinrange would visit) - else a mob would wrongly skip its
//     scan and fail to aggro.
//   * mobgrid_dec never underflows below 0.

#include "mobgrid.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
		if (!(cond)) { printf("FAIL: %s\n", (msg)); failures++; } \
		else         { printf("ok  : %s\n", (msg)); } \
	} while (0)

#define BXS 12
#define BYS 12
static int grid[BXS*BYS];

#define POS(bx,by) ((bx) + (by)*BXS)
#define B MOBGRID_BLOCK   // 8

int main(void)
{
	memset(grid, 0, sizeof(grid));

	// empty grid -> nothing found anywhere
	CHECK(mobgrid_any(grid, BXS, BYS, 40, 40, 14) == 0, "empty grid: no PC near");

	// put one PC in block (5,5); a mob standing in that block sees it
	mobgrid_inc(grid, POS(5,5));
	CHECK(mobgrid_any(grid, BXS, BYS, 5*B, 5*B, 14) == 1, "PC in own block is found");

	// a mob 14 tiles away (view_range) on the low side still covers block 5
	// (tile 5*8=40; 40+14=54 -> block 6; 40-14=26 -> block 3). Mob at tile 54:
	// range 14 -> blocks (54-14)/8=5 .. (54+14)/8=8 -> includes block 5.
	CHECK(mobgrid_any(grid, BXS, BYS, 54, 40, 14) == 1, "PC within view_range (high x) is found");
	CHECK(mobgrid_any(grid, BXS, BYS, 40, 54, 14) == 1, "PC within view_range (high y) is found");

	// far away: mob at tile (0,0), range 14 -> blocks 0..1; block 5 not covered
	CHECK(mobgrid_any(grid, BXS, BYS, 0, 0, 14) == 0, "PC out of range is not found");

	// boundary: negative lower bound must clamp, not read grid[-1]
	mobgrid_inc(grid, POS(0,0));
	CHECK(mobgrid_any(grid, BXS, BYS, 2, 2, 14) == 1, "low-corner query clamps and finds block 0");

	// boundary: upper bound must clamp to bxs-1/bys-1
	mobgrid_inc(grid, POS(BXS-1, BYS-1));
	CHECK(mobgrid_any(grid, BXS, BYS, (BXS-1)*B+7, (BYS-1)*B+7, 14) == 1, "high-corner query clamps and finds last block");

	// inc/dec accounting: two in, two out -> empty
	memset(grid, 0, sizeof(grid));
	mobgrid_inc(grid, POS(3,3));
	mobgrid_inc(grid, POS(3,3));
	CHECK(grid[POS(3,3)] == 2, "two increments -> count 2");
	mobgrid_dec(grid, POS(3,3));
	mobgrid_dec(grid, POS(3,3));
	CHECK(grid[POS(3,3)] == 0, "two decrements -> count 0");
	CHECK(mobgrid_any(grid, BXS, BYS, 3*B, 3*B, 14) == 0, "fully decremented block reports empty");

	// dec underflow guard: dec below zero stays at 0 (never negative -> never a
	// stuck phantom that would force scans forever, never a wrap that hides a PC)
	mobgrid_dec(grid, POS(3,3));
	CHECK(grid[POS(3,3)] == 0, "decrement below zero clamps to 0");

	printf(failures ? "\n%d CHECK(S) FAILED\n" : "\nALL CHECKS PASSED\n", failures);
	return failures ? 1 : 0;
}
