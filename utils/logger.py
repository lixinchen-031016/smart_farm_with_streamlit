"""日志管理模块

提供统一的日志记录功能，支持将操作日志记录到数据库，当数据库记录失败时回退到文件日志。

主要功能：
- 记录用户操作到数据库
- 支持不同级别的日志记录
- 数据库记录失败时的文件日志回退机制
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import OperationLog

# 延迟导入以避免循环导入
get_session = None

def _get_get_session():
    """获取get_session函数

    延迟导入get_session函数，避免循环导入问题。

    Returns:
        callable: get_session函数

    Examples:
        >>> session_getter = _get_get_session()
        >>> with session_getter() as session:
        ...     # 使用session进行数据库操作
        ...     pass
    """
    global get_session
    if get_session is None:
        from utils.database import get_session as _get_session
        get_session = _get_session
    return get_session


def log_operation(user, log_level, action, details):
    """记录操作日志到数据库

    将用户操作记录到数据库中，支持不同的日志级别，当数据库记录失败时会回退到文件日志。

    Args:
        user (str): 操作用户名
        log_level (str): 日志级别，如"INFO", "ERROR", "WARNING"等
        action (str): 操作类型，如"数据预测", "用户登录"等
        details (str): 操作详细信息

    Returns:
        None: 无返回值

    Raises:
        Exception: 数据库记录失败时会捕获并回退到文件日志
    """
    try:
        # 使用上下文管理器获取数据库会话
        with _get_get_session()() as session:
            new_log = OperationLog(
                log_time=datetime.now(),
                log_level=log_level.upper(),
                username=user,
                action_type=action,
                action_details=details
            )
            session.add(new_log)
    except Exception as e:
        # 数据库记录失败时回退到文件日志
        fallback_msg = f"[DB_ERROR]{str(e)} - User: {user}, Level: {log_level}, Action: {action}, Details: {details}"
        logging.error(fallback_msg)
        # 同时打印到控制台
        print(f"日志记录失败: {str(e)}")
        print(f"日志内容: [{log_level.upper()}] {user} - {action}: {details}")
