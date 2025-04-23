import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 加载环境变量
load_dotenv()

# MySQL数据库连接配置
engine = create_engine(os.getenv('DATABASE_URL'))

# 创建会话工厂并初始化session对象
Session = sessionmaker(bind=engine)
session = Session()