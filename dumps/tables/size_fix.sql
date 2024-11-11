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
-- Dumping data for table `size_fix`
--

LOCK TABLES `size_fix` WRITE;
/*!40000 ALTER TABLE `size_fix` DISABLE KEYS */;
/*!40000 ALTER TABLE `size_fix` ENABLE KEYS */;
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
