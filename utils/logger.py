import logging
from datetime import datetime

from sqlalchemy.orm import Session

from models import OperationLog
from utils.database import get_session


def log_operation(user, log_level, action, details):
    """记录操作日志到数据库"""
    session: Session = get_session()
    try:
        new_log = OperationLog(
            log_time=datetime.now(),
            log_level=log_level.upper(),
            username=user,
            action_type=action,
            action_details=details
        )
        session.add(new_log)
        session.commit()
    except Exception as e:
        session.rollback()
        # 数据库记录失败时回退到文件日志
        fallback_msg = f"[DB_ERROR]{str(e)} - User: {user}, Level: {log_level}, Action: {action}, Details: {details}"
        logging.error(fallback_msg)
    finally:
        session.close()
