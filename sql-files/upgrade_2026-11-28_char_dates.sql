-- [chardates] Two dates of a character (S. 2026-11-28). Run by hand:
--   mysql ragnarok < sql-files/upgrade_2026-11-28_char_dates.sql
-- Without these columns the char-server keeps working and only logs that the dates are off.
-- * char.created: when the character was made. Existing characters get NULL (the date is unknown), every new one
--   gets the time of its INSERT from the column default, whoever inserts it (char-server or the web site).
-- * char.maxed: when the character first reached base level 99 and job level 70, written by the char-server on the
--   save that brings it there; kept after that (a rebirth does not clear it). Characters that were already 99/70
--   before this upgrade stay NULL.
ALTER TABLE `char` ADD COLUMN IF NOT EXISTS `created` DATETIME NULL DEFAULT NULL,
	ADD COLUMN IF NOT EXISTS `maxed` DATETIME NULL DEFAULT NULL;
ALTER TABLE `char` MODIFY COLUMN `created` DATETIME NULL DEFAULT CURRENT_TIMESTAMP;
