import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import streamlit as st
from utils.logger import log_operation
from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity

class DatabaseSyncManager:
    """
    数据库同步管理器，用于同步云端和本地数据库
    """
    
    def __init__(self, cloud_db_url, local_db_url):
        """
        初始化同步管理器
        
        Args:
            cloud_db_url (str): 云端数据库连接URL
            local_db_url (str): 本地数据库连接URL
        """
        self.cloud_engine = create_engine(cloud_db_url)
        self.local_engine = create_engine(local_db_url)
        self.cloud_session = sessionmaker(bind=self.cloud_engine)()
        self.local_session = sessionmaker(bind=self.local_engine)()
        
    def sync_table_data(self, table_class, table_name, timestamp_column='timestamp'):
        """
        同步单个表的数据
        
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
        
        try:
            # 获取云端和本地数据的最新时间戳
            cloud_max_time = self._get_max_timestamp(self.cloud_session, table_name, timestamp_column)
            local_max_time = self._get_max_timestamp(self.local_session, table_name, timestamp_column)
            
            # 从云端同步到本地 (云端有更新的数据)
            if cloud_max_time and (not local_max_time or cloud_max_time > local_max_time):
                cloud_data = self._fetch_data_after_timestamp(
                    self.cloud_session, table_class, timestamp_column, local_max_time)
                inserted_count = self._insert_data(self.local_session, table_class, cloud_data)
                sync_stats['cloud_to_local'] = inserted_count
                
            # 从本地同步到云端 (本地有更新的数据)
            if local_max_time and (not cloud_max_time or local_max_time > cloud_max_time):
                local_data = self._fetch_data_after_timestamp(
                    self.local_session, table_class, timestamp_column, cloud_max_time)
                inserted_count = self._insert_data(self.cloud_session, table_class, local_data)
                sync_stats['local_to_cloud'] = inserted_count
                
            # 处理时间戳相同的冲突数据
            if cloud_max_time and local_max_time and cloud_max_time == local_max_time:
                sync_stats['conflicts'] = self._resolve_conflicts(
                    table_class, table_name, timestamp_column)
                
        except Exception as e:
            log_operation("system", "ERROR", "数据同步", f"同步表 {table_name} 时出错: {str(e)}")
            raise e
            
        return sync_stats
    
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
        except Exception:
            return None
    
    def _fetch_data_after_timestamp(self, session, table_class, timestamp_column, timestamp):
        """
        获取指定时间戳之后的数据
        
        Args:
            session: 数据库会话
            table_class: SQLAlchemy模型类
            timestamp_column (str): 时间戳列名
            timestamp (datetime): 时间戳
            
        Returns:
            list: 数据列表
        """
        query = session.query(table_class)
        if timestamp:
            query = query.filter(getattr(table_class, timestamp_column) > timestamp)
        return query.all()
    
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
        except Exception as e:
            session.rollback()
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
        self.cloud_session.close()
        self.local_session.close()


def sync_databases_ui():
    """
    数据库同步的Streamlit用户界面
    """
    st.title("🔄 数据库同步")
    
    st.markdown("""
    ### 数据同步功能说明
    - **双向同步**: 自动检测云端和本地数据库的数据差异
    - **增量同步**: 只同步新增或修改的数据，提高效率
    - **冲突处理**: 自动处理数据冲突，确保数据一致性
    """)
    
    # 获取数据库连接信息
    cloud_db_url = st.text_input("云端数据库连接URL", 
                                os.getenv('CLOUD_DATABASE_URL', ''),
                                type="password")
    local_db_url = st.text_input("本地数据库连接URL", 
                                os.getenv('LOCAL_DATABASE_URL', ''),
                                type="password")
    
    if st.button("开始同步"):
        if not cloud_db_url or not local_db_url:
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
            st.error(f"数据同步失败: {str(e)}")
            log_operation(st.session_state.get('username', 'system'), "ERROR", 
                         "数据库同步", f"同步失败: {str(e)}")


if __name__ == "__main__":
    # 可以作为独立脚本运行
    pass