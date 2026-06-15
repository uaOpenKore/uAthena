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
