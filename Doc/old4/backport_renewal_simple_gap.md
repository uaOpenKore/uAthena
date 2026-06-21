# Renewal 2d simple gap-лог (адаптации/dedup/boundary/unresolved/orphan)


## ninja_quests.txt
- ADAPT [=->set] .@string1$ = "Check Ingredients.";
- ADAPT [=->set] .@string2$ = "Check Stats.";
- ADAPT [=->set] .@string1$ = "";
- ADAPT [=->set] .@string2$ = "";
- ADAPT [=->set] .@string1$ = "Check Ingredients.";
- ADAPT [=->set] .@string2$ = "Check Stats.";
- ADAPT [=->set] .@string1$ = "";
- ADAPT [=->set] .@string2$ = "";

## cooking_quest.txt
- BOUNDARY [prt_cas] prt_cas,324,200,5	duplicate(Charles Orleans#cook_)	Charles Orleans#cook	4_M_OILMAN
- BOUNDARY [prt_cas] prt_cas,329,206,3	duplicate(Madeleine Chu#cook_)	Madeleine Chu#cook	4_COOK
- BOUNDARY [prt_cas] prt_cas,329,194,3	duplicate(Child with Cat#cook_)	Child with Cat#cook	4_F_YUNYANG
- BOUNDARY [prt_cas] prt_cas,329,192,3	duplicate(Wickebine#cook_)	Wickebine#cook	4_F_JOB_ASSASSIN

## mrsmile.txt
- BOUNDARY [izlude_a] izlude_a,125,175,4	duplicate(SmileHelper)	Smile Assistance#iz_a	92
- BOUNDARY [izlude_b] izlude_b,125,175,4	duplicate(SmileHelper)	Smile Assistance#iz_b	92
- BOUNDARY [izlude_c] izlude_c,125,175,4	duplicate(SmileHelper)	Smile Assistance#iz_c	92
- BOUNDARY [izlude_d] izlude_d,125,175,4	duplicate(SmileHelper)	Smile Assistance#iz_d	92
- ORPHAN [SmileHelper] izlude,125,175,4	duplicate(SmileHelper)	Smile Assistance#iz	92
- ORPHAN [SmileHelper] morocc,159,107,4	duplicate(SmileHelper)	Smile Assistance#moc2	92

## monstertamers.txt
- ORPHAN [MonsterTamer_izlude] izlude_in,55,105,4	duplicate(MonsterTamer_izlude)	Monster Tamer#izu	125

## the_sign_quest.txt
- BOUNDARY [prt_cas] prt_cas,87,214,8	duplicate(Soldier#s11_)	Soldier#s11	8W_SOLDIER
