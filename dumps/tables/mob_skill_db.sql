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
-- Dumping data for table `mob_skill_db`
--

LOCK TABLES `mob_skill_db` WRITE;
/*!40000 ALTER TABLE `mob_skill_db` DISABLE KEYS */;
/*!40000 ALTER TABLE `mob_skill_db` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed
