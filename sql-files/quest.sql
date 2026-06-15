--
-- Table structure for table `quest` (questlog system)
-- One row per (char_id, quest_id). state: 0=inactive, 1=active, 2=complete.
--
CREATE TABLE IF NOT EXISTS `quest` (
  `char_id` int(11) unsigned NOT NULL default '0',
  `quest_id` int(10) unsigned NOT NULL,
  `state` enum('0','1','2') NOT NULL default '0',
  `time` int(11) unsigned NOT NULL default '0',
  `count1` mediumint(8) unsigned NOT NULL default '0',
  `count2` mediumint(8) unsigned NOT NULL default '0',
  `count3` mediumint(8) unsigned NOT NULL default '0',
  PRIMARY KEY  USING BTREE (`char_id`,`quest_id`)
) ENGINE=MyISAM;
