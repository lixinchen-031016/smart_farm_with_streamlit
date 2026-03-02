/*
 Navicat Premium Dump SQL

 Source Server         : root
 Source Server Type    : MySQL
 Source Server Version : 80042 (8.0.42)
 Source Host           : localhost:3306
 Source Schema         : intelligent_farm

 Target Server Type    : MySQL
 Target Server Version : 80042 (8.0.42)
 File Encoding         : 65001

 Date: 02/03/2026 15:28:21
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for intelligent_farm_airtemperaturehumidity
-- ----------------------------
DROP TABLE IF EXISTS `intelligent_farm_airtemperaturehumidity`;
CREATE TABLE `intelligent_farm_airtemperaturehumidity` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `temperature` double NOT NULL,
  `humidity` double NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_air_temperature_humidity_timestamp` (`timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=209685 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;

-- ----------------------------
-- Table structure for intelligent_farm_light_intensity
-- ----------------------------
DROP TABLE IF EXISTS `intelligent_farm_light_intensity`;
CREATE TABLE `intelligent_farm_light_intensity` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `value` double NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_light_intensity_timestamp` (`timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=209681 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;

-- ----------------------------
-- Table structure for intelligent_farm_soilmoisture
-- ----------------------------
DROP TABLE IF EXISTS `intelligent_farm_soilmoisture`;
CREATE TABLE `intelligent_farm_soilmoisture` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `value` double NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_soil_moisture_timestamp` (`timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=209681 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;

-- ----------------------------
-- Table structure for intelligent_farm_soilnutrient
-- ----------------------------
DROP TABLE IF EXISTS `intelligent_farm_soilnutrient`;
CREATE TABLE `intelligent_farm_soilnutrient` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `value` double NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_soil_nutrient_timestamp` (`timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=209681 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;

-- ----------------------------
-- Table structure for operation_logs
-- ----------------------------
DROP TABLE IF EXISTS `operation_logs`;
CREATE TABLE `operation_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `log_time` datetime NOT NULL,
  `log_level` varchar(10) NOT NULL,
  `username` varchar(50) DEFAULT NULL,
  `action_type` varchar(50) NOT NULL,
  `action_details` text,
  `details_json` json GENERATED ALWAYS AS (json_object(_utf8mb4'time_range',trim(substring_index(substring_index(`action_details`,_utf8mb4'时间范围:',-(1)),_utf8mb4' ',2)),_utf8mb4'filename',nullif(substring_index(substring_index(`action_details`,_utf8mb4'文件名:',-(1)),_utf8mb4' ',1),_utf8mb4''),_utf8mb4'metrics',json_object(_utf8mb4'temperature',nullif(substring_index(substring_index(`action_details`,_utf8mb4'温度:',-(1)),_utf8mb4' ',1),_utf8mb4''),_utf8mb4'humidity',nullif(substring_index(substring_index(`action_details`,_utf8mb4'湿度:',-(1)),_utf8mb4' ',1),_utf8mb4''),_utf8mb4'soil_moisture',nullif(substring_index(substring_index(`action_details`,_utf8mb4'土壤湿度:',-(1)),_utf8mb4' ',1),_utf8mb4'')))) VIRTUAL,
  PRIMARY KEY (`id`,`log_time`),
  KEY `idx_username` (`username`),
  KEY `idx_action_type` (`action_type`)
) ENGINE=InnoDB AUTO_INCREMENT=1567 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
/*!50100 PARTITION BY RANGE (year(`log_time`))
(PARTITION p2022 VALUES LESS THAN (2023) ENGINE = InnoDB,
 PARTITION p2023 VALUES LESS THAN (2024) ENGINE = InnoDB,
 PARTITION p2024 VALUES LESS THAN (2025) ENGINE = InnoDB,
 PARTITION p2025 VALUES LESS THAN (2026) ENGINE = InnoDB,
 PARTITION p_future VALUES LESS THAN MAXVALUE ENGINE = InnoDB) */;

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `last_login_time` timestamp NOT NULL,
  `role` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `admin_request` tinyint(1) NOT NULL,
  `admin_request_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
