-- --------------------------------------------------------
-- Verkkotietokone:              127.0.0.1
-- Palvelinversio:               11.4.2-MariaDB - mariadb.org binary distribution
-- Server OS:                    Win64
-- HeidiSQL Versio:              12.6.0.6765
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Dumping database structure for discord
CREATE DATABASE IF NOT EXISTS `discord` /*!40100 DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci */;
USE `discord`;

-- Dumping structure for taulu discord.applies
CREATE TABLE IF NOT EXISTS `applies` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `discord` varchar(50) NOT NULL,
  `message` varchar(50) NOT NULL,
  `votes` varchar(255) NOT NULL DEFAULT '{}',
  `enddate` datetime DEFAULT NULL,
  `status` varchar(50) DEFAULT 'inprogress',
  `waitdate` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=109 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Tietojen vientiä ei oltu valittu.

-- Dumping structure for taulu discord.registered_users
CREATE TABLE IF NOT EXISTS `registered_users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `discord` varchar(255) NOT NULL,
  `status` enum('admins','allowlisted','processing','none') NOT NULL DEFAULT 'none',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=103 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Tietojen vientiä ei oltu valittu.

-- Dumping structure for taulu discord.settings
CREATE TABLE IF NOT EXISTS `settings` (
  `name` varchar(50) DEFAULT NULL,
  `value` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Tietojen vientiä ei oltu valittu.

-- Dumping structure for taulu discord.tickets
CREATE TABLE IF NOT EXISTS `tickets` (
  `channel` varchar(255) DEFAULT NULL,
  `user` varchar(255) DEFAULT NULL,
  `isActive` set('yes','no') DEFAULT 'yes'
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Tietojen vientiä ei oltu valittu.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
