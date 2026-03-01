DROP TABLE IF EXISTS `custom_mail`;
CREATE TABLE `custom_mail` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `sender_name` VARCHAR(32) NOT NULL,
  `dest_id` INT NOT NULL,
  `zeny` INT DEFAULT 0,
  `id1` INT DEFAULT 0, `am1` INT DEFAULT 0,
  `id2` INT DEFAULT 0, `am2` INT DEFAULT 0,
  `id3` INT DEFAULT 0, `am3` INT DEFAULT 0
) ENGINE=MyISAM;
