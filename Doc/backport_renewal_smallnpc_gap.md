# Renewal small-NPC gap-лог (адаптации/dedup/boundary/unresolved/orphan)


## guides_dicastes.txt
- COMMENT [ET_SURPRISE] emotion ET_SURPRISE;

## guides_rockridge.txt
- MANUAL [unregistered-map:harboro1] harboro1,356,211,5	script	Guide#rockridge01	4_F_ANYA,{
- ADAPT [=->set] .@s = select( "[Kafra Employee]", "[Inn]", "[Weapon/Armor Shop]", "[Tool Shop]", "[Sheriff's Office]", "Clear mini-map.", "Cancel." );
- BOUNDARY [harboro1] harboro1,80,211,3	duplicate(Guide#rockridge01)	Guide#rockridge02	4_F_ANYA
- BOUNDARY [harboro1] Guide#rockridge01

## TrainingZone123.txt
- MANUAL [unregistered-map:tra_fild01] tra_fild01,204,110,2	script	Training Ground Warehouse Soldier#fild01_1	8W_SOLDIER,{
- ADAPT [=->set] .@storage_num = 1;
- ADAPT [=->set] .@storage_num = 2;
- ADAPT [=->set] .@storage_num = 3;
- ADAPT [=->set] .@guildid = getcharid( 2 );
- ADAPT [guild_has_permission->0] if( getgdskilllv( .@guildid, "GD_GUILD_STORAGE" ) == 0 || !guild_has_permission( GUILD_PERM_STORAGE ) ){
- ADAPT [op=->set] Zeny -= 1000;
- ADAPT [op=->set] Zeny -= 1000;
- BOUNDARY [tra_fild01] tra_fild01,15,110,6	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild01_2	8W_SOLDIER
- BOUNDARY [tra_fild01] tra_fild01,113,32,0	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild01_3	8W_SOLDIER
- BOUNDARY [tra_fild01] tra_fild01,111,100,4	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild01_4	8W_SOLDIER
- BOUNDARY [tra_fild02] tra_fild02,204,110,2	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild02_1	8W_SOLDIER
- BOUNDARY [tra_fild02] tra_fild02,15,110,6	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild02_2	8W_SOLDIER
- BOUNDARY [tra_fild02] tra_fild02,113,32,0	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild02_3	8W_SOLDIER
- BOUNDARY [tra_fild02] tra_fild02,111,100,4	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild02_4	8W_SOLDIER
- BOUNDARY [tra_fild03] tra_fild03,204,110,2	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild03_1	8W_SOLDIER
- BOUNDARY [tra_fild03] tra_fild03,15,110,6	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild03_2	8W_SOLDIER
- BOUNDARY [tra_fild03] tra_fild03,113,32,0	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild03_3	8W_SOLDIER
- BOUNDARY [tra_fild03] tra_fild03,111,100,4	duplicate(Training Ground Warehouse Soldier#fild01_1)	Training Ground Warehouse Soldier#fild03_4	8W_SOLDIER
- MANUAL [unregistered-map:tra_fild01] tra_fild01,142,113,6	script	Cleaning Robot#fild01	EP17_2_OMEGA_CLEANER,{
- ADAPT [=->set] .@num = atoi( charat(strnpcinfo(2), 5) );
- COMMENT [charat] .@num = atoi( charat(strnpcinfo(2), 5) );
- ADAPT [=->set] .is_moving[.@num] = true;
- COMMENT [ET_SWEAT,ET_PROFUSELY_SWEAT,ET_HUNGRY,ET_OHNO] setarray .@emotions[0], ET_SWEAT, ET_PROFUSELY_SWEAT, ET_HUNGRY, ET_OHNO;
- ADAPT [=->set] .@r = rand( getarraysize(.@emotions) );
- ADAPT [=->set] .@r = rand( getarraysize(.@speed) );
- ADAPT [=->set] .sens[.@num] = 1;
- ADAPT [=->set] .sens[.@num] = -1;
- ADAPT [op=->set] .@x += 8 * .sens[.@num];
- ADAPT [=->set] .sens[.@num] = 1;
- ADAPT [=->set] .sens[.@num] = -1;
- ADAPT [op=->set] .@x += 8 * .sens[.@num];
- ADAPT [=->set] .sens[.@num] = 1;
- ADAPT [=->set] .sens[.@num] = -1;
- ADAPT [op=->set] .@y += 8 * .sens[.@num];
- COMMENT [getnpcid] unitwalk getnpcid(0),.@x,.@y, strnpcinfo(0) + "::OnMoveEnd";
- ADAPT [=->set] .@num = atoi( charat(strnpcinfo(2), 5) );
- COMMENT [charat] .@num = atoi( charat(strnpcinfo(2), 5) );
- ADAPT [=->set] .is_moving[.@num] = false;
- ADAPT [=->set] .@num = atoi( charat(strnpcinfo(2), 5) );
- COMMENT [charat] .@num = atoi( charat(strnpcinfo(2), 5) );
- ADAPT [=->set] .sens[.@num] = 1;
- BOUNDARY [tra_fild02] tra_fild02,53,113,2	duplicate(Cleaning Robot#fild01)	Cleaning Robot#fild02	EP17_2_OMEGA_CLEANER
- BOUNDARY [tra_fild03] tra_fild03,110,57,4	duplicate(Cleaning Robot#fild01)	Cleaning Robot#fild03	EP17_2_OMEGA_CLEANER
- MANUAL [unregistered-map:tra_fild01] tra_fild01,122,75,6	script	Neighborhood Grandmother#npc02	4_F_JPNOBA,{
- MANUAL [unregistered-map:tra_fild01] tra_fild01,34,102,3	script	Cat#npc03	4_CAT_REST,{
- MANUAL [unregistered-map:tra_fild01] tra_fild01,34,120,3	script	Fress#npc05	4_M_SITDOWN,{
- MANUAL [unregistered-map:tra_fild01] tra_fild01,128,142,7	script	Nine Oranges#npc04	4_F_ROGUE,{
- MANUAL [unregistered-map:tra_fild01] tra_fild01,97,64,3	script	Village#npc01	4_M_CHN8GUEK,{
- MANUAL [unregistered-map:tra_fild02] tra_fild02,101,90,5	script	Jar Cat#npc09	4_CAT_SAILOR5,{
- MANUAL [unregistered-map:tra_fild02] tra_fild02,166,46,3	script	Little One#npc06	4_M_KID2,{
- MANUAL [unregistered-map:tra_fild02] tra_fild02,129,93,6	script	Kekekekereurur#npc10	4_GEFFEN_02,{
- MANUAL [unregistered-map:tra_fild03] tra_fild03,98,46,7	script	Lumberjack#npc13	4_M_NOV_HUNT,{
- MANUAL [unregistered-map:tra_fild03] tra_fild03,53,140,5	script	Dong#npc15	4_M_CACTUSMAN1,{
- MANUAL [unregistered-map:tra_fild03] tra_fild03,92,108,7	script	Cat#npc12	4_CAT_REST,{
- MANUAL [unregistered-map:tra_fild03] tra_fild03,180,102,4	script	Coco#npc14	4_COCO,{
- COMMENT [ET_QUESTION] emotion ET_QUESTION;
- BOUNDARY [tra_fild01] Training Ground Warehouse Soldier#fild01_1

## adven_boards.txt
- ADAPT [=->set] .@size = getargcount();
- COMMENT [getargcount] .@size = getargcount();
- ADAPT [=->set] .@i = 0;
- ADAPT [=->set] .@mob_id = getarg(.@i);
- COMMENT [charat] mes "[Geffenia Section "+ charat( strnpcinfo(2),8 ) +"]";
- COMMENT [ET_HUK] emotion ET_HUK;
- UNRESOLVED [getargcount] F_AvenBoard
- UNRESOLVED [multiline-args] Signpost#Ant Hell 1
- DEDUP [Signposts#Geffen Dungeon] Signposts#Geffen Dungeon
- UNRESOLVED [multiline-args] Signposts#Glastheim
- DEDUP [Signposts#Nogg Road] Signposts#Nogg Road
- DEDUP [Signposts#Mjolnir Dead] Signposts#Mjolnir Dead
- UNRESOLVED [multiline-args] Signposts#Prontera_Laby
- UNRESOLVED [multiline-args] Signposts#Alde_Laby
- DEDUP [Signposts#Sphinx] Signposts#Sphinx
- DEDUP [Signposts#Clock Tower] Signposts#Clock Tower
- DEDUP [Signposts#Orc Dungeon] Signposts#Orc Dungeon
- UNRESOLVED [multiline-args] Signposts#Juperos Ruins
- UNRESOLVED [multiline-args] Signposts#Izlude
- DEDUP [Signposts#Toy Factory] Signposts#Toy Factory
- UNRESOLVED [multiline-args] Signposts#Sunken Ship
- UNRESOLVED [multiline-args] Signposts#Comodo East
- UNRESOLVED [multiline-args] Signposts#Comodo West
- UNRESOLVED [multiline-args] Signposts#Comodo North
- UNRESOLVED [multiline-args] Signposts#Payon Cave
- DEDUP [Signposts#Pyramid] Signposts#Pyramid
- UNRESOLVED [multiline-args] Signpost#Abyss Lake
- UNRESOLVED [multiline-args] Signpost#Einbech Dungeon
- UNRESOLVED [multiline-args] Signpost#Ice Cave
- UNRESOLVED [multiline-args] Signpost#Thor Volcano
- UNRESOLVED [multiline-args] Signpost#Odin Temple
- UNRESOLVED [multiline-args] Signpost#Starlight Reef
- UNRESOLVED [charat] Signpost#Geffenia1
- UNRESOLVED [multiline-args] Signpost#Nameless Island
- UNRESOLVED [multiline-args] Signpost#Somatology
- UNRESOLVED [multiline-args] Signpost#Holy Ground
- UNRESOLVED [multiline-args] Signpost#Robot Factory
- UNRESOLVED [multiline-args] Guide#Thanatos1
- DEDUP [Signpost#Culvert] Signpost#Culvert
- UNRESOLVED [multiline-args] Signpost#Turtle Island
- UNRESOLVED [multiline-args] Signpost#Amatsu Dungeon
- UNRESOLVED [multiline-args] Signpost#Kunlun Dungeon
- UNRESOLVED [multiline-args] Signpost#Luoyang Dungeon
- UNRESOLVED [multiline-args] Signpost#Ayothaya
- UNRESOLVED [multiline-args] Signpost#Moscovia
- UNRESOLVED [multiline-args] Signpost#Brasilis
- UNRESOLVED [multiline-args] Signpost#Dewata_Krakatau
- UNRESOLVED [multiline-args] Signpost#Dewata_Istana
- UNRESOLVED [multiline-args] Signpost#Kamidal
- ORPHAN [Signpost#Ant Hell 1] cmd_fild08,341,84,0	duplicate(Signpost#Ant Hell 1)	Signposts#Ant Hell2	2_BULLETIN_BOARD
- ORPHAN [Signpost#Geffenia1] gefenia02,120,108,0	duplicate(Signpost#Geffenia1)	Signpost#Geffenia2	2_BULLETIN_BOARD
- ORPHAN [Signpost#Geffenia1] gefenia03,131,201,0	duplicate(Signpost#Geffenia1)	Signpost#Geffenia3	2_BULLETIN_BOARD
- ORPHAN [Signpost#Geffenia1] gefenia04,130,95,0	duplicate(Signpost#Geffenia1)	Signpost#Geffenia4	2_BULLETIN_BOARD
- ORPHAN [Guide#Thanatos1] tha_t01,156,78,0	duplicate(Guide#Thanatos1)	Guide#Thanatos2	CLEAR_NPC
- ORPHAN [Signpost#Kamidal] dic_fild01,27,83,0	duplicate(Signpost#Kamidal)	Signpost#Kamidal Exit	2_BULLETIN_BOARD

## dimensional_gap.txt
- MANUAL [unregistered-map:dali] dali,137,87,4	script	Allied Forces Soldier	4_M_MOCASS1,{
- MANUAL [unregistered-map:dali] dali,122,60,4	script	Morocc Soldier	4_M_MOC_SOLDIER,{
- MANUAL [unregistered-map:dali] dali,51,104,6	script	Spledide Soldier	4_M_FAIRYSOLDIER2,{
- MANUAL [unregistered-map:dali] dali,56,126,4	script	Dispatched Sapha	4_MAN_BENKUNI,{
- BOUNDARY [dali] dali,109,94,4	shop	Sundries Merchant	4_M_MERCAT2,611:-1,1750:-1,1065:-1
- MANUAL [unregistered-map:dali] dali,112,95,4	script	Logistics Manager	4_M_MERCAT2,{
- ADAPT [op=->set] Zeny -= 200;
- MANUAL [unregistered-map:dali] dali,115,85,5	script	Party Leader#dali	2_M_SWORDMASTER,{
- MANUAL [unregistered-map:dali] dali,115,85,0	script	#dalichat	-1,{
- COMMENT [getnpcid,ET_SLEEPY] emotion ET_SLEEPY, getnpcid(0, "Party Member#SURA");
- COMMENT [getnpcid,ET_FRET] emotion ET_FRET, getnpcid(0, "Party Member#SURA");
- COMMENT [getnpcid,ET_FRET] emotion ET_FRET, getnpcid(0, "Party Member#SURA");
- COMMENT [getnpcid,ET_ANGER] emotion ET_ANGER, getnpcid(0, "Party Member#MONK");
- COMMENT [getnpcid,ET_FRET] emotion ET_FRET, getnpcid(0, "Party Member#SURA");
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Party Member#CRU");
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Party Member#MONK");
- COMMENT [getnpcid,ET_SLEEPY] emotion ET_SLEEPY, getnpcid(0, "Party Member#SURA");
- COMMENT [getnpcid,ET_KIK] emotion ET_KIK, getnpcid(0, "Party Member#CRU");
- COMMENT [getnpcid,ET_ANGER] emotion ET_ANGER, getnpcid(0, "Party Member#GUILL");
- COMMENT [getnpcid,ET_CRY] emotion ET_CRY, getnpcid(0, "Party Leader#dali2");
- MANUAL [unregistered-map:dali] dali,115,85,3	script	Party Leader#dali2	2_M_SWORDMASTER,{}
- MANUAL [unregistered-map:dali] dali,117,81,7	script	Party Member#WANDERER	4_F_WANDERER,{}
- MANUAL [unregistered-map:dali] dali,117,79,5	script	Party Member#CRU	4_F_CRU,{}
- MANUAL [unregistered-map:dali] dali,118,83,3	script	Party Member#MONK	4_F_MONK,{}
- MANUAL [unregistered-map:dali] dali,119,76,7	script	Party Member#SHADOW	4_F_SHADOWCHASER,{}
- MANUAL [unregistered-map:dali] dali,119,78,2	script	Party Member#GUILL	4_M_JPNOJI,{}
- MANUAL [unregistered-map:dali] dali,120,77,4	script	Party Member#SURA	4_F_SURA,{}
- MANUAL [unregistered-map:dali] dali,120,81,3	script	Party Member#EINOLD	4_M_EINOLD,{}
- MANUAL [unregistered-map:dali] dali,102,83,5	script	Merchant Prince#HUMERC	4_M_HUMERCHANT,2,2,{
- MANUAL [unregistered-map:dali] dali,105,82,1	script	Jumpy Knight#JP_RUN	4_M_JP_RUN,{
- MANUAL [unregistered-map:dali] dali,63,112,7	script	Merchant Prince#HUMERC2	4_M_HUMERCHANT,2,2,{
- MANUAL [unregistered-map:dali] dali,67,113,3	script	Jumpy Knight#JP_RUN2	4_M_JP_RUN,{
- MANUAL [unregistered-map:dali] dali,89,97,3	script	Merchant Prince#HUMERC3	4_M_HUMERCHANT,{
- MANUAL [unregistered-map:dali] dali,89,94,7	script	Jumpy Knight#JP_RUN3	4_M_JP_RUN,{
- MANUAL [unregistered-map:dali02] dali02,58,123,3	script	Curious Knight#KY_KNT	4_M_KY_KNT,{
- MANUAL [unregistered-map:dali02] dali02,51,112,5	script	Confused Thief#DST_SOL	4_DST_SOLDIER,{
- MANUAL [unregistered-map:dali02] dali02,65,115,5	script	Adventurous Rafflesia#ra	4_M_RAFLE_GR,{
- MANUAL [unregistered-map:dali02] dali02,68,117,5	script	Guide#ra	4_M_RAFLE_GR,{
- MANUAL [unregistered-map:dali02] dali02,65,119,5	script	Tourist#ra	4_M_RAFLE_GR,{
- MANUAL [unregistered-map:dali02] dali02,69,122,5	script	Traveller#ra	4_M_RAFLE_GR,{
- BOUNDARY [dali] Allied Forces Soldier
- BOUNDARY [dali] Morocc Soldier
- BOUNDARY [dali] Spledide Soldier
- BOUNDARY [dali] Dispatched Sapha
- BOUNDARY [dali] Logistics Manager
- BOUNDARY [dali] Party Leader#dali
- BOUNDARY [dali] #dalichat
- BOUNDARY [dali] Party Leader#dali2
- BOUNDARY [dali] Party Member#WANDERER
- BOUNDARY [dali] Party Member#CRU
- BOUNDARY [dali] Party Member#MONK
- BOUNDARY [dali] Party Member#SHADOW
- BOUNDARY [dali] Party Member#GUILL
- BOUNDARY [dali] Party Member#SURA
- BOUNDARY [dali] Party Member#EINOLD
- BOUNDARY [dali] Merchant Prince#HUMERC
- BOUNDARY [dali] Jumpy Knight#JP_RUN
- BOUNDARY [dali] Merchant Prince#HUMERC2
- BOUNDARY [dali] Jumpy Knight#JP_RUN2
- BOUNDARY [dali] Merchant Prince#HUMERC3
- BOUNDARY [dali] Jumpy Knight#JP_RUN3
- BOUNDARY [dali02] Curious Knight#KY_KNT
- BOUNDARY [dali02] Confused Thief#DST_SOL
- BOUNDARY [dali02] Adventurous Rafflesia#ra
- BOUNDARY [dali02] Guide#ra
- BOUNDARY [dali02] Tourist#ra
- BOUNDARY [dali02] Traveller#ra

## item_merge.txt
- COMMENT [mergeitem] mergeitem;
- UNRESOLVED [mergeitem] Mergician#mall

## kachua_key.txt
- ADAPT [=->set] .@key$ = "K_Secret_Key";
- ADAPT [=->set] .@keyname$ = getitemname( .@key$ );
- ADAPT [=->set] .@box$ = "Main_Lucky_Box";
- ADAPT [=->set] .@boxname$ = getitemname( .@box$ );
- COMMENT [mesitemlink] mes "^4d4dffYou can open this box by consuming " + mesitemlink( .@key$ ) + ".^000000";
- COMMENT [mesitemlink] mes "Not enough " + mesitemlink( .@key$ ) + ".";
- COMMENT [consumeitem] consumeitem(.@box$);
- COMMENT [mesitemlink] mes "You do not have enough " + mesitemlink( .@key$ ) + ".";
- ADAPT [for/incr->set] for (.@i = 1; .@i <= 10; ++.@i) {
- COMMENT [consumeitem] consumeitem(.@box$);
- UNRESOLVED [consumeitem,mesitemlink] Kachua's Secret Box#bm

## mail.txt
- BOUNDARY [izlude_a] izlude_a,136,94,0	duplicate(MailBox)	Mailbox#iz_a	888
- BOUNDARY [izlude_b] izlude_b,136,94,0	duplicate(MailBox)	Mailbox#iz_b	888
- BOUNDARY [izlude_c] izlude_c,136,94,0	duplicate(MailBox)	Mailbox#iz_c	888
- BOUNDARY [izlude_d] izlude_d,136,94,0	duplicate(MailBox)	Mailbox#iz_d	888

## resetskill.txt
- BOUNDARY [izlude_a] izlude_a,127,175,3	duplicate(Hypnotist#novice)	Hypnotist#novice_a	124
- BOUNDARY [izlude_b] izlude_b,127,175,3	duplicate(Hypnotist#novice)	Hypnotist#novice_b	124
- BOUNDARY [izlude_c] izlude_c,127,175,3	duplicate(Hypnotist#novice)	Hypnotist#novice_c	124
- BOUNDARY [izlude_d] izlude_d,127,175,3	duplicate(Hypnotist#novice)	Hypnotist#novice_d	124

## stone_change.txt
- ADAPT [=->set] .@i = select("Steel, please.:Iron, please.:Iron Ore, please.:Rough Oridecon, please.:No, thanks.");
- ADAPT [=->set] .@item = .@ores[.@i-1];
- ADAPT [=->set] .@count = countitem(.@item);

## turbo_track.txt
- ORPHAN [MountManager_turbo] alde_gld,181,199,5	duplicate(MountManager_turbo)	Mount Manager	845

## bulletin_boards.txt
- BOUNDARY [izlude_a] izlude_a,25,103,0	duplicate(BulletinBoard_iz)	Bulletin Board#5_a	837
- BOUNDARY [izlude_b] izlude_b,25,103,0	duplicate(BulletinBoard_iz)	Bulletin Board#5_b	837
- BOUNDARY [izlude_c] izlude_c,25,103,0	duplicate(BulletinBoard_iz)	Bulletin Board#5_c	837
- BOUNDARY [izlude_d] izlude_d,25,103,0	duplicate(BulletinBoard_iz)	Bulletin Board#5_d	837
- DEDUP [Bulletin Board#5] Bulletin Board#5
