-- MySQL dump 9.11
--
-- Host: localhost    Database: tp
-- ------------------------------------------------------
-- Server version	4.0.20-log

DROP DATABASE tp;
CREATE DATABASE tp;
USE tp;

--
-- Table structure for table `board`
--

DROP TABLE IF EXISTS `board`;
CREATE TABLE `board` (
  `id` bigint(20) NOT NULL default '0',
  `name` tinyblob NOT NULL,
  `desc` blob NOT NULL,
  PRIMARY KEY  (`id`)
) TYPE=InnoDB;

--
-- Dumping data for table `board`
--

--
-- Table structure for table `message`
--

DROP TABLE IF EXISTS `message`;
CREATE TABLE `message` (
  `id` bigint(20) NOT NULL auto_increment,
  `bid` bigint(20) NOT NULL default '0',
  `slot` bigint(20) NOT NULL default '0',
  `subject` tinyblob NOT NULL,
  `body` blob NOT NULL,
  PRIMARY KEY  (`id`)
) TYPE=InnoDB;

--
-- Dumping data for table `message`
--


--
-- Table structure for table `object`
--

DROP TABLE IF EXISTS `object`;
CREATE TABLE `object` (
  `id` bigint(20) NOT NULL auto_increment,
  `type` varchar(255) NOT NULL default '',
  `name` tinyblob NOT NULL,
  `size` bigint(20) NOT NULL default '0',
  `posx` bigint(20) NOT NULL default '0',
  `posy` bigint(20) NOT NULL default '0',
  `posz` bigint(20) NOT NULL default '0',
  `velx` bigint(20) NOT NULL default '0',
  `vely` bigint(20) NOT NULL default '0',
  `velz` bigint(20) NOT NULL default '0',
  `parent` bigint(20) NOT NULL default '-1',
  `extra` blob NOT NULL,
  PRIMARY KEY  (`id`)
) TYPE=InnoDB;

--
-- Dumping data for table `object`
--

INSERT INTO `object` VALUES (-1,'sobjects.Universe','The Universe',100000000000,0,0,0,0,0,0,-1,'(dp0\nS\'turn\'\np1\nI0\ns.');
INSERT INTO `object` VALUES (1,'sobjects.Galaxy','The Milky Way',10000000000,0,0,-6000,0,0,1000,0,'(dp0\n.');

--
-- Table structure for table `order`
--

DROP TABLE IF EXISTS `order`;
CREATE TABLE `order` (
  `id` bigint(20) NOT NULL auto_increment,
  `type` varchar(255) NOT NULL default '',
  `oid` bigint(20) NOT NULL default '0',
  `slot` bigint(20) NOT NULL default '0',
  `worked` bigint(20) NOT NULL default '0',
  `extra` blob NOT NULL,
  PRIMARY KEY  (`id`)
) TYPE=InnoDB;

--
-- Dumping data for table `order`
--

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint(20) NOT NULL auto_increment,
  `username` tinyblob NOT NULL,
  `password` tinyblob NOT NULL,
  PRIMARY KEY  (`id`)
) TYPE=InnoDB;

--
-- Dumping data for table `user`
--

INSERT INTO `user` VALUES (1,'admin@tp','adminpassword');

UPDATE object SET id = 0 WHERE name='The Universe';
