// Copyright (c) Athena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder
//
// See mobgrid.h. [perf]

#include "mobgrid.h"

void mobgrid_inc(int *grid, int pos)
{
	grid[pos]++;
}

void mobgrid_dec(int *grid, int pos)
{
	if (--grid[pos] < 0)
		grid[pos] = 0;   // never negative: a stuck phantom would force scans forever
}

int mobgrid_any(const int *grid, int bxs, int bys, int x, int y, int range)
{
	int bx0 = (x - range) / MOBGRID_BLOCK, bx1 = (x + range) / MOBGRID_BLOCK;
	int by0 = (y - range) / MOBGRID_BLOCK, by1 = (y + range) / MOBGRID_BLOCK;
	int bx, by;

	if (bx0 < 0) bx0 = 0;
	if (by0 < 0) by0 = 0;
	if (bx1 >= bxs) bx1 = bxs - 1;
	if (by1 >= bys) by1 = bys - 1;

	for (by = by0; by <= by1; by++)
		for (bx = bx0; bx <= bx1; bx++)
			if (grid[bx + by * bxs] > 0)
				return 1;
	return 0;
}
