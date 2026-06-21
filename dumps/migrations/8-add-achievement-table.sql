CREATE TABLE IF NOT EXISTS `achievement` (
  `char_id` int(11) unsigned NOT NULL default '0',
  `achievement_id` int(10) unsigned NOT NULL,
  `count` int(11) unsigned NOT NULL default '0',
  `completed` int(11) unsigned NOT NULL default '0',
  `rewarded` tinyint(1) unsigned NOT NULL default '0',
  PRIMARY KEY  USING BTREE (`char_id`,`achievement_id`)
) ENGINE=MyISAM;
