-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: wareflow_db
-- ------------------------------------------------------
-- Server version	5.7.44-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `batch_stages`
--

DROP TABLE IF EXISTS `batch_stages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `batch_stages` (
  `stage_id` int(11) NOT NULL AUTO_INCREMENT,
  `batch_id` varchar(50) DEFAULT NULL,
  `stage_name` varchar(100) NOT NULL,
  `target_hours` decimal(5,2) NOT NULL,
  `target_qty` int(11) DEFAULT '0',
  `actual_hours` decimal(5,2) DEFAULT '0.00',
  `start_timestamp` timestamp NULL DEFAULT NULL,
  `end_timestamp` timestamp NULL DEFAULT NULL,
  `delayed_by` decimal(5,2) DEFAULT '0.00',
  `status` varchar(50) DEFAULT 'In Progress',
  PRIMARY KEY (`stage_id`),
  KEY `batch_id` (`batch_id`),
  CONSTRAINT `batch_stages_ibfk_1` FOREIGN KEY (`batch_id`) REFERENCES `production_batches` (`batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `batch_stages`
--

LOCK TABLES `batch_stages` WRITE;
/*!40000 ALTER TABLE `batch_stages` DISABLE KEYS */;
/*!40000 ALTER TABLE `batch_stages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `component_consumption`
--

DROP TABLE IF EXISTS `component_consumption`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `component_consumption` (
  `consumption_id` int(11) NOT NULL AUTO_INCREMENT,
  `batch_id` varchar(50) DEFAULT NULL,
  `component_id` varchar(50) DEFAULT NULL,
  `stage_name` varchar(100) DEFAULT NULL,
  `qty_used` int(11) NOT NULL,
  `status` enum('Active','Inactive') DEFAULT 'Active',
  `consumed_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`consumption_id`),
  KEY `component_id` (`component_id`),
  KEY `batch_id` (`batch_id`),
  CONSTRAINT `component_consumption_ibfk_1` FOREIGN KEY (`component_id`) REFERENCES `components` (`component_id`),
  CONSTRAINT `component_consumption_ibfk_2` FOREIGN KEY (`batch_id`) REFERENCES `production_batches` (`batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `component_consumption`
--

LOCK TABLES `component_consumption` WRITE;
/*!40000 ALTER TABLE `component_consumption` DISABLE KEYS */;
/*!40000 ALTER TABLE `component_consumption` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `components`
--

DROP TABLE IF EXISTS `components`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `components` (
  `component_id` varchar(50) NOT NULL,
  `part_name` varchar(100) NOT NULL,
  `description` text,
  `warehouse_stock` int(11) DEFAULT '0',
  `floor_stock` int(11) DEFAULT '0',
  `min_threshold` int(11) NOT NULL,
  PRIMARY KEY (`component_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `components`
--

LOCK TABLES `components` WRITE;
/*!40000 ALTER TABLE `components` DISABLE KEYS */;
/*!40000 ALTER TABLE `components` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `demand_predictions`
--

DROP TABLE IF EXISTS `demand_predictions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `demand_predictions` (
  `forecast_id` int(11) NOT NULL AUTO_INCREMENT,
  `product_id` varchar(50) DEFAULT NULL,
  `predicted_demand_qty` int(11) NOT NULL,
  `forecast_period_start` date NOT NULL,
  `forecast_period_end` date NOT NULL,
  `generated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`forecast_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `demand_predictions_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `demand_predictions`
--

LOCK TABLES `demand_predictions` WRITE;
/*!40000 ALTER TABLE `demand_predictions` DISABLE KEYS */;
/*!40000 ALTER TABLE `demand_predictions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `finished_goods`
--

DROP TABLE IF EXISTS `finished_goods`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `finished_goods` (
  `finished_good_id` varchar(50) NOT NULL,
  `batch_id` varchar(50) DEFAULT NULL,
  `product_id` varchar(50) DEFAULT NULL,
  `generation_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `qc_status` varchar(20) DEFAULT 'Pending QC',
  PRIMARY KEY (`finished_good_id`),
  KEY `batch_id` (`batch_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `finished_goods_ibfk_1` FOREIGN KEY (`batch_id`) REFERENCES `production_batches` (`batch_id`),
  CONSTRAINT `finished_goods_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `finished_goods`
--

LOCK TABLES `finished_goods` WRITE;
/*!40000 ALTER TABLE `finished_goods` DISABLE KEYS */;
/*!40000 ALTER TABLE `finished_goods` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `junction_of_materials`
--

DROP TABLE IF EXISTS `junction_of_materials`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `junction_of_materials` (
  `jom_id` int(11) NOT NULL AUTO_INCREMENT,
  `product_id` varchar(50) NOT NULL,
  `component_id` varchar(50) NOT NULL,
  `quantity_required` int(11) NOT NULL,
  PRIMARY KEY (`jom_id`),
  KEY `product_id` (`product_id`),
  KEY `component_id` (`component_id`),
  CONSTRAINT `junction_of_materials_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`) ON DELETE CASCADE,
  CONSTRAINT `junction_of_materials_ibfk_2` FOREIGN KEY (`component_id`) REFERENCES `components` (`component_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `junction_of_materials`
--

LOCK TABLES `junction_of_materials` WRITE;
/*!40000 ALTER TABLE `junction_of_materials` DISABLE KEYS */;
/*!40000 ALTER TABLE `junction_of_materials` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `material_requests`
--

DROP TABLE IF EXISTS `material_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `material_requests` (
  `request_id` int(11) NOT NULL AUTO_INCREMENT,
  `component_id` varchar(50) DEFAULT NULL,
  `requested_qty` int(11) NOT NULL,
  `status` varchar(20) DEFAULT 'Pending',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `batch_id` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`request_id`),
  KEY `component_id` (`component_id`),
  KEY `batch_id` (`batch_id`),
  CONSTRAINT `material_requests_ibfk_1` FOREIGN KEY (`component_id`) REFERENCES `components` (`component_id`),
  CONSTRAINT `material_requests_ibfk_2` FOREIGN KEY (`batch_id`) REFERENCES `production_batches` (`batch_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `material_requests`
--

LOCK TABLES `material_requests` WRITE;
/*!40000 ALTER TABLE `material_requests` DISABLE KEYS */;
/*!40000 ALTER TABLE `material_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `material_transfers`
--

DROP TABLE IF EXISTS `material_transfers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `material_transfers` (
  `transfer_id` int(11) NOT NULL AUTO_INCREMENT,
  `component_id` varchar(50) DEFAULT NULL,
  `dispatched_qty` int(11) NOT NULL,
  `transfer_status` varchar(20) DEFAULT 'In Transit',
  `dispatched_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `received_at` timestamp NULL DEFAULT NULL,
  `batch_id` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`transfer_id`),
  KEY `component_id` (`component_id`),
  KEY `batch_id` (`batch_id`),
  CONSTRAINT `material_transfers_ibfk_1` FOREIGN KEY (`component_id`) REFERENCES `components` (`component_id`),
  CONSTRAINT `material_transfers_ibfk_2` FOREIGN KEY (`batch_id`) REFERENCES `production_batches` (`batch_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `material_transfers`
--

LOCK TABLES `material_transfers` WRITE;
/*!40000 ALTER TABLE `material_transfers` DISABLE KEYS */;
/*!40000 ALTER TABLE `material_transfers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `production_batches`
--

DROP TABLE IF EXISTS `production_batches`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `production_batches` (
  `batch_id` varchar(50) NOT NULL,
  `product_id` varchar(50) NOT NULL,
  `target_qty` int(11) NOT NULL,
  `completed_qty` int(11) DEFAULT '0',
  `status` varchar(50) DEFAULT 'Initialized',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`batch_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `production_batches_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `production_batches`
--

LOCK TABLES `production_batches` WRITE;
/*!40000 ALTER TABLE `production_batches` DISABLE KEYS */;
/*!40000 ALTER TABLE `production_batches` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `products`
--

DROP TABLE IF EXISTS `products`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `products` (
  `product_id` varchar(50) NOT NULL,
  `product_name` varchar(100) NOT NULL,
  `description` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `products`
--

LOCK TABLES `products` WRITE;
/*!40000 ALTER TABLE `products` DISABLE KEYS */;
/*!40000 ALTER TABLE `products` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `quality_check`
--

DROP TABLE IF EXISTS `quality_check`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `quality_check` (
  `inspection_id` int(11) NOT NULL AUTO_INCREMENT,
  `inspection_type` enum('Raw Material', 'Finished Good') NOT NULL,
  `component_id` varchar(50) DEFAULT NULL,
  `finished_good_id` varchar(50) DEFAULT NULL,
  `batch_id` varchar(50) DEFAULT NULL,
  `qty_checked` int(11) NOT NULL,
  `result` varchar(10) NOT NULL,
  `checking_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`inspection_id`),
  KEY `component_id` (`component_id`),
  KEY `finished_good_id` (`finished_good_id`),
  KEY `batch_id` (`batch_id`),
  CONSTRAINT `quality_check_ibfk_1` FOREIGN KEY (`component_id`) REFERENCES `components` (`component_id`),
  CONSTRAINT `quality_check_ibfk_2` FOREIGN KEY (`finished_good_id`) REFERENCES `finished_goods` (`finished_good_id`) ON DELETE CASCADE,
  CONSTRAINT `quality_check_ibfk_3` FOREIGN KEY (`batch_id`) REFERENCES `production_batches` (`batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `quality_check`
--

LOCK TABLES `quality_check` WRITE;
/*!40000 ALTER TABLE `quality_check` DISABLE KEYS */;
/*!40000 ALTER TABLE `quality_check` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `user_role` enum('Supervisor','Inventory Inspector','Worker') NOT NULL,
  `full_name` varchar(100) DEFAULT NULL,
  `username` varchar(50) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `phone_number` varchar(20) DEFAULT NULL,
  `department` varchar(100) DEFAULT NULL,
  `email_verified` tinyint(1) DEFAULT '0',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `Email_Verification`
--

DROP TABLE IF EXISTS `Email_Verification`;
CREATE TABLE `Email_Verification` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `otp` varchar(6) NOT NULL,
  `expiry_time` timestamp NOT NULL,
  `purpose` enum('Registration','Password Reset') NOT NULL,
  `payload` text,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Table structure for table `Product_Workflow`
--

DROP TABLE IF EXISTS `Product_Workflow`;
CREATE TABLE `Product_Workflow` (
  `product_id` varchar(50) NOT NULL,
  `stage_name` varchar(100) NOT NULL,
  `sequence_order` int(11) NOT NULL,
  PRIMARY KEY (`product_id`,`sequence_order`),
  UNIQUE KEY `uk_product_stage` (`product_id`,`stage_name`),
  CONSTRAINT `fk_product_workflow_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-16 21:57:45
