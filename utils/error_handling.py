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
    """获取log_operation函数

    延迟导入log_operation函数以避免循环导入。

    Returns:
        function: log_operation函数

    Examples:
        >>> log_op = _get_log_operation()
        >>> log_op("admin", "INFO", "测试", "测试日志")
    """
    global log_operation
    if log_operation is None:
        from utils.logger import log_operation as _log_operation
        log_operation = _log_operation
    return log_operation


class SmartFarmError(Exception):
    """智能农场系统基础异常类

    智能农场系统的基础异常类，所有其他异常类都继承自此类。

    Attributes:
        message (str): 异常消息
        error_code (str): 错误代码
        severity (str): 严重程度
        timestamp (datetime): 异常发生时间

    Examples:
        >>> raise SmartFarmError("测试异常", "TEST_ERROR", "WARNING")
    """
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR", severity: str = "ERROR"):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.timestamp = datetime.now()
        super().__init__(self.message)


class DatabaseError(SmartFarmError):
    """数据库相关异常

    数据库操作相关的异常，如连接失败、查询错误等。

    Examples:
        >>> raise DatabaseError("数据库连接失败")
    """
    def __init__(self, message: str, error_code: str = "DATABASE_ERROR"):
        super().__init__(message, error_code, "ERROR")


class AuthenticationError(SmartFarmError):
    """认证相关异常

    认证操作相关的异常，如登录失败、权限不足等。

    Examples:
        >>> raise AuthenticationError("登录失败")
    """
    def __init__(self, message: str, error_code: str = "AUTH_ERROR"):
        super().__init__(message, error_code, "WARNING")


class DataProcessingError(SmartFarmError):
    """数据处理相关异常

    数据处理操作相关的异常，如数据格式错误、处理失败等。

    Examples:
        >>> raise DataProcessingError("数据格式错误")
    """
    def __init__(self, message: str, error_code: str = "DATA_PROCESSING_ERROR"):
        super().__init__(message, error_code, "ERROR")


class PredictionError(SmartFarmError):
    """预测相关异常

    预测操作相关的异常，如模型训练失败、预测计算错误等。

    Examples:
        >>> raise PredictionError("预测模型训练失败")
    """
    def __init__(self, message: str, error_code: str = "PREDICTION_ERROR"):
        super().__init__(message, error_code, "ERROR")


class ModuleError(SmartFarmError):
    """模块相关异常

    模块操作相关的异常，如模块加载失败、依赖缺失等。

    Examples:
        >>> raise ModuleError("模块加载失败")
    """
    def __init__(self, message: str, error_code: str = "MODULE_ERROR"):
        super().__init__(message, error_code, "WARNING")


def handle_exception(e: Exception, username: Optional[str] = None, operation: str = "未知操作") -> Dict[str, Any]:
    """统一处理异常

    统一处理异常，包括异常类型判断、日志记录和异常信息构建。

    Args:
        e (Exception): 异常对象
        username (str, optional): 用户名，默认为None
        operation (str, optional): 操作名称，默认为"未知操作"

    Returns:
        Dict[str, Any]: 异常信息字典，包含错误类型、错误代码、消息、严重程度、时间戳和堆栈信息

    Examples:
        >>> try:
        ...     1 / 0
        ... except Exception as e:
        ...     error_info = handle_exception(e, "admin", "测试操作")
        ...     print(error_info["message"])
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
    """显示错误信息

    根据异常信息的严重程度，在 Streamlit 界面上显示相应的错误消息。

    Args:
        error_info (Dict[str, Any]): 异常信息字典，包含错误类型、错误代码、消息、严重程度等信息
        show_details (bool, optional): 是否显示详细错误信息，默认为 False

    Examples:
        >>> error_info = {"severity": "ERROR", "message": "测试错误", "traceback": "..."}
        >>> display_error(error_info, show_details=True)
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
    """异常处理装饰器

    为函数添加异常处理能力，捕获并处理执行过程中的所有异常。

    Args:
        func (callable): 要装饰的函数

    Returns:
        callable: 装饰后的函数，具有异常处理能力

    Examples:
        >>> @exception_handler
        ... def risky_operation():
        ...     1 / 0
        ...
        >>> risky_operation()  # 会捕获异常并显示错误信息
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
    """安全执行函数，捕获并处理异常

    安全执行指定的函数，捕获并处理执行过程中的所有异常。

    Args:
        func (callable): 要执行的函数
        *args: 函数位置参数
        **kwargs: 函数关键字参数

    Returns:
        Any: 函数返回值或 None（如果发生异常）

    Examples:
        >>> def risky_operation():
        ...     1 / 0
        ...
        >>> result = safe_execute(risky_operation)
        >>> print(result)  # 输出: None
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
