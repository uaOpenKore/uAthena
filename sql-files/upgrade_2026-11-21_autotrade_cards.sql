-- 2026-11-21: the autotrade goods with their refine, broken flag and cards, for a search on the web site (S.).
-- Run by hand:  mysql ragnarok < sql-files/upgrade_2026-11-21_autotrade_cards.sql
-- Without these columns the map-server keeps the shops as before, only without them (it logs that at start).
-- The types are those of `cart_inventory`.
ALTER TABLE `autotrade_item`
	ADD COLUMN `refine` TINYINT(3) UNSIGNED NOT NULL DEFAULT '0',
	ADD COLUMN `attribute` TINYINT(4) NOT NULL DEFAULT '0',
	ADD COLUMN `card0` INT(11) NOT NULL DEFAULT '0',
	ADD COLUMN `card1` INT(11) NOT NULL DEFAULT '0',
	ADD COLUMN `card2` INT(11) NOT NULL DEFAULT '0',
	ADD COLUMN `card3` INT(11) NOT NULL DEFAULT '0';
