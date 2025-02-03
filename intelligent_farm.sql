/*
 Navicat Premium Data Transfer

 Source Server         : root
 Source Server Type    : MySQL
 Source Server Version : 80300
 Source Host           : localhost:3306
 Source Schema         : intelligent_farm

 Target Server Type    : MySQL
 Target Server Version : 80300
 File Encoding         : 65001

 Date: 27/01/2025 14:22:00
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for intelligent_farm_airtemperaturehumidity
-- ----------------------------
DROP TABLE IF EXISTS `intelligent_farm_airtemperaturehumidity`;
CREATE TABLE `intelligent_farm_airtemperaturehumidity`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `temperature` double NOT NULL,
  `humidity` double NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 97 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of intelligent_farm_airtemperaturehumidity
-- ----------------------------
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (1, 22.3, 45, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (2, 23.1, 47.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (3, 22.3, 45, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (4, 23.1, 47.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (5, 21.9, 46, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (6, 22.7, 48.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (7, 22.3, 45, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (8, 23.1, 47.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (9, 21.9, 46, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (10, 22.7, 48.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (11, 23.5, 50, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (12, 24.3, 52.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (13, 25.1, 51, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (14, 25.9, 53.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (15, 26.7, 52, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (16, 27.5, 54.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (17, 28.3, 53, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (18, 29.1, 55.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (19, 29.9, 54, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (20, 30.7, 56.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (21, 31.5, 55, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (22, 32.3, 57.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (23, 33.1, 56, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (24, 33.9, 58.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (25, 34.7, 57, '2023-10-01 13:30:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (26, 35.5, 59.5, '2023-10-01 13:35:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (27, 22.3, 45, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (28, 23.1, 47.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (29, 21.9, 46, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (30, 22.7, 48.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (31, 23.5, 50, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (32, 24.3, 52.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (33, 25.1, 51, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (34, 25.9, 53.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (35, 26.7, 52, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (36, 27.5, 54.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (37, 28.3, 53, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (38, 29.1, 55.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (39, 29.9, 54, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (40, 30.7, 56.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (41, 31.5, 55, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (42, 32.3, 57.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (43, 33.1, 56, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (44, 33.9, 58.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (45, 34.7, 57, '2023-10-01 13:30:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (46, 35.5, 59.5, '2023-10-01 13:35:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (47, 22.3, 45, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (48, 23.1, 47.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (49, 21.9, 46, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (50, 22.7, 48.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (51, 23.5, 50, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (52, 24.3, 52.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (53, 25.1, 51, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (54, 25.9, 53.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (55, 26.7, 52, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (56, 27.5, 54.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (57, 28.3, 53, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (58, 29.1, 55.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (59, 29.9, 54, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (60, 30.7, 56.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (61, 31.5, 55, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (62, 32.3, 57.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (63, 33.1, 56, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (64, 33.9, 58.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (65, 34.7, 57, '2023-10-01 13:30:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (66, 35.5, 59.5, '2023-10-01 13:35:00');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (67, 17.92, 48.82, '2025-01-24 16:36:09');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (68, 25.95, 61.33, '2025-01-24 16:36:14');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (69, 34.39, 34.81, '2025-01-24 16:36:19');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (70, 15.99, 47.31, '2025-01-24 16:36:24');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (71, 34.39, 48.78, '2025-01-24 16:36:29');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (72, 24.03, 60.03, '2025-01-24 16:36:34');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (73, 28.8, 43.63, '2025-01-24 16:39:37');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (74, 28.41, 54.35, '2025-01-24 16:39:42');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (75, 23.41, 30.11, '2025-01-24 16:39:47');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (76, 28.93, 53.97, '2025-01-24 16:39:52');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (77, 30.41, 47.87, '2025-01-24 16:39:57');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (78, 31.81, 39.34, '2025-01-24 16:40:02');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (79, 31.35, 39.58, '2025-01-24 16:40:07');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (80, 27.28, 52.14, '2025-01-24 16:40:12');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (81, 30.18, 54.39, '2025-01-24 16:40:17');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (82, 17.4, 48.35, '2025-01-24 16:40:22');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (83, 21.58, 66.67, '2025-01-24 16:40:27');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (84, 24.21, 30.94, '2025-01-24 16:40:32');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (85, 34.41, 38.3, '2025-01-24 16:40:37');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (86, 34.95, 50, '2025-01-24 16:40:42');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (87, 26.67, 67.11, '2025-01-24 16:40:47');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (88, 20.45, 52.75, '2025-01-24 16:40:52');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (89, 25.49, 44.93, '2025-01-24 16:40:57');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (90, 20.14, 44.38, '2025-01-24 16:41:02');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (91, 28.04, 43.53, '2025-01-24 16:41:07');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (92, 30.64, 55.6, '2025-01-25 20:34:03');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (93, 15.76, 48.88, '2025-01-25 20:34:08');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (94, 24.03, 64.94, '2025-01-25 20:34:13');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (95, 34.8, 60.45, '2025-01-25 20:34:18');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (96, 28.52, 43.63, '2025-01-25 20:34:23');
INSERT INTO `intelligent_farm_airtemperaturehumidity` VALUES (97, 22.21, 42.44, '2025-01-25 20:35:07');

-- ----------------------------
-- Table structure for intelligent_farm_soilmoisture
-- ----------------------------
DROP TABLE IF EXISTS `intelligent_farm_soilmoisture`;
CREATE TABLE `intelligent_farm_soilmoisture`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `value` double NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 97 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of intelligent_farm_soilmoisture
-- ----------------------------
INSERT INTO `intelligent_farm_soilmoisture` VALUES (1, 30.5, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (2, 32, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (3, 30.5, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (4, 32, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (5, 35, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (6, 33.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (7, 30.5, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (8, 32, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (9, 35, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (10, 33.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (11, 34, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (12, 36.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (13, 37, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (14, 38.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (15, 39, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (16, 40.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (17, 41, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (18, 42.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (19, 43, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (20, 44.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (21, 45, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (22, 46.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (23, 47, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (24, 48.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (25, 49, '2023-10-01 13:30:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (26, 50.5, '2023-10-01 13:35:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (27, 30.5, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (28, 32, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (29, 35, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (30, 33.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (31, 34, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (32, 36.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (33, 37, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (34, 38.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (35, 39, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (36, 40.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (37, 41, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (38, 42.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (39, 43, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (40, 44.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (41, 45, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (42, 46.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (43, 47, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (44, 48.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (45, 49, '2023-10-01 13:30:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (46, 50.5, '2023-10-01 13:35:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (47, 30.5, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (48, 32, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (49, 35, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (50, 33.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (51, 34, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (52, 36.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (53, 37, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (54, 38.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (55, 39, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (56, 40.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (57, 41, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (58, 42.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (59, 43, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (60, 44.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (61, 45, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (62, 46.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (63, 47, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (64, 48.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (65, 49, '2023-10-01 13:30:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (66, 50.5, '2023-10-01 13:35:00');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (67, 70.7, '2025-01-24 16:36:09');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (68, 46.56, '2025-01-24 16:36:14');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (69, 56.22, '2025-01-24 16:36:19');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (70, 54.51, '2025-01-24 16:36:24');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (71, 32.75, '2025-01-24 16:36:29');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (72, 55.49, '2025-01-24 16:36:34');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (73, 56.27, '2025-01-24 16:39:37');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (74, 77.56, '2025-01-24 16:39:42');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (75, 29.54, '2025-01-24 16:39:47');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (76, 75.21, '2025-01-24 16:39:52');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (77, 43.06, '2025-01-24 16:39:57');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (78, 20.64, '2025-01-24 16:40:02');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (79, 37.61, '2025-01-24 16:40:07');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (80, 72.98, '2025-01-24 16:40:12');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (81, 72.95, '2025-01-24 16:40:17');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (82, 26.42, '2025-01-24 16:40:22');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (83, 52.98, '2025-01-24 16:40:27');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (84, 76.79, '2025-01-24 16:40:32');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (85, 21.96, '2025-01-24 16:40:37');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (86, 23.57, '2025-01-24 16:40:42');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (87, 49.04, '2025-01-24 16:40:47');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (88, 33.35, '2025-01-24 16:40:52');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (89, 78.8, '2025-01-24 16:40:57');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (90, 61.99, '2025-01-24 16:41:02');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (91, 39.72, '2025-01-24 16:41:07');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (92, 57.28, '2025-01-25 20:34:03');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (93, 20.84, '2025-01-25 20:34:08');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (94, 67.62, '2025-01-25 20:34:13');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (95, 60.59, '2025-01-25 20:34:18');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (96, 57.12, '2025-01-25 20:34:23');
INSERT INTO `intelligent_farm_soilmoisture` VALUES (97, 42.48, '2025-01-25 20:35:07');

-- ----------------------------
-- Table structure for intelligent_farm_soilnutrient
-- ----------------------------
DROP TABLE IF EXISTS `intelligent_farm_soilnutrient`;
CREATE TABLE `intelligent_farm_soilnutrient`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `value` double NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 97 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of intelligent_farm_soilnutrient
-- ----------------------------
INSERT INTO `intelligent_farm_soilnutrient` VALUES (1, 120, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (2, 118.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (3, 120, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (4, 118.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (5, 119, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (6, 117.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (7, 120, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (8, 118.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (9, 119, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (10, 117.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (11, 116, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (12, 114.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (13, 113, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (14, 111.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (15, 110, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (16, 108.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (17, 107, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (18, 105.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (19, 104, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (20, 102.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (21, 101, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (22, 99.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (23, 98, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (24, 96.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (25, 95, '2023-10-01 13:30:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (26, 93.5, '2023-10-01 13:35:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (27, 120, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (28, 118.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (29, 119, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (30, 117.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (31, 116, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (32, 114.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (33, 113, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (34, 111.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (35, 110, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (36, 108.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (37, 107, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (38, 105.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (39, 104, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (40, 102.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (41, 101, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (42, 99.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (43, 98, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (44, 96.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (45, 95, '2023-10-01 13:30:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (46, 93.5, '2023-10-01 13:40:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (47, 120, '2023-10-01 12:00:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (48, 118.5, '2023-10-01 12:05:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (49, 119, '2023-10-01 12:10:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (50, 117.5, '2023-10-01 12:15:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (51, 116, '2023-10-01 12:20:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (52, 114.5, '2023-10-01 12:25:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (53, 113, '2023-10-01 12:30:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (54, 111.5, '2023-10-01 12:35:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (55, 110, '2023-10-01 12:40:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (56, 108.5, '2023-10-01 12:45:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (57, 107, '2023-10-01 12:50:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (58, 105.5, '2023-10-01 12:55:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (59, 104, '2023-10-01 13:00:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (60, 102.5, '2023-10-01 13:05:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (61, 101, '2023-10-01 13:10:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (62, 99.5, '2023-10-01 13:15:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (63, 98, '2023-10-01 13:20:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (64, 96.5, '2023-10-01 13:25:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (65, 95, '2023-10-01 13:45:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (66, 93.5, '2023-10-01 13:40:00');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (67, 1.89, '2025-01-24 16:36:09');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (68, 1.95, '2025-01-24 16:36:14');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (69, 4.78, '2025-01-24 16:36:19');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (70, 3.44, '2025-01-24 16:36:24');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (71, 4.75, '2025-01-24 16:36:29');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (72, 2.08, '2025-01-24 16:36:34');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (73, 3.84, '2025-01-24 16:39:37');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (74, 3.09, '2025-01-24 16:39:42');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (75, 4.26, '2025-01-24 16:39:47');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (76, 3.76, '2025-01-24 16:39:52');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (77, 1.11, '2025-01-24 16:39:57');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (78, 2.22, '2025-01-24 16:40:02');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (79, 1.37, '2025-01-24 16:40:07');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (80, 3.38, '2025-01-24 16:40:12');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (81, 1.96, '2025-01-24 16:40:17');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (82, 4.59, '2025-01-24 16:40:22');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (83, 2.43, '2025-01-24 16:40:27');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (84, 4.61, '2025-01-24 16:40:32');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (85, 1.99, '2025-01-24 16:40:37');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (86, 1.85, '2025-01-24 16:40:42');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (87, 3.4, '2025-01-24 16:40:47');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (88, 1.45, '2025-01-24 16:40:52');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (89, 2.69, '2025-01-24 16:40:57');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (90, 1.81, '2025-01-24 16:41:02');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (91, 4.75, '2025-01-24 16:41:07');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (92, 3.51, '2025-01-25 20:34:03');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (93, 3.62, '2025-01-25 20:34:08');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (94, 4.43, '2025-01-25 20:34:13');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (95, 1.68, '2025-01-25 20:34:18');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (96, 1.74, '2025-01-25 20:34:23');
INSERT INTO `intelligent_farm_soilnutrient` VALUES (97, 1.06, '2025-01-25 20:35:07');

SET FOREIGN_KEY_CHECKS = 1;
