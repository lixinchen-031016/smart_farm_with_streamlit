
# 基于Streamlit的智慧大棚数据可视化系统 V1.0

## 目录
1. [简介](#1-简介)
2. [背景](#2-背景)
3. [主要功能](#3-主要功能)
4. [目标用户](#4-目标用户)
5. [运行环境](#5-运行环境)
6. [安装与部署](#6-安装与部署)
7. [使用方法](#7-使用方法)
8. [技术细节](#8-技术细节)
9. [测试结果](#9-测试结果)
10. [贡献者](#10-贡献者)

---

## 1. 简介

本系统是一个基于Streamlit的Web应用程序，旨在为智能农场提供高效的数据管理、分析和可视化平台。通过该工具，用户可以轻松导入、清洗、分析和可视化智能农场的环境数据，同时管理员可以进行用户管理、系统监控、数据备份和恢复等高级操作。

---

## 2. 背景

随着农业现代化的推进，智能农场逐渐成为现代农业的重要组成部分。智能农场通过传感器和物联网技术实时监控环境参数（如空气温度、湿度、土壤湿度和养分等），以优化农业生产。然而，大量的环境数据需要有效的管理和分析工具来支持决策。为此，我们开发了此系统，帮助用户更好地利用这些数据。

---

## 3. 主要功能

### 用户功能：
- **登录与注册**：用户可以通过用户名和密码进行登录或注册新账户。
- **实时数据预览**：展示最新的环境数据，并支持导出数据。
- **数据概览**：上传并查看数据文件的基本信息。
- **数据清洗**：处理数据中的重复行和缺失值。
- **数据分析**：提供描述性统计和相关性分析。
- **数据可视化**：创建各种图表（如散点图、线图、柱状图等）。
- **高级分析**：进行数据分组和聚合分析。

### 管理员功能：
- **用户管理**：添加、编辑和删除用户。
- **系统监控**：监控服务器资源使用情况。
- **数据备份与恢复**：备份和恢复数据库中的数据。

---

## 4. 目标用户

- **普通用户**：农场工作人员和技术人员，负责日常的数据查看和分析。
- **管理员**：系统管理员，负责用户管理、系统监控、数据备份和恢复等高级操作。

---

## 5. 运行环境

### 系统硬件环境
- CPU：建议使用多核处理器（如Intel i5或以上）。
- 内存：Windows环境下至少8GB RAM，推荐16GB或以上；Linux环境下至少4GB RAM，推荐8GB或以上。
- 存储：至少40GB SSD，用于存储操作系统和应用数据。
- 网络：稳定且高速的互联网连接，建议带宽不低于10Mbps。

### 系统软件环境
- 操作系统：Windows 10/11, macOS, 或 Linux（推荐Ubuntu 20.04及以上版本）
- 编程语言：Python 3.8及以上版本
- 依赖库：
    - Streamlit
    - Pandas
    - Plotly
    - SQLAlchemy
    - bcrypt
    - psutil
- 数据库：MySQL 8.0及以上版本
- 运行平台：本地Docker环境或云服务器（如AWS、Azure、阿里云）中Docker环境

---

## 6. 安装与部署

### 步骤 1：安装必要工具
在云服务器中安装以下工具：
```bash
sudo apt-get update && sudo apt-get install docker.io
sudo apt update && sudo apt install git
```

### 步骤 2：拉取项目代码
使用Git命令将项目代码拉取下来：
```bash
git clone -b login-register_data-visualization_without_random_data_inside --single-branch https://github.com/lixinchen-031016/smart_farm_with_streamlit.git
```

### 步骤 3：进入项目目录
进入拉取下来的项目文件夹：
```bash
cd smart_farm_with_streamlit
```

### 步骤 4：启动服务
在包含 `docker-compose.yml` 文件的目录下执行以下命令：
```bash
docker-compose up
```

### 步骤 5：配置镜像源（如有网络问题）
如果存在网络问题，修改镜像源配置文件：
```bash
sudo mkdir -p /etc/docker
sudo vim /etc/docker/daemon.json
```
在文件中添加以下内容：
```json
{
    "registry-mirrors": [
      "https://0vmzj3q6.mirror.aliyuncs.com",
      "https://docker.m.daocloud.io",
      "https://mirror.baidubce.com",
      "https://dockerproxy.com",
      "https://mirror.iscas.ac.cn",
      "https://huecker.io",
      "https://dockerhub.timeweb.cloud",
      "https://noohub.ru",
      "https://vlgh0kqj.mirror.aliyuncs.com",
      "http://hub-mirror.c.163.com",
      "https://docker.nju.edu.cn",
      "https://docker.mirrors.sjtug.sjtu.edu.cn",
      "https://mirror.ccs.tencentyun.com"
    ]
}
```
保存后重启Docker服务：
```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 步骤 6：初始化数据库
进入数据库容器并运行SQL脚本或使用Navicat连接数据库

运行 `intelligent_farm.sql` 脚本完成数据库初始化。

---

## 7. 使用方法

### 登录与注册
1. 打开应用首页。
2. 输入用户名和密码进行登录。
3. 如果是新用户，请点击“注册”按钮，填写用户名和密码完成注册。

### 功能操作
详见各章节功能描述及操作步骤。

---

## 8. 技术细节

### 文件结构
- `app.py`：主程序文件，包含所有功能模块和页面逻辑。
- 依赖库：
    - `bcrypt`：用于密码加密和验证。
    - `pandas`：用于数据处理和分析。
    - `plotly`：用于数据可视化。
    - `psutil`：用于系统监控。
    - `sqlalchemy`：用于数据库操作。
    - `streamlit`：用于构建Web应用程序。

### 数据库模型
- `AirTemperatureHumidity`：存储空气温度和湿度数据。
- `SoilMoisture`：存储土壤湿度数据。
- `SoilNutrient`：存储土壤养分数据。
- `User`：存储用户信息（用户名、密码、角色等）。

### 架构设计
- 前端：基于Streamlit构建，提供用户友好的界面。
- 后端：使用SQLAlchemy连接MySQL数据库，进行数据的增删改查操作。
- 安全：用户密码通过bcrypt进行加密存储，确保用户信息安全。

---

## 9. 测试结果

### 单元测试
- 登录与注册：测试用户登录和注册功能，确保密码加密和验证正确。
- 数据导入与导出：测试不同格式的数据文件导入和导出功能。
- 数据清洗：测试数据清洗功能，确保重复行删除和缺失值处理正确。
- 数据分析与可视化：测试数据分析和可视化功能，确保图表生成正确。

### 集成测试
- 用户管理：测试管理员添加、编辑和删除用户的功能。
- 系统监控：测试服务器资源监控功能，确保数据准确。
- 数据备份与恢复：测试数据备份和恢复功能，确保数据完整性和一致性。

---

## 10. 贡献者

感谢所有为本项目做出贡献的开发者和测试人员！

---

如果您有任何问题或建议，请随时联系我们！