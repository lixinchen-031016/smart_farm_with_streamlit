"""
数据预测模块自动保存功能
提供预测结果的自动保存、历史记录管理和数据导出功能
"""

import json
import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from utils.error_handling import PredictionError, handle_exception
from utils.logger import log_operation


class PredictionSaveManager:
    """预测数据保存管理器 - 单例模式"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """创建单例实例

        实现PredictionSaveManager的单例模式，确保整个应用中只有一个实例。

        Returns:
            PredictionSaveManager: 单例实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化预测保存管理器

        初始化存储目录、数据库和线程池，确保保存功能正常运行。
        由于采用单例模式，只会在首次创建实例时执行初始化。

        Returns:
            None
        """
        if self._initialized:
            return
        
        self._initialized = True
        self.base_dir = Path(__file__).parent.parent
        self.predictions_dir = self.base_dir / 'predictions_exports'
        self.history_db_path = self.predictions_dir / 'prediction_history.db'
        self.max_history_records = 1000  # 最大历史记录数
        self.auto_save_enabled = True
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # 初始化存储目录和数据库
        self._init_storage()
    
    def _init_storage(self):
        """初始化存储目录和数据库

        创建预测导出目录并初始化SQLite历史数据库，确保存储系统正常运行。

        Raises:
            PredictionError: 初始化存储失败时抛出

        Returns:
            None
        """
        try:
            # 创建预测导出目录
            self.predictions_dir.mkdir(parents=True, exist_ok=True)
            
            # 初始化SQLite历史数据库
            self._init_history_db()
            
            log_operation("system", "INFO", "预测保存管理器初始化", 
                         f"存储目录: {self.predictions_dir}")
        except Exception as e:
            log_operation("system", "ERROR", "预测保存管理器初始化失败", str(e))
            raise PredictionError(f"初始化存储失败: {str(e)}")
    
    def _init_history_db(self):
        """初始化历史记录数据库

        创建预测历史表和相关索引，确保数据库结构正确初始化。

        Returns:
            None
        """
        conn = sqlite3.connect(str(self.history_db_path))
        cursor = conn.cursor()
        
        # 创建预测历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id TEXT UNIQUE NOT NULL,
                prediction_type TEXT NOT NULL,
                model_type TEXT NOT NULL,
                prediction_days INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rmse REAL,
                r_squared REAL,
                data_points INTEGER,
                file_path TEXT,
                metadata TEXT,
                status TEXT DEFAULT 'success'
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prediction_time 
            ON prediction_history(created_at)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prediction_type 
            ON prediction_history(prediction_type)
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_prediction_id(self, prediction_type: str) -> str:
        """生成唯一的预测ID

        基于预测类型、时间戳和随机后缀生成唯一的预测ID，确保每个预测结果都有唯一标识。

        Args:
            prediction_type (str): 预测类型

        Returns:
            str: 唯一的预测ID
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = os.urandom(4).hex()
        return f"{prediction_type}_{timestamp}_{random_suffix}"
    
    def save_prediction_result(
        self,
        historical_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        prediction_type: str,
        model_type: str,
        prediction_days: int,
        model_explanation: str = "",
        rmse: float = 0.0,
        r_squared: float = 0.0,
        additional_metrics: Optional[Dict[str, Any]] = None,
        username: str = "system"
    ) -> Dict[str, str]:
        """
        保存预测结果 - 主入口方法
        
        Args:
            historical_data: 历史数据DataFrame
            forecast_data: 预测数据DataFrame
            prediction_type: 预测类型（如"空气温度"、"空气湿度"等）
            model_type: 使用的模型类型
            prediction_days: 预测天数
            model_explanation: 模型说明
            rmse: 均方根误差
            r_squared: 决定系数
            additional_metrics: 额外的评估指标
            username: 用户名
            
        Returns:
            包含保存路径和ID的字典
        """
        if not self.auto_save_enabled:
            return {"status": "skipped", "message": "自动保存已禁用"}
        
        try:
            prediction_id = self._generate_prediction_id(prediction_type)
            timestamp = datetime.now()
            
            # 1. 保存为CSV格式（便于数据分析）
            csv_path = self._save_to_csv(
                historical_data, forecast_data, prediction_id, timestamp
            )
            
            # 2. 保存为Markdown报告（便于阅读）
            md_path = self._save_to_markdown(
                historical_data, forecast_data, prediction_id, timestamp,
                prediction_type, model_type, prediction_days,
                model_explanation, rmse, r_squared, additional_metrics
            )
            
            # 3. 记录到历史数据库
            self._record_to_history(
                prediction_id, prediction_type, model_type, prediction_days,
                rmse, r_squared, len(forecast_data), str(csv_path),
                additional_metrics
            )
            
            # 4. 异步清理旧记录
            self._executor.submit(self._cleanup_old_records)
            
            # 记录操作日志
            log_operation(
                username, "INFO", "预测结果自动保存",
                f"预测ID: {prediction_id}, 类型: {prediction_type}, 模型: {model_type}, "
                f"天数: {prediction_days}, RMSE: {rmse:.4f}"
            )
            
            return {
                "status": "success",
                "prediction_id": prediction_id,
                "csv_path": str(csv_path),
                "markdown_path": str(md_path),
                "timestamp": timestamp.isoformat()
            }
            
        except Exception as e:
            error_info = handle_exception(e, username, "预测结果保存")
            log_operation(username, "ERROR", "预测结果保存失败", str(e))
            return {
                "status": "error",
                "message": str(e),
                "error_code": error_info.get("error_code", "UNKNOWN")
            }
    
    def _save_to_csv(
        self,
        historical_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        prediction_id: str,
        timestamp: datetime
    ) -> Path:
        """保存为CSV格式

        将历史数据和预测数据合并保存为CSV文件，便于后续数据分析和处理。

        Args:
            historical_data (pd.DataFrame): 历史数据DataFrame
            forecast_data (pd.DataFrame): 预测数据DataFrame
            prediction_id (str): 预测ID
            timestamp (datetime): 时间戳

        Returns:
            Path: 保存的CSV文件路径
        """
        filename = f"prediction_{prediction_id}.csv"
        filepath = self.predictions_dir / filename
        
        # 准备历史数据
        hist_df = historical_data.copy()
        hist_df['data_type'] = 'historical'
        if 'timestamp' not in hist_df.columns and hist_df.index.name:
            hist_df = hist_df.reset_index()
        
        # 准备预测数据
        forecast_df = forecast_data.copy()
        forecast_df['data_type'] = 'forecast'
        
        # 合并数据
        combined_df = pd.concat([hist_df, forecast_df], ignore_index=True)
        combined_df['prediction_id'] = prediction_id
        combined_df['created_at'] = timestamp.isoformat()
        
        # 保存为CSV
        combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath
    
    def _save_to_markdown(
        self,
        historical_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        prediction_id: str,
        timestamp: datetime,
        prediction_type: str,
        model_type: str,
        prediction_days: int,
        model_explanation: str,
        rmse: float,
        r_squared: float,
        additional_metrics: Optional[Dict[str, Any]]
    ) -> Path:
        """保存为Markdown报告格式

        生成详细的Markdown格式预测报告，包含基本信息、模型性能指标、数据统计和预测数据预览。

        Args:
            historical_data (pd.DataFrame): 历史数据DataFrame
            forecast_data (pd.DataFrame): 预测数据DataFrame
            prediction_id (str): 预测ID
            timestamp (datetime): 时间戳
            prediction_type (str): 预测类型
            model_type (str): 模型类型
            prediction_days (int): 预测天数
            model_explanation (str): 模型说明
            rmse (float): 均方根误差
            r_squared (float): 决定系数
            additional_metrics (Dict[str, Any], optional): 额外的评估指标

        Returns:
            Path: 保存的Markdown文件路径
        """
        filename = f"prediction_{prediction_id}.md"
        filepath = self.predictions_dir / filename
        
        # 计算统计数据
        hist_values = historical_data.iloc[:, 0] if len(historical_data.columns) > 0 else historical_data
        forecast_values = forecast_data['value'] if 'value' in forecast_data.columns else forecast_data.iloc[:, 0]
        
        md_content = f"""# 📊 农业数据预测报告

## 基本信息

| 项目 | 值 |
|------|-----|
| **预测ID** | `{prediction_id}` |
| **预测类型** | {prediction_type} |
| **模型类型** | {model_type} |
| **预测天数** | {prediction_days} 天 |
| **生成时间** | {timestamp.strftime('%Y-%m-%d %H:%M:%S')} |

## 📈 模型性能指标

| 指标 | 值 | 评级 |
|------|-----|------|
| **RMSE** | {rmse:.4f} | {"优秀 ✅" if rmse < 1.0 else "良好 ✓" if rmse < 2.0 else "中等 ⚠️" if rmse < 3.0 else "需改进 ❌"} |
| **R²** | {r_squared:.4f} | {"优秀 ✅" if r_squared > 0.8 else "良好 ✓" if r_squared > 0.6 else "中等 ⚠️" if r_squared > 0.4 else "需改进 ❌"} |

## 📊 数据统计

### 历史数据
- **数据点数**: {len(historical_data)}
- **均值**: {hist_values.mean():.2f}
- **标准差**: {hist_values.std():.2f}
- **最小值**: {hist_values.min():.2f}
- **最大值**: {hist_values.max():.2f}

### 预测数据
- **数据点数**: {len(forecast_data)}
- **预测均值**: {forecast_values.mean():.2f}
- **预测最小值**: {forecast_values.min():.2f}
- **预测最大值**: {forecast_values.max():.2f}

## 🧠 模型说明

{model_explanation}

## 📋 预测数据预览

### 前5条预测记录

| 时间 | 预测值 |
|------|--------|
"""
        
        # 添加前5条预测数据
        preview_df = forecast_data.head(5)
        for _, row in preview_df.iterrows():
            time_val = row.get('timestamp', row.get('ds', 'N/A'))
            value_val = row.get('value', row.get('yhat', 'N/A'))
            md_content += f"| {time_val} | {value_val:.2f} |\n"
        
        md_content += f"""

## 💾 数据文件

- **CSV格式**: `prediction_{prediction_id}.csv`

---
*本报告由智能农业数据预测系统自动生成*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return filepath
    
    def _record_to_history(
        self,
        prediction_id: str,
        prediction_type: str,
        model_type: str,
        prediction_days: int,
        rmse: float,
        r_squared: float,
        data_points: int,
        file_path: str,
        metadata: Optional[Dict[str, Any]]
    ):
        """记录到历史数据库

        将预测结果记录到SQLite历史数据库，便于后续查询和分析。

        Args:
            prediction_id (str): 预测ID
            prediction_type (str): 预测类型
            model_type (str): 模型类型
            prediction_days (int): 预测天数
            rmse (float): 均方根误差
            r_squared (float): 决定系数
            data_points (int): 数据点数
            file_path (str): 文件路径
            metadata (Dict[str, Any], optional): 额外的元数据

        Returns:
            None
        """
        conn = sqlite3.connect(str(self.history_db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO prediction_history 
            (prediction_id, prediction_type, model_type, prediction_days, 
             rmse, r_squared, data_points, file_path, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            prediction_id, prediction_type, model_type, prediction_days,
            rmse, r_squared, data_points, file_path,
            json.dumps(metadata, ensure_ascii=False) if metadata else None
        ))
        
        conn.commit()
        conn.close()
    
    def _cleanup_old_records(self):
        """清理旧的历史记录

        当历史记录数量超过最大限制时，删除最旧的记录，确保数据库大小合理。

        Returns:
            None
        """
        try:
            conn = sqlite3.connect(str(self.history_db_path))
            cursor = conn.cursor()
            
            # 获取记录总数
            cursor.execute('SELECT COUNT(*) FROM prediction_history')
            count = cursor.fetchone()[0]
            
            if count > self.max_history_records:
                # 删除最旧的记录
                cursor.execute('''
                    DELETE FROM prediction_history 
                    WHERE id IN (
                        SELECT id FROM prediction_history 
                        ORDER BY created_at ASC 
                        LIMIT ?
                    )
                ''', (count - self.max_history_records,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                log_operation("system", "INFO", "历史记录清理", 
                             f"删除了 {deleted_count} 条旧记录")
            
            conn.close()
        except Exception as e:
            log_operation("system", "ERROR", "历史记录清理失败", str(e))
    
    def get_prediction_history(
        self,
        prediction_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取预测历史记录

        从历史数据库中查询预测记录，支持按预测类型、日期范围过滤和限制返回数量。

        Args:
            prediction_type (str, optional): 预测类型，默认为None（获取所有类型）
            start_date (str, optional): 开始日期，默认为None
            end_date (str, optional): 结束日期，默认为None
            limit (int, optional): 返回记录数量限制，默认为100

        Returns:
            List[Dict[str, Any]]: 预测历史记录列表
        """
        conn = sqlite3.connect(str(self.history_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM prediction_history WHERE 1=1'
        params = []
        
        if prediction_type:
            query += ' AND prediction_type = ?'
            params.append(prediction_type)
        
        if start_date:
            query += ' AND created_at >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND created_at <= ?'
            params.append(end_date)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        result = [dict(row) for row in rows]
        conn.close()
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取预测统计信息

        从历史数据库中获取预测统计信息，包括总预测次数、最近7天预测次数和各类型预测统计。

        Returns:
            Dict[str, Any]: 预测统计信息字典，包含总预测次数、最近7天预测次数和各类型预测统计
        """
        conn = sqlite3.connect(str(self.history_db_path))
        cursor = conn.cursor()
        
        # 总预测次数
        cursor.execute('SELECT COUNT(*) FROM prediction_history')
        total_predictions = cursor.fetchone()[0]
        
        # 各类型预测统计
        cursor.execute('''
            SELECT prediction_type, COUNT(*) as count, AVG(rmse) as avg_rmse
            FROM prediction_history
            GROUP BY prediction_type
        ''')
        type_stats = cursor.fetchall()
        
        # 最近7天预测次数
        cursor.execute('''
            SELECT COUNT(*) FROM prediction_history
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        recent_predictions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_predictions": total_predictions,
            "recent_predictions_7d": recent_predictions,
            "by_type": [
                {"type": t[0], "count": t[1], "avg_rmse": t[2]}
                for t in type_stats
            ]
        }


# 全局保存管理器实例
prediction_save_manager = PredictionSaveManager()


def auto_save_prediction(
    historical_data: pd.DataFrame,
    forecast_data: pd.DataFrame,
    prediction_type: str,
    model_type: str,
    prediction_days: int,
    model_explanation: str = "",
    rmse: float = 0.0,
    r_squared: float = 0.0,
    additional_metrics: Optional[Dict[str, Any]] = None,
    username: str = "system"
) -> Dict[str, str]:
    """自动保存预测结果的便捷函数

    将预测结果保存为CSV格式和Markdown报告，并记录到历史数据库中，
    支持异步清理旧记录，确保存储空间合理使用。

    Args:
        historical_data (pd.DataFrame): 历史数据DataFrame
        forecast_data (pd.DataFrame): 预测数据DataFrame
        prediction_type (str): 预测类型（如"空气温度"、"空气湿度"等）
        model_type (str): 使用的模型类型
        prediction_days (int): 预测天数
        model_explanation (str, optional): 模型说明，默认为空字符串
        rmse (float, optional): 均方根误差，默认为0.0
        r_squared (float, optional): 决定系数，默认为0.0
        additional_metrics (Dict[str, Any], optional): 额外的评估指标，默认为None
        username (str, optional): 用户名，默认为"system"

    Returns:
        Dict[str, str]: 包含保存结果的字典，包括状态、预测ID、文件路径等信息

    Examples:
        >>> result = auto_save_prediction(
        ...     historical_data=hist_df,
        ...     forecast_data=forecast_df,
        ...     prediction_type="空气温度",
        ...     model_type="Prophet+SARIMA",
        ...     prediction_days=7,
        ...     model_explanation="模型说明...",
        ...     rmse=0.5,
        ...     r_squared=0.85,
        ...     username="admin"
        ... )
        >>> print(result["status"])
        success
    """
    return prediction_save_manager.save_prediction_result(
        historical_data=historical_data,
        forecast_data=forecast_data,
        prediction_type=prediction_type,
        model_type=model_type,
        prediction_days=prediction_days,
        model_explanation=model_explanation,
        rmse=rmse,
        r_squared=r_squared,
        additional_metrics=additional_metrics,
        username=username
    )


def get_prediction_history(
    prediction_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """获取预测历史记录的便捷函数

    从历史数据库中获取预测记录，支持按预测类型过滤和限制返回数量。

    Args:
        prediction_type (str, optional): 预测类型，默认为None（获取所有类型）
        limit (int, optional): 返回记录数量限制，默认为100

    Returns:
        List[Dict[str, Any]]: 预测历史记录列表，每个元素为包含预测信息的字典
    """
    return prediction_save_manager.get_prediction_history(
        prediction_type=prediction_type,
        limit=limit
    )
