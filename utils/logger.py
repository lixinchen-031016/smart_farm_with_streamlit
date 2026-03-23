import logging
from datetime import datetime

from sqlalchemy.orm import Session

from models import OperationLog

# 延迟导入以避免循环导入
get_session = None

def _get_get_session():
    """获取get_session函数"""
    global get_session
    if get_session is None:
        from utils.database import get_session as _get_session
        get_session = _get_session
    return get_session


def log_operation(user, log_level, action, details):
    """记录操作日志到数据库"""
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
