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
-- Dumping data for table `pet_db`
--

LOCK TABLES `pet_db` WRITE;
/*!40000 ALTER TABLE `pet_db` DISABLE KEYS */;
/*!40000 ALTER TABLE `pet_db` ENABLE KEYS */;
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
