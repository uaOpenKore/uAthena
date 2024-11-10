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
-- Dumping data for table `char`
--

LOCK TABLES `char` WRITE;
/*!40000 ALTER TABLE `char` DISABLE KEYS */;
/*!40000 ALTER TABLE `char` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-11-10 22:36:15
