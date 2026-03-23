"""
全局异常处理模块
提供统一的异常处理机制，包括异常捕获、日志记录和用户友好的错误提示
"""

import traceback
from datetime import datetime
from typing import Optional, Dict, Any

import streamlit as st

# 延迟导入以避免循环导入
log_operation = None

def _get_log_operation():
    """获取log_operation函数"""
    global log_operation
    if log_operation is None:
        from utils.logger import log_operation as _log_operation
        log_operation = _log_operation
    return log_operation


class SmartFarmError(Exception):
    """智能农场系统基础异常类"""
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR", severity: str = "ERROR"):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.timestamp = datetime.now()
        super().__init__(self.message)


class DatabaseError(SmartFarmError):
    """数据库相关异常"""
    def __init__(self, message: str, error_code: str = "DATABASE_ERROR"):
        super().__init__(message, error_code, "ERROR")


class AuthenticationError(SmartFarmError):
    """认证相关异常"""
    def __init__(self, message: str, error_code: str = "AUTH_ERROR"):
        super().__init__(message, error_code, "WARNING")


class DataProcessingError(SmartFarmError):
    """数据处理相关异常"""
    def __init__(self, message: str, error_code: str = "DATA_PROCESSING_ERROR"):
        super().__init__(message, error_code, "ERROR")


class PredictionError(SmartFarmError):
    """预测相关异常"""
    def __init__(self, message: str, error_code: str = "PREDICTION_ERROR"):
        super().__init__(message, error_code, "ERROR")


class ModuleError(SmartFarmError):
    """模块相关异常"""
    def __init__(self, message: str, error_code: str = "MODULE_ERROR"):
        super().__init__(message, error_code, "WARNING")


def handle_exception(e: Exception, username: Optional[str] = None, operation: str = "未知操作") -> Dict[str, Any]:
    """
    统一处理异常
    
    Args:
        e: 异常对象
        username: 用户名
        operation: 操作名称
    
    Returns:
        异常信息字典
    """
    # 确定异常类型和严重程度
    if isinstance(e, SmartFarmError):
        error_type = e.__class__.__name__
        error_code = e.error_code
        severity = e.severity
        message = e.message
    else:
        error_type = type(e).__name__
        error_code = "UNEXPECTED_ERROR"
        severity = "ERROR"
        message = str(e)
    
    # 获取详细的异常堆栈
    error_traceback = traceback.format_exc()
    
    # 记录异常日志
    try:
        _get_log_operation()(
            username or "system",
            severity,
            f"异常处理 - {operation}",
            f"{error_type}: {message}\n{error_traceback}"
        )
    except Exception as log_error:
        # 如果日志记录失败，打印到控制台
        print(f"日志记录失败: {str(log_error)}")
        print(f"异常信息: [{severity}] {error_type}: {message}")
    
    # 构建异常信息字典
    error_info = {
        "error_type": error_type,
        "error_code": error_code,
        "message": message,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "traceback": error_traceback
    }
    
    return error_info


def display_error(error_info: Dict[str, Any], show_details: bool = False):
    """
    显示错误信息
    
    Args:
        error_info: 异常信息字典
        show_details: 是否显示详细信息
    """
    # 根据严重程度显示不同的消息类型
    if error_info["severity"] == "ERROR":
        st.error(f"❌ {error_info['message']}")
    elif error_info["severity"] == "WARNING":
        st.warning(f"⚠️ {error_info['message']}")
    else:
        st.info(f"ℹ️ {error_info['message']}")
    
    # 显示详细信息（如果需要）
    if show_details:
        with st.expander("查看详细错误信息"):
            st.code(error_info["traceback"])


def exception_handler(func):
    """
    异常处理装饰器
    
    Args:
        func: 要装饰的函数
    
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 获取用户名（如果在session_state中）
            username = st.session_state.get('username', 'unknown')
            # 获取操作名称
            operation = func.__name__
            # 处理异常
            error_info = handle_exception(e, username, operation)
            # 显示错误信息
            display_error(error_info, show_details=True)
            return None
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def safe_execute(func, *args, **kwargs):
    """
    安全执行函数，捕获并处理异常
    
    Args:
        func: 要执行的函数
        *args: 函数参数
        **kwargs: 函数关键字参数
    
    Returns:
        函数返回值或None（如果发生异常）
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        # 获取用户名（如果在session_state中）
        username = st.session_state.get('username', 'unknown')
        # 获取操作名称
        operation = func.__name__ if hasattr(func, '__name__') else 'unknown'
        # 处理异常
        error_info = handle_exception(e, username, operation)
        # 显示错误信息
        display_error(error_info)
        return None
