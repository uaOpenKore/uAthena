-- 2026-11-21: daily play-time limit (daily_play_limit in conf/battle/misc.conf). Run by hand:
--   mysql ragnarok < sql-files/upgrade_2026-11-21_playlimit.sql
-- Without these columns the char-server keeps working and only logs that the limit is off.
-- * char.play_minutes: whole minutes the character spent on the map-server on the day play_date (YYYYMMDD);
--   minutes stamped with another date than play_reset.reset_date count as 0.
-- * play_reset: one row, the date and the moment of the last reset (00:00 server time, or 24 h after the last one).
ALTER TABLE `char`
	ADD COLUMN IF NOT EXISTS `play_minutes` INT UNSIGNED NOT NULL DEFAULT '0',
	ADD COLUMN IF NOT EXISTS `play_date` INT UNSIGNED NOT NULL DEFAULT '0';

CREATE TABLE IF NOT EXISTS `play_reset` (
	`id` TINYINT UNSIGNED NOT NULL DEFAULT '0',
	`reset_date` INT UNSIGNED NOT NULL DEFAULT '0',
	`reset_at` DATETIME NOT NULL DEFAULT '2000-01-01 00:00:00',
	PRIMARY KEY (`id`)
);
