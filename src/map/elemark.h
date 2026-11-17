// Copyright (c) uAthena / bornrok.com
// Element mark (S. 2026-11-17): a player's hit whose element passes below 100% marks the monster; the next
// player hit on it uses the mark up, and if that hit's element passes above 100% its whole element damage
// doubles (Wind on Water 1: 175% -> 350%). Pure rules only, so test_elemark.c needs nothing else; battle.c
// applies them (who/where the mark works: battle_elemark_target).
#ifndef _ELEMARK_H_
#define _ELEMARK_H_

// Element ratio (%) of the hit that uses a mark: above 100% the whole ratio doubles (S.: "должен весь дамаг
// удвоиться", 175% -> 350%); 100% and below (resisted, immune, healing) stays as attr_fix.txt says
// (S.: "стойкости не будем усиливать").
static inline int elemark_boost_ratio(int ratio)
{
	return ratio > 100 ? 2*ratio : ratio;
}

// Mark state after one hit on the monster.
//   marked: the monster carried a mark before this hit
//   landed: the hit was not a miss (a miss neither sets nor uses a mark)
//   weak:   the hit's main element passed below 100%
// The mark has no timer, and the hit that uses it never marks again (S.: "второй удар должен снимать метку").
static inline int elemark_after_hit(int marked, int landed, int weak)
{
	if (!landed)
		return marked;
	if (marked)
		return 0;
	return weak ? 1 : 0;
}

#endif /* _ELEMARK_H_ */
