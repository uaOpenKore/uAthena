# Renewal town-NPC gap-лог (адаптации/комментирования)

Тестировщики: проверьте COMMENT/MANUAL — потерянная функция или ручная правка.
Схема — Doc/backport_renewal_warps_npc_design.md §4.3.

## dewata
- COMMENT [vip_status] set .@cost, vip_status(VIP_STATUS_ACTIVE)?1000:10000;
- COMMENT [getgroupitem] getgroupitem(IG_GiftBox);
- COMMENT [ET_FRET] emotion ET_FRET;
- COMMENT [ET_FRET] emotion ET_FRET;
- COMMENT [ET_FRET] emotion ET_FRET;
- COMMENT [ET_FRET] emotion ET_FRET;
- COMMENT [ET_CRY] emotion ET_CRY;
- COMMENT [ET_OHNO] emotion ET_OHNO;
- COMMENT [ET_CRY] emotion ET_CRY;
- COMMENT [ET_BEST] emotion ET_BEST;
- COMMENT [getnpcid,ET_OK] emotion ET_OK, getnpcid(0, "Restauranteur#dew");
- COMMENT [ET_SCRATCH] emotion ET_SCRATCH;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_CONFUSE] emotion ET_CONFUSE;
- COMMENT [ET_OHNO] emotion ET_OHNO;
- COMMENT [ET_OK] emotion ET_OK;
- ADAPT [consumeitem->delitem] consumeitem 12043; //Str_Dish03
- ADAPT [consumeitem->delitem] consumeitem 12058; //Agi_Dish03
- ADAPT [consumeitem->delitem] consumeitem 12063; //Dex_Dish03
- ADAPT [consumeitem->delitem] consumeitem 12053; //Vit_Dish03
- ADAPT [consumeitem->delitem] consumeitem 12048; //Int_Dish03
- ADAPT [consumeitem->delitem] consumeitem 12068; //Luk_Dish03
- COMMENT [ET_FRET] emotion ET_FRET;
- COMMENT [ET_CHUP] emotion ET_CHUP;
- COMMENT [getnpcid,ET_CHUPCHUP] emotion ET_CHUPCHUP, getnpcid(0, "Sweet Married Couple#2");
- COMMENT [ET_SMILE] emotion ET_SMILE;
- COMMENT [getnpcid,ET_SMILE] emotion ET_SMILE, getnpcid(0, "Sweet Married Couple#2");
- COMMENT [ET_QUESTION] emotion ET_QUESTION;
- COMMENT [ET_QUESTION] emotion ET_QUESTION;
- COMMENT [getnpcid,ET_CHUP] emotion ET_CHUP, getnpcid(0, "Sweet Married Couple#1");
- COMMENT [ET_CHUPCHUP] emotion ET_CHUPCHUP;
- COMMENT [getnpcid,ET_SMILE] emotion ET_SMILE, getnpcid(0, "Sweet Married Couple#1");
- COMMENT [ET_SMILE] emotion ET_SMILE;
- COMMENT [ET_SMILE] emotion ET_SMILE;
- COMMENT [ET_QUESTION] emotion ET_QUESTION;
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Sarr#dew");
- COMMENT [ET_HUK] emotion ET_HUK;
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Sipo#dew");
- COMMENT [ET_HUK] emotion ET_HUK, playerattached();
- COMMENT [ET_FRET] emotion ET_FRET;
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Sarr#dew");
- COMMENT [getnpcid,ET_HUK] emotion ET_HUK, getnpcid(0, "Siyak#dew");
- COMMENT [ET_KIK] emotion ET_KIK;
- COMMENT [ET_HUK] emotion ET_HUK, playerattached();
- COMMENT [ET_SCRATCH] emotion ET_SCRATCH;
- COMMENT [ET_CRY] emotion ET_CRY;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_CRY] emotion ET_CRY;
- COMMENT [ET_CRY] emotion ET_CRY;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_THINK] emotion ET_THINK, playerattached();
- COMMENT [ET_KEK] emotion ET_KEK;
- COMMENT [ET_KEK] emotion ET_KEK;
- COMMENT [ET_QUESTION] emotion ET_QUESTION;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_OTL] emotion ET_OTL;
- COMMENT [ET_THROB] emotion ET_THROB;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_THROB] emotion ET_THROB;
- COMMENT [ET_CRY] emotion ET_CRY;
- COMMENT [ET_HNG] emotion ET_HNG;
- COMMENT [ET_CRY] emotion ET_CRY;

## dicastes
- COMMENT [ET_THROB] emotion ET_THROB;
- COMMENT [ET_QUESTION] emotion ET_QUESTION;
- COMMENT [ET_QUESTION] emotion ET_QUESTION;
- COMMENT [ET_SWEAT] emotion ET_SWEAT;
- COMMENT [ET_SWEAT] emotion ET_SWEAT;
- COMMENT [ET_DELIGHT] emotion ET_DELIGHT;
- COMMENT [ET_DELIGHT] emotion ET_DELIGHT;
- COMMENT [ET_THINK] emotion ET_THINK;
- COMMENT [ET_THINK] emotion ET_THINK;
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Crazy Venknick#fihsing1");
- COMMENT [ET_CRY] emotion ET_CRY, playerattached();
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Complaining Galten#fihs");
- COMMENT [ET_THINK] emotion ET_THINK;
- COMMENT [ET_THINK] emotion ET_THINK, playerattached();

## eclage

## malangdo
- BOUNDARY [izlude_a] izlude_a,182,218,4	duplicate(Odgnalam)	Odgnalam#iz_a	554
- BOUNDARY [izlude_b] izlude_b,182,218,4	duplicate(Odgnalam)	Odgnalam#iz_b	554
- BOUNDARY [izlude_c] izlude_c,182,218,4	duplicate(Odgnalam)	Odgnalam#iz_c	554
- BOUNDARY [izlude_d] izlude_d,182,218,4	duplicate(Odgnalam)	Odgnalam#iz_d	554
- COMMENT [ET_CHUP] emotion ET_CHUP;
- COMMENT [ET_DELIGHT] emotion ET_DELIGHT;
- COMMENT [getnpcid,ET_DELIGHT] emotion ET_DELIGHT, getnpcid(0, "Minstrel#mal");
- COMMENT [ET_COOL] emotion ET_COOL;
- COMMENT [ET_KIK] emotion ET_KIK;
- COMMENT [ET_KIK] emotion ET_KIK;
- COMMENT [ET_SPARK] emotion ET_SPARK;
- COMMENT [ET_COOL] emotion ET_COOL;
- COMMENT [ET_KIK] emotion ET_KIK;
- COMMENT [ET_KIK] emotion ET_KIK;

## malaya
- ADAPT [npc()->npc strnpcinfo(0)] enablenpc();
- ADAPT [npc()->npc strnpcinfo(0)] disablenpc();
- ADAPT [npc()->npc strnpcinfo(0)] enablenpc();
- ADAPT [npc()->npc strnpcinfo(0)] disablenpc();
- COMMENT [is_party_leader] if (is_party_leader() == true)
- COMMENT [ET_HUK] emotion ET_HUK;
- COMMENT [ET_HUK] emotion ET_HUK;
- COMMENT [ET_OHNO] emotion ET_OHNO;
- COMMENT [ET_KIK] emotion ET_KIK;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT;
- COMMENT [ET_STARE_ABOUT] emotion ET_STARE_ABOUT;
- COMMENT [ET_HUK] emotion ET_HUK;
- COMMENT [ET_SCRATCH] emotion ET_SCRATCH;
- ADAPT [=->set] .@mapName$        = getarg(0);
- ADAPT [=->set] .@passengers      = getarg(1);
- SITEFIX [.@i < getargcount] for (.@i = 5; .@i < getargcount(); .@i++) {
- ADAPT [for/incr->set] for (.@i = 5; getarg(.@i, "\x7F") != "\x7F"; .@i++) {
- ADAPT [for/incr->set] for (.@i = 0; .@i < getarraysize(.@msgJeepneyInfo$); .@i++) {

## mora
- COMMENT [ET_COOL] emotion ET_COOL;
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT, playerattached();
- COMMENT [ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT, playerattached();
- COMMENT [ET_CRY] emotion ET_CRY;
- COMMENT [ET_HUK] emotion ET_HUK;
- COMMENT [ET_OK] emotion ET_OK;
- COMMENT [ET_HNG] emotion ET_HNG;
- COMMENT [ET_SORRY] emotion ET_SORRY;
- COMMENT [ET_CRY] emotion ET_CRY;
- COMMENT [ET_SHY] emotion ET_SHY;
- COMMENT [ET_HUNGRY] emotion ET_HUNGRY;
- COMMENT [getnpcid,ET_ANGER] emotion ET_ANGER, getnpcid(0, "Traveler#ep14_1_1");
- COMMENT [getnpcid,ET_FRET] emotion ET_FRET, getnpcid(0, "Traveler#ep14_1_2");
- COMMENT [getnpcid,ET_PROFUSELY_SWEAT] emotion ET_PROFUSELY_SWEAT, getnpcid(0, "Traveler#ep14_1_3");
- COMMENT [getnpcid,ET_AHA] emotion ET_AHA, getnpcid(0, "Traveler#ep14_1_1");
- COMMENT [ET_QUESTION] emotion ET_QUESTION, playerattached();
- COMMENT [getnpcid,ET_ANGER] emotion ET_ANGER, getnpcid(0, "Traveler#ep14_1_1");
- COMMENT [getnpcid,ET_FRET] emotion ET_FRET, getnpcid(0, "Traveler#ep14_1_2");
- COMMENT [getnpcid,ET_ANGER] emotion ET_ANGER, getnpcid(0, "Traveler#ep14_1_1");
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Traveler#ep14_1_1");
- COMMENT [getnpcid,ET_FRET] emotion ET_FRET, getnpcid(0, "Traveler#ep14_1_2");
- COMMENT [getnpcid,ET_OK] emotion ET_OK, getnpcid(0, "Traveler#ep14_1_2");
- COMMENT [getnpcid,ET_ANGER] emotion ET_ANGER, getnpcid(0, "Traveler#ep14_1_1");
- COMMENT [getnpcid,ET_FRET] emotion ET_FRET, getnpcid(0, "Traveler#ep14_1_3");
- COMMENT [ET_STARE_ABOUT] emotion ET_STARE_ABOUT, playerattached();
- SITEFIX [switch] switch(atoi(charat(strnpcinfo(2),9))) {
