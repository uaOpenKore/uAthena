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
-- Dumping data for table `skill_tree`
--

LOCK TABLES `skill_tree` WRITE;
/*!40000 ALTER TABLE `skill_tree` DISABLE KEYS */;
/*!40000 ALTER TABLE `skill_tree` ENABLE KEYS */;
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
