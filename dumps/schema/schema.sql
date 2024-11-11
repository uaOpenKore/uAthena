-- MySQL dump 10.13  Distrib 5.5.54, for Linux (i686)
--
-- Host: localhost    Database: ragnarok
-- ------------------------------------------------------
-- Server version	5.5.54

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `abra_db`
--

DROP TABLE IF EXISTS `abra_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `abra_db` (
  `ID` smallint(6) NOT NULL DEFAULT '0',
  `Dummy` text NOT NULL,
  `Req_Lvl` smallint(6) NOT NULL DEFAULT '0',
  `Per` smallint(6) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `atcommandlog`
--

DROP TABLE IF EXISTS `atcommandlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `atcommandlog` (
  `atcommand_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `atcommand_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `account_id` int(11) unsigned NOT NULL DEFAULT '0',
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `char_name` varchar(30) NOT NULL DEFAULT '',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  `command` varchar(50) NOT NULL DEFAULT '',
  PRIMARY KEY (`atcommand_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `attr_fix`
--

DROP TABLE IF EXISTS `attr_fix`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `attr_fix` (
  `Level` tinyint(4) NOT NULL DEFAULT '0',
  `None` tinyint(4) NOT NULL DEFAULT '0',
  `Water` tinyint(4) NOT NULL DEFAULT '0',
  `Earth` tinyint(4) NOT NULL DEFAULT '0',
  `Fire` tinyint(4) NOT NULL DEFAULT '0',
  `Wind` tinyint(4) NOT NULL DEFAULT '0',
  `Poison` tinyint(4) NOT NULL DEFAULT '0',
  `Saint` tinyint(4) NOT NULL DEFAULT '0',
  `Darkness` tinyint(4) NOT NULL DEFAULT '0',
  `Sense` tinyint(4) NOT NULL DEFAULT '0',
  `Immortality` tinyint(4) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `branchlog`
--

DROP TABLE IF EXISTS `branchlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `branchlog` (
  `branch_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `branch_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `account_id` int(11) NOT NULL DEFAULT '0',
  `char_id` int(11) NOT NULL DEFAULT '0',
  `char_name` varchar(30) NOT NULL DEFAULT '',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  PRIMARY KEY (`branch_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cart_inventory`
--

DROP TABLE IF EXISTS `cart_inventory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cart_inventory` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `char_id` int(11) NOT NULL DEFAULT '0',
  `nameid` int(11) NOT NULL DEFAULT '0',
  `amount` int(11) NOT NULL DEFAULT '0',
  `equip` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `identify` smallint(6) NOT NULL DEFAULT '0',
  `refine` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `attribute` tinyint(4) NOT NULL DEFAULT '0',
  `card0` int(11) NOT NULL DEFAULT '0',
  `card1` int(11) NOT NULL DEFAULT '0',
  `card2` int(11) NOT NULL DEFAULT '0',
  `card3` int(11) NOT NULL DEFAULT '0',
  `broken` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `char_id` (`char_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cast_db`
--

DROP TABLE IF EXISTS `cast_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cast_db` (
  `ID` smallint(6) NOT NULL DEFAULT '0',
  `Cast_List` mediumint(9) NOT NULL DEFAULT '0',
  `Delay_List` text NOT NULL,
  `Upkeep_Time` text NOT NULL,
  `Upkeep_Time2` text NOT NULL,
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `castle_db`
--

DROP TABLE IF EXISTS `castle_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `castle_db` (
  `CastleID` tinyint(4) NOT NULL DEFAULT '0',
  `map_name` text NOT NULL,
  `castle_name` text NOT NULL,
  `switch_flag` tinyint(4) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `char`
--

DROP TABLE IF EXISTS `char`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `char` (
  `char_id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `account_id` int(11) unsigned NOT NULL DEFAULT '0',
  `char_num` tinyint(4) NOT NULL DEFAULT '0',
  `name` varchar(30) NOT NULL DEFAULT '',
  `class` smallint(11) unsigned NOT NULL DEFAULT '0',
  `base_level` bigint(20) unsigned NOT NULL DEFAULT '1',
  `job_level` bigint(20) unsigned NOT NULL DEFAULT '1',
  `base_exp` bigint(20) NOT NULL DEFAULT '0',
  `job_exp` bigint(20) NOT NULL DEFAULT '0',
  `zeny` int(11) unsigned NOT NULL DEFAULT '0',
  `str` smallint(11) unsigned NOT NULL DEFAULT '0',
  `agi` smallint(11) unsigned NOT NULL DEFAULT '0',
  `vit` smallint(11) unsigned NOT NULL DEFAULT '0',
  `int` smallint(11) unsigned NOT NULL DEFAULT '0',
  `dex` smallint(11) unsigned NOT NULL DEFAULT '0',
  `luk` smallint(11) unsigned NOT NULL DEFAULT '0',
  `max_hp` mediumint(11) unsigned NOT NULL DEFAULT '0',
  `hp` mediumint(11) unsigned NOT NULL DEFAULT '0',
  `max_sp` mediumint(11) unsigned NOT NULL DEFAULT '0',
  `sp` mediumint(11) unsigned NOT NULL DEFAULT '0',
  `status_point` smallint(11) unsigned NOT NULL DEFAULT '0',
  `skill_point` smallint(11) unsigned NOT NULL DEFAULT '0',
  `option` int(11) NOT NULL DEFAULT '0',
  `karma` tinyint(3) NOT NULL DEFAULT '0',
  `manner` tinyint(3) NOT NULL DEFAULT '0',
  `party_id` smallint(11) unsigned NOT NULL DEFAULT '0',
  `guild_id` smallint(11) unsigned NOT NULL DEFAULT '0',
  `pet_id` int(11) unsigned NOT NULL DEFAULT '0',
  `hair` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `hair_color` smallint(11) unsigned NOT NULL DEFAULT '0',
  `clothes_color` smallint(4) unsigned NOT NULL DEFAULT '0',
  `weapon` smallint(11) unsigned NOT NULL DEFAULT '1',
  `shield` smallint(11) unsigned NOT NULL DEFAULT '0',
  `head_top` smallint(11) unsigned NOT NULL DEFAULT '0',
  `head_mid` smallint(11) unsigned NOT NULL DEFAULT '0',
  `head_bottom` smallint(11) unsigned NOT NULL DEFAULT '0',
  `last_map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  `last_x` smallint(11) unsigned NOT NULL DEFAULT '53',
  `last_y` smallint(11) unsigned NOT NULL DEFAULT '111',
  `save_map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  `save_x` smallint(11) unsigned NOT NULL DEFAULT '53',
  `save_y` smallint(11) unsigned NOT NULL DEFAULT '111',
  `partner_id` int(11) unsigned NOT NULL DEFAULT '0',
  `online` tinyint(4) NOT NULL DEFAULT '0',
  `father` int(11) unsigned NOT NULL DEFAULT '0',
  `mother` int(11) unsigned NOT NULL DEFAULT '0',
  `child` int(11) unsigned NOT NULL DEFAULT '0',
  `fame` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`char_id`),
  KEY `party_id` (`party_id`),
  KEY `guild_id` (`guild_id`)
) ENGINE=InnoDB AUTO_INCREMENT=150000 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `charlog`
--

DROP TABLE IF EXISTS `charlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `charlog` (
  `time` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `char_msg` varchar(255) NOT NULL DEFAULT 'char select',
  `account_id` int(11) NOT NULL DEFAULT '0',
  `char_num` tinyint(4) NOT NULL DEFAULT '0',
  `name` varchar(255) NOT NULL DEFAULT '',
  `str` int(11) unsigned NOT NULL DEFAULT '0',
  `agi` int(11) unsigned NOT NULL DEFAULT '0',
  `vit` int(11) unsigned NOT NULL DEFAULT '0',
  `int` int(11) unsigned NOT NULL DEFAULT '0',
  `dex` int(11) unsigned NOT NULL DEFAULT '0',
  `luk` int(11) unsigned NOT NULL DEFAULT '0',
  `hair` tinyint(4) NOT NULL DEFAULT '0',
  `hair_color` int(11) NOT NULL DEFAULT '0'
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chatlog`
--

DROP TABLE IF EXISTS `chatlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `chatlog` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `time` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `type` set('W','P','G') NOT NULL DEFAULT 'W',
  `type_id` int(11) NOT NULL DEFAULT '0',
  `src_charid` int(11) NOT NULL DEFAULT '0',
  `src_accountid` int(11) NOT NULL DEFAULT '0',
  `src_map` varchar(17) NOT NULL DEFAULT 'prontera.gat',
  `src_map_x` smallint(4) NOT NULL DEFAULT '0',
  `src_map_y` smallint(4) NOT NULL DEFAULT '0',
  `dst_charname` varchar(25) NOT NULL DEFAULT '',
  `message` varchar(150) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `create_arrow_db`
--

DROP TABLE IF EXISTS `create_arrow_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `create_arrow_db` (
  `SourceID` mediumint(9) NOT NULL DEFAULT '0',
  `MakeID1` mediumint(9) NOT NULL DEFAULT '0',
  `MakeNum1` mediumint(9) NOT NULL DEFAULT '0',
  `MakeID2` mediumint(9) NOT NULL DEFAULT '0',
  `MakeNum2` mediumint(9) NOT NULL DEFAULT '0',
  `MakeID3` mediumint(9) NOT NULL DEFAULT '0',
  `MakeNum3` mediumint(9) NOT NULL DEFAULT '0',
  `MakeID4` mediumint(9) NOT NULL DEFAULT '0',
  `MakeNum4` mediumint(9) NOT NULL DEFAULT '0',
  `MakeID5` mediumint(9) NOT NULL DEFAULT '0',
  `MakeNum5` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `droplog`
--

DROP TABLE IF EXISTS `droplog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `droplog` (
  `drop_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `drop_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `kill_char_id` int(11) NOT NULL DEFAULT '0',
  `monster_id` smallint(6) NOT NULL DEFAULT '0',
  `item1` int(11) NOT NULL DEFAULT '0',
  `item2` int(11) NOT NULL DEFAULT '0',
  `item3` int(11) NOT NULL DEFAULT '0',
  `item4` int(11) NOT NULL DEFAULT '0',
  `item5` int(11) NOT NULL DEFAULT '0',
  `item6` int(11) NOT NULL DEFAULT '0',
  `item7` int(11) NOT NULL DEFAULT '0',
  `item8` int(11) NOT NULL DEFAULT '0',
  `item9` int(11) NOT NULL DEFAULT '0',
  `itemCard` int(11) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  PRIMARY KEY (`drop_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exp`
--

DROP TABLE IF EXISTS `exp`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exp` (
  `EXP1` bigint(9) NOT NULL DEFAULT '0',
  `EXP2` bigint(9) NOT NULL DEFAULT '0',
  `EXP3` bigint(9) NOT NULL DEFAULT '0',
  `EXP4` bigint(9) NOT NULL DEFAULT '0',
  `EXP5` bigint(9) NOT NULL DEFAULT '0',
  `EXP6` bigint(9) NOT NULL DEFAULT '0',
  `EXP7` bigint(9) NOT NULL DEFAULT '0',
  `EXP8` bigint(9) NOT NULL DEFAULT '0',
  `EXP9` bigint(9) NOT NULL DEFAULT '0',
  `EXP10` bigint(9) NOT NULL DEFAULT '0',
  `EXP11` bigint(9) NOT NULL DEFAULT '0',
  `EXP12` bigint(9) NOT NULL DEFAULT '0',
  `EXP13` bigint(9) NOT NULL DEFAULT '0',
  `EXP14` bigint(9) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exp_guild`
--

DROP TABLE IF EXISTS `exp_guild`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exp_guild` (
  `Level` tinyint(4) NOT NULL DEFAULT '0',
  `EXP` int(11) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `friends`
--

DROP TABLE IF EXISTS `friends`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `friends` (
  `char_id` int(11) NOT NULL DEFAULT '0',
  `friend_account` int(11) NOT NULL DEFAULT '0',
  `friend_id` int(11) NOT NULL DEFAULT '0'
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `global_reg_value`
--

DROP TABLE IF EXISTS `global_reg_value`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `global_reg_value` (
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `str` varchar(255) NOT NULL DEFAULT '',
  `value` varchar(255) NOT NULL DEFAULT '0',
  `type` int(11) NOT NULL DEFAULT '3',
  `account_id` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`char_id`,`str`,`account_id`),
  KEY `account_id` (`account_id`),
  KEY `char_id` (`char_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild`
--

DROP TABLE IF EXISTS `guild`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guild` (
  `guild_id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(24) NOT NULL DEFAULT '',
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `master` varchar(24) NOT NULL DEFAULT '',
  `guild_lv` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `connect_member` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `max_member` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `average_lv` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `exp` int(11) unsigned NOT NULL DEFAULT '0',
  `next_exp` int(11) unsigned NOT NULL DEFAULT '0',
  `skill_point` tinyint(11) unsigned NOT NULL DEFAULT '0',
  `mes1` varchar(60) NOT NULL DEFAULT '',
  `mes2` varchar(120) NOT NULL DEFAULT '',
  `emblem_len` int(11) unsigned NOT NULL DEFAULT '0',
  `emblem_id` int(11) unsigned NOT NULL DEFAULT '0',
  `emblem_data` blob NOT NULL,
  PRIMARY KEY (`guild_id`,`char_id`),
  UNIQUE KEY `guild_id` (`guild_id`),
  KEY `char_id` (`char_id`),
  CONSTRAINT `guild_ibfk_1` FOREIGN KEY (`char_id`) REFERENCES `char` (`char_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild_alliance`
--

DROP TABLE IF EXISTS `guild_alliance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guild_alliance` (
  `guild_id` int(11) unsigned NOT NULL DEFAULT '0',
  `opposition` int(11) unsigned NOT NULL DEFAULT '0',
  `alliance_id` int(11) unsigned NOT NULL DEFAULT '0',
  `name` varchar(24) NOT NULL DEFAULT '',
  PRIMARY KEY (`guild_id`,`alliance_id`),
  KEY `alliance_id` (`alliance_id`),
  CONSTRAINT `guild_alliance_ibfk_1` FOREIGN KEY (`guild_id`) REFERENCES `guild` (`guild_id`) ON DELETE CASCADE,
  CONSTRAINT `guild_alliance_ibfk_2` FOREIGN KEY (`alliance_id`) REFERENCES `guild` (`guild_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild_castle`
--

DROP TABLE IF EXISTS `guild_castle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guild_castle` (
  `castle_id` int(11) unsigned NOT NULL DEFAULT '0',
  `guild_id` int(11) unsigned NOT NULL DEFAULT '0',
  `economy` int(11) unsigned NOT NULL DEFAULT '0',
  `defense` int(11) unsigned NOT NULL DEFAULT '0',
  `triggerE` int(11) unsigned NOT NULL DEFAULT '0',
  `triggerD` int(11) unsigned NOT NULL DEFAULT '0',
  `nextTime` int(11) unsigned NOT NULL DEFAULT '0',
  `payTime` int(11) unsigned NOT NULL DEFAULT '0',
  `createTime` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleC` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleG0` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleG1` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleG2` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleG3` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleG4` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleG5` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleG6` int(11) unsigned NOT NULL DEFAULT '0',
  `visibleG7` int(11) unsigned NOT NULL DEFAULT '0',
  `gHP0` int(11) unsigned NOT NULL DEFAULT '0',
  `ghP1` int(11) unsigned NOT NULL DEFAULT '0',
  `gHP2` int(11) unsigned NOT NULL DEFAULT '0',
  `gHP3` int(11) unsigned NOT NULL DEFAULT '0',
  `gHP4` int(11) unsigned NOT NULL DEFAULT '0',
  `gHP5` int(11) unsigned NOT NULL DEFAULT '0',
  `gHP6` int(11) unsigned NOT NULL DEFAULT '0',
  `gHP7` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`castle_id`),
  KEY `guild_id` (`guild_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild_expulsion`
--

DROP TABLE IF EXISTS `guild_expulsion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guild_expulsion` (
  `guild_id` int(11) unsigned NOT NULL DEFAULT '0',
  `name` varchar(24) NOT NULL DEFAULT '',
  `mes` varchar(40) NOT NULL DEFAULT '',
  `acc` varchar(40) NOT NULL DEFAULT '',
  `account_id` int(11) unsigned NOT NULL DEFAULT '0',
  `rsv1` int(11) unsigned NOT NULL DEFAULT '0',
  `rsv2` int(11) unsigned NOT NULL DEFAULT '0',
  `rsv3` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`guild_id`,`name`),
  CONSTRAINT `guild_expulsion_ibfk_1` FOREIGN KEY (`guild_id`) REFERENCES `guild` (`guild_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild_member`
--

DROP TABLE IF EXISTS `guild_member`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guild_member` (
  `guild_id` int(11) unsigned NOT NULL DEFAULT '0',
  `account_id` int(11) unsigned NOT NULL DEFAULT '0',
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `hair` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `hair_color` smallint(6) unsigned NOT NULL DEFAULT '0',
  `gender` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `class` smallint(6) unsigned NOT NULL DEFAULT '0',
  `lv` smallint(6) unsigned NOT NULL DEFAULT '0',
  `exp` bigint(20) unsigned NOT NULL DEFAULT '0',
  `exp_payper` tinyint(11) unsigned NOT NULL DEFAULT '0',
  `online` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `position` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `rsv1` int(11) unsigned NOT NULL DEFAULT '0',
  `rsv2` int(11) unsigned NOT NULL DEFAULT '0',
  `name` varchar(24) NOT NULL DEFAULT '',
  PRIMARY KEY (`guild_id`,`char_id`),
  KEY `char_id` (`char_id`),
  CONSTRAINT `guild_member_ibfk_1` FOREIGN KEY (`guild_id`) REFERENCES `guild` (`guild_id`) ON DELETE CASCADE,
  CONSTRAINT `guild_member_ibfk_2` FOREIGN KEY (`char_id`) REFERENCES `char` (`char_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild_position`
--

DROP TABLE IF EXISTS `guild_position`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guild_position` (
  `guild_id` int(9) unsigned NOT NULL DEFAULT '0',
  `position` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `name` varchar(24) NOT NULL DEFAULT '',
  `mode` tinyint(11) unsigned NOT NULL DEFAULT '0',
  `exp_mode` tinyint(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`guild_id`,`position`),
  KEY `guild_id` (`guild_id`),
  CONSTRAINT `guild_position_ibfk_1` FOREIGN KEY (`guild_id`) REFERENCES `guild` (`guild_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild_skill`
--

DROP TABLE IF EXISTS `guild_skill`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guild_skill` (
  `guild_id` int(11) unsigned NOT NULL DEFAULT '0',
  `id` smallint(11) unsigned NOT NULL DEFAULT '0',
  `lv` tinyint(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`guild_id`,`id`),
  CONSTRAINT `guild_skill_ibfk_1` FOREIGN KEY (`guild_id`) REFERENCES `guild` (`guild_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild_storage`
--

DROP TABLE IF EXISTS `guild_storage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guild_storage` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `guild_id` int(11) unsigned NOT NULL DEFAULT '0',
  `nameid` int(11) unsigned NOT NULL DEFAULT '0',
  `amount` int(11) unsigned NOT NULL DEFAULT '0',
  `equip` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `identify` smallint(6) unsigned NOT NULL DEFAULT '0',
  `refine` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `attribute` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `card0` smallint(11) NOT NULL DEFAULT '0',
  `card1` smallint(11) NOT NULL DEFAULT '0',
  `card2` smallint(11) NOT NULL DEFAULT '0',
  `card3` smallint(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `guild_id` (`guild_id`),
  CONSTRAINT `guild_storage_ibfk_1` FOREIGN KEY (`guild_id`) REFERENCES `guild` (`guild_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `interlog`
--

DROP TABLE IF EXISTS `interlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `interlog` (
  `time` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `log` varchar(255) NOT NULL DEFAULT ''
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inventory`
--

DROP TABLE IF EXISTS `inventory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `inventory` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `nameid` int(11) unsigned NOT NULL DEFAULT '0',
  `amount` int(11) unsigned NOT NULL DEFAULT '0',
  `equip` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `identify` smallint(6) NOT NULL DEFAULT '0',
  `refine` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `attribute` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `card0` smallint(11) NOT NULL DEFAULT '0',
  `card1` smallint(11) NOT NULL DEFAULT '0',
  `card2` smallint(11) NOT NULL DEFAULT '0',
  `card3` smallint(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `char_id` (`char_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ipbanlist`
--

DROP TABLE IF EXISTS `ipbanlist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ipbanlist` (
  `list` varchar(255) NOT NULL DEFAULT '',
  `btime` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `rtime` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `reason` varchar(255) NOT NULL DEFAULT ''
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `item_bluebox`
--

DROP TABLE IF EXISTS `item_bluebox`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `item_bluebox` (
  `NameID` mediumint(9) NOT NULL DEFAULT '0',
  `item_name` text NOT NULL,
  `rate` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `item_cardalbum`
--

DROP TABLE IF EXISTS `item_cardalbum`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `item_cardalbum` (
  `NameID` mediumint(9) NOT NULL DEFAULT '0',
  `item_name` text NOT NULL,
  `rate` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `item_db`
--

DROP TABLE IF EXISTS `item_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `item_db` (
  `id` smallint(5) unsigned NOT NULL DEFAULT '0',
  `name_english` varchar(24) DEFAULT NULL,
  `name_japanese` varchar(24) DEFAULT NULL,
  `type` tinyint(2) unsigned NOT NULL DEFAULT '0',
  `price_buy` mediumint(10) unsigned DEFAULT NULL,
  `price_sell` mediumint(10) unsigned DEFAULT NULL,
  `weight` smallint(5) unsigned NOT NULL DEFAULT '0',
  `attack` tinyint(3) unsigned DEFAULT NULL,
  `defence` tinyint(3) unsigned DEFAULT NULL,
  `range` tinyint(2) unsigned DEFAULT NULL,
  `slots` tinyint(2) unsigned DEFAULT NULL,
  `equip_jobs` int(12) unsigned DEFAULT NULL,
  `equip_upper` tinyint(8) unsigned DEFAULT NULL,
  `equip_genders` tinyint(2) unsigned DEFAULT NULL,
  `equip_locations` smallint(4) unsigned DEFAULT NULL,
  `weapon_level` tinyint(2) unsigned DEFAULT NULL,
  `equip_level` tinyint(3) unsigned DEFAULT NULL,
  `refineable` tinyint(1) unsigned DEFAULT NULL,
  `view` tinyint(3) unsigned DEFAULT NULL,
  `script` text,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `item_db2`
--

DROP TABLE IF EXISTS `item_db2`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `item_db2` (
  `id` smallint(5) unsigned NOT NULL DEFAULT '0',
  `name_english` varchar(30) NOT NULL DEFAULT '',
  `name_japanese` varchar(30) NOT NULL DEFAULT '',
  `type` tinyint(2) unsigned NOT NULL DEFAULT '0',
  `price_buy` mediumint(10) unsigned DEFAULT NULL,
  `price_sell` mediumint(10) unsigned DEFAULT NULL,
  `weight` smallint(5) unsigned NOT NULL DEFAULT '0',
  `attack` tinyint(3) unsigned DEFAULT NULL,
  `defence` tinyint(3) unsigned DEFAULT NULL,
  `range` tinyint(2) unsigned DEFAULT NULL,
  `slots` tinyint(2) unsigned DEFAULT NULL,
  `equip_jobs` int(12) unsigned DEFAULT NULL,
  `equip_upper` tinyint(8) unsigned DEFAULT NULL,
  `equip_genders` tinyint(2) unsigned DEFAULT NULL,
  `equip_locations` smallint(4) unsigned DEFAULT NULL,
  `weapon_level` tinyint(2) unsigned DEFAULT NULL,
  `equip_level` tinyint(3) unsigned DEFAULT NULL,
  `refineable` tinyint(1) unsigned DEFAULT NULL,
  `view` tinyint(3) unsigned DEFAULT NULL,
  `script` text,
  `comment` text,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `item_giftbox`
--

DROP TABLE IF EXISTS `item_giftbox`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `item_giftbox` (
  `NameID` mediumint(9) NOT NULL DEFAULT '0',
  `item_name` text NOT NULL,
  `rate` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `item_scroll`
--

DROP TABLE IF EXISTS `item_scroll`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `item_scroll` (
  `NameID` mediumint(9) NOT NULL DEFAULT '0',
  `item_name` text NOT NULL,
  `rate` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `item_violetbox`
--

DROP TABLE IF EXISTS `item_violetbox`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `item_violetbox` (
  `NameID` mediumint(9) NOT NULL DEFAULT '0',
  `item_name` text NOT NULL,
  `rate` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `job_db1`
--

DROP TABLE IF EXISTS `job_db1`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `job_db1` (
  `Class_ID` tinyint(4) NOT NULL DEFAULT '0',
  `Weight` mediumint(9) NOT NULL DEFAULT '0',
  `HP` smallint(6) NOT NULL DEFAULT '0',
  `HP2` smallint(6) NOT NULL DEFAULT '0',
  `SP` smallint(6) NOT NULL DEFAULT '0',
  `Empty` smallint(6) NOT NULL DEFAULT '0',
  `Dagger` smallint(6) NOT NULL DEFAULT '0',
  `Sword` smallint(6) NOT NULL DEFAULT '0',
  `Two_Handed_Sword` smallint(6) NOT NULL DEFAULT '0',
  `Spear` smallint(6) NOT NULL DEFAULT '0',
  `Two_Handed_Spear` smallint(6) NOT NULL DEFAULT '0',
  `Axe` smallint(6) NOT NULL DEFAULT '0',
  `Two_Handed_Axe` smallint(6) NOT NULL DEFAULT '0',
  `Rod` smallint(6) NOT NULL DEFAULT '0',
  `Club` smallint(6) NOT NULL DEFAULT '0',
  `Stick` smallint(6) NOT NULL DEFAULT '0',
  `Bow` smallint(6) NOT NULL DEFAULT '0',
  `Fist` smallint(6) NOT NULL DEFAULT '0',
  `Musical` smallint(6) NOT NULL DEFAULT '0',
  `Whip` smallint(6) NOT NULL DEFAULT '0',
  `Book` smallint(6) NOT NULL DEFAULT '0',
  `Katar` smallint(6) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `login`
--

DROP TABLE IF EXISTS `login`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `login` (
  `account_id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `userid` varchar(255) NOT NULL DEFAULT '',
  `user_pass` varchar(32) NOT NULL DEFAULT '',
  `lastlogin` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `sex` char(1) NOT NULL DEFAULT 'M',
  `logincount` mediumint(9) unsigned NOT NULL DEFAULT '0',
  `email` varchar(60) NOT NULL DEFAULT '',
  `level` tinyint(3) NOT NULL DEFAULT '0',
  `error_message` smallint(11) unsigned NOT NULL DEFAULT '0',
  `connect_until` smallint(11) unsigned NOT NULL DEFAULT '0',
  `last_ip` varchar(100) NOT NULL DEFAULT '',
  `memo` smallint(11) unsigned NOT NULL DEFAULT '0',
  `ban_until` int(11) unsigned NOT NULL DEFAULT '0',
  `state` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`account_id`),
  KEY `name` (`userid`)
) ENGINE=InnoDB AUTO_INCREMENT=2000000 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `loginlog`
--

DROP TABLE IF EXISTS `loginlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `loginlog` (
  `time` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `ip` varchar(64) NOT NULL DEFAULT '',
  `user` varchar(32) NOT NULL DEFAULT '',
  `rcode` tinyint(4) NOT NULL DEFAULT '0',
  `log` varchar(255) NOT NULL DEFAULT ''
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mail`
--

DROP TABLE IF EXISTS `mail`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mail` (
  `message_id` int(11) NOT NULL AUTO_INCREMENT,
  `to_account_id` int(11) NOT NULL DEFAULT '0',
  `to_char_name` varchar(24) NOT NULL DEFAULT '',
  `from_account_id` int(11) NOT NULL DEFAULT '0',
  `from_char_name` varchar(24) NOT NULL DEFAULT '',
  `message` varchar(80) NOT NULL DEFAULT '',
  `read_flag` tinyint(1) NOT NULL DEFAULT '0',
  `priority` tinyint(1) NOT NULL DEFAULT '0',
  `check_flag` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`message_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mapreg`
--

DROP TABLE IF EXISTS `mapreg`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mapreg` (
  `varname` varchar(32) NOT NULL,
  `index` int(11) unsigned NOT NULL DEFAULT '0',
  `value` varchar(255) NOT NULL,
  KEY `varname` (`varname`),
  KEY `index` (`index`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `memo`
--

DROP TABLE IF EXISTS `memo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `memo` (
  `memo_id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `map` varchar(255) NOT NULL DEFAULT '',
  `x` smallint(9) unsigned NOT NULL DEFAULT '0',
  `y` smallint(9) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`memo_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `migrations`
--

DROP TABLE IF EXISTS `migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `migrations` (
  `file` varchar(50) NOT NULL,
  `dati` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mob_boss`
--

DROP TABLE IF EXISTS `mob_boss`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mob_boss` (
  `MobID` mediumint(9) NOT NULL DEFAULT '0',
  `MobName` text NOT NULL,
  `Rate` int(11) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mob_branch`
--

DROP TABLE IF EXISTS `mob_branch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mob_branch` (
  `MobID` mediumint(9) NOT NULL DEFAULT '0',
  `MobName` text NOT NULL,
  `Rate` int(11) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mob_db`
--

DROP TABLE IF EXISTS `mob_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mob_db` (
  `ID` mediumint(9) unsigned NOT NULL DEFAULT '0',
  `Name` text NOT NULL,
  `Name2` text NOT NULL,
  `LV` tinyint(6) unsigned NOT NULL DEFAULT '0',
  `HP` int(9) unsigned NOT NULL DEFAULT '0',
  `SP` mediumint(9) unsigned NOT NULL DEFAULT '0',
  `EXP` mediumint(9) unsigned NOT NULL DEFAULT '0',
  `JEXP` mediumint(9) unsigned NOT NULL DEFAULT '0',
  `Range1` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `ATK1` smallint(6) unsigned NOT NULL DEFAULT '0',
  `ATK2` smallint(6) unsigned NOT NULL DEFAULT '0',
  `DEF` smallint(6) unsigned NOT NULL DEFAULT '0',
  `MDEF` smallint(6) unsigned NOT NULL DEFAULT '0',
  `STR` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `AGI` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `VIT` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `INT` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `DEX` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `LUK` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `Range2` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `Range3` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `Scale` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `Race` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `Element` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `Mode` smallint(6) unsigned NOT NULL DEFAULT '0',
  `Speed` smallint(6) unsigned NOT NULL DEFAULT '0',
  `ADelay` smallint(6) unsigned NOT NULL DEFAULT '0',
  `aMotion` smallint(6) unsigned NOT NULL DEFAULT '0',
  `dMotion` smallint(6) unsigned NOT NULL DEFAULT '0',
  `Drop1id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop1per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop2id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop2per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop3id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop3per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop4id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop4per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop5id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop5per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop6id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop6per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop7id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop7per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop8id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop8per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop9id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `Drop9per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `DropCardid` smallint(9) unsigned NOT NULL DEFAULT '0',
  `DropCardper` smallint(9) unsigned NOT NULL DEFAULT '0',
  `MEXP` mediumint(9) unsigned NOT NULL DEFAULT '0',
  `ExpPer` smallint(9) unsigned NOT NULL DEFAULT '0',
  `MVP1id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `MVP1per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `MVP2id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `MVP2per` smallint(9) unsigned NOT NULL DEFAULT '0',
  `MVP3id` smallint(9) unsigned NOT NULL DEFAULT '0',
  `MVP3per` smallint(9) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`ID`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mob_db2`
--

DROP TABLE IF EXISTS `mob_db2`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mob_db2` (
  `ID` mediumint(9) NOT NULL DEFAULT '0',
  `Name` text NOT NULL,
  `Name2` text NOT NULL,
  `LV` smallint(6) NOT NULL DEFAULT '0',
  `HP` mediumint(9) NOT NULL DEFAULT '0',
  `SP` mediumint(9) NOT NULL DEFAULT '0',
  `EXP` mediumint(9) NOT NULL DEFAULT '0',
  `JEXP` mediumint(9) NOT NULL DEFAULT '0',
  `Range1` tinyint(4) NOT NULL DEFAULT '0',
  `ATK1` smallint(6) NOT NULL DEFAULT '0',
  `ATK2` smallint(6) NOT NULL DEFAULT '0',
  `DEF` smallint(6) NOT NULL DEFAULT '0',
  `MDEF` smallint(6) NOT NULL DEFAULT '0',
  `STR` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `AGI` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `VIT` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `INT` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `DEX` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `LUK` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `Range2` tinyint(4) NOT NULL DEFAULT '0',
  `Range3` tinyint(4) NOT NULL DEFAULT '0',
  `Scale` tinyint(4) NOT NULL DEFAULT '0',
  `Race` tinyint(4) NOT NULL DEFAULT '0',
  `Element` tinyint(4) NOT NULL DEFAULT '0',
  `Mode` smallint(6) NOT NULL DEFAULT '0',
  `Speed` smallint(6) NOT NULL DEFAULT '0',
  `ADelay` smallint(6) NOT NULL DEFAULT '0',
  `aMotion` smallint(6) NOT NULL DEFAULT '0',
  `dMotion` smallint(6) NOT NULL DEFAULT '0',
  `Drop1id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop1per` mediumint(9) NOT NULL DEFAULT '0',
  `Drop2id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop2per` mediumint(9) NOT NULL DEFAULT '0',
  `Drop3id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop3per` mediumint(9) NOT NULL DEFAULT '0',
  `Drop4id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop4per` mediumint(9) NOT NULL DEFAULT '0',
  `Drop5id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop5per` mediumint(9) NOT NULL DEFAULT '0',
  `Drop6id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop6per` mediumint(9) NOT NULL DEFAULT '0',
  `Drop7id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop7per` mediumint(9) NOT NULL DEFAULT '0',
  `Drop8id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop8per` mediumint(9) NOT NULL DEFAULT '0',
  `Drop9id` mediumint(9) NOT NULL DEFAULT '0',
  `Drop9per` mediumint(9) NOT NULL DEFAULT '0',
  `DropCardid` mediumint(9) NOT NULL DEFAULT '0',
  `DropCardper` mediumint(9) NOT NULL DEFAULT '0',
  `MEXP` mediumint(9) NOT NULL DEFAULT '0',
  `ExpPer` mediumint(9) NOT NULL DEFAULT '0',
  `MVP1id` mediumint(9) NOT NULL DEFAULT '0',
  `MVP1per` mediumint(9) NOT NULL DEFAULT '0',
  `MVP2id` mediumint(9) NOT NULL DEFAULT '0',
  `MVP2per` mediumint(9) NOT NULL DEFAULT '0',
  `MVP3id` mediumint(9) NOT NULL DEFAULT '0',
  `MVP3per` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mob_poring`
--

DROP TABLE IF EXISTS `mob_poring`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mob_poring` (
  `MobID` smallint(6) NOT NULL DEFAULT '0',
  `MobName` text NOT NULL,
  `Rate` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mob_skill_db`
--

DROP TABLE IF EXISTS `mob_skill_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mob_skill_db` (
  `Mob_ID` smallint(6) NOT NULL DEFAULT '0',
  `Dummy` text NOT NULL,
  `State` text NOT NULL,
  `Skill_ID` smallint(6) NOT NULL DEFAULT '0',
  `Skill_LV` tinyint(4) NOT NULL DEFAULT '0',
  `Use_Rate` smallint(6) NOT NULL DEFAULT '0',
  `Cast_Time` smallint(6) NOT NULL DEFAULT '0',
  `Delay` smallint(6) NOT NULL DEFAULT '0',
  `Disturbance` text NOT NULL,
  `Target` text NOT NULL,
  `Condition_Type` text NOT NULL,
  `Condition_Value` smallint(6) NOT NULL DEFAULT '0',
  `Value1` mediumint(9) NOT NULL DEFAULT '0',
  `Value2` mediumint(9) NOT NULL DEFAULT '0',
  `Value3` mediumint(9) NOT NULL DEFAULT '0',
  `Value4` mediumint(9) NOT NULL DEFAULT '0',
  `Value5` mediumint(9) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mvplog`
--

DROP TABLE IF EXISTS `mvplog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mvplog` (
  `mvp_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `mvp_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `kill_char_id` int(11) NOT NULL DEFAULT '0',
  `monster_id` smallint(6) NOT NULL DEFAULT '0',
  `prize` int(11) NOT NULL DEFAULT '0',
  `mvpexp` mediumint(9) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  PRIMARY KEY (`mvp_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `npclog`
--

DROP TABLE IF EXISTS `npclog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `npclog` (
  `npc_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `npc_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `account_id` int(11) unsigned NOT NULL DEFAULT '0',
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `char_name` varchar(30) NOT NULL DEFAULT '',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  `mes` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`npc_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `party`
--

DROP TABLE IF EXISTS `party`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `party` (
  `party_id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(100) NOT NULL DEFAULT '',
  `exp` tinyint(11) unsigned NOT NULL DEFAULT '0',
  `item` tinyint(11) unsigned NOT NULL DEFAULT '0',
  `leader_id` int(11) unsigned NOT NULL DEFAULT '0',
  `leader_char` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`party_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pet`
--

DROP TABLE IF EXISTS `pet`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pet` (
  `pet_id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `class` mediumint(9) unsigned NOT NULL DEFAULT '0',
  `name` varchar(24) NOT NULL DEFAULT '',
  `account_id` int(11) unsigned NOT NULL DEFAULT '0',
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `level` smallint(4) unsigned NOT NULL DEFAULT '0',
  `egg_id` smallint(11) unsigned NOT NULL DEFAULT '0',
  `equip` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `intimate` smallint(9) unsigned NOT NULL DEFAULT '0',
  `hungry` smallint(9) unsigned NOT NULL DEFAULT '0',
  `rename_flag` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `incuvate` int(11) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`pet_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pet_db`
--

DROP TABLE IF EXISTS `pet_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pet_db` (
  `MobID` smallint(6) NOT NULL DEFAULT '0',
  `Name` text NOT NULL,
  `JName` text NOT NULL,
  `ItemID` smallint(6) NOT NULL DEFAULT '0',
  `EggID` smallint(6) NOT NULL DEFAULT '0',
  `AcceID` smallint(6) NOT NULL DEFAULT '0',
  `FoodID` smallint(6) NOT NULL DEFAULT '0',
  `Fullness` smallint(6) NOT NULL DEFAULT '0',
  `HungryDeray` smallint(6) NOT NULL DEFAULT '0',
  `R_Hungry` smallint(6) NOT NULL DEFAULT '0',
  `R_Full` smallint(6) NOT NULL DEFAULT '0',
  `Intimate` smallint(6) NOT NULL DEFAULT '0',
  `Die` smallint(6) NOT NULL DEFAULT '0',
  `Capture` smallint(6) NOT NULL DEFAULT '0',
  `Speed` smallint(6) NOT NULL DEFAULT '0',
  `S_Performance` smallint(6) NOT NULL DEFAULT '0',
  `Talk_Convert_Class` smallint(6) NOT NULL DEFAULT '0',
  `Attack_Rate` smallint(6) NOT NULL DEFAULT '0',
  `Defence_Attack_Rate` smallint(6) NOT NULL DEFAULT '0',
  `Change_Target_Rate` smallint(6) NOT NULL DEFAULT '0',
  `Pet_Script` text NOT NULL,
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `picklog`
--

DROP TABLE IF EXISTS `picklog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `picklog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `time` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `char_id` int(11) NOT NULL DEFAULT '0',
  `type` set('M','P','L','T','V','S','N','C','A') NOT NULL DEFAULT 'P',
  `nameid` int(11) NOT NULL DEFAULT '0',
  `amount` int(11) NOT NULL DEFAULT '1',
  `refine` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `card0` int(11) NOT NULL DEFAULT '0',
  `card1` int(11) NOT NULL DEFAULT '0',
  `card2` int(11) NOT NULL DEFAULT '0',
  `card3` int(11) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `presentlog`
--

DROP TABLE IF EXISTS `presentlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `presentlog` (
  `present_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `present_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `src_id` tinyint(1) NOT NULL DEFAULT '0',
  `account_id` int(11) NOT NULL DEFAULT '0',
  `char_id` int(11) NOT NULL DEFAULT '0',
  `char_name` varchar(30) NOT NULL DEFAULT '',
  `nameid` int(11) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  PRIMARY KEY (`present_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `produce_db`
--

DROP TABLE IF EXISTS `produce_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `produce_db` (
  `ID` smallint(6) NOT NULL DEFAULT '0',
  `ItemLV` tinyint(4) NOT NULL DEFAULT '0',
  `RequireSkill` smallint(6) NOT NULL DEFAULT '0',
  `MaterialID1` smallint(6) NOT NULL DEFAULT '0',
  `MaterialAmount1` smallint(6) NOT NULL DEFAULT '0',
  `MaterialID2` smallint(6) NOT NULL DEFAULT '0',
  `MaterialAmount2` smallint(6) NOT NULL DEFAULT '0',
  `MaterialID3` smallint(6) NOT NULL DEFAULT '0',
  `MaterialAmount3` smallint(6) NOT NULL DEFAULT '0',
  `MaterialID4` smallint(6) NOT NULL DEFAULT '0',
  `MaterialAmount4` smallint(6) NOT NULL DEFAULT '0',
  `MaterialID5` smallint(6) NOT NULL DEFAULT '0',
  `MaterialAmount5` smallint(6) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `producelog`
--

DROP TABLE IF EXISTS `producelog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `producelog` (
  `produce_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `produce_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `account_id` int(11) NOT NULL DEFAULT '0',
  `char_id` int(11) NOT NULL DEFAULT '0',
  `char_name` varchar(30) NOT NULL DEFAULT '',
  `nameid` int(11) NOT NULL DEFAULT '0',
  `slot1` int(11) NOT NULL DEFAULT '0',
  `slot2` int(11) NOT NULL DEFAULT '0',
  `slot3` int(11) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  `success` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`produce_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ragsrvinfo`
--

DROP TABLE IF EXISTS `ragsrvinfo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ragsrvinfo` (
  `index` int(11) NOT NULL DEFAULT '0',
  `name` varchar(255) NOT NULL DEFAULT '',
  `exp` int(11) unsigned NOT NULL DEFAULT '0',
  `jexp` int(11) unsigned NOT NULL DEFAULT '0',
  `drop` int(11) unsigned NOT NULL DEFAULT '0',
  `motd` varchar(255) NOT NULL DEFAULT ''
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `refine_db`
--

DROP TABLE IF EXISTS `refine_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `refine_db` (
  `Refine_Bonus` tinyint(4) NOT NULL DEFAULT '0',
  `Danger_Bonus` tinyint(4) NOT NULL DEFAULT '0',
  `Safe_Limit` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance1` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance2` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance3` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance4` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance5` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance6` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance7` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance8` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance9` tinyint(4) NOT NULL DEFAULT '0',
  `RefineChance10` tinyint(4) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `refinelog`
--

DROP TABLE IF EXISTS `refinelog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `refinelog` (
  `refine_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `refine_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `account_id` int(11) NOT NULL DEFAULT '0',
  `char_id` int(11) NOT NULL DEFAULT '0',
  `char_name` varchar(30) NOT NULL DEFAULT '',
  `nameid` int(11) NOT NULL DEFAULT '0',
  `refine` tinyint(2) NOT NULL DEFAULT '0',
  `card0` int(11) NOT NULL DEFAULT '0',
  `card1` int(11) NOT NULL DEFAULT '0',
  `card2` int(11) NOT NULL DEFAULT '0',
  `card3` int(11) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  `success` tinyint(1) NOT NULL DEFAULT '0',
  `item_level` tinyint(2) NOT NULL DEFAULT '0',
  PRIMARY KEY (`refine_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sc_data`
--

DROP TABLE IF EXISTS `sc_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sc_data` (
  `account_id` int(11) unsigned NOT NULL,
  `char_id` int(11) unsigned NOT NULL,
  `type` smallint(11) unsigned NOT NULL,
  `tick` int(11) NOT NULL,
  `val1` int(11) NOT NULL DEFAULT '0',
  `val2` int(11) NOT NULL DEFAULT '0',
  `val3` int(11) NOT NULL DEFAULT '0',
  `val4` int(11) NOT NULL DEFAULT '0',
  KEY `account_id` (`account_id`),
  KEY `char_id` (`char_id`),
  CONSTRAINT `scdata_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `login` (`account_id`) ON DELETE CASCADE,
  CONSTRAINT `scdata_ibfk_2` FOREIGN KEY (`char_id`) REFERENCES `char` (`char_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `size_fix`
--

DROP TABLE IF EXISTS `size_fix`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `size_fix` (
  `Element` tinyint(4) NOT NULL DEFAULT '0',
  `Dagger` tinyint(4) NOT NULL DEFAULT '0',
  `Sword` tinyint(4) NOT NULL DEFAULT '0',
  `Two_Handed_Sword` tinyint(4) NOT NULL DEFAULT '0',
  `Spear` tinyint(4) NOT NULL DEFAULT '0',
  `Two_Handed_Spear` tinyint(4) NOT NULL DEFAULT '0',
  `Axe` tinyint(4) NOT NULL DEFAULT '0',
  `Two_Handed_Axe` tinyint(4) NOT NULL DEFAULT '0',
  `Club` tinyint(4) NOT NULL DEFAULT '0',
  `Whip` tinyint(4) NOT NULL DEFAULT '0',
  `Stick` tinyint(4) NOT NULL DEFAULT '0',
  `Bow` tinyint(4) NOT NULL DEFAULT '0',
  `Fist` tinyint(4) NOT NULL DEFAULT '0',
  `Musical` tinyint(4) NOT NULL DEFAULT '0',
  `Rod` tinyint(4) NOT NULL DEFAULT '0',
  `Book` tinyint(4) NOT NULL DEFAULT '0',
  `Katar` tinyint(4) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `skill`
--

DROP TABLE IF EXISTS `skill`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `skill` (
  `char_id` int(11) unsigned NOT NULL DEFAULT '0',
  `id` smallint(11) unsigned NOT NULL DEFAULT '0',
  `lv` tinyint(4) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`char_id`,`id`),
  KEY `char_id` (`char_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `skill_db`
--

DROP TABLE IF EXISTS `skill_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `skill_db` (
  `ID` smallint(6) NOT NULL DEFAULT '0',
  `Range` smallint(6) NOT NULL DEFAULT '0',
  `Hit` smallint(6) NOT NULL DEFAULT '0',
  `inf` smallint(6) NOT NULL DEFAULT '0',
  `nk` smallint(6) NOT NULL DEFAULT '0',
  `max` smallint(6) NOT NULL DEFAULT '0',
  `list_num` smallint(6) NOT NULL DEFAULT '0',
  `castcancel` text NOT NULL,
  `cast_defence_rate` smallint(6) NOT NULL DEFAULT '0',
  `inf2` smallint(6) NOT NULL DEFAULT '0',
  `maxcount` smallint(6) NOT NULL DEFAULT '0',
  `skill_type` text NOT NULL,
  `blow_count` smallint(6) NOT NULL DEFAULT '0',
  `Comment` text
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `skill_require_db`
--

DROP TABLE IF EXISTS `skill_require_db`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `skill_require_db` (
  `ID` smallint(6) NOT NULL DEFAULT '0',
  `List_HP` text NOT NULL,
  `List_SP` text NOT NULL,
  `List_HP_Rate` text NOT NULL,
  `List_SP_Rate` text NOT NULL,
  `List_Zeny` text NOT NULL,
  `List_Weapon` text NOT NULL,
  `State` text NOT NULL,
  `Spiritball` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID1` mediumint(9) NOT NULL DEFAULT '0',
  `Amount1` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID2` mediumint(9) NOT NULL DEFAULT '0',
  `Amount2` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID3` mediumint(9) NOT NULL DEFAULT '0',
  `Amount3` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID4` mediumint(9) NOT NULL DEFAULT '0',
  `Amount4` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID5` mediumint(9) NOT NULL DEFAULT '0',
  `Amount5` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID6` mediumint(9) NOT NULL DEFAULT '0',
  `Amount6` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID7` mediumint(9) NOT NULL DEFAULT '0',
  `Amount7` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID8` mediumint(9) NOT NULL DEFAULT '0',
  `Amount8` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID9` mediumint(9) NOT NULL DEFAULT '0',
  `Amount9` tinyint(4) NOT NULL DEFAULT '0',
  `ItemID10` mediumint(9) NOT NULL DEFAULT '0',
  `Amount10` tinyint(4) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `skill_tree`
--

DROP TABLE IF EXISTS `skill_tree`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `skill_tree` (
  `Upper` tinyint(4) NOT NULL DEFAULT '0',
  `JobNo` tinyint(4) NOT NULL DEFAULT '0',
  `Skill_ID` smallint(6) NOT NULL DEFAULT '0',
  `MaxLV` tinyint(4) NOT NULL DEFAULT '0',
  `Skill_ID_Require1` smallint(6) NOT NULL DEFAULT '0',
  `Skill_LV_Require1` tinyint(4) NOT NULL DEFAULT '0',
  `Skill_ID_Require2` smallint(6) NOT NULL DEFAULT '0',
  `Skill_LV_Require2` tinyint(4) NOT NULL DEFAULT '0',
  `Skill_ID_Require3` smallint(6) NOT NULL DEFAULT '0',
  `Skill_LV_Require3` tinyint(4) NOT NULL DEFAULT '0',
  `Skill_ID_Require4` smallint(6) NOT NULL DEFAULT '0',
  `Skill_LV_Require4` tinyint(4) NOT NULL DEFAULT '0',
  `Skill_ID_Require5` smallint(6) NOT NULL DEFAULT '0',
  `Skill_LV_Require5` tinyint(4) NOT NULL DEFAULT '0',
  `Comment` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sstatus`
--

DROP TABLE IF EXISTS `sstatus`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sstatus` (
  `index` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `name` varchar(255) NOT NULL DEFAULT '',
  `user` int(11) unsigned NOT NULL DEFAULT '0'
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `storage`
--

DROP TABLE IF EXISTS `storage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `storage` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `account_id` int(11) unsigned NOT NULL DEFAULT '0',
  `nameid` int(11) unsigned NOT NULL DEFAULT '0',
  `amount` smallint(11) unsigned NOT NULL DEFAULT '0',
  `equip` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `identify` smallint(6) unsigned NOT NULL DEFAULT '0',
  `refine` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `attribute` tinyint(4) unsigned NOT NULL DEFAULT '0',
  `card0` smallint(11) NOT NULL DEFAULT '0',
  `card1` smallint(11) NOT NULL DEFAULT '0',
  `card2` smallint(11) NOT NULL DEFAULT '0',
  `card3` smallint(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `account_id` (`account_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tradelog`
--

DROP TABLE IF EXISTS `tradelog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tradelog` (
  `trade_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `trade_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `src_account_id` int(11) NOT NULL DEFAULT '0',
  `src_char_id` int(11) NOT NULL DEFAULT '0',
  `src_char_name` varchar(30) NOT NULL DEFAULT '',
  `des_account_id` int(11) NOT NULL DEFAULT '0',
  `des_char_id` int(11) NOT NULL DEFAULT '0',
  `des_char_name` varchar(30) NOT NULL DEFAULT '',
  `nameid` int(11) NOT NULL DEFAULT '0',
  `amount` int(11) NOT NULL DEFAULT '1',
  `refine` tinyint(4) NOT NULL DEFAULT '0',
  `card0` int(11) NOT NULL DEFAULT '0',
  `card1` int(11) NOT NULL DEFAULT '0',
  `card2` int(11) NOT NULL DEFAULT '0',
  `card3` int(11) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  `zeny` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`trade_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vendlog`
--

DROP TABLE IF EXISTS `vendlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `vendlog` (
  `vend_id` mediumint(9) unsigned NOT NULL AUTO_INCREMENT,
  `vend_date` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `vend_account_id` int(11) NOT NULL DEFAULT '0',
  `vend_char_id` int(11) NOT NULL DEFAULT '0',
  `vend_char_name` varchar(30) NOT NULL DEFAULT '',
  `buy_account_id` int(11) NOT NULL DEFAULT '0',
  `buy_char_id` int(11) NOT NULL DEFAULT '0',
  `buy_char_name` varchar(30) NOT NULL DEFAULT '',
  `nameid` int(11) NOT NULL DEFAULT '0',
  `amount` int(11) NOT NULL DEFAULT '1',
  `refine` tinyint(4) NOT NULL DEFAULT '0',
  `card0` int(11) NOT NULL DEFAULT '0',
  `card1` int(11) NOT NULL DEFAULT '0',
  `card2` int(11) NOT NULL DEFAULT '0',
  `card3` int(11) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  `zeny` int(11) NOT NULL DEFAULT '0',
  KEY `vend_id` (`vend_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `zenylog`
--

DROP TABLE IF EXISTS `zenylog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zenylog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `time` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `char_id` int(11) NOT NULL DEFAULT '0',
  `src_id` int(11) NOT NULL DEFAULT '0',
  `type` set('M','T','V','S','N','A') NOT NULL DEFAULT 'S',
  `amount` int(11) NOT NULL DEFAULT '0',
  `map` varchar(20) NOT NULL DEFAULT 'prontera.gat',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-11-11 20:43:14
