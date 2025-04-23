from datetime import datetime

import bcrypt
import pandas as pd
import streamlit as st
from sqlalchemy.orm import sessionmaker
from models import User  # 导入User模型
from utils.database import engine  # 导入数据库连接

Session = sessionmaker(bind=engine)
session = Session()

# from sqlalchemy.orm import sessionmaker
# from models import User
# from utils.database import engine
# Session = sessionmaker(bind=engine)
# session = Session()

# 添加: 引入新的数据库模块
from utils.database import get_session

# 替换: 使用get_session()方法获取会话对象
session = get_session()

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
            if user.role == 'admin':
                st.experimental_set_query_params(page="user_management")
            else:
                st.experimental_set_query_params(page="data_preview")
        else:
            st.error("用户名或密码错误")
    
    if st.button("注册"):
        st.experimental_set_query_params(page="register")

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
                new_user = User(username=username, password=hashed_password.decode('utf-8'), last_login_time=datetime.now())
                session.add(new_user)
                session.commit()
                st.success("注册成功，请登录")
                st.experimental_set_query_params(page="login")

def user_management():
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    st.title("用户管理")

    # 添加用户
    st.header("添加用户")
    new_username = st.text_input("新用户名", key="new_username")
    new_password = st.text_input("新密码", type="password", key="new_password")
    new_role = st.selectbox("角色", ["user", "admin"])
    if st.button("添加用户"):
        existing_user = session.query(User).filter_by(username=new_username).first()
        if existing_user:
            st.error("用户名已存在")
        else:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            new_user = User(username=new_username, password=hashed_password.decode('utf-8'), last_login_time=datetime.now(), role=new_role)
            session.add(new_user)
            session.commit()
            st.success("用户添加成功")

    # 用户列表
    st.header("用户列表")
    users = session.query(User).all()
    user_data = [(user.id, user.username, user.role) for user in users]
    df = pd.DataFrame(user_data, columns=['ID', '用户名', '角色'])
    st.dataframe(df)

    # 编辑和删除用户
    user_id = st.number_input("输入要编辑或删除的用户ID", min_value=1, step=1, key="user_id")
    action = st.selectbox("选择操作", ["编辑", "删除"])
    if action == "编辑":
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            new_username = st.text_input("新用户名", value=user.username, key="edit_username")
            new_password = st.text_input("新密码", type="password", key="edit_password")
            new_role = st.selectbox("角色", ["uesr", "admin"], index=["user", "admin"].index(user.role))
            if st.button("保存更改"):
                user.username = new_username
                if new_password:
                    user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                user.role = new_role
                session.commit()
                st.success("用户信息已更新")
        else:
            st.error("用户不存在")
    elif action == "删除":
        if st.button("确认删除"):
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                session.delete(user)
                session.commit()
                st.success("用户已删除")
            else:
                st.error("用户不存在")
