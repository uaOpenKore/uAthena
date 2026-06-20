--
-- Widen mob_db base-stat columns so high-stat mobs import faithfully.
--
-- GvG treasure boxes and Emperium-room crystals (db/mob_db2.txt) carry DEX=999
-- (TREASURE_BOX41-49, CRYSTAL_6-9, TREASURE_BOX_I). That overflowed the original
-- `tinyint(4) unsigned` (max 255) stat columns and produced
-- "Out of range value for column 'DEX'" on import, truncating the value to 255.
--
-- The server keeps these stats in `unsigned short` (0..65535 -- struct
-- status_data in src/map/map.h), so the SQL columns are widened to match:
-- `smallint(6) unsigned`.
--
-- Idempotent: re-running MODIFY to the same type is a no-op. dumps.sh applies it
-- after 1-mob_db.sql (re)creates the table and before A-mob_db.sql fills it; it
-- can also be run by hand to patch a live database without re-importing mob_db.
--

ALTER TABLE `mob_db`
  MODIFY `STR` smallint(6) unsigned NOT NULL default '0',
  MODIFY `AGI` smallint(6) unsigned NOT NULL default '0',
  MODIFY `VIT` smallint(6) unsigned NOT NULL default '0',
  MODIFY `INT` smallint(6) unsigned NOT NULL default '0',
  MODIFY `DEX` smallint(6) unsigned NOT NULL default '0',
  MODIFY `LUK` smallint(6) unsigned NOT NULL default '0';

--
-- Widen mob_db drop/MVP item-id columns so renewal item ids import faithfully.
--
-- The renewal-mob backport (db/mob_db2.txt, see Doc/backport_renewal_mobs.md) drops
-- renewal items/cards whose ids exceed the original `smallint(9) unsigned` (max 65535):
-- backported cards reach ~700000 and lv4 weapons in item_db2 reach 840026. That
-- overflowed the *id columns on import. The server keeps item ids in `int`
-- (struct item_data, src/map/itemdb.h), so the columns are widened to
-- `mediumint(8) unsigned` (max 16,777,215), which covers every current item id.
-- Only the *id columns need it; the *per (rate) columns stay <= 10000.
--
-- Idempotent; runs after 1-mob_db.sql and before A-mob_db.sql, same as above.
--

ALTER TABLE `mob_db`
  MODIFY `MVP1id`    mediumint(8) unsigned NOT NULL default '0',
  MODIFY `MVP2id`    mediumint(8) unsigned NOT NULL default '0',
  MODIFY `MVP3id`    mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop1id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop2id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop3id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop4id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop5id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop6id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop7id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop8id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `Drop9id`   mediumint(8) unsigned NOT NULL default '0',
  MODIFY `DropCardid` mediumint(8) unsigned NOT NULL default '0';
