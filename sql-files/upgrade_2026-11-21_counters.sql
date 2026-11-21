-- 2026-11-21: room for the AUTO_INCREMENT counters (run by hand: mysql ragnarok < upgrade_2026-11-21_counters.sql).
-- * The log tables used mediumint (max 16,777,215 rows ever inserted - only a TRUNCATE resets the counter): past
--   it every INSERT fails and that log stops. -> INT UNSIGNED (4,294,967,295).
-- * picklog/zenylog used signed int (2,147,483,647) -> INT UNSIGNED.
-- * cart_inventory.id was signed while inventory/storage/guild_storage are unsigned; the char-server reads all
--   four as unsigned now -> INT UNSIGNED like the others.
-- Each ALTER rewrites the table: run it while the server is stopped (the log tables are emptied monthly, they
-- are instant; cart_inventory has ~30k rows). IF EXISTS: a table this server does not have is skipped.
ALTER TABLE IF EXISTS `atcommandlog` MODIFY `atcommand_id` INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `branchlog`    MODIFY `branch_id`    INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `droplog`      MODIFY `drop_id`      INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `mvplog`       MODIFY `mvp_id`       INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `npclog`       MODIFY `npc_id`       INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `presentlog`   MODIFY `present_id`   INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `producelog`   MODIFY `produce_id`   INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `refinelog`    MODIFY `refine_id`    INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `tradelog`     MODIFY `trade_id`     INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `vendlog`      MODIFY `vend_id`      INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `picklog`      MODIFY `id`           INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `zenylog`      MODIFY `id`           INT UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE IF EXISTS `cart_inventory` MODIFY `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT;
