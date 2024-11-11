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
-- Dumping data for table `mob_db2`
--

LOCK TABLES `mob_db2` WRITE;
/*!40000 ALTER TABLE `mob_db2` DISABLE KEYS */;
/*!40000 ALTER TABLE `mob_db2` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-11-11 18:49:58
