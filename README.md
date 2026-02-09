# 基于Streamlit的智慧大棚数据可视化系统

## 目录
1. [简介](#1-简介)
2. [背景](#2-背景)
3. [主要功能](#3-主要功能)
4. [目标用户](#4-目标用户)
5. [运行环境](#5-运行环境)
6. [安装与部署](#6-安装与部署)
7. [使用方法](#7-使用方法)
8. [技术细节](#8-技术细节)
9. [贡献者](#9-贡献者)

---

## 1. 简介

本系统是一个基于Streamlit的Web应用程序，旨在为智能农场提供高效的数据管理、分析和可视化平台。通过该工具，用户可以轻松导入、清洗、分析和可视化智能农场的环境数据，同时管理员可以进行用户管理、系统监控、数据备份和恢复等高级操作。

---

## 2. 背景

随着农业现代化的推进，智能农场逐渐成为现代农业的重要组成部分。智能农场通过传感器和物联网技术实时监控环境参数（如空气温度、湿度、土壤湿度和养分等），以优化农业生产。然而，大量的环境数据需要有效的管理和分析工具来支持决策。为此，我们开发了此系统，帮助用户更好地利用这些数据。

---

## 3. 主要功能

### 用户功能：
- **综合监控仪表板**：综合展示农场环境数据和系统状态，提供一站式数据查看体验。
- **实时数据预览**：展示最新的环境数据，并支持导出数据。
- **数据概览**：上传并查看数据文件的基本信息。
- **数据清洗**：处理数据中的重复行和缺失值，支持多格式数据导出。
- **数据分析**：提供描述性统计和相关性分析。
- **数据可视化**：支持9种图表类型和JSON格式图表导出。
- **高级分析**：进行数据分组和聚合分析。
- **本地数据预测**：支持多种预测模型（SARIMA/LSTM/Transformer/Prophet），进行7-30天数据预测，可视化预测趋势。
- **机器学习模型**：对环境数据进行机器学习模型训练和预测，并支持模型预测。
- **自动化决策**：基于传感器数据的自动决策和建议系统，根据预设规则生成环境调控建议。
- **数据库同步**：支持本地和云端数据库之间的数据同步。
- **使用说明**：完整的系统使用说明书，包含所有功能的操作指南。

### 管理员功能：
- **用户管理**：支持密码修改、角色分配、密码重置，以及管理员申请审批。
- **系统监控**：CPU/内存/磁盘使用率可视化，日志可视化。
- **数据备份与恢复**：AES-256加密备份，支持按时间范围增量备份；支持加密备份文件+密钥文件双重验证恢复。
- **日志查看**：查看和下载操作日志。
- **调试信息**：在调试模式下可查看系统环境信息、资源监控、数据库状态、性能分析等详细信息。
- **模块配置管理**：动态启用/禁用系统功能模块，自定义系统功能和权限。

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
- 编程语言：Python 3.11及以上版本
- 依赖库：
    - Streamlit 1.45.1
    - Pandas 2.2.3
    - PyTorch 2.7.1
    - Plotly 5.24.1
    - SQLAlchemy 2.0.41
    - bcrypt 4.3.0
    - psutil 7.0.0
    - numpy 1.26.4
    - matplotlib 3.10.3
    - scipy 1.14.1
    - statsmodels 0.14.4
    - scikit-learn 1.6.1
    - cryptography 45.0.2
    - openpyxl 3.1.5
    - PyMySQL 1.1.1
    - APScheduler 3.11.0
    - PyArrow 18.1.0
    - joblib 1.4.2
    - prophet 1.1.7
    - streamlit-extras 0.7.1
    - streamlit-option-menu 0.4.0
    - python-jose (PyJWT 2.10.1)
    - python-dotenv 1.1.0
    - 以及requirements.txt中列出的其他依赖项
- 数据库：MySQL 8.0及以上版本
- 运行平台：本地Docker环境或云服务器（如AWS、Azure、阿里云）中Docker环境

---

## 6. 安装与部署（Linux环境下的Docker容器部署）
### 步骤 1：安装必要工具
在云服务器中安装以下工具：
```
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

### 步骤 4：环境变量配置
- 在项目根目录创建.env文件并配置以下参数：
```ini
# 数据库连接信息  
DATABASE_URL=mysql+pymysql://root:0000@db/intelligent_farm
#  应用安全配置
SECRET_KEY=031016
```


### 步骤 5：启动服务
在包含 [docker-compose.yml]文件的目录下执行以下命令：
```bash
docker-compose up
```

### 步骤 6：配置镜像源（如有网络问题）
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

### 步骤 7：初始化数据库
进入数据库容器并运行SQL脚本或使用Navicat连接数据库

运行 `intelligent_farm.sql` 脚本完成数据库初始化。

---

## 7. 使用方法

### 登录与注册
1. 打开应用首页。
2. 输入用户名和密码进行登录。
3. 如果是新用户，请点击"注册"按钮，填写用户名和密码完成注册。
4. 注册时可选择身份类型（普通用户或管理员），若选择管理员需等待审批。

### 功能操作
#### 数据管理
1. **综合监控仪表板**：登录后默认进入综合监控仪表板页面，可查看最新的环境数据指标和系统状态。
2. **实时数据预览**：查看最新的环境数据指标。
3. **数据概览**：可选择从数据库读取数据或上传CSV/Excel/JSON文件进行分析。
4. **数据清洗**：处理数据中的重复行、缺失值，可删除不需要的列并进行交互式数据编辑。
5. **数据分析**：提供描述性统计和相关性分析功能。
6. **高级分析**：支持数据分组和聚合分析。

#### 数据可视化
1. 选择数据可视化功能。
2. 选择时间范围筛选数据。
3. 选择图表类型（散点图/线图/柱状图/箱线图/直方图/饼图/热力图）。
4. 配置相应的参数进行可视化展示。

#### 预测分析
1. 进入本地数据预测功能。
2. 选择要预测的数据类型（空气温度/湿度、土壤湿度等）。
3. 选择预测模型（SARIMA/LSTM/Transformer/Prophet）。
4. 设置预测天数（1-30天）。
5. 查看预测结果和模型说明。

#### 机器学习
1. 进入机器学习功能。
2. 选择目标变量和特征列。
3. 选择模型类型（分类或回归）。
4. 训练模型并进行预测。

#### 自动化决策
1. 进入自动化决策功能。
2. 点击"评估当前环境条件"按钮。
3. 系统将根据预设规则和历史趋势分析生成环境调控建议。

#### 模块配置管理（仅管理员）
1. 进入模块配置管理功能。
2. 查看所有功能模块的状态（启用/禁用）。
3. 根据需要启用或禁用特定功能模块。
4. 可设置模块权限（所有用户/仅管理员）。
5. 系统将自动处理模块间的依赖关系。

#### 系统管理（仅管理员）
1. **用户管理**：添加、编辑、删除用户，修改用户密码，审批管理员申请。
2. **系统监控**：查看服务器资源使用情况，获取性能优化建议。
3. **日志查看**：查看和下载操作日志。
4. **数据备份**：按时间范围备份数据。
5. **数据恢复**：使用备份文件和密钥恢复数据。
6. **调试信息**：在调试模式下查看系统详细信息。

---

## 8. 技术细节

### 文件结构
- `app.py`：主程序文件，包含所有功能模块和页面逻辑。
- `models.py`：数据库模型定义文件。
- `utils`：工具函数定义文件夹，包含各功能模块的实现。
- `requirements.txt`：依赖库列表文件。
- `docker-compose.yml`：Docker容器配置文件。
- `.env`：环境变量配置文件。
- `Dockerfile`：Docker镜像构建文件。
- `README.md`：项目文档。
- `auth.py`: 用户认证模块。
- `data_gen.py`: 数据生成模块。
- `clear_tables.py`：清空数据库表模块。
- `module_config.json`：模块配置文件，定义系统功能模块的启用状态和依赖关系。
- 各工具模块文件：
    - `utils/analysis.py`：数据分析工具
    - `utils/backup.py`：数据备份工具
    - `utils/database.py`：数据库连接工具
    - `utils/data_operations.py`：数据操作工具
    - `utils/data_preview.py`：数据预览工具
    - `utils/debug_utils.py`：调试工具
    - `utils/decision_engine.py`：自动化决策引擎
    - `utils/instruction_manual.py`：使用说明文档
    - `utils/log_viewer.py`：日志查看工具
    - `utils/logger.py`：日志记录工具
    - `utils/machine_learning.py`：机器学习工具
    - `utils/module_manager.py`：模块管理工具
    - `utils/module_config_ui.py`：模块配置管理UI
    - `utils/predictions.py`：预测分析工具
    - `utils/restore.py`：数据恢复工具
    - `utils/system_monitoring.py`：系统监控工具
    - `utils/user_management.py`：用户管理工具
    - `utils/visualization.py`：数据可视化工具

### 数据库模型
- `AirTemperatureHumidity`：存储空气温度和湿度数据。
- `SoilMoisture`：存储土壤湿度数据。
- `SoilNutrient`：存储土壤养分数据。
- `LightIntensity`：存储光照强度数据。
- `User`：存储用户信息（用户名、密码、角色等）。
- `OperationLog`: 存储用户操作日志。

### 架构设计
- 前端：基于Streamlit构建，提供用户友好的界面。
- 后端：使用SQLAlchemy连接MySQL数据库，进行数据的增删改查操作。
- 安全：采用bcrypt密码哈希加密+JWT令牌认证，确保用户信息安全。
- 操作审计表：记录用户关键操作日志
- 模块化设计：通过模块管理系统实现功能的动态启用/禁用
- 延迟加载：使用延迟导入机制提高应用启动性能

### 模块管理系统
系统采用模块化设计，通过[module_config.json](file:///Users/lixinchen/PycharmProjects/smart_farm_with_streamlit/module_config.json)文件管理各个功能模块的启用状态和依赖关系。每个模块可以独立启用或禁用，系统会自动处理模块间的依赖关系，确保系统稳定运行。

模块分类包括：
- 核心功能
- 数据处理
- 数据分析
- 预测分析
- 系统管理
- 数据管理
- 智能分析
- 帮助

### 核心技术组件

#### 1. 综合监控仪表板
提供一体化的监控界面，整合了实时数据展示和系统状态监控，让用户能够快速了解当前农场环境和系统运行情况。

#### 2. 自动化决策引擎
基于传感器数据和历史趋势分析，系统可以自动生成环境调控建议：
- 土壤湿度管理建议（灌溉控制）
- 温度调控建议（保温/降温）
- 湿度调节建议（增湿/除湿）
- 光照强度优化建议（补光）
- 结合历史趋势分析，提供更精准的决策建议

#### 3. 预测分析系统
支持多种预测模型：
- SARIMA模型：适用于时间序列数据预测
- LSTM神经网络：深度学习模型，适用于复杂时间序列预测
- Prophet模型：Facebook开发的时间序列预测模型
- Transformer模型：基于注意力机制的预测模型


#### 4. 机器学习平台
提供完整的机器学习工作流：
- 支持分类和回归任务
- 多种算法选择（随机森林、SVM、线性回归等）
- 模型训练和评估功能
- 模型对比功能，帮助选择最佳模型

#### 5. 系统监控与性能优化
实时监控系统资源使用情况：
- CPU使用率监控
- 内存使用情况分析
- 磁盘空间监控
- 性能优化建议生成
- 模块启用情况分析

#### 6. 数据安全与备份
- 数据加密备份（AES-256）
- 按时间范围增量备份
- 加密备份文件+密钥文件双重验证恢复
- 数据库同步功能

---

## 9. 贡献者

---
感谢所有为本项目做出贡献的开发者和测试人员！
- [XinChen Li](https://github.com/lixinchen-031016)
---

如果您有任何问题或建议，请随时联系我们！