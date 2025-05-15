from datetime import datetime

import bcrypt
from sqlalchemy.orm import sessionmaker

from utils.database import engine  # 导入数据库连接

Session = sessionmaker(bind=engine)
session = Session()

from models import User  # 导入User模型
from utils.logger import log_operation  # 添加: 引入日志记录函数


def login(session, st):
    st.title("登录")
    username = st.text_input("用户名", key="login_username")
    password = st.text_input("密码", type="password", key="login_password")
    user_type = st.radio("选择登录类型", ["用户", "管理员"], index=0)
    if st.button("登录"):
        user = session.query(User).filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.session_state['role'] = user.role
            user.last_login_time = datetime.now()
            session.commit()
            log_operation(username, "用户登录", f"用户 {username} 成功登录")  # 添加: 记录登录日志
            if user.role == 'admin':
                st.query_params.page = "user_management"
            else:
                st.query_params.page = "data_preview"
        else:
            st.error("用户名或密码错误")

    if st.button("注册"):
        st.query_params.page = "register"


def register(session, st):
    st.title("注册")
    username = st.text_input("用户名", key="register_username")
    password = st.text_input("密码", type="password", key="register_password")
    confirm_password = st.text_input("确认密码", type="password", key="confirm_password")
    if st.button("注册"):
        if password != confirm_password:
            st.error("密码不一致")
        else:
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                st.error("用户名已存在")
            else:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                new_user = User(username=username, password=hashed_password.decode('utf-8'),
                                last_login_time=datetime.now())
                session.add(new_user)
                session.commit()
                log_operation(username, "用户注册", f"用户 {username} 注册成功")  # 添加: 记录注册日志
                st.success("注册成功，请登录")
                st.query_params.page = "login"
