import bcrypt
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import sessionmaker

from models import User
from utils.logger import log_operation
import streamlit as st

def user_management(session, username, role):
    """
    显示用户管理页面，允许管理员添加、编辑和删除用户
    """
    st.title("用户管理")

    # 添加用户
    st.header("添加用户")
    new_username = st.text_input("新用户名", key="new_username")
    new_password = st.text_input("新密码", type="password", key="new_password")
    new_role = st.selectbox("角色", ["user", "admin"], key="new_role")
    if st.button("添加用户"):
        existing_user = session.query(User).filter_by(username=new_username).first()
        if existing_user:
            st.error("用户名已存在")
        else:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            new_user = User(username=new_username, password=hashed_password.decode('utf-8'),
                           last_login_time=datetime.now(), role=new_role)
            session.add(new_user)
            session.commit()
            log_operation(username, 'INFO', "添加用户", f"添加用户 {new_username}")
            st.success("用户添加成功")

    # 用户列表
    st.header("用户列表")
    users = session.query(User).all()
    user_data = [(user.id, user.username, user.role) for user in users]
    df = pd.DataFrame(user_data, columns=['ID', '用户名', '角色'])
    st.dataframe(df)

    # 编辑和删除用户
    user_id = st.number_input("输入要编辑或删除的用户ID", min_value=1, step=1, key="user_id")
    action = st.selectbox("选择操作", ["编辑", "删除"], key="action_selectbox")
    if action == "编辑":
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            new_username = st.text_input("新用户名", value=user.username, key="edit_username")
            new_role = st.selectbox("角色", ["user", "admin"], index=["user", "admin"].index(user.role),
                                   key="edit_role_selectbox")
            if st.button("保存更改"):
                user.username = new_username
                user.role = new_role
                session.commit()
                log_operation(username, "INFO", "编辑用户", f"编辑用户 {user.username}")
                st.success("用户信息已更新")
        else:
            st.error("用户不存在")
    elif action == "删除":
        if st.button("确认删除"):
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                session.delete(user)
                session.commit()
                log_operation(username, 'WARING', "删除用户", f"删除用户 {user.username}")
                st.success("用户已删除")
            else:
                st.error("用户不存在")

    # 修改用户密码功能
    st.header("修改用户密码")
    password_user_id = st.number_input("输入要修改密码的用户ID", min_value=1, step=1, key="password_user_id")
    new_password = st.text_input("新密码", type="password", key="password_new_password")
    confirm_password = st.text_input("确认新密码", type="password", key="password_confirm_password")
    if st.button("修改密码"):
        log_operation(username, "INFO", "用户管理-修改密码",
                     f"修改用户ID: {password_user_id} 的密码")
        user = session.query(User).filter_by(id=password_user_id).first()
        if user:
            if new_password != confirm_password:
                st.error("两次输入的密码不一致")
            else:
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                user.password = hashed_password.decode('utf-8')
                session.commit()
                log_operation(username, 'WARING', "修改用户密码",
                             f"修改用户 {user.username} 的密码")
                st.success("密码修改成功")
        else:
            st.error("用户不存在")