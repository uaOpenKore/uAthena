# Реневал-контент, НЕ бэкпортированный (rAthena 7f08087, 2026-06-18)

Перечень того, что осталось за рамками бэкпорта реневал-мобов/карт (см. `backport_renewal_mobs.md`). Вселенная — контент, связанный с обработанными реневал-мобами (1683 кандидата + предметы, что они роняют); полный реневал-каталог rAthena (тысячи карт/предметов вне дропа этих мобов) сюда НЕ входит.

## Сводка

| Категория | Кол-во | Причина |
|---|---:|---|
| Мобы не добавлены | 459 | ID>10000 > движок `MAX_MOB_DB=10000` |
| Карты не добавлены | 3 | ID уже занят другим предметом uAthena |
| Карты добавлены БЕЗ эффекта | 246 | скрипт = реневал-бонус/`.@`/1-арг (в item_db2 как коллекционка) |
| Предметы (не-карты) не добавлены | 387 | реневал-предмет отсутствует в uAthena (дроп обнулён) |
| Карты в дропе не добавлены | 3 | (подмножество «карт не добавлено», в дропе мобов) |

## 1. Мобы не добавлены — 459 (ID > 10000)

Поднять `MAX_MOB_DB` = правка движка (вне «без новых механик»).

| ID | AegisName | Name | Lv |
|---:|---|---|---:|
| 20255 | ILL_TEDDY_BEAR_R | Red Teddy Bear | 155 |
| 20256 | ILL_TEDDY_BEAR_Y | Yellow Teddy Bear | 155 |
| 20257 | ILL_TEDDY_BEAR_G | Green Teddy Bear | 157 |
| 20258 | ILL_TEDDY_BEAR_W | White Teddy Bear | 155 |
| 20259 | ILL_TEDDY_BEAR_B | Blue Teddy Bear | 152 |
| 20260 | ILL_TEDDY_BEAR_S | Shining Teddy Bear | 160 |
| 20261 | ILL_PITMAN | Hardworking Pitman | 154 |
| 20262 | ILL_MINERAL | Soul Fragment | 153 |
| 20263 | ILL_OBSIDIAN | Sinister Obsidian | 156 |
| 20264 | G_ILL_TEDDY_BEAR_R | Red Teddy Bear | 155 |
| 20265 | G_ILL_TEDDY_BEAR_Y | Yellow Teddy Bear | 155 |
| 20266 | G_ILL_TEDDY_BEAR_G | Green Teddy Bear | 157 |
| 20267 | G_ILL_TEDDY_BEAR_W | White Teddy Bear | 155 |
| 20268 | G_ILL_TEDDY_BEAR_B | Blue Teddy Bear | 152 |
| 20269 | GUILD_SKILL_FLAG | Guild Skill Flag | 90 |
| 20270 | ILL_TRI_JOINT | Ancient Tri Joint | 164 |
| 20271 | ILL_STALACTIC_GOLEM | Ancient Stalactic Golem | 167 |
| 20272 | ILL_MEGALITH | Ancient Megalith | 166 |
| 20273 | ILL_TAO_GUNKA | Ancient Tao Gunka | 169 |
| 20274 | ILL_STONE_SHOOTER | Ancient Stone Shooter | 166 |
| 20275 | ILL_WOOTAN_SHOOTER | Ancient Wootan Shooter | 164 |
| 20276 | ILL_WOOTAN_FIGHTER | Ancient Wootan Fighter | 167 |
| 20277 | ILL_WOOTAN_DEFENDER | Ancient Wootan Defender | 169 |
| 20278 | G_ILL_MEGALITH | Ancient Megalith | 166 |
| 20279 | G_ILL_WOOTAN_SHOOTER | Ancient Wootan Shooter | 164 |
| 20280 | G_ILL_WOOTAN_FIGHTER | Ancient Wootan Fighter | 167 |
| 20340 | MD_EL_A17T | EL1-A17T | 118 |
| 20341 | MD_E_EA1L | E-EA1L | 116 |
| 20342 | MD_E_EA2S | E-EA2S | 117 |
| 20343 | MD_E_13EN0 | E-13EN0 | 118 |
| 20344 | MD_VENOM_BUG | Chemical Poison | 110 |
| 20345 | MD_CONSTANT | Bio Battery | 110 |
| 20346 | MD_MIGUEL | Miguel | 115 |
| 20347 | MD_MIGUEL_G | Miguel G. | 115 |
| 20348 | MD_A013_CAPUT | A013 - Caput | 110 |
| 20349 | MD_A013_DOLOR | A013 - Dolor | 111 |
| 20350 | MD_A013_BELLARE | A013 - Bellare | 112 |
| 20351 | MD_MANHOLE2 | Manhole | 1 |
| 20352 | MD_POMPOM | Fatal Pompom | 112 |
| 20353 | MD_CROB | Sorrow Crob | 111 |
| 20355 | EP17_1_BELLARE1 | Heart Hunter Bellare | 120 |
| 20356 | EP17_1_BELLARE2 | High Hunter Bellare | 165 |
| 20357 | EP17_1_SANARE1 | Heart Hunter Sanare | 120 |
| 20358 | EP17_1_SANARE2 | High Hunter Sanare | 168 |
| 20359 | EP17_1_PLAGA1 | Plaga | 164 |
| 20360 | EP17_1_PLAGA2 | Mutant Plaga | 178 |
| 20361 | EP17_1_DOLOR1 | Dolor | 122 |
| 20362 | EP17_1_DOLOR2 | Mutant Dolor | 173 |
| 20363 | EP17_1_VENENUM1 | Venenum | 123 |
| 20364 | EP17_1_VENENUM2 | Mutant Venenum | 176 |
| 20365 | EP17_1_TWIN_CAPUT1 | Twin Caput | 125 |
| 20366 | EP17_1_TWIN_CAPUT2 | Mutant Twin Caput | 175 |
| 20367 | RAYDRIC_H | Contaminated Raydric | 185 |
| 20368 | RAYDRIC_ARCHER_H | Contaminated Raydric Ar | 184 |
| 20369 | GARGOYLE_H | Frozen Gargoyle | 186 |
| 20370 | STING_H | Contaminated Sting | 180 |
| 20371 | RAGGED_ZOMBIE_H | Prison Breaker | 186 |
| 20372 | BLAZZER_H | Rigid Blazer | 178 |
| 20373 | NIGHTMARE_TERROR_H | Rigid Nightmare Terror | 179 |
| 20374 | DELETER1_H | Rigid Sky Deleter | 174 |
| 20375 | DELETER2_H | Rigid Earth Deleter | 173 |
| 20376 | EXPLOSION_H | Rigid Explosion | 171 |
| 20377 | KAHO_H | Rigid Kaho | 173 |
| 20378 | LAVA_GOLEM_H | Rigid Lava Golem | 177 |
| 20379 | ICE_GHOST_H | Ice Ghost | 189 |
| 20380 | FLAME_GHOST_H | Flame Ghost | 189 |
| 20381 | EP17_1_R4885_BESTIA | R48-85-Bestia | 174 |
| 20382 | G_TWIN_CAPUT2 | Twin Capute | 175 |
| 20419 | MUSPELLSKOLL_H | Rigid Muspellskoll | 188 |
| 20420 | WANDER_MAN_H | Corrupted Wanderer | 187 |
| 20421 | BRINARANEA_H | Corrupted Spider Queen | 195 |
| 20422 | DARK_LORD_H | Corrupted Dark Lord | 194 |
| 20543 | MD_ED_M_SCIENCE | MD_ED_M_SCIENCE | 172 |
| 20560 | G_MINERAL_G | Green Mineral | 190 |
| 20592 | POISONOUS | Poisonous | 188 |
| 20593 | TOXIOUS | Toxious | 188 |
| 20594 | MINERAL_G | Green Mineral | 190 |
| 20595 | MINERAL_R | Red Mineral | 190 |
| 20596 | MINERAL_W | White Mineral | 190 |
| 20597 | MINERAL_P | Purple Mineral | 190 |
| 20598 | JEWELIANT | Jewelry Ant | 191 |
| 20599 | G_JEWELIANT | Jewelry Ant | 191 |
| 20600 | JEWEL | Jewel | 192 |
| 20601 | JUNGOLIANT | Jewel Ungoliant | 197 |
| 20602 | PORCELLIO_W | White Porcellio | 188 |
| 20603 | ABYSSMAN | Abyssman | 190 |
| 20620 | MD_REDPEPPER | Red Pepper | 135 |
| 20621 | MD_REDPEPPER_H | Senior Red Pepper | 185 |
| 20622 | MD_ASSISTANT | Assistant Bot | 137 |
| 20623 | MD_ASSISTANT_H | Senior Assistant Bot | 187 |
| 20624 | MD_DRY_RAFFLESIA | Dry Rafflesia | 140 |
| 20625 | MD_DRY_RAFFLESIA_H | Senior Dry Rafflesia | 190 |
| 20626 | MD_ALNOLDI_EX | Special Alnoldi | 143 |
| 20627 | MD_ALNOLDI_EX_H | Senior Special Alnoldi | 193 |
| 20628 | EP17_2_ALPHA_MASTER | Manager Alpha | 180 |
| 20629 | EP17_2_BETA_BASIC | Manager Beta | 165 |
| 20630 | EP17_2_BETA_BASIC_NG | Broken Beta | 145 |
| 20631 | MD_BETA_SCISSORE_NG | Broken Gardener Beta | 135 |
| 20632 | MD_BETA_SCISSORE_NG_H | S. Broken Gardener Beta | 185 |
| 20633 | EP17_2_BETA_CLEANER_A | Broken Cleaner | 143 |
| 20634 | EP17_2_BETA_CLEANER_B | Broken Cleaner | 144 |
| 20635 | EP17_2_BETA_BATHS_A | Cleaning Robot | 145 |
| 20636 | EP17_2_BETA_BATHS_B | Cleaning Robot | 145 |
| 20637 | EP17_2_BETA_ITEMKEEPER | Broken Warehouse Manager | 185 |
| 20638 | EP17_2_BETA_GUARDS | Beta Guards | 140 |
| 20639 | EP17_2_BETA_GUARDS_NG | Broken Beta Guards | 186 |
| 20640 | EP17_2_OMEGA_CLEANER | Cleaning Robot | 130 |
| 20641 | EP17_2_OMEGA_CLEANER_NG | Broken Cleaning Robot | 175 |
| 20642 | MD_SWEETY | Sweety | 139 |
| 20643 | EP17_2_PHEN | Boiled Water Phen | 139 |
| 20644 | EP17_2_MARC | Boiled Water Marc | 137 |
| 20645 | EP17_2_SWORD_FISH | Boiled Water Swordfish | 138 |
| 20646 | EP17_2_PIRANHA | Boiled Water Piranha | 138 |
| 20647 | EP17_2_BATH_MERMAID | Elder of Chung-Geum | 141 |
| 20648 | EP17_2_PITAYA_BOSS | Boss Meow | 168 |
| 20649 | EP17_2_PITAYA_R | Red Pitaya | 162 |
| 20650 | EP17_2_PITAYA_Y | Yellow Pitaya | 164 |
| 20651 | EP17_2_PITAYA_B | Blue Pitaya | 165 |
| 20652 | EP17_2_PITAYA_V | Violet Pitaya | 165 |
| 20653 | EP17_2_PITAYA_G | Green Pitaya | 166 |
| 20654 | G_PITAYA_R | Red Pitaya | 132 |
| 20655 | G_PITAYA_Y | Yellow Pitaya | 134 |
| 20656 | G_PITAYA_B | Blue Pitaya | 135 |
| 20657 | G_PITAYA_V | Violet Pitaya | 135 |
| 20658 | G_PITAYA_G | Green Pitaya | 136 |
| 20659 | MD_PITAYA_BOSS | Pitaya Boss | 138 |
| 20660 | MD_PITAYA_R | Red Pitaya | 132 |
| 20661 | MD_PITAYA_Y | Yellow Pitaya | 134 |
| 20662 | MD_PITAYA_B | Blue Pitaya | 135 |
| 20663 | MD_PITAYA_V | Violet Pitaya | 135 |
| 20664 | MD_PITAYA_G | Green Pitaya | 136 |
| 20665 | MD_VERPORTA | Verporta | 136 |
| 20666 | MD_VERPORTE_H | Verporte | 186 |
| 20667 | MD_SILVA_PAPILIA | Silva Papilia | 145 |
| 20668 | MD_GRAN_PAPILIA | Gran Papilia | 195 |
| 20669 | MD_PAPILA | Papila | 138 |
| 20670 | MD_PAPILA_H | Senior Papila | 188 |
| 20671 | MD_PAPILA_RUBA | Papila Ruba | 139 |
| 20672 | MD_PAPILA_RUBA_H | Senior Papila Ruba | 190 |
| 20673 | MD_PAPILA_RUBA2 | Papila Ruba | 150 |
| 20674 | MD_PAPILA_CAE | Papila Cae | 137 |
| 20675 | MD_PAPILA_CAE_H | Senior Papila Cae | 187 |
| 20676 | MD_PAPILA_CAE2 | Papila Cae | 150 |
| 20677 | MD_ARIES | Aries | 140 |
| 20678 | MD_ARIES_H | Senior Aries | 190 |
| 20679 | EP17_2_GUARDIAN_PARTS | Guardian Parts | 130 |
| 20680 | EP17_2_HEART_HUNTER | Heart Hunter Skirmisher | 130 |
| 20681 | G_EP17_2_HEART_HUNTER | Heart Hunter Skirmisher | 130 |
| 20682 | EP17_2_HEART_HUNTER_H | Heart Hunter Skirmisher | 176 |
| 20683 | EP17_2_BOOKWORM | Bookworm | 141 |
| 20684 | EP17_2_ROAMING_SPLBOOK | Roaming Spellbook | 144 |
| 20685 | EP17_2_VENENUM3 | Sewage Venenum | 142 |
| 20686 | EP17_2_CRAMP | Sewage Cramp | 140 |
| 20687 | EP17_2_WATERFALL | Sewage Waterfall | 141 |
| 20688 | EP17_2_BELLARE3 | Elite Bellare | 143 |
| 20689 | EP17_2_DOLOR3 | Spell Addicted Dolor | 145 |
| 20690 | EP17_2_PLASMA_Y | Released Spell | 144 |
| 20691 | EP17_2_PLAGA3 | Spell Addicted Plaga | 192 |
| 20692 | EP17_2_SANARE3 | Spell Addicted Sanare | 194 |
| 20693 | EP17_2_PLASMA_R | Powerful Spell | 193 |
| 20694 | EP17_2_PLASMA_R2 | Sharp Spell | 193 |
| 20696 | EP17_2_CHILD_ADMIN1 | Child Admin Beta | 130 |
| 20697 | EP17_2_CHILD_ADMIN2 | Child Admin Alpha | 180 |
| 20698 | G_ASSISTANT | Assistant | 137 |
| 20699 | G_BELLARE3 | Heart Hunter Commander | 143 |
| 20700 | G_BETA_SCISSORE_NG | Broken Gardener Beta | 135 |
| 20801 | ILL_SROPHO | Deep Sea Sropho | 147 |
| 20802 | ILL_OBEAUNE | Deep Sea Obeaune | 149 |
| 20803 | ILL_DEVIACE | Deep Sea Deviace | 150 |
| 20804 | ILL_MARSE | Deep Sea Marse | 149 |
| 20805 | ILL_MERMAN | Deep Sea Merman | 148 |
| 20806 | ILL_SEDORA | Deep Sea Sedora | 199 |
| 20807 | ILL_SWORD_FISH | Deep Sea Swordfish | 199 |
| 20808 | ILL_STROUF | Deep Sea Strouf | 201 |
| 20809 | ILL_PHEN | Deep Sea Phen | 199 |
| 20810 | ILL_KING_DRAMOH | Deep Sea King Dramoh | 205 |
| 20811 | ILL_KRAKEN | Deep Sea Kraken | 204 |
| 20834 | ABR_BATTLE_WARIOR | ABR Battle Warrior | 200 |
| 20835 | ABR_DUAL_CANNON | ABR Duel Cannon | 200 |
| 20836 | ABR_MOTHER_NET | ABR Mother Net | 200 |
| 20837 | ABR_INFINITY | ABR Infinity | 200 |
| 20843 | ILL_ABYSMAL_WITCH | Deep Sea Witch | 205 |
| 20846 | MD_HIDDEN_GROUND01 | Plague of Corruption | 170 |
| 20847 | MD_HIDDEN_GROUND02 | Plague of Corruption | 170 |
| 20848 | SUMMON_WOODENWARRIOR | Wooden Warrior | 200 |
| 20849 | SUMMON_WOODEN_FAIRY | Wooden Fairy | 200 |
| 20850 | SUMMON_CREEPER | Creeper | 200 |
| 20851 | SUMMON_HELLTREE | Hell Tree | 200 |
| 20920 | CHIMERA_LAVA | Lavaeter | 243 |
| 20921 | CHIMERA_FULGOR | Fulgor | 244 |
| 20922 | CHIMERA_NAPEO | Napeo | 244 |
| 20923 | CHIMERA_GALENSIS | Galensis | 244 |
| 20924 | CHIMERA_AMITERA | Amitera | 227 |
| 20925 | CHIMERA_LITUS | Litus | 228 |
| 20926 | CHIMERA_FILLIA | Fillia | 229 |
| 20927 | CHIMERA_VANILAQUS | Vanilaqus | 230 |
| 20928 | CHIMERA_THEONE | The One | 245 |
| 20929 | GIANT_CAPUT | Giant Caput | 213 |
| 20930 | DOLORIAN | Dolorian | 214 |
| 20931 | PLAGARION | Plagarion | 215 |
| 20932 | DEADRE | Deadre | 214 |
| 20933 | VENEDI | Venedi | 213 |
| 20934 | R001_BESTIA | R001-Bestia | 215 |
| 20935 | GAN_CEANN | Gan Ceann | 215 |
| 20936 | DISGUISER | Disguiser | 254 |
| 20937 | BRUTAL_MURDERER | Brutal Murderer | 214 |
| 20938 | GHOST_CUBE | Ghost Cube | 213 |
| 20939 | LUDE_GAL | Lude Gal | 213 |
| 20940 | BLUEMOON_LOLI_RURI | Blue Moon Loli Ruri | 255 |
| 20941 | GROTE | Grote | 253 |
| 20942 | PIERROTZOIST | Pierrotzoist | 255 |
| 20943 | DEATH_WITCH | Death Witch | 255 |
| 21064 | S_DUMMY_100_SMALL | Training Dummy (Small) | 100 |
| 21065 | S_DUMMY_100_MEDIUM | Training Dummy (Medium) | 100 |
| 21066 | S_DUMMY_100_LARGE | Training Dummy (Large) | 100 |
| 21067 | S_DUMMY_100_NOTHING | Training Dummy (Neutral) | 100 |
| 21068 | S_DUMMY_100_DRAGON | Training Dummy (Dragon) | 100 |
| 21069 | S_DUMMY_100_ANIMAL | Training Dummy (Brute) | 100 |
| 21070 | S_DUMMY_100_HUMAN | Training Dummy (Human) | 100 |
| 21071 | S_DUMMY_100_INSECT | Training Dummy (Insect) | 100 |
| 21072 | S_DUMMY_100_FISH | Training Dummy (Fish) | 100 |
| 21073 | S_DUMMY_100_DEMON | Training Dummy (Demon) | 100 |
| 21074 | S_DUMMY_100_PLANT | Training Dummy (Plant) | 100 |
| 21075 | S_DUMMY_100_ANGEL | Training Dummy (Angel) | 100 |
| 21076 | S_DUMMY_100_UNDEAD | Training Dummy (Undead) | 100 |
| 21077 | S_DUMMY_100_NOTHING2 | Dummy (Neutral Lv1) | 100 |
| 21078 | S_DUMMY_100_WATER | Dummy (Water Lv1) | 100 |
| 21079 | S_DUMMY_100_GROUND | Dummy (Earth Lv1) | 100 |
| 21080 | S_DUMMY_100_FIRE | Dummy (Fire Lv1) | 100 |
| 21081 | S_DUMMY_100_WIND | Dummy (Wind Lv1) | 100 |
| 21082 | S_DUMMY_100_POISON | Dummy (Poison Lv1) | 100 |
| 21083 | S_DUMMY_100_SAINT | Dummy (Holy Lv1) | 100 |
| 21084 | S_DUMMY_100_DARKNESS | Dummy (Dark Lv1) | 100 |
| 21085 | S_DUMMY_100_TELEKINESIS | Dummy (Ghost Lv1) | 100 |
| 21086 | S_DUMMY_100_UNDEAD2 | Dummy (Undead Lv1) | 100 |
| 21087 | S_DUMMY_100_HUMANP | Dummy (Human Player) | 100 |
| 21088 | S_DUMMY_100_DORAMP | Dummy (Doram Player) | 100 |
| 21292 | EP18_ARMED_VILLAGER01 | Armed villager | 180 |
| 21293 | EP18_ARMED_VILLAGER02 | Armed villager | 180 |
| 21294 | EP18_ARMED_VILLAGER03 | Armed villager | 180 |
| 21295 | EP18_ASH_TOAD | Ash Toad | 179 |
| 21296 | EP18_RAKEHAND | Rakehand | 177 |
| 21297 | EP18_SPARK | Spark | 181 |
| 21298 | EP18_HOT_MOLAR | Hot Molar | 212 |
| 21299 | EP18_VOLCARING | Volcaring | 185 |
| 21300 | EP18_LAVA_TOAD | Lava Toad | 211 |
| 21301 | EP18_BURNING_FANG | Burning Fang | 212 |
| 21302 | EP18_ASHHOPPER | Ashhopper | 185 |
| 21303 | EP18_ASHRING | Ashring | 185 |
| 21304 | EP18_GREY_WOLF | Grey Wolf | 187 |
| 21305 | EP18_TUMBLE_RING | Tumblering | 185 |
| 21306 | EP18_FIREWIND_KITE | Firewind Kite | 188 |
| 21307 | EP18_PHANTOM_WOLF | Phantom Wolf | 186 |
| 21308 | EP18_MD_HEARTHUNTER_A | Heart Hunter | 178 |
| 21309 | EP18_MD_THOR_GUARD | Base Soldier | 179 |
| 21310 | EP18_MD_GUARD_A | Temple Guard | 179 |
| 21311 | EP18_MD_GUARD_B | Traditional Temple Guard | 182 |
| 21312 | EP18_MD_HEARTHUNTER_R | Heart Hunter | 184 |
| 21313 | EP18_MD_HEARTHUNTER_F | Heart Hunter | 185 |
| 21314 | EP18_MD_SCHULANG | Schulang | 185 |
| 21315 | EP18_MD_DEMI_FREYJA | Twisted God Freyja | 186 |
| 21316 | EP18_MD_SCHULANG_R | Schulang | 185 |
| 21317 | EP18_MD_DEMI_FREYJA_R | Twisted God Freyja | 185 |
| 21318 | EP18_MD_SANARE_R | Goddess Guardian | 170 |
| 21319 | EP18_MD_HEARTHUNTER_R2 | Cottage Keeper | 170 |
| 21320 | EP18_NPC_MARAM | Maram | 185 |
| 21321 | EP18_NPC_MIRIAM | Miriam | 185 |
| 21322 | EP18_NPC_SUAD | Suad | 185 |
| 21323 | EP18_GREY_GOAT | Ashen Goat | 168 |
| 21324 | EP18_GREY_WOLF_BABY | Baby Gray Wolf | 165 |
| 21360 | EP18_MD_SCHULANG_L | Schulang | 224 |
| 21361 | EP18_MD_DEMI_FREYJA_L | Twisted God Freyja | 224 |
| 21377 | EP18_MD_SANARE_L | Goddess Guardian | 210 |
| 21378 | EP18_MD_HEARTHUNTER_L | Cottage Keeper | 210 |
| 21386 | ILL_ANDRE | Diligent Andre | 167 |
| 21387 | ILL_SOLDIER_ANDR | Diligent Soldier Andre | 169 |
| 21388 | ILL_ANDRE_LARVA | Diligent Andre Larva | 164 |
| 21389 | ILL_DENIRO | Diligent Deniro | 167 |
| 21390 | ILL_PIERE | Diligent Piere | 167 |
| 21391 | ILL_ANT_EGG | Mushy Ant Egg | 164 |
| 21392 | ILL_GIEARTH | Gutsy Giearth | 168 |
| 21393 | ILL_FARMILIAR | Gutsy Familiar | 166 |
| 21394 | ILL_VITATA | Diligent Vitata | 169 |
| 21395 | ILL_MAYA | Silent Maya | 175 |
| 21866 | HEROS_IN_ORB_1 | Spring Jewel | 250 |
| 21867 | HEROS_IN_ORB_2 | Summer Jewel | 250 |
| 21868 | HEROS_IN_ORB_3 | Autumn Jewel | 250 |
| 21869 | HEROS_IN_ORB_4 | Winter Jewel | 250 |
| 21887 | HEROS_OUT_ORB | Jewel | 250 |
| 22177 | MD_PRI_DRAGON_1 | MD_PRI_DRAGON_1 |  |
| 22178 | MD_PRI_DRAGON_2 | MD_PRI_DRAGON_2 |  |
| 22179 | MD_PRI_DRAGON_3 | MD_PRI_DRAGON_3 |  |
| 22180 | MD_PRI_DRAGON_4 | MD_PRI_DRAGON_4 |  |
| 22192 | SPIRIT_G_LAND_S | L Blue Earth Spirit | 262 |
| 22193 | SPIRIT_G_LAND_M | Blue Earth Spirit | 263 |
| 22194 | SPIRIT_G_LAND_L | G Blue Earth Spirit | 264 |
| 22195 | SPIRIT_G_LAND_SL | M Blue Earth Spirit | 264 |
| 22196 | SPIRIT_B_FLAME_S | L Blue Flame Spirit | 262 |
| 22197 | SPIRIT_B_FLAME_M | Blue Flame Spirit | 263 |
| 22198 | SPIRIT_B_FLAME_L | G Blue Flame Spirit | 264 |
| 22199 | SPIRIT_B_FLAME_SL | Blue Flame Mutant Spirit | 264 |
| 22200 | SPIRIT_S_WIND_S | L Strong Wind Spirit | 262 |
| 22201 | SPIRIT_S_WIND_M | Strong Wind Spirit | 263 |
| 22202 | SPIRIT_S_WIND_L | G Strong Wind Spirit | 264 |
| 22203 | SPIRIT_S_WIND_SL | M Strong Wind Spirit | 264 |
| 22204 | SPIRIT_I_WATER_S | L Cold Water Spirit | 262 |
| 22205 | SPIRIT_I_WATER_M | Cold Water Spirit | 263 |
| 22206 | SPIRIT_I_WATER_L | G Cold Water Spirit | 264 |
| 22207 | SPIRIT_I_WATER_SL | M Cold Water Spirit | 264 |
| 22208 | SPIRIT_C_LAND_S | L Polluted Earth Spirit | 263 |
| 22209 | SPIRIT_C_LAND_M | Polluted Earth Spirit | 264 |
| 22210 | SPIRIT_C_LAND_L | G Polluted Earth Spirit | 265 |
| 22211 | SPIRIT_C_LAND_SL | M Polluted Earth Spirit | 265 |
| 22212 | SPIRIT_C_FLAME_S | L Tainted Flame Spirit | 263 |
| 22213 | SPIRIT_C_FLAME_M | Tainted Flame Spirit | 264 |
| 22214 | SPIRIT_C_FLAME_L | G Tainted Flame Spirit | 265 |
| 22215 | SPIRIT_C_FLAME_SL | M Tainted Flame Spirit | 265 |
| 22216 | SPIRIT_H_WATER_S | L Hot Water Spirit | 262 |
| 22217 | SPIRIT_H_WATER_M | Hot Water Spirit | 263 |
| 22218 | SPIRIT_H_WATER_L | G Hot Water Spirit | 264 |
| 22219 | SPIRIT_H_WATER_SL | M Hot Water Spirit | 264 |
| 22220 | SPIRIT_D_WIND_S | L Dry Wind Spirit | 262 |
| 22221 | SPIRIT_D_WIND_M | Dry Wind Spirit | 263 |
| 22222 | SPIRIT_D_WIND_L | G Dry Wind Spirit | 264 |
| 22223 | SPIRIT_D_WIND_SL | M Dry Wind Spirit | 264 |
| 22224 | SPIRIT_R_FLAME_S | L Red Flame Spirit | 262 |
| 22225 | SPIRIT_R_FLAME_M | Red Flame Spirit | 263 |
| 22226 | SPIRIT_R_FLAME_L | G Red Flame Spirit | 264 |
| 22227 | SPIRIT_R_FLAME_SL | M Red Flame Spirit | 264 |
| 22228 | SPIRIT_F_LAND_S | L Solid Earth Spirit | 262 |
| 22229 | SPIRIT_F_LAND_M | Solid Earth Spirit | 263 |
| 22230 | SPIRIT_F_LAND_L | G Solid Earth Spirit | 264 |
| 22231 | SPIRIT_F_LAND_SL | M Solid Earth Spirit | 264 |
| 22232 | SPIRIT_C_WATER_S | L Polluted Water Spirit | 263 |
| 22233 | SPIRIT_C_WATER_M | Polluted Water Spirit | 264 |
| 22234 | SPIRIT_C_WATER_L | G Polluted Water Spirit | 265 |
| 22235 | SPIRIT_C_WATER_SL | M Polluted Water Spirit | 265 |
| 22236 | SPIRIT_C_WIND_S | L Tainted Wind Spirit | 263 |
| 22237 | SPIRIT_C_WIND_M | Tainted Wind Spirit | 264 |
| 22238 | SPIRIT_C_WIND_L | G Tainted Wind Spirit | 265 |
| 22239 | SPIRIT_C_WIND_SL | M Tainted Wind Spirit | 265 |
| 22551 | S_DUMMY_SMALL_R10 | Dummy (Small) | 100 |
| 22552 | S_DUMMY_MEDIUM_R10 | Dummy (Medium) | 100 |
| 22553 | S_DUMMY_LARGE_R10 | Dummy (Large) | 100 |
| 22554 | S_DUMMY_XLARGE_R40 | Dummy (Extra Large) | 100 |
| 22555 | S_DUMMY_SMALL_R20 | Dummy (Small) | 100 |
| 22556 | S_DUMMY_MEDIUM_R20 | Dummy (Medium) | 100 |
| 22557 | S_DUMMY_LARGE_R20 | Dummy (Large) | 100 |
| 22558 | S_DUMMY_XLARGE_R50 | Dummy (Extra Large) | 100 |
| 22559 | S_DUMMY_SMALL_R30 | Dummy (Small) | 100 |
| 22560 | S_DUMMY_MEDIUM_R30 | Dummy (Medium) | 100 |
| 22561 | S_DUMMY_SMALL1 | Dummy (Small) | 100 |
| 22562 | S_DUMMY_MEDIUM1 | Dummy (Medium) | 100 |
| 22563 | S_DUMMY_LARGE1 | Dummy (Large) | 100 |
| 22564 | S_DUMMY_SMALL1_R10 | Dummy (Small) | 100 |
| 22565 | S_DUMMY_MEDIUM1_R10 | Dummy (Medium) | 100 |
| 22566 | S_DUMMY_LARGE1_R10 | Dummy (Large) | 100 |
| 22567 | S_DUMMY_XLARGE1_R40 | Dummy (Extra Large) | 100 |
| 22568 | S_DUMMY_SMALL1_R20 | Dummy (Small) | 100 |
| 22569 | S_DUMMY_MEDIUM1_R20 | Dummy (Medium) | 100 |
| 22570 | S_DUMMY_LARGE1_R20 | Dummy (Large) | 100 |
| 22571 | S_DUMMY_XLARGE1_R50 | Dummy (Extra Large) | 100 |
| 22572 | S_DUMMY_SMALL1_R30 | Dummy (Small) | 100 |
| 22573 | S_DUMMY_MEDIUM1_R30 | Dummy (Medium) | 100 |
| 22574 | S_DUMMY_LARGE1_R30 | Dummy (Large) | 100 |
| 22575 | S_DUMMY_SMALL2 | Dummy (Small) | 100 |
| 22576 | S_DUMMY_MEDIUM2 | Dummy (Medium) | 100 |
| 22577 | S_DUMMY_LARGE2 | Dummy (Large) | 100 |
| 22578 | S_DUMMY_SMALL2_R10 | Dummy (Small) | 100 |
| 22579 | S_DUMMY_MEDIUM2_R10 | Dummy (Medium) | 100 |
| 22580 | S_DUMMY_LARGE2_R10 | Dummy (Large) | 100 |
| 22581 | S_DUMMY_XLARGE2_R40 | Dummy (Extra Large) | 100 |
| 22582 | S_DUMMY_SMALL2_R20 | Dummy (Small) | 100 |
| 22583 | S_DUMMY_MEDIUM2_R20 | Dummy (Medium) | 100 |
| 22584 | S_DUMMY_LARGE2_R20 | Dummy (Large) | 100 |
| 22585 | S_DUMMY_XLARGE2_R50 | Dummy (Extra Large) | 100 |
| 22586 | S_DUMMY_SMALL2_R30 | Dummy (Small) | 100 |
| 22587 | S_DUMMY_MEDIUM2_R30 | Dummy (Medium) | 100 |
| 22588 | S_DUMMY_LARGE2_R30 | Dummy (Large) | 100 |
| 22589 | S_DUMMY_SMALL_M10 | Dummy (Small) | 100 |
| 22590 | S_DUMMY_MEDIUM_M10 | Dummy (Medium) | 100 |
| 22591 | S_DUMMY_LARGE_M10 | Dummy (Large) | 100 |
| 22592 | S_DUMMY_XLARGE_M40 | Dummy (Extra Large) | 100 |
| 22593 | S_DUMMY_SMALL_M20 | Dummy (Small) | 100 |
| 22594 | S_DUMMY_MEDIUM_M20 | Dummy (Medium) | 100 |
| 22595 | S_DUMMY_LARGE_M20 | Dummy (Large) | 100 |
| 22596 | S_DUMMY_XLARGE_M50 | Dummy (Extra Large) | 100 |
| 22597 | S_DUMMY_SMALL_M30 | Dummy (Small) | 100 |
| 22598 | S_DUMMY_MEDIUM_M30 | Dummy (Medium) | 100 |
| 22599 | S_DUMMY_LARGE_M30 | Dummy (Large) | 100 |
| 22600 | S_DUMMY_SMALL3 | Dummy (Small) | 100 |
| 22601 | S_DUMMY_MEDIUM3 | Dummy (Medium) | 100 |
| 22602 | S_DUMMY_LARGE3 | Dummy (Large) | 100 |
| 22603 | S_DUMMY_SMALL3_M10 | Dummy (Small) | 100 |
| 22604 | S_DUMMY_MEDIUM3_M10 | Dummy (Medium) | 100 |
| 22605 | S_DUMMY_LARGE3_M10 | Dummy (Large) | 100 |
| 22606 | S_DUMMY_XLARGE1_M40 | Dummy (Extra Large) | 100 |
| 22607 | S_DUMMY_SMALL3_M20 | Dummy (Small) | 100 |
| 22608 | S_DUMMY_MEDIUM3_M20 | Dummy (Medium) | 100 |
| 22609 | S_DUMMY_LARGE3_M20 | Dummy (Large) | 100 |
| 22610 | S_DUMMY_XLARGE1_M50 | Dummy (Extra Large) | 100 |
| 22611 | S_DUMMY_SMALL3_M30 | Dummy (Small) | 100 |
| 22612 | S_DUMMY_MEDIUM3_M30 | Dummy (Medium) | 100 |
| 22613 | S_DUMMY_LARGE3_M30 | Dummy (Large) | 100 |
| 22614 | S_DUMMY_SMALL4 | Dummy (Small) | 100 |
| 22615 | S_DUMMY_MEDIUM4 | Dummy (Medium) | 100 |
| 22616 | S_DUMMY_LARGE4 | Dummy (Large) | 100 |
| 22617 | S_DUMMY_SMALL4_M10 | Dummy (Small) | 100 |
| 22618 | S_DUMMY_MEDIUM4_M10 | Dummy (Medium) | 100 |
| 22619 | S_DUMMY_LARGE4_M10 | Dummy (Large) | 100 |
| 22620 | S_DUMMY_XLARGE2_M40 | Dummy (Extra Large) | 100 |
| 22621 | S_DUMMY_SMALL4_M20 | Dummy (Small) | 100 |
| 22622 | S_DUMMY_MEDIUM4_M20 | Dummy (Medium) | 100 |
| 22623 | S_DUMMY_LARGE4_M20 | Dummy (Large) | 100 |
| 22624 | S_DUMMY_XLARGE2_M50 | Dummy (Extra Large) | 100 |
| 22625 | S_DUMMY_SMALL4_M30 | Dummy (Small) | 100 |
| 22626 | S_DUMMY_MEDIUM4_M30 | Dummy (Medium) | 100 |
| 22627 | S_DUMMY_LARGE4_M30 | Dummy (Large) | 100 |
| 22628 | S_DUMMY2_NOTHING | Dummy (Formless Race) | 100 |
| 22629 | S_DUMMY2_DRAGON | Dummy (Dragon Race) | 100 |
| 22630 | S_DUMMY2_ANIMAL | Dummy (Brute Race) | 100 |
| 22631 | S_DUMMY2_HUMAN | Dummy (Human Race) | 100 |
| 22632 | S_DUMMY2_INSECT | Dummy (Insect Race) | 100 |
| 22633 | S_DUMMY2_FISH | Dummy (Fish Race) | 100 |
| 22634 | S_DUMMY2_DEMON | Dummy (Demon Race) | 100 |
| 22635 | S_DUMMY2_PLANT | Dummy (Plant Race) | 100 |
| 22636 | S_DUMMY2_ANGEL | Dummy (Angel Race) | 100 |
| 22637 | S_DUMMY2_UNDEAD | Dummy (Undead Race) | 100 |
| 22638 | S_DUMMY3_NOTHING | Dummy (Formless Race) | 100 |
| 22639 | S_DUMMY3_DRAGON | Dummy (Dragon Race) | 100 |
| 22640 | S_DUMMY3_ANIMAL | Dummy (Brute Race) | 100 |
| 22641 | S_DUMMY3_HUMAN | Dummy (Human Race) | 100 |
| 22642 | S_DUMMY3_INSECT | Dummy (Insect Race) | 100 |
| 22643 | S_DUMMY3_FISH | Dummy (Fish Race) | 100 |
| 22644 | S_DUMMY3_DEMON | Dummy (Demon Race) | 100 |
| 22645 | S_DUMMY3_PLANT | Dummy (Plant Race) | 100 |
| 22646 | S_DUMMY3_ANGEL | Dummy (Angel Race) | 100 |
| 22647 | S_DUMMY3_UNDEAD | Dummy (Undead Race) | 100 |
| 22648 | S_DUMMY2_NOTHING2 | Dummy (Neutral) | 100 |
| 22649 | S_DUMMY2_WATER | Dummy (Water) | 100 |
| 22650 | S_DUMMY2_GROUND | Dummy (Earth) | 100 |
| 22651 | S_DUMMY2_FIRE | Dummy (Fire) | 100 |
| 22652 | S_DUMMY2_WIND | Dummy (Wind) | 100 |
| 22653 | S_DUMMY2_POISON | Dummy (Poison) | 100 |
| 22654 | S_DUMMY2_SAINT | Dummy (Holy) | 100 |
| 22655 | S_DUMMY2_DARKNESS | Dummy (Dark) | 100 |
| 22656 | S_DUMMY2_TELEKINESIS | Dummy (Ghost) | 100 |
| 22657 | S_DUMMY2_UNDEAD2 | Dummy (Undead) | 100 |
| 22658 | S_DUMMY3_NOTHING2 | Dummy (Neutral) | 100 |
| 22659 | S_DUMMY3_WATER | Dummy (Water) | 100 |
| 22660 | S_DUMMY3_GROUND | Dummy (Earth) | 100 |
| 22661 | S_DUMMY3_FIRE | Dummy (Fire) | 100 |
| 22662 | S_DUMMY3_WIND | Dummy (Wind) | 100 |
| 22663 | S_DUMMY3_POISON | Dummy (Poison) | 100 |
| 22664 | S_DUMMY3_SAINT | Dummy (Holy) | 100 |
| 22665 | S_DUMMY3_DARKNESS | Dummy (Dark) | 100 |
| 22666 | S_DUMMY3_TELEKINESIS | Dummy (Ghost) | 100 |
| 22667 | S_DUMMY3_UNDEAD2 | Dummy (Undead) | 100 |
| 22668 | S_DUMMY_LARGE_R30 | Dummy (Large) | 100 |

## 2. Карты НЕ добавлены — 3 (конфликт ID)

| ID | AegisName | Причина |
|---:|---|---|
| 4359 | B_Eremes_Card | ID занят другим предметом в uAthena |
| 4361 | B_Harword_Card | ID занят другим предметом в uAthena |
| 4441 | Fallen_Bishop_Card | ID занят другим предметом в uAthena |

## 3. Карты добавлены в item_db2, но БЕЗ эффекта — 246

Предмет существует (дроп/коллекция/торговля), скрипт-бонус не портирован (реневал-бонус, `.@`, или 1-арг `bonus`). Оригиналы скриптов — в `backport_renewal_card_scripts.txt`.

| ID | AegisName |
|---:|---|
| 4472 | Bradium_Goram_Card |
| 4474 | Jakudam_Card |
| 4505 | Scaraba_Card |
| 4507 | Q_Scaraba_Card |
| 4510 | Miming_Card |
| 4511 | Little_Fatum_Card |
| 4518 | Banaspaty_Card |
| 4520 | Leak_Card |
| 4522 | Sropho_Card |
| 4528 | Mutant_Coelacanth_Card |
| 4529 | Cruel_Coelacanth_Card |
| 4531 | Red_Eruma_Card |
| 4533 | Mini_Octopus_Card |
| 4556 | Fenrir_Card |
| 4557 | Fenrir_Card_ |
| 4562 | Champion_Card |
| 4570 | Flamel_Card |
| 4574 | Daehyon_Card |
| 4575 | Soheon_Card |
| 4576 | Gioia_Card |
| 4577 | Elvira_Card |
| 4578 | Pyuriel_Card |
| 4579 | Lora_Card |
| 4581 | Rudo_Card |
| 4583 | Engkanto_Card |
| 4586 | Tikbalang_Card |
| 4596 | AntiqueBook_Card |
| 4597 | LichternB_Card |
| 4598 | LichternY_Card |
| 4599 | LichternR_Card |
| 4600 | LichternG_Card |
| 4601 | Amdarais_Card |
| 4607 | FaithfulManager_Card |
| 4610 | Sarah_Card |
| 4629 | Arc_Elder_Card |
| 4635 | P_Amdarais_Card |
| 4636 | Bijou_Card |
| 4639 | Tappy_Card |
| 4642 | IFN_Toad_Card |
| 4643 | IFN_V_Wolf_Card |
| 4644 | IFN_Vocal_Card |
| 4645 | IFN_Eclipse_Card |
| 4650 | IFN_OrcHero_Card |
| 4656 | Grave_Mummy_Card |
| 4657 | Grave_A_Mummy_Card |
| 4660 | Basilisk1_Card |
| 4661 | Basilisk2_Card |
| 4662 | Big_Eggring_Card |
| 4669 | Ju_Mandragora_Card |
| 4670 | Fru_Pom_Spider_Card |
| 4671 | Sorcerer_Card |
| 4672 | Sura_Card |
| 4673 | Minstrel_Card |
| 4674 | GuillotineCross_Card |
| 4675 | Archbishop_Card |
| 4676 | Ranger_Card |
| 4677 | Mechanic_Card |
| 4678 | Warlock_Card |
| 4679 | RuneKnight_Card |
| 4680 | RoyalGuard_Card |
| 4681 | Genetic_Card |
| 4682 | ShadowChaser_Card |
| 4683 | Wanderer_Card |
| 4684 | Real_Eremes_Card |
| 4685 | Real_Magaleta_Card |
| 4686 | Real_Katrinn_Card |
| 4687 | Real_Shecil_Card |
| 4688 | Real_Harword_Card |
| 4689 | Real_Seyren_Card |
| 4690 | Real_Randel_Card |
| 4691 | Real_Flamel_Card |
| 4692 | Real_Ceila_Card |
| 4693 | Real_Chen_Card |
| 4694 | Real_Gertie_Card |
| 4695 | Real_Trentini_Card |
| 4696 | Real_Alphoccio_Card |
| 4698 | Step_Card |
| 4699 | Rock_Step_Card |
| 27012 | Kick_Step_Card |
| 27013 | KickAndKick_Card |
| 27014 | GreenCenere_Card |
| 27015 | RepairRobot_T_Card |
| 27020 | T_W_O_Card |
| 27025 | Lich_Lord_Card |
| 27026 | Fire_Condor_Card |
| 27028 | Fire_Frilldora_Card |
| 27030 | Fulbuk_Card |
| 27082 | AngerNineTail_Card |
| 27083 | BitterBonGun_Card |
| 27084 | BitterSohee_Card |
| 27085 | BitterMunak_Card |
| 27086 | BitterArcherSk_Card |
| 27087 | WizardOfVeritas_Card |
| 27101 | SweetNightM_Card |
| 27102 | MattDrainliar_Card |
| 27103 | LivingDead_Card |
| 27106 | Grand_Pere_Card |
| 27113 | AwakenKtullanux_Card |
| 27114 | OminousSolider_Card |
| 27115 | OminousPermeter_Card |
| 27117 | OminousAssulter_Card |
| 27118 | OminousFreezer_Card |
| 27119 | OminousTurtleG_Card |
| 27121 | Piranha_Card |
| 27123 | Toucan_Card |
| 27149 | Heart_Hunter_Card |
| 27151 | Evil_Card |
| 27152 | Cutie_Card |
| 27157 | Wood_Goblin_Card |
| 27164 | Faceworm_Q_Card |
| 27166 | Faceworm_Egg_Card |
| 27167 | Faceworm_L_Card |
| 27169 | Payon_Soldier_Card |
| 27172 | Cowraiders3_Card |
| 27173 | E_Cowraiders1_Card |
| 27174 | E_Cowraiders2_Card |
| 27175 | E_Cowraiders3_Card |
| 27176 | Rr_Cramp_Card |
| 27177 | Rr_Arclouse_Card |
| 27178 | Gaster_Card |
| 27179 | Coyote_Card |
| 27181 | AirShip_Raid_Card |
| 27182 | Felock_Card |
| 27249 | Archi_Card |
| 27250 | Dio_Anemos_Card |
| 27253 | Geffen_Thief_Card |
| 27255 | Ordre_Card |
| 27257 | Kuro_Akuma_Card |
| 27259 | Rechenier_Card |
| 27261 | Jew_Card |
| 27262 | Dy_Card |
| 27263 | Fei_Kanabian_Card |
| 27286 | Colorful_T_Bear_Card |
| 27287 | Shining_T_Bear_Card |
| 27288 | Pitman_Worker_Card |
| 27289 | Fragment_Of_Soul_Card |
| 27290 | Sinister_Obsidian_Card |
| 27292 | Ancient_Sta_Golem_Card |
| 27293 | Ancient_Megalith_Card |
| 27294 | Ancient_Tao_Gunka_Card |
| 27295 | Ancient_S_Shooter_Card |
| 27296 | Ancient_W_Shooter_Card |
| 27298 | Ancient_W_Deffend_Card |
| 27305 | EL_A17T_Card |
| 27306 | Bellare_Card |
| 27307 | High_Bellare_Card |
| 27308 | Sanare_Card |
| 27309 | High_Sanare_Card |
| 27310 | Plaga_Card |
| 27311 | Mutant_Plaga_Card |
| 27313 | Mt_Dolor_Card |
| 27314 | Venenum_Card |
| 27315 | Mt_Venenum_Card |
| 27318 | Miguel_Card |
| 27320 | E_EA1L_Card |
| 27321 | DespairGodMorocc_Card |
| 27324 | Brinaranea_Card |
| 27327 | ReaperAnkou_Card |
| 27346 | Firm_Muspell_Card |
| 27348 | Firm_Lava_G_Card |
| 27350 | Firm_Deleter1_Card |
| 27356 | Frozen_Gargoyle_Card |
| 27361 | Polluted_W_Man_Card |
| 27362 | Polluted_Spi_Q_Card |
| 31017 | XM_Cookie_Card |
| 31018 | XM_Mystcase_Card |
| 31019 | XM_Lude_Card |
| 31020 | XM_Hylozoist_Card |
| 31023 | XM_Celine_Kimi_Card |
| 31024 | As_Bdy_Knight_Card |
| 31025 | As_Wind_Ghost_Card |
| 31026 | As_Ragged_Golem_Card |
| 300005 | Abyss_Man_Card |
| 300006 | Jeweliant_Card |
| 300076 | Beta_Guards_Ng_Card |
| 300077 | O_Cleaner_Ng_Card |
| 300078 | Sweety_Card |
| 300082 | Assistant_H_Card |
| 300086 | Alnoldi_Ex_H_Card |
| 300087 | Beta_Scissore_Ng_Card |
| 300088 | B_Scissore_Ng_H_Card |
| 300090 | Verporte_H_Card |
| 300094 | Papila_Ruba_H_Card |
| 300096 | Papila_Cae_H_Card |
| 300098 | Aries_H_Card |
| 300099 | Silva_Papilia_Card |
| 300100 | Gran_Papilia_Card |
| 300101 | Beta_Cleaner_Card |
| 300102 | Beta_Baths_A_Card |
| 300103 | Bath_Mermaid_Card |
| 300104 | Bookworm_Card |
| 300105 | Roaming_Splbook_Card |
| 300106 | Pitaya_R_Card |
| 300108 | Venenum3_Card |
| 300109 | EP17_2_Cramp_Card |
| 300110 | Waterfall_Card |
| 300112 | Dolor3_Card |
| 300113 | Plasma_Y_Card |
| 300114 | Plaga3_Card |
| 300115 | Sanare3_Card |
| 300116 | Plasma_R_Card |
| 300117 | Plasma_R2_Card |
| 300118 | EP17_2_Phen_Card |
| 300119 | EP17_2_Sword_Fish_Card |
| 300121 | EP17_2_Marc_Card |
| 300122 | Pitaya_Y_Card |
| 300123 | Pitaya_V_Card |
| 300124 | Pitaya_B_Card |
| 300125 | Pitaya_G_Card |
| 300140 | ILL_Sropho_Card |
| 300141 | ILL_Obeaune_Card |
| 300142 | ILL_Deviace_Card |
| 300145 | ILL_Abysmal_Witch_Card |
| 300149 | ILL_Phen_Card |
| 300211 | EP18_Ash_Toad_Card |
| 300214 | EP18_Hot_Molar_Card |
| 300215 | EP18_Volcaring_Card |
| 300216 | EP18_Lava_Toad_Card |
| 300217 | EP18_Burning_Fang_Card |
| 300218 | EP18_Ashhopper_Card |
| 300219 | EP18_Ashring_Card |
| 300220 | EP18_Grey_Wolf_Card |
| 300221 | EP18_Tumble_Ring_Card |
| 300222 | EP18_Firewind_Kite_Card |
| 300223 | EP18_Phantom_Wolf_Card |
| 300231 | ILL_Andre_soldier_Card |
| 300234 | ILL_Piere_Card |
| 300237 | ILL_Farmiliar_Card |
| 300238 | ILL_Vitata_Card |
| 300239 | ILL_Maya_Card |
| 300240 | Gan_Ceann_Card |
| 300241 | Brutal_Murderer_Card |
| 300244 | Disguiser_Card |
| 300245 | Bluemoon_Loli_Ruri_Card |
| 300246 | Grote_Card |
| 300247 | Pierrotzoist_Card |
| 300251 | Plagarion_Card |
| 300252 | Deadre_Card |
| 300253 | Venedi_Card |
| 300255 | Litus_Card |
| 300256 | Fillia_Card |
| 300257 | Vanilaqus_Card |
| 300258 | Lava_Eater_Card |
| 300259 | Fulgor_Card |
| 300260 | Napeo_Card |
| 300265 | Regen_Scientist_Card |

## 4. Предметы (не-карты) НЕ добавлены — 387

Реневал-предметы (снаряга/расходники/прочее), которые роняют ДОБАВЛЕННЫЕ мобы, но их нет в uAthena → в дропе обнулены. Кандидаты на будущий item-бэкпорт.

| AegisName | Name | Type (rAthena) |
|---|---|---|
| 2019_SSTARR_TBOX | 2019 Superstar R Ticket Box | Usable |
| 2019_SSTARR_TICKET | 2019 Superstar R Ticket | Etc |
| ABUNDANTLY_FOXTAIL | Enriched Foxtail Staff | Weapon |
| AGRADE_POCKET | A Grade Coin Bag | Usable |
| AIRSHIP_ARMOR | Airship's Armor | Armor |
| AIRSHIP_BOOTS | Airship's Boots | Armor |
| AIRSHIP_CAPE | Airship's Cloak | Armor |
| AIRSHIP_PART | Unprocessed Parts | Usable |
| AIR_STRONGHOLD_KEY | Sky Fortress Key | Etc |
| AMAZING_FOXTAIL | Mysterious Foxtail Staff | Weapon |
| ANCIENT_GRUDGE | Ancient Grudge | Etc |
| ANGER_SEAGOD | Sea God's Wrath | Etc |
| ANVIL_OF_VELUND | Anvil Of Velund | Etc |
| ASSASSIN_HANDCUFFS | Assassin Handcuffs | Armor |
| AWAKENING_POTION_B | "[Not For Sale] Awakening Potion" | Usable |
| BAD_CAN | Bad Canned Food | Etc |
| BAG_OF_SELLING_GOODS | Bag Of Selling Goods | Etc |
| BAKONAWA_ARMOR | Bakunawa Scale Armor | Armor |
| BAKONAWA_DOLL | Bakonawa Doll | Etc |
| BAKONAWA_SPIRIT_PIECE | Piece of Bakonawa's Spirit | Etc |
| BANDITSSCARF | Bandit's Scarf | Etc |
| BANGUNGOT_BOOTS | Bangungot Boots of Nightmare | Armor |
| BANGUNGOT_DOLL | Bangungot Doll | Etc |
| BANGUNGOT_SPIRIT_PIECE | Piece of Bangungot's Spirit | Etc |
| BASE_GUITAR | Bass Guitar | Weapon |
| BEAUTIFUL_FLOWER | Beautiful Flower | Etc |
| BERDYSZ | Berdysz | Weapon |
| BERSERK_GUITAR | Berserk Guitar | Weapon |
| BERSERK_POTION_B | "[Not For Sale] Berserk Potion" | Usable |
| BGRADE_POCKET | B Grade Coin Bag | Usable |
| BIBLE_OF_PROMISE2 | Bible of Promise(2nd Vol.) | Armor |
| BIGSIZE_FOXTAIL | Large Foxtail Staff | Weapon |
| BISHOP_NECKLACE | Bishop Necklace | Armor |
| BLACK_ROSARY | Dark Rosary | Armor |
| BLACK_WING_BROOCH | Black Wing Brooch | Armor |
| BLACK_WING_SUITS | Black Wing Suits | Armor |
| BLOODY_COIN | Bloody Coin | Etc |
| BLOODY_LETTER | Bloody Letter | Etc |
| BLOODY_LOVELETTER | Bloody Love Letter | Etc |
| BLOODY_PAGE | Bloody Page | Etc |
| BLOOD_TEARS | Blood Tears | Weapon |
| BLOOD_THIRST | Blood Thirst | Etc |
| BRACELET_OF_VELUND | Bracelet Of Velund | Etc |
| BRILLIANT_HAT_BOX | Brilliant Hat Box | Usable |
| BROKENARROW | Broken Arrow | Etc |
| BROKENSHOTGUN | Broken Shotgun | Etc |
| BROKEN_FARMING_UTENSIL | Broken Farming Utensil | Etc |
| BROKEN_HORN | Broken Horn | Etc |
| BROWNMUFFLER | Brown Muffler | Etc |
| BROWNRATTAIL | Brown Rat Tail | Etc |
| BS_MAKING_S | Mysterious Combination Bundle | Usable |
| BUILD_UP_POTION_AC | Build Up Potion AC | Usable |
| BUILD_UP_POTION_SC | Build Up Potion SC | Usable |
| BUILD_UP_POTION_SS | Build Up Potion SS | Usable |
| BULLET_CASE_BLAZE | Incandescence Shot Cartridge | Usable |
| BULLET_CASE_FLEEZE | Glaciation Shot Cartridge | Usable |
| BURNINGFEATHER | Burning Feather | Etc |
| BURNINGSKIN | Burning Bug Skin | Etc |
| BURNING_ROSE | Burning Rose | Weapon |
| BUTTERFLY_HAIR_CLIP | Butterfly Hair Decoration | Etc |
| BUWAYA_CLOTH | Buwaya Sack Cloth | Armor |
| BUWAYA_DOLL | Buwaya Doll | Etc |
| BUWAYA_SPIRIT_PIECE | Piece of Buwaya's Spirit | Etc |
| CAPTIVE_HATCHLING | Captive Hatchling | Etc |
| CELEBRATE_EGG | Memorial Egg | Usable |
| CENDRAWASIH_F | Cendrawasih Feather | Etc |
| CENTER_POTION_B | "[Not For Sale] Concentration Potion" | Usable |
| CHARLESTON_PARTS | Charleston Parts | Etc |
| CHARM_G_NECKLACE | Charm Grass Necklace | Armor |
| CHISEL_OF_GIANT | Chisel Of Giant | Etc |
| CHOCOLATE_DRINK_B | Chocolate Drink | Healing |
| CLATTERING_SKULL | Clattering Skull | Etc |
| CLEANBONE | Clean Bone | Etc |
| CLOSEDMIND_BOX | Closed Mind Box | Cash |
| COAGULATED_SPELL | Coagulated Spell | Etc |
| COMBO_BATTLE_GLOVE | Combo Battle Glove | Weapon |
| COMODO_L | Comodo Leather | Etc |
| CONTABASS | Contrabass | Weapon |
| CORE_JELLY | Core Jelly | Etc |
| CREEPER_BOW | Creeper Bow | Weapon |
| CRIMSONROCK_5_SCROLL | Level 5 Crimson Rock | DelayConsume |
| CRUDEAMMO | Crude Ammo | Etc |
| CRUDESCIMITER | Crude Scimitar | Etc |
| CRYSTAL_OF_GRUDGE | Cursed Crystal | Usable |
| CURSED_BOOK | Cursed Book | Armor |
| C_BIJOUHAT | Costume Bijou Hat | Armor |
| C_BLAZING_SOUL | Costume Blazing Soul | Armor |
| C_CAMOUFLAGE_RABBITHOOD | Costume Camouflage Rabbit Hood | Armor |
| C_CAT_SANTA_HAT | Cat Santa Hat | Armor |
| C_CIRCLET_OF_BONE | Costume Circlet Of Bones | Armor |
| C_DRIVER_BAND_R | Costume Driver Band(Red) | Armor |
| C_DRIVER_BAND_Y | Costume Driver Band(Yellow) | Armor |
| C_DYING_SWAN | Costume Dying Swan | Armor |
| C_MAGIC_STONE_HAT | Costume Magic Stone Hat | Armor |
| C_MIDAS_WHISPER | Costume Midas Whisper | Armor |
| C_MINSTREL_SONG_HAT | Costume Minstrel Song's Hat | Armor |
| C_MITRA | Costume Mitra | Armor |
| C_PROTECT_OF_CROWN | Costume Protect Of Crown | Armor |
| C_RED_BONNET | Costume Red Bonnet | Armor |
| C_RUNE_CIRCLET | Costume Rune Circlet | Armor |
| C_SANTAHAIRBAND | Costume Santa Hairband | Armor |
| C_SCHMIDT_HELM | Costume Schmitz Helm | Armor |
| C_SHADOW_HANDICRAFT | Costume Shadow Handicraft | Armor |
| C_SILENT_EXECUTER | Costume Silent Executor | Armor |
| C_SNIPER_GOGGLE | Costume Sniper Google | Armor |
| C_WIND_WHISPER | Costume Wind Whisper | Armor |
| DANDELION_RING | Dandelion Ring | Usable |
| DARK_CRYSTAL | Crystal of Darkness | Etc |
| DARK_DEBRIS | Fragment of Darkness | Etc |
| DARK_INVITATION | Invitation of Darkness | Usable |
| DARK_RED_CLOT | Black As Night Piece | Usable |
| DARK_ROSE | Dark Rose | Weapon |
| DEADLYPOISONPOWDER | Deadly Poison Powder | Etc |
| DELICIOUS_JELLY | Delicious Jelly | Healing |
| DESICCANT | Dehumidifiers | Etc |
| DESTRUCTION_ROD | Staff of Destruction | Weapon |
| DETAIL_MODEL_FOXTAIL | Fine Foxtail Replica | Weapon |
| DIABOLUS_MANTEAU | Diabolus Manteau | Armor |
| DIAMONDDUST5_SCROLL | Level 5 Diamond Dust | DelayConsume |
| DISTORTED_IRON_PLATE | Crushed Can Iron Plate | Etc |
| DIVINE_CLOTH | Divine Cloth | Armor |
| DORAM_ELE_CAPE | Elegant Doram Manteau | Armor |
| DORAM_ELE_SHOES | Elegant Doram Shoes | Armor |
| DORAM_ELE_SUIT | Elegant Doram Suit | Armor |
| DORAM_HIGH_CAPE | Luxury Doram Manteau | Armor |
| DORAM_HIGH_SHOES | Luxury Doram Shoes | Armor |
| DORAM_HIGH_SUIT | Luxury Doram Suit | Armor |
| DORAM_ONLY_CAPE | Private Doram Manteau | Armor |
| DORAM_ONLY_SHOES | Private Doram Shoes | Armor |
| DORAM_ONLY_SUIT | Private Doram Suits | Armor |
| DRAGONBALL_BLUE | Blue Bijou | Etc |
| DRAGONBALL_GREEN | Green Bijou | Etc |
| DRAGONBALL_YELLOW | Yellow Bijou | Etc |
| DRAGONFRY_FOXTAIL | Dragonfly Sitting Foxtail Staff | Weapon |
| DRAGON_BREATH | Dragon Breath | Armor |
| DREAM_PIECE | Fragment of Dreams | Etc |
| DRIED_CLOVER | Well-dried Clover | Etc |
| DRIED_LEAF_OF_YGG | Dried Yggdrasil Leaf | Etc |
| DR_LIFE_POTION_02 | Basil | Healing |
| DUSTBALL | Dustball | Etc |
| DUST_FIRE | Dustfire | Weapon |
| EARTH_BOW | Earth Bow | Weapon |
| ELEGANT_FLOWER | Elegant Flower | Etc |
| ENCYCLOPEDIA | Encyclopedia | Weapon |
| EX_MODEL_FOXTAIL | Exquisite Foxtail Model | Weapon |
| EYE_DROPS | Eye Drops | Etc |
| E_BCRYSTAL_BOX | Don Cristal Chino Box | Usable |
| FACEWORM_LEG | Faceworm Leg | Weapon |
| FALLEN_LEAVES_BRANCH | Fallen Leaves Branch | Etc |
| FANCY_FAIRY_WING | Fancy Fairy Wing | Etc |
| FELOCK_ARMOR | Felrock's Armor | Armor |
| FELOCK_BOOTS | Felrock's Boots | Armor |
| FELOCK_CAP | Felrock's Hat | Armor |
| FELOCK_CAPE | Felrock's Cloak | Armor |
| FENRIR_CARD__ | Fenrir's Power Scroll | Usable |
| FLORAL_BRACELET_OF_IGU | Floral Bracelet Of Aigu | Armor |
| FREEZE_DREAM | Frozen Dream | Usable |
| FRESH_G_NECKLACE | Fresh Grass Necklace | Armor |
| FROZEN_BREASTPLATE | Frozen Breastplate | Armor |
| FROZEN_PIECEOFROCK | Frozen Stone Fragment | Etc |
| FRUIT_OF_MASTELA_BOX2 | Fruit Of Mastela 100 Box | Usable |
| GEFFENIA_BOOK_WATER | Geffenia Tomb of Water | Armor |
| GIANT_SHIELD | Giant Shield | Armor |
| GLAST_DECAYED_NAIL | Glast Decayed Nail | Etc |
| GLAST_HORRENDOUS_MOUTH | Glast Horrendous Mouth | Etc |
| GLOVE_OF_SHURA | Sura Gauntlet | Armor |
| GOAST_CHILL | Chills Of Death | Etc |
| GOLDEN_BRACELET | Golden Ornament | Etc |
| GOLDEN_POTION_RG | RG Golden Potion | Usable |
| GOLD_SPIRIT_CHAIN | Angel Blessing | Armor |
| GRAY_SHARD | Gray Shard | Etc |
| GREAT_CHEF_ORLEANS01 | Chef King Orleans Vol.1 | Etc |
| GREEN_OPERATION_COAT | Green Surgical Gown | Armor |
| GUST_BOW | Gust Bow | Weapon |
| GYMNASTICS_RIBBON | Rhythmic Gymnastics Ribbon | Weapon |
| HALLOWEEN_COIN | Halloween Coin | Etc |
| HAMMER_OF_VELUND | Hammer Of Velund | Etc |
| HARDEN_BREASTPLATE | Hardened Breastplate | Armor |
| HARDWOOD_SLIPPER | Wooden Slipper | Armor |
| HAZYDREAM | Hazy Dream Fragment | Etc |
| HAZYMOONCAKE | Hazy Mooncake | Healing |
| HEARTY_RICE_CAKE | Hearty Rice Cake | Healing |
| HEART_HUNTER_SEAL | Heart Hunter's Seal | Etc |
| HIGH_FASHION_SANDALS | High Fashion Sandals | Armor |
| HIGH_WEAPON_BOX | Advanced Weapons Box | Usable |
| HIPPIE_GUITAR | Hippie Guitar | Weapon |
| HIPPIE_ROPE | Hippie Rope | Weapon |
| HOLY_ARROW_QUIVER | Holy Arrow Quiver | Usable |
| HURRICANE_FURY | Hurricane's Fury | Weapon |
| ILLUSIONSTONE | Illusion Stone | Etc |
| ILLUSORYSTONE | Illusion Gemstone | Etc |
| INK_BALL | Sea Ink | Usable |
| INORGANIC_PUMPKIN | Inorganic Pumpkin | Etc |
| INSIDEOUT_SHIRT | Inside-out Shirt | Usable |
| IRON_BUG | Iron Worm | Healing |
| IXION_WING | Ixion Wings | Weapon |
| JEJELLOPY | Jejellopy | Etc |
| JUST_FINISH | Finisher | Weapon |
| KALASAK | Kalasag | Armor |
| KEY_OF_TWISTED_TIME | Twisted Key of Time | DelayConsume |
| KTULLANUXSEYE | Ktullanux Eye | Etc |
| LARGESCRAP | Huge Metal Scrap | Etc |
| LEAF_BOOKMARK | Leaf Bookmark | Etc |
| LEGEND_OF_KAFRA01 | Kafra Legend Vol.1 | Etc |
| LICH_BONE_WAND | Lich's Bone Wand | Weapon |
| LIGHT_WHITE_POT_ | "[Not for Sale] Light White Potion" | Healing |
| LONG_FOXTAIL | Long Foxtail Staff | Weapon |
| LOUNGE_SUIT | Menswear | Armor |
| LOW_COIN_POCKET | Minor Coin Bag | Usable |
| MAGICAL_FOXTAIL | Magical Foxtail Staff | Weapon |
| MAGICAL_MOON_CAKE | Grace Moon Cake | Healing |
| MAGIC_BRONZE_BULLION | Magic Bronze Bullion | Etc |
| MANTEAU_OF_FALLEN | Fallen Warrior Manteau | Armor |
| MATURE_CACAO | Aged Cacao Beans | Etc |
| MEMORIZE_BOOK_ | Memory Book | Armor |
| METEO_PLATE_ARMOR | Meteo Plate Armor | Armor |
| MID_COIN_POCKET | Intermediate Coin Bag | Usable |
| MINE_WORKER_PICKAX | Mine Worker's Pickaxe | Weapon |
| MODEL_FOXTAIL | Foxtail Model | Weapon |
| MONOKAGE | Monokage | Weapon |
| MONSTER_BLOOD | Monster Blood | Etc |
| MOVING_BLACK_THINGS | Moving Black Material | Etc |
| MURASAME_ | Murasame | Weapon |
| MYSTERIOUS_FLOWER | Mysterious Flower | Etc |
| NIGHTMAREOFLUMP | Cluster of Nightmares | Etc |
| OCTUPUS_LEG | Fresh Octopus Legs | Healing |
| OLDDOLL | Fine Old Doll | Etc |
| OLDSHELL | Old Shell | Etc |
| OLDTANK | Old Fuel | Etc |
| OLD_COIN_POCKET | Old Coin Bag | Usable |
| OLD_ORE_BOX | Old Ore Box | Usable |
| OLD_PARASOL | Old Parasol | Weapon |
| OLD_WHITE_CLOTH | Old White Cloth | Etc |
| ONE_EYED_GLASS_ | Monocle | Armor |
| ORC_ARCHER_BOW_ | Orc Archer Bow | Weapon |
| ORGANIC_PUMPKIN | Organic Pumpkin | Etc |
| ORIGIN_OF_ELEMENTAL | Elemental Origin | Weapon |
| ORLEANS_GOWN | Orleans's Gown | Armor |
| ORLEANS_SERVER | Orleans's Server | Armor |
| PARTICLES_OF_ENERGY4 | Sinister Energy Particle | Etc |
| PARTICLES_OF_ENERGY5 | Fallen Energy Particle | Etc |
| PENDANT_OF_CHAOS | Pendant of Chaos | Armor |
| PENDANT_OF_HARMONY | Pendant of Harmony | Armor |
| PEONY_MOMMY | Peony Mamy | DelayConsume |
| PEUZ_PLATE | Peuz's Plate | Armor |
| PEUZ_SEAL | Peuz's Seal | Armor |
| PIECEOFBLACKSPIRIT | Piece of Black Horn | Etc |
| PIECES_OF_GRUDGE | Cursed Fragment | Usable |
| PIECES_OF_SENTIMENT | Sentimental Fragment | DelayConsume |
| PIECE_OF_CHIMERA | Piece of Chimera | Etc |
| PIECE_OF_GIGANTES | Fragments Of Gigan | Etc |
| PIERCING_STAFF | Piercing Staff | Weapon |
| PILE_OF_ACORN | Pile Of Acorn | Etc |
| PLATINUM_SHOTEL | Platinum Shotel | Weapon |
| POCKET_WATCH_ | Pocket Watch | Armor |
| POISON_BOTTLE_B | Poison Bottle | Usable |
| PORINGTOWNCARROT | Poring Village Carrot | Armor |
| PORINGTOWNONION | Poring Village Leek | Armor |
| PRETTY_G_NECKLACE | Cute Grass Necklace | Armor |
| PRICKLY_FRUIT_ | Red Prickly Fruit | Healing |
| PRIZEOFHERO | Prize Of Hero | Usable |
| PROBLEMATICAL_PART | Questioned Parts | Etc |
| PROTECTRINGOFKING | Royal Guardian Ring | Armor |
| RED_ECO_BOOTS | Red Eco-Friendly Shoes | Armor |
| RED_EYES | Red Eye | Etc |
| REVENGER | Avenger | Weapon |
| RIB_OF_JORMUNGAND | Rib Of Jormungand | Etc |
| RIDER_INSIGNIA | Rider Insignia | Armor |
| RIPE_WATERMELON | Ripe Watermelon | Etc |
| ROBE_OF_AFFECTION | Robe Of Affection | Armor |
| ROBE_OF_JUDGEMENT | Robe Of Judgement | Armor |
| ROBE_OF_SARAH | Sarah's Battle Robe | Armor |
| RWC_CELE_FIRE | RWC Celebration Firecracker | Usable |
| RWC_CELE_FIRE2 | RWC Celebration Firecracker | Usable |
| SABAH_CLOTH | Sapha's Cloth | Armor |
| SABAH_RING | Sapha Ring | Armor |
| SANDPAPER | Sandpaper | Etc |
| SANDSTORM | Sandstorm | Weapon |
| SCALPEL | Scalpel | Weapon |
| SCARLET_BIBLE | Crimson Bible | Weapon |
| SCARLET_DAGGER | Crimson Dagger | Weapon |
| SCARLET_KATAR | Crimson Katar | Weapon |
| SCARLET_KNUCKLE | Crimson Knuckles | Weapon |
| SCARLET_LANCE | Crimson Lance | Weapon |
| SCARLET_MACE | Crimson Mace | Weapon |
| SCARLET_REVOLVER | Crimson Revolver | Weapon |
| SCARLET_ROD | Crimson Rod | Weapon |
| SCARLET_SABER | Crimson Saber | Weapon |
| SCARLET_SPEAR | Crimson Spear | Weapon |
| SCARLET_STAFF | Crimson Two-Handed Staff | Weapon |
| SCARLET_TWOHAND_AXE | Crimson Two-Handed Axe | Weapon |
| SCARLET_TWOHAND_SWORD | Crimson Two-Handed Sword | Weapon |
| SCARLET_VIOLLIN | Crimson Violin | Weapon |
| SCARLET_WIRE | Crimson Whip | Weapon |
| SEA_WITCH_FOOT | Sea Witch's Foot | Weapon |
| SECRET_OF_RUNE | Secret Of Rune | Etc |
| SEED_OF_YGGDRASIL_ | "[Not For Sale] Yggdrasil Seed" | Healing |
| SGRADE_POCKET | S Grade Coin Bag | Usable |
| SG_BLUE_POTION_BOX | Siege Blue Potion Box | Usable |
| SG_VIOLET_POTION_BOX | Siege Violet Potion Box | Usable |
| SG_WEAPON_SUPPLY_BOX | WoE Weapon Supply Box | Usable |
| SG_WHITE_POTION_BOX | Siege White Potion Box | Usable |
| SHABBYOLDSCROLL | Old Scroll | Usable |
| SHABBY_OLD_BELT | Worn-Out Belt | Etc |
| SHADOWDECON | Shadowdecon | Etc |
| SHADOWDECON_ORE | Shadowdecon Ore | Etc |
| SHADOW_WALK_ | Shadow Walk | Armor |
| SHATTERED_RUNE | Broken Magic Stone | Etc |
| SHINING_SPORE | Shining Spore | Etc |
| SHIPSLOG | Logbooks | Etc |
| SHORT_BAT_FUR | Short Bat Hair | Etc |
| SIEGE_BOOTS | Siege Boots | Armor |
| SIEGE_GREAVE | Siege Greaves | Armor |
| SIEGE_MANTEAU | Siege Manteau | Armor |
| SIEGE_MUFFLER | Siege Muffler | Armor |
| SIEGE_PLATE | Siege Plate | Armor |
| SIEGE_ROBE | Siege Robe | Armor |
| SIEGE_SHOES | Siege Shoes | Armor |
| SIEGE_SUITS | Siege Suit | Armor |
| SIENNA_5_SCROLL | Level 5 Sienna Execrate | DelayConsume |
| SIGN_OF_DESTRUCTION | Token Of Destruction | Etc |
| SILVER_BRACELET | Silver Bracelet | Etc |
| SKIN_OF_HRAESVELG | Skin Of Hraesvelg | Etc |
| SLAPPING_HERB | Slapping Herb | DelayConsume |
| SMALL_WOODEN_CHEST | Small Wooden Chest | Etc |
| SNOWBALL | Snowball | Etc |
| SNOW_FLIP | Snow Flip | DelayConsume |
| SOUL_OF_ACOLYTE | Acolyte Soul | Etc |
| SOUL_OF_ARCHER | Archer Soul | Etc |
| SOUL_OF_MAGICION | Mage Soul | Etc |
| SOUL_OF_MERCHANT | Merchant Soul | Etc |
| SOUL_OF_SWORDMAN | Swordman Soul | Etc |
| SOUL_OF_THIEF | Thief Soul | Etc |
| SPECTRAL_SPEAR | Spectral Spear | Weapon |
| SPIRIT_OF_HUGIN | Spirit Of Hugin | Etc |
| SPIRIT_OF_MUNIN | Spirit Of Munin | Etc |
| SPLENDID_BOX2 | Splendid Box2 | Usable |
| SPOON | Spoon | Weapon |
| SPRITJEWEL | Spirit Jewel | Etc |
| STOLEN_CACAO | Stolen Cocoa Beans | Etc |
| STONEFORWORK | Crafted Stone | Etc |
| STONE_OF_BLESSING | Stone Of Blessing | Etc |
| STRANGE_FOXTAIL | Strange God Foxtail Staff | Weapon |
| SUBJUGATIONFLYER | Recruitment Leaflet | Etc |
| SUPPLEMENT_PART_AGI | Supplement Part Agi | Armor |
| SUSPICIOUSMAGICCIRCLE | Suspicious Pentacle | Etc |
| SWAMPBUGPEELINGS | Swamp Bug Shell | Etc |
| TAE_GOO_LYEON | Tae Goo Lyeon | Weapon |
| TEMPORAL_CRYSTAL | Temporal Crystal | Etc |
| TEST_REAGENT | Test Reagent | Usable |
| THIRSTY_FLOWER | Dried Flower | Etc |
| THORNY_BUCKLER | Thorny Buckler | Armor |
| TIDUNG | Tidung | Armor |
| TIKBALANG_THICK_SPINE | Tikbalang's Thick Spine | Etc |
| TOOTHOFFLAMEFRILLDORA | Frilldora's Fiery Nape | Etc |
| TOOTHOFFLAMEGOLEM | Golem's Fiery Stone Tooth | Etc |
| TOOTH_OF_JITTERBUG | Jitterbug's Tooth | Etc |
| TORN_DIARY | Torn Paper | Etc |
| TWILIGHT_DESERT | Desert Twilight | Weapon |
| ULFHEDINN | Ulfhedinn | Armor |
| ULTRA_LIGHT_MSHIELD | Ultralight Magic Shield | Armor |
| UNSENT_MAIL | Unsent Letter | Etc |
| UPGRADE_PART_BOOSTER | Upgrade Part - Booster | Armor |
| UR_SEAL | Ur's Seal | Armor |
| VALKYRIE_FRAGMENT | Fragments Valkyrie Power | Etc |
| VAMPIRE'S_SERVANT | A Vampire's Servant | Armor |
| VARETYR_5_SCROLL | Level 5 Varetyr Spear | DelayConsume |
| VIGILANTE_BOW | Vigilante Bow | Weapon |
| WALKING_STICK | Gentleman's Staff | Weapon |
| WHITE_ECO_SHIRT | White Eco-Shirt | Armor |
| WHITE_POTION_B | White Potion | Healing |
| WHITE_SHIRT | White Shirt | Armor |
| WHITE_WING_BROOCH | White Wing Brooch | Armor |
| WILL_OF_DARKNESS_ | Will of Red Darkness | Etc |
| WILL_OF_OWNER | Will Master | Etc |
| WILL_OF_WARRIOR | Warrior's Will | Etc |
| WINGED_RING_OF_NEWOZ | Oz's New Wing Ring | Armor |
| WOE_BLUE_POTION | Siege Blue Potion | Healing |
| WOE_VIOLET_POTION | Siege Purple Potion | Healing |
| WOE_WHITE_POTION | Siege White Potion | Healing |
| WORNREVOLVER | Worn Revolver | Etc |
| WRONG_ENGINE | Failed Engine | Etc |
| YAGA_PESTLE | Yaga's Pestle | Etc |
| YGGDRASIL_DUST | Yggdrasil Dust | DelayConsume |
| YUMMYSTEM | Yummy Stem | Etc |
| ZELUNIUM | Zelunium | Etc |
| ZELUNIUM_ORE | Zelunium Ore | Etc |

## 5. Карты в дропе добавленных мобов, отсутствующие в uAthena — 3

(Эти card-дропы обнулены; пересекается с разделом 2.)

| AegisName | Name |
|---|---|
| B_EREMES_CARD | Assassin Cross Card |
| B_HARWORD_CARD | MasterSmith Card |
| FALLEN_BISHOP_CARD | Fallen Bishop Hibram Card |

