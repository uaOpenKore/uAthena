-- [site] Indexes for the web site's lookups by stable keys (Doc/site_ids.md, S. 2026-11-23): the site finds an
-- account by its login, a character by its name, a guild / party by its name, and resolves the ids in subqueries.
-- Already there in main.sql: login.userid (`name`), char.name (`name`), char.account_id, inventory/cart char_id,
-- storage.account_id, guild_storage.guild_id, guild_member.char_id. Each line below adds a missing one; a line that
-- fails with "Duplicate key name" means that index is there already -- harmless, go on with the next.
ALTER TABLE `guild` ADD INDEX `name` (`name`);
ALTER TABLE `party` ADD INDEX `name` (`name`);
ALTER TABLE `pet` ADD INDEX `char_id` (`char_id`);
ALTER TABLE `homunculus` ADD INDEX `char_id` (`char_id`);
ALTER TABLE `autotrade_shop` ADD INDEX `account_id` (`account_id`);
ALTER TABLE `autotrade_item` ADD INDEX `nameid` (`nameid`);
