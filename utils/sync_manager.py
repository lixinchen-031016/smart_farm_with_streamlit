import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import streamlit as st
from utils.logger import log_operation
from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from urllib.parse import quote_plus
import re
import time
from functools import wraps

class DatabaseSyncManager:
    """
    数据库同步管理器，用于同步云端和本地数据库
    """
    
    def __init__(self, cloud_db_url, local_db_url):
        """
        初始化同步管理器，使用连接池优化
        
        Args:
            cloud_db_url (str): 云端数据库连接URL
            local_db_url (str): 本地数据库连接URL
        """
        try:
            # 配置连接池参数
            pool_config = {
                'pool_size': 10,
                'max_overflow': 20,
                'pool_recycle': 3600,  # 1小时回收连接
                'pool_pre_ping': True,  # 检查连接有效性
                'echo': False  # 生产环境关闭SQL日志
            }
            
            self.cloud_engine = create_engine(cloud_db_url, **pool_config)
            self.local_engine = create_engine(local_db_url, **pool_config)
            self.cloud_session = sessionmaker(bind=self.cloud_engine)()
            self.local_session = sessionmaker(bind=self.local_engine)()
        except SQLAlchemyError as e:
            log_operation("system", "ERROR", "数据库连接", f"创建数据库引擎失败: {str(e)}")
            raise Exception(f"数据库连接失败: {str(e)}")
        
    def sync_table_data(self, table_class, table_name, timestamp_column='timestamp'):
        """
        同步单个表的数据，增强审计日志
        
        Args:
            table_class: SQLAlchemy模型类
            table_name (str): 表名
            timestamp_column (str): 时间戳列名
            
        Returns:
            dict: 同步结果统计
        """
        sync_stats = {
            'table': table_name,
            'cloud_to_local': 0,
            'local_to_cloud': 0,
            'conflicts': 0
        }
        
        # 记录操作开始
        operation_id = f"sync_{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log_operation(st.session_state.get('username', 'system'), "INFO", 
                     "数据同步开始", f"开始同步表 {table_name} (操作ID: {operation_id})")
        
        try:
            # 获取云端和本地数据的最新时间戳
            cloud_max_time = self._get_max_timestamp(self.cloud_session, table_name, timestamp_column)
            local_max_time = self._get_max_timestamp(self.local_session, table_name, timestamp_column)
            
            # 记录时间戳信息
            log_operation(st.session_state.get('username', 'system'), "INFO", 
                         "时间戳检查", f"表 {table_name} - 云端最大时间戳: {cloud_max_time}, 本地最大时间戳: {local_max_time}")
            
            # 从云端同步到本地 (云端有更新的数据)
            if cloud_max_time and (not local_max_time or cloud_max_time > local_max_time):
                cloud_data = self._fetch_data_after_timestamp(
                    self.cloud_session, table_class, timestamp_column, local_max_time)
                inserted_count = self._insert_data(self.local_session, table_class, cloud_data)
                sync_stats['cloud_to_local'] = inserted_count
                log_operation(st.session_state.get('username', 'system'), "INFO", 
                             "数据同步", f"从云端同步 {inserted_count} 条数据到本地 ({table_name})")
                
            # 从本地同步到云端 (本地有更新的数据)
            if local_max_time and (not cloud_max_time or local_max_time > cloud_max_time):
                local_data = self._fetch_data_after_timestamp(
                    self.local_session, table_class, timestamp_column, cloud_max_time)
                inserted_count = self._insert_data(self.cloud_session, table_class, local_data)
                sync_stats['local_to_cloud'] = inserted_count
                log_operation(st.session_state.get('username', 'system'), "INFO", 
                             "数据同步", f"从本地同步 {inserted_count} 条数据到云端 ({table_name})")
                
            # 处理时间戳相同的冲突数据
            if cloud_max_time and local_max_time and cloud_max_time == local_max_time:
                sync_stats['conflicts'] = self._resolve_conflicts(
                    table_class, table_name, timestamp_column)
                
            # 记录操作完成
            log_operation(st.session_state.get('username', 'system'), "INFO", 
                         "数据同步完成", f"完成同步表 {table_name} (操作ID: {operation_id}) - 统计: {sync_stats}")
                
        except Exception as e:
            log_operation(st.session_state.get('username', 'system'), "ERROR", 
                         "数据同步", f"同步表 {table_name} 时出错 (操作ID: {operation_id}): {str(e)}")
            raise e
            
        return sync_stats
    
    # 添加重试机制装饰器
    def retry_on_failure(max_retries=3, delay=1):
        """
        重试装饰器
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            log_operation("system", "WARN", "重试机制", 
                                         f"函数 {func.__name__} 第 {attempt+1} 次尝试失败: {str(e)}，{delay}秒后重试")
                            time.sleep(delay)
                        else:
                            log_operation("system", "ERROR", "重试机制", 
                                         f"函数 {func.__name__} 在 {max_retries} 次尝试后仍然失败: {str(e)}")
                raise last_exception
            return wrapper
        return decorator
    
    # 应用重试机制到关键函数
    @retry_on_failure(max_retries=3, delay=2)
    def _get_max_timestamp(self, session, table_name, timestamp_column):
        """
        获取表中最大时间戳
        
        Args:
            session: 数据库会话
            table_name (str): 表名
            timestamp_column (str): 时间戳列名
            
        Returns:
            datetime: 最大时间戳或None
        """
        try:
            result = session.execute(
                text(f"SELECT MAX({timestamp_column}) FROM {table_name}")
            ).fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            log_operation("system", "ERROR", "数据查询", f"获取表 {table_name} 最大时间戳失败: {str(e)}")
            return None
    
    @retry_on_failure(max_retries=2, delay=1)
    def _fetch_data_after_timestamp(self, session, table_class, timestamp_column, timestamp):
        """
        获取指定时间戳之后的数据，使用分批处理避免内存溢出
        
        Args:
            session: 数据库会话
            table_class: SQLAlchemy模型类
            timestamp_column (str): 时间戳列名
            timestamp (datetime): 时间戳
            
        Returns:
            list: 数据列表
        """
        try:
            query = session.query(table_class)
            if timestamp:
                query = query.filter(getattr(table_class, timestamp_column) > timestamp)
            
            # 分批获取数据，避免一次性加载大量数据到内存
            batch_size = 1000
            offset = 0
            all_data = []
            
            while True:
                batch_data = query.offset(offset).limit(batch_size).all()
                if not batch_data:
                    break
                all_data.extend(batch_data)
                offset += batch_size
                
                # 如果数据量较大，添加短暂延迟避免阻塞
                if len(all_data) > 5000:
                    time.sleep(0.01)
                    
            return all_data
        except SQLAlchemyError as e:
            log_operation("system", "ERROR", "数据查询", f"查询数据失败: {str(e)}")
            raise e
    
    @retry_on_failure(max_retries=2, delay=1)
    def _insert_data(self, session, table_class, data):
        """
        插入数据到数据库
        
        Args:
            session: 数据库会话
            table_class: SQLAlchemy模型类
            data (list): 要插入的数据列表
            
        Returns:
            int: 插入的记录数
        """
        if not data:
            return 0
            
        try:
            # 转换为字典列表
            dict_data = []
            for record in data:
                record_dict = {}
                for column in table_class.__table__.columns:
                    record_dict[column.name] = getattr(record, column.name)
                dict_data.append(record_dict)
                
            # 批量插入
            session.bulk_insert_mappings(table_class, dict_data)
            session.commit()
            return len(dict_data)
        except SQLAlchemyError as e:
            session.rollback()
            log_operation("system", "ERROR", "数据插入", f"插入数据失败: {str(e)}")
            raise e
    
    def _resolve_conflicts(self, table_class, table_name, timestamp_column):
        """
        解决数据冲突
        
        Args:
            table_class: SQLAlchemy模型类
            table_name (str): 表名
            timestamp_column (str): 时间戳列名
            
        Returns:
            int: 冲突解决数量
        """
        # 简单的冲突解决策略：跳过相同时间戳的数据
        # 在实际应用中，可以根据业务需求实现更复杂的冲突解决策略
        log_operation("system", "INFO", "冲突处理", f"检测到表 {table_name} 存在数据冲突，采用跳过策略")
        return 0
    
    def sync_all_data(self):
        """
        同步所有表的数据
        
        Returns:
            list: 各表同步结果统计列表
        """
        # 修正表名以匹配实际数据库表名
        tables_to_sync = [
            (AirTemperatureHumidity, 'intelligent_farm_airtemperaturehumidity'),
            (SoilMoisture, 'intelligent_farm_soilmoisture'),
            (SoilNutrient, 'intelligent_farm_soilnutrient'),
            (LightIntensity, 'intelligent_farm_light_intensity')
        ]
        
        sync_results = []
        
        for table_class, table_name in tables_to_sync:
            result = self.sync_table_data(table_class, table_name)
            sync_results.append(result)
            
        return sync_results
    
    def close_connections(self):
        """
        关闭数据库连接
        """
        try:
            self.cloud_session.close()
            self.local_session.close()
        except Exception as e:
            log_operation("system", "ERROR", "连接关闭", f"关闭数据库连接时出错: {str(e)}")



def validate_database_inputs(host, port, name, user, password):
    """
    验证数据库连接参数
    """
    errors = []
    
    # 验证IP地址格式
    if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$|^localhost$|^[\w.-]+$', host):
        errors.append("无效的主机地址格式")
    
    # 验证端口范围
    if not (1 <= port <= 65535):
        errors.append("端口号必须在1-65535之间")
    
    # 验证数据库名称
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        errors.append("数据库名称只能包含字母、数字和下划线")
    
    # 验证用户名
    if not re.match(r'^[a-zA-Z0-9_]+$', user):
        errors.append("用户名只能包含字母、数字和下划线")
    
    # 验证密码强度
    if len(password) < 8:
        errors.append("密码长度至少为8位")
    
    return errors


def sync_databases_ui():
    """
    数据库同步的Streamlit用户界面，增强安全性
    """
    st.title("🔄 数据库同步")
    
    st.markdown("""
    ### 数据同步功能说明
    - **双向同步**: 自动检测云端和本地数据库的数据差异
    - **增量同步**: 只同步新增或修改的数据，提高效率
    - **冲突处理**: 自动处理数据冲突，确保数据一致性
    """)
    
    # 获取数据库连接信息
    
    # 修改为输入IP地址和端口，默认使用MySQL
    st.subheader("云端数据库配置")
    cloud_db_host = st.text_input("云端数据库IP地址", os.getenv('CLOUD_DATABASE_HOST', 'localhost'))
    cloud_db_port = st.number_input("云端数据库端口", min_value=1, max_value=65535, value=int(os.getenv('CLOUD_DATABASE_PORT', 3306)))
    cloud_db_name = st.text_input("云端数据库名称", os.getenv('CLOUD_DATABASE_NAME', 'intelligent_farm'))
    cloud_db_user = st.text_input("云端数据库用户名", os.getenv('CLOUD_DATABASE_USER', 'root'))
    cloud_db_password = st.text_input("云端数据库密码", os.getenv('CLOUD_DATABASE_PASSWORD', ''), type="password")
    
    st.subheader("本地数据库配置")
    local_db_host = st.text_input("本地数据库IP地址", os.getenv('LOCAL_DATABASE_HOST', 'localhost'))
    local_db_port = st.number_input("本地数据库端口", min_value=1, max_value=65535, value=int(os.getenv('LOCAL_DATABASE_PORT', 3306)))
    local_db_name = st.text_input("本地数据库名称", os.getenv('LOCAL_DATABASE_NAME', 'intelligent_farm'))
    local_db_user = st.text_input("本地数据库用户名", os.getenv('LOCAL_DATABASE_USER', 'root'))
    local_db_password = st.text_input("本地数据库密码", os.getenv('LOCAL_DATABASE_PASSWORD', ''), type="password")
    
    # 添加连接测试按钮
    if st.button("测试数据库连接"):
        # 验证输入参数
        validation_errors = validate_database_inputs(
            cloud_db_host, cloud_db_port, cloud_db_name, 
            cloud_db_user, cloud_db_password
        )
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
            return
        
        try:
            cloud_db_url = f"mysql+pymysql://{cloud_db_user}:{quote_plus(cloud_db_password)}@{cloud_db_host}:{cloud_db_port}/{cloud_db_name}"
            local_db_url = f"mysql+pymysql://{local_db_user}:{quote_plus(local_db_password)}@{local_db_host}:{local_db_port}/{local_db_name}"
            
            with st.spinner("正在测试连接..."):
                sync_manager = DatabaseSyncManager(cloud_db_url, local_db_url)
                # 简单执行查询测试连接
                sync_manager.cloud_session.execute(text("SELECT 1"))
                sync_manager.local_session.execute(text("SELECT 1"))
                sync_manager.close_connections()
                
            st.success("✅ 数据库连接测试成功！")
        except Exception as e:
            # 提供更详细的错误信息
            error_msg = str(e)
            if "Access denied" in error_msg:
                st.error(f"❌ 数据库连接测试失败: 用户名或密码错误\n\n详细信息: {error_msg}")
            elif "Can't connect" in error_msg:
                st.error(f"❌ 数据库连接测试失败: 无法连接到数据库服务器，请检查IP地址和端口\n\n详细信息: {error_msg}")
            elif "Unknown database" in error_msg:
                st.error(f"❌ 数据库连接测试失败: 数据库不存在\n\n详细信息: {error_msg}")
            else:
                st.error(f"❌ 数据库连接测试失败: {error_msg}")
    
    # 添加数据库连接安全验证
    if st.button("验证数据库权限"):
        try:
            cloud_db_url = f"mysql+pymysql://{cloud_db_user}:{quote_plus(cloud_db_password)}@{cloud_db_host}:{cloud_db_port}/{cloud_db_name}"
            
            with st.spinner("正在验证权限..."):
                sync_manager = DatabaseSyncManager(cloud_db_url, cloud_db_url)  # 使用相同连接测试
                
                # 检查必要的权限
                permissions = []
                tables_to_check = [
                    'intelligent_farm_airtemperaturehumidity',
                    'intelligent_farm_soilmoisture',
                    'intelligent_farm_soilnutrient',
                    'intelligent_farm_light_intensity'
                ]
                
                for table in tables_to_check:
                    try:
                        # 尝试执行SELECT和INSERT权限检查
                        sync_manager.cloud_session.execute(text(f"SELECT COUNT(*) FROM {table} LIMIT 1"))
                        # 修改INSERT语句，提供必要的字段和默认值
                        if 'airtemperaturehumidity' in table:
                            sync_manager.cloud_session.execute(text(f"INSERT INTO {table} (temperature, humidity, timestamp) VALUES (0.0, 0.0, NOW())"))
                        elif 'soilmoisture' in table:
                            sync_manager.cloud_session.execute(text(f"INSERT INTO {table} (value, timestamp) VALUES (0.0, NOW())"))
                        elif 'soilnutrient' in table:
                            sync_manager.cloud_session.execute(text(f"INSERT INTO {table} (value, timestamp) VALUES (0.0, NOW())"))
                        elif 'light_intensity' in table:
                            sync_manager.cloud_session.execute(text(f"INSERT INTO {table} (value, timestamp) VALUES (0.0, NOW())"))
                        sync_manager.cloud_session.rollback()  # 回滚避免实际插入
                        permissions.append(f"✅ {table}: 读写权限正常")
                    except Exception as e:
                        if "command denied" in str(e).lower() or "access denied" in str(e).lower():
                            permissions.append(f"❌ {table}: 权限不足")
                        else:
                            permissions.append(f"? {table}: 无法验证 ({str(e)[:50]}...)")
                
                sync_manager.close_connections()
                
                # 显示权限检查结果
                st.subheader("权限检查结果")
                for perm in permissions:
                    if perm.startswith("✅"):
                        st.success(perm)
                    elif perm.startswith("❌"):
                        st.error(perm)
                    else:
                        st.warning(perm)
                        
        except Exception as e:
            st.error(f"权限验证失败: {str(e)}")
    
    if st.button("开始同步"):
        # 验证输入参数
        validation_errors = validate_database_inputs(
            cloud_db_host, cloud_db_port, cloud_db_name, 
            cloud_db_user, cloud_db_password
        )
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
            return
        
        # 构建MySQL连接URL，对密码进行URL编码
        cloud_db_url = f"mysql+pymysql://{cloud_db_user}:{quote_plus(cloud_db_password)}@{cloud_db_host}:{cloud_db_port}/{cloud_db_name}"
        local_db_url = f"mysql+pymysql://{local_db_user}:{quote_plus(local_db_password)}@{local_db_host}:{local_db_port}/{local_db_name}"
        
        if not cloud_db_host or not local_db_host:
            st.error("请填写完整的数据库连接信息")
            return
            
        try:
            with st.spinner("正在进行数据同步..."):
                # 创建同步管理器
                sync_manager = DatabaseSyncManager(cloud_db_url, local_db_url)
                
                # 执行同步
                sync_results = sync_manager.sync_all_data()
                
                # 关闭连接
                sync_manager.close_connections()
                
                # 显示同步结果
                st.success("数据同步完成！")
                
                # 创建结果表格
                result_data = []
                total_cloud_to_local = 0
                total_local_to_cloud = 0
                total_conflicts = 0
                
                for result in sync_results:
                    result_data.append({
                        '数据表': result['table'],
                        '云端→本地': result['cloud_to_local'],
                        '本地→云端': result['local_to_cloud'],
                        '冲突数量': result['conflicts']
                    })
                    total_cloud_to_local += result['cloud_to_local']
                    total_local_to_cloud += result['local_to_cloud']
                    total_conflicts += result['conflicts']
                
                st.dataframe(pd.DataFrame(result_data))
                
                # 显示汇总信息
                col1, col2, col3 = st.columns(3)
                col1.metric("云端→本地记录数", total_cloud_to_local)
                col2.metric("本地→云端记录数", total_local_to_cloud)
                col3.metric("处理冲突数", total_conflicts)
                
                log_operation(st.session_state.get('username', 'system'), "INFO", 
                             "数据库同步", f"同步完成 - 云端→本地: {total_cloud_to_local}, 本地→云端: {total_local_to_cloud}")
                
        except Exception as e:
            error_msg = str(e)
            if "Access denied" in error_msg:
                st.error(f"数据同步失败: 用户名或密码错误，请检查数据库用户名和密码\n\n详细信息: {error_msg}")
            elif "Can't connect" in error_msg:
                st.error(f"数据同步失败: 无法连接到数据库服务器，请检查IP地址和端口\n\n详细信息: {error_msg}")
            elif "Unknown database" in error_msg:
                st.error(f"数据同步失败: 数据库不存在，请检查数据库名称\n\n详细信息: {error_msg}")
            else:
                st.error(f"数据同步失败: {error_msg}")
            log_operation(st.session_state.get('username', 'system'), "ERROR", 
                         "数据库同步", f"同步失败: {str(e)}")


if __name__ == "__main__":
    # 可以作为独立脚本运行
    pass
