-- [Backport] rental items: add `expire_time` (absolute unix-time of expiry, 0 = not a rental)
-- to the four item-bearing tables. IF NOT EXISTS keeps it re-run-safe under `dumps.sh update`
-- (which re-applies all migrations). MariaDB >= 10.0 supports ADD COLUMN IF NOT EXISTS.
ALTER TABLE `inventory`      ADD COLUMN IF NOT EXISTS `expire_time` int(11) unsigned NOT NULL DEFAULT '0';
ALTER TABLE `cart_inventory` ADD COLUMN IF NOT EXISTS `expire_time` int(11) unsigned NOT NULL DEFAULT '0';
ALTER TABLE `storage`        ADD COLUMN IF NOT EXISTS `expire_time` int(11) unsigned NOT NULL DEFAULT '0';
ALTER TABLE `guild_storage`  ADD COLUMN IF NOT EXISTS `expire_time` int(11) unsigned NOT NULL DEFAULT '0';
