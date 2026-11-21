-- 2026-11-21: autotrade shops survive a server restart. Run by hand:
--   mysql ragnarok < sql-files/upgrade_2026-11-21_autotrade.sql
-- Without these tables the map-server keeps working and only logs that keeping the shops is off.
-- The goods stay in cart_inventory: a row only says which cart slot is sold, how many and for how much.
-- cp1251 like `char`: a shop title comes from the game client in cp1251.
-- Natural keys, no auto-increment: one shop per character, one row per cart slot of it.
CREATE TABLE IF NOT EXISTS `autotrade_shop` (
	`char_id` INT UNSIGNED NOT NULL,
	`account_id` INT UNSIGNED NOT NULL,
	`sex` TINYINT UNSIGNED NOT NULL DEFAULT '0',
	`map` VARCHAR(16) NOT NULL,
	`x` SMALLINT UNSIGNED NOT NULL,
	`y` SMALLINT UNSIGNED NOT NULL,
	`dir` TINYINT UNSIGNED NOT NULL DEFAULT '0',
	`title` VARCHAR(80) NOT NULL DEFAULT '',
	`opened` DATETIME NOT NULL DEFAULT '2000-01-01 00:00:00',
	PRIMARY KEY (`char_id`)
) DEFAULT CHARSET=cp1251;

CREATE TABLE IF NOT EXISTS `autotrade_item` (
	`char_id` INT UNSIGNED NOT NULL,
	`cart_slot` SMALLINT UNSIGNED NOT NULL,
	`nameid` INT UNSIGNED NOT NULL,
	`amount` SMALLINT UNSIGNED NOT NULL,
	`price` INT UNSIGNED NOT NULL,
	PRIMARY KEY (`char_id`, `cart_slot`)
) DEFAULT CHARSET=cp1251;
