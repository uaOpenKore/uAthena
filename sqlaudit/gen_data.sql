-- Synthetic prod-scale data for the SQL audit (isolated instance only).
-- 10k accounts, 25k chars, ~1M inventory, ~1M storage, ~870k registry rows, etc.
SET SESSION sql_mode = '';

TRUNCATE login;
INSERT INTO login (account_id, userid, user_pass, lastlogin, sex, logincount, email, level, error_message, connect_until, last_ip, memo, ban_until, state)
SELECT 2000000 + seq, CONCAT('user', seq), MD5(CONCAT('pw', seq)), NOW() - INTERVAL (seq % 900) HOUR, IF(seq % 2, 'M', 'F'), seq % 500, 'a@a.com', IF(seq < 5, 99, 0), 0, 0, CONCAT('10.0.', seq % 250, '.', seq % 200), 0, 0, 0
FROM seq_0_to_9999;
INSERT INTO login (account_id, userid, user_pass, sex, email, level) VALUES (1, 's1', 'p1', 'S', 'athena@athena.com', 0);

TRUNCATE `char`;
INSERT INTO `char` (char_id, account_id, char_num, name, class, base_level, job_level, base_exp, job_exp, zeny, str, agi, vit, `int`, dex, luk, max_hp, hp, max_sp, sp, party_id, guild_id, pet_id, homun_id, last_map, last_x, last_y, save_map, save_x, save_y, online, fame)
SELECT 150000 + seq, 2000000 + (seq % 10000), seq DIV 10000, CONCAT('Char', seq), seq % 25, 1 + seq % 99, 1 + seq % 50, seq * 7, seq * 3, seq * 13 % 100000000, 1 + seq % 99, 1 + seq % 99, 1 + seq % 99, 1 + seq % 99, 1 + seq % 99, 1 + seq % 99, 5000, 5000, 500, 500,
       IF(seq % 5 = 0, 1 + seq % 2000, 0), IF(seq % 3 = 0, 1 + seq % 300, 0), 0, 0, 'prontera', 150, 150, 'prontera', 150, 150, IF(seq % 100 = 0, 1, 0), IF(seq % 7 = 0, seq % 5000, 0)
FROM seq_0_to_24999;

TRUNCATE inventory;
INSERT INTO inventory (char_id, nameid, amount, equip, identify, refine, attribute, card0, card1, card2, card3, expire_time)
SELECT 150000 + (seq DIV 40), 501 + (seq % 40), 1 + seq % 100, 0, 1, 0, 0, 0, 0, 0, 0, 0 FROM seq_0_to_999999;

TRUNCATE cart_inventory;
INSERT INTO cart_inventory (char_id, nameid, amount, equip, identify, refine, attribute, card0, card1, card2, card3, expire_time, broken)
SELECT 150000 + (seq DIV 10) * 5, 501 + (seq % 10), 10, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0 FROM seq_0_to_49999;

TRUNCATE storage;
INSERT INTO storage (account_id, nameid, amount, equip, identify, refine, attribute, card0, card1, card2, card3, expire_time)
SELECT 2000000 + (seq DIV 100), 501 + (seq % 100), 5, 0, 1, 0, 0, 0, 0, 0, 0, 0 FROM seq_0_to_999999;

TRUNCATE global_reg_value;
INSERT INTO global_reg_value (char_id, str, value, type, account_id)
SELECT 150000 + (seq DIV 30), CONCAT('charvar', seq % 30), seq % 1000, 3, 2000000 + ((seq DIV 30) % 10000) FROM seq_0_to_749999;
INSERT INTO global_reg_value (char_id, str, value, type, account_id)
SELECT 0, CONCAT('#accvar', seq % 10), seq % 1000, 2, 2000000 + (seq DIV 10) FROM seq_0_to_99999;
INSERT INTO global_reg_value (char_id, str, value, type, account_id)
SELECT 0, CONCAT('##acc2var', seq % 2), seq % 1000, 1, 2000000 + (seq DIV 2) FROM seq_0_to_19999;

TRUNCATE skill;
INSERT INTO skill (char_id, id, lv) SELECT 150000 + (seq DIV 30), 1 + (seq % 30), 1 + seq % 10 FROM seq_0_to_749999;

TRUNCATE quest;
INSERT INTO quest (char_id, quest_id, state, time, count1, count2, count3) SELECT 150000 + (seq DIV 15), 1000 + (seq % 15), '1', 0, 0, 0, 0 FROM seq_0_to_374999;
TRUNCATE achievement;
INSERT INTO achievement (char_id, achievement_id, count, completed, rewarded) SELECT 150000 + (seq DIV 10), 1 + (seq % 10), 3, 0, 0 FROM seq_0_to_249999;

TRUNCATE friends;
INSERT INTO friends (char_id, friend_account, friend_id) SELECT 150000 + (seq DIV 5), 2000000 + ((seq * 7919) % 10000), 150000 + ((seq * 7919) % 25000) FROM seq_0_to_124999;

TRUNCATE hotkey;
INSERT INTO hotkey (char_id, hotkey, type, itemskill_id, skill_lvl) SELECT 150000 + (seq DIV 10), seq % 10, 0, 501, 0 FROM seq_0_to_249999;

TRUNCATE memo;
INSERT INTO memo (char_id, map, x, y) SELECT 150000 + (seq DIV 2), 'prontera', 100, 100 FROM seq_0_to_49999;

TRUNCATE sc_data;
INSERT INTO sc_data (account_id, char_id, type, tick, val1, val2, val3, val4) SELECT 2000000 + ((seq * 3) % 10000), 150000 + seq * 3, 1, 60000, 1, 0, 0, 0 FROM seq_0_to_7499;

TRUNCATE guild;
INSERT INTO guild (guild_id, name, char_id, master, guild_lv, connect_member, max_member, average_lv, exp, next_exp, skill_point, mes1, mes2, emblem_len, emblem_id, emblem_data)
SELECT 1 + seq, CONCAT('Guild', seq), 150000 + seq * 3, CONCAT('Char', seq * 3), 10, 0, 76, 80, 0, 1000, 0, '', '', 0, 0, NULL FROM seq_0_to_299;
TRUNCATE guild_member;
INSERT INTO guild_member (guild_id, account_id, char_id, hair, hair_color, gender, class, lv, exp, exp_payper, online, position, rsv1, rsv2, name)
SELECT 1 + (seq DIV 25), 2000000 + ((seq * 3) % 10000), 150000 + seq * 3, 1, 1, 0, 1, 80, 0, 0, 0, IF(seq % 25 = 0, 0, 1 + seq % 19), 0, 0, CONCAT('Char', seq * 3) FROM seq_0_to_7499;
TRUNCATE guild_position;
INSERT INTO guild_position (guild_id, position, name, mode, exp_mode) SELECT 1 + (seq DIV 20), seq % 20, CONCAT('Position ', seq % 20), 0, 0 FROM seq_0_to_5999;
TRUNCATE guild_skill;
INSERT INTO guild_skill (guild_id, id, lv) SELECT 1 + (seq DIV 15), 10000 + (seq % 15), 1 FROM seq_0_to_4499;
TRUNCATE guild_storage;
INSERT INTO guild_storage (guild_id, nameid, amount, equip, identify, refine, attribute, card0, card1, card2, card3, expire_time)
SELECT 1 + (seq DIV 500), 501 + (seq % 500), 3, 0, 1, 0, 0, 0, 0, 0, 0, 0 FROM seq_0_to_149999;

TRUNCATE party;
INSERT INTO party (party_id, name, exp, item, leader_id, leader_char) SELECT 1 + seq, CONCAT('Party', seq), 0, 0, 2000000 + ((seq * 5) % 10000), 150000 + seq * 5 FROM seq_0_to_1999;

TRUNCATE pet;
INSERT INTO pet (pet_id, class, name, account_id, char_id, level, egg_id, equip, intimate, hungry, rename_flag, incuvate)
SELECT 1 + seq, 1002, 'Poring', 2000000 + ((seq * 5) % 10000), 150000 + seq * 5, 1, 9001, 0, 250, 50, 0, IF(seq % 2, 1, 0) FROM seq_0_to_4999;

TRUNCATE homunculus;
INSERT INTO homunculus (homun_id, char_id, class, name, level, exp, intimacy, hunger, str, agi, vit, `int`, dex, luk, hp, max_hp, sp, max_sp, skill_point, alive, rename_flag, vaporize)
SELECT 1 + seq, 150000 + seq * 8, 6001, 'Lif', 10, 0, 1000, 50, 1, 1, 1, 1, 1, 1, 100, 100, 10, 10, 0, 1, 0, 0 FROM seq_0_to_2999;
TRUNCATE skill_homunculus;
INSERT INTO skill_homunculus (homun_id, id, lv) SELECT 1 + (seq DIV 4), 8001 + (seq % 4), 1 FROM seq_0_to_11999;

TRUNCATE mercenary;
INSERT INTO mercenary (mer_id, char_id, class, hp, sp, kill_counter, life_time) SELECT 1 + seq, 150000 + seq * 20, 6017, 100, 10, 0, 1800000 FROM seq_0_to_999;
TRUNCATE mercenary_owner;
INSERT INTO mercenary_owner (char_id, merc_id, arch_calls, arch_faith, spear_calls, spear_faith, sword_calls, sword_faith) SELECT 150000 + seq * 5, 0, 0, 0, 0, 0, 0, 0 FROM seq_0_to_4999;

TRUNCATE mail;
INSERT INTO mail (message_id, to_account_id, to_char_name, from_account_id, from_char_name, message, read_flag, priority, check_flag)
SELECT 1 + seq, 2000000 + (seq % 10000), CONCAT('Char', seq % 25000), 2000000 + ((seq * 13) % 10000), CONCAT('Char', (seq * 13) % 25000), 'hello', IF(seq % 3, 1, 0), 0, IF(seq % 3, 1, 0) FROM seq_0_to_49999;

TRUNCATE loginlog;
INSERT INTO loginlog (time, ip, user, rcode, log) SELECT NOW() - INTERVAL seq SECOND, 167772160 + (seq % 50000), CONCAT('user', seq % 10000), IF(seq % 10, 100, 1), 'login ok' FROM seq_0_to_999999;
TRUNCATE charlog;
INSERT INTO charlog (time, char_msg, account_id, char_num, name, str, agi, vit, `int`, dex, luk, hair, hair_color) SELECT NOW() - INTERVAL seq SECOND, 'char select', 2000000 + (seq % 10000), 0, CONCAT('Char', seq % 25000), 1, 1, 1, 1, 1, 1, 1, 1 FROM seq_0_to_299999;

TRUNCATE mapreg;
INSERT INTO mapreg (varname, `index`, value) SELECT CONCAT('$var', seq % 400), seq DIV 400, seq FROM seq_0_to_1999;

ANALYZE TABLE login, `char`, inventory, cart_inventory, storage, global_reg_value, skill, quest, achievement, friends, hotkey, memo, sc_data, guild, guild_member, guild_position, guild_skill, guild_storage, party, pet, homunculus, skill_homunculus, mercenary, mercenary_owner, mail, loginlog, charlog, mapreg;
