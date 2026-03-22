from datetime import datetime

import bcrypt
import pandas as pd
import streamlit as st

from auth import check_password_complexity  # 导入密码复杂度检查函数
from models import User
from utils.logger import log_operation


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
        # 添加密码复杂度检查
        is_complex, msg = check_password_complexity(new_password)
        if not is_complex:
            st.error(msg)
            log_operation(username, "ERROR", "添加用户", f"密码复杂度不足: {msg}")
            return

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

    # 管理员申请审批
    st.header("管理员申请审批")
    pending_admins = session.query(User).filter_by(admin_request=True).all()

    if pending_admins:
        st.subheader("待审批的管理员申请")
        for user in pending_admins:
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"用户名: {user.username}")
            with col2:
                st.write(
                    f"申请时间: {user.admin_request_time.strftime('%Y-%m-%d %H:%M:%S') if user.admin_request_time else 'N/A'}")
            with col3:
                if st.button("批准", key=f"approve_{user.id}"):
                    user.role = 'admin'
                    user.admin_request = False
                    user.admin_request_time = None
                    session.commit()
                    log_operation(username, 'INFO', "管理员审批", f"批准用户 {user.username} 的管理员申请")
                    st.success(f"已批准 {user.username} 的管理员申请")
                    st.rerun()
            with col4:
                if st.button("拒绝", key=f"reject_{user.id}"):
                    user.admin_request = False
                    user.admin_request_time = None
                    session.commit()
                    log_operation(username, 'INFO', "管理员审批", f"拒绝用户 {user.username} 的管理员申请")
                    st.success(f"已拒绝 {user.username} 的管理员申请")
                    st.rerun()
    else:
        st.info("暂无待审批的管理员申请")

    # 用户列表
    st.header("用户列表")
    users = session.query(User).all()
    user_data = [(user.id, user.username, user.role, "是" if user.admin_request else "否") for user in users]
    df = pd.DataFrame(user_data, columns=['ID', '用户名', '角色', '管理员申请中'])
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
                log_operation(username, "WARNING", "编辑用户", f"编辑用户 {user.username}")
                st.success("用户信息已更新")
        else:
            st.error("用户不存在")
    elif action == "删除":
        if st.button("确认删除"):
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                session.delete(user)
                session.commit()
                log_operation(username, 'WARNING', "删除用户", f"删除用户 {user.username}")
                st.success("用户已删除")
            else:
                st.error("用户不存在")

    # 修改用户密码功能
    st.header("修改用户密码")
    password_user_id = st.number_input("输入要修改密码的用户ID", min_value=1, step=1, key="password_user_id")
    new_password = st.text_input("新密码", type="password", key="password_new_password")
    confirm_password = st.text_input("确认新密码", type="password", key="password_confirm_password")
    if st.button("修改密码"):
        # 添加密码复杂度检查
        is_complex, msg = check_password_complexity(new_password)
        if not is_complex:
            st.error(msg)
            log_operation(username, "ERROR", "修改密码", f"密码复杂度不足: {msg}")
            return

        log_operation(username, "WARNING", "用户管理-修改密码",
                      f"修改用户ID: {password_user_id} 的密码")
        user = session.query(User).filter_by(id=password_user_id).first()
        if user:
            if new_password != confirm_password:
                st.error("两次输入的密码不一致")
            else:
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                user.password = hashed_password.decode('utf-8')
                session.commit()
                log_operation(username, 'WARNING', "修改用户密码",
                              f"修改用户 {user.username} 的密码")
                st.success("密码修改成功")
        else:
            st.error("用户不存在")
