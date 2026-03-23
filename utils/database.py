import os
import time
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# 加载环境变量
load_dotenv()

# 数据库连接配置
DATABASE_CONFIG = {
    'url': os.getenv('DATABASE_URL'),
    'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
    'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '10')),
    'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
    'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
    'echo': os.getenv('DB_ECHO', 'False').lower() == 'true'
}

# 创建引擎时添加异常处理和重试机制
def create_db_engine():
    """创建数据库引擎，带重试机制"""
    retry_count = 3
    retry_delay = 2
    
    for i in range(retry_count):
        try:
            engine = create_engine(
                DATABASE_CONFIG['url'],
                pool_size=DATABASE_CONFIG['pool_size'],
                max_overflow=DATABASE_CONFIG['max_overflow'],
                pool_timeout=DATABASE_CONFIG['pool_timeout'],
                pool_recycle=DATABASE_CONFIG['pool_recycle'],
                echo=DATABASE_CONFIG['echo']
            )
            # 测试连接
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            print(f"数据库连接失败 (尝试 {i+1}/{retry_count}): {str(e)}")
            if i < retry_count - 1:
                time.sleep(retry_delay)
            else:
                return None

# 创建引擎
engine = create_db_engine()

# 创建会话工厂，设置expire_on_commit=False，避免会话提交后对象过期
Session = sessionmaker(bind=engine, expire_on_commit=False) if engine else None


from utils.error_handling import DatabaseError

@contextmanager
def get_session():
    """
    数据库会话上下文管理器
    
    用法:
        with get_session() as session:
            # 数据库操作
    """
    if not engine:
        raise DatabaseError("数据库连接未初始化")
    
    session = None
    try:
        session = Session()
        yield session
        session.commit()
    except SQLAlchemyError as e:
        if session:
            session.rollback()
        raise DatabaseError(f"数据库操作失败: {str(e)}")
    finally:
        if session:
            try:
                session.close()
            except:
                pass

def safe_db_operation(func):
    """
    数据库操作安全装饰器
    
    Args:
        func: 数据库操作函数
    
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        with get_session() as session:
            return func(session, *args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
