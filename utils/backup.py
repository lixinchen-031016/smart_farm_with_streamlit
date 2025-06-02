import io
import zipfile

import sqlalchemy
import streamlit as st
from cryptography.fernet import Fernet

from utils.data_operations import fetch_data_in_bulk
from utils.database import engine
from utils.logger import log_operation


def backup_data(session, start_time, end_time):
    """
    备份指定时间范围内的数据
    :param session: 数据库会话对象
    :param start_time: 开始时间
    :param end_time: 结束时间
    :return: 包含加密密钥和加密 SQL 文件的压缩字节流
    """
    # 调用批量查询函数
    df = fetch_data_in_bulk(session, start_time, end_time)

    # 将数据导出为 SQL 文件
    sql_file = io.StringIO()
    for _, row in df.iterrows():
        sql_file.write(
            f"INSERT INTO intelligent_farm_airtemperaturehumidity (temperature, humidity, timestamp) VALUES ({row['temperature']}, {row['humidity']}, '{row['timestamp']}');\n")
        sql_file.write(
            f"INSERT INTO intelligent_farm_soilmoisture (value, timestamp) VALUES ({row['soil_moisture']}, '{row['timestamp']}');\n")
        sql_file.write(
            f"INSERT INTO intelligent_farm_soilnutrient (value, timestamp) VALUES ({row['soil_nutrient']}, '{row['timestamp']}');\n")
        sql_file.write(
            f"INSERT INTO intelligent_farm_light_intensity (value, timestamp) VALUES ({row['light_intensity']}, '{row['timestamp']}');\n")
        sql_file.write(f"\n")
    sql_file.seek(0)

    # 将 StringIO 对象转换为字节流
    sql_bytes = sql_file.getvalue().encode('utf-8')

    # 生成加密密钥并加密数据
    key = Fernet.generate_key()
    encrypted_sql_bytes = Fernet(key).encrypt(sql_bytes)

    # 创建压缩文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('backup.sql.encrypted', encrypted_sql_bytes)
        zip_file.writestr('encryption_key.txt', key.decode('utf-8'))

    zip_buffer.seek(0)

    # 记录操作日志
    log_operation(st.session_state['username'], "INFO","数据备份", f"时间范围: {start_time} - {end_time}")

    return zip_buffer.getvalue()


def restore_data(uploaded_file, key):
    """
    恢复上传的 SQL 文件
    :param uploaded_file: 上传的加密 SQL 文件
    :param key: 解密密钥
    :return: 恢复结果
    """
    try:
        # 读取上传的 SQL 文件内容
        encrypted_sql_bytes = uploaded_file.read()

        # 使用提供的密钥解密 SQL 文件
        fernet = Fernet(key.encode('utf-8'))
        decrypted_sql_bytes = fernet.decrypt(encrypted_sql_bytes)
        sql_script = decrypted_sql_bytes.decode('utf-8')

        # 将 SQL 脚本拆分为单个 SQL 语句
        sql_statements = sql_script.split(';')

        # 执行 SQL 脚本
        with engine.connect() as connection:
            for statement in sql_statements:
                statement = statement.strip()
                if statement:  # 确保语句不为空
                    # 检查并处理 nan 值
                    if 'nan' in statement:
                        continue
                    connection.execute(sqlalchemy.text(statement))

        # 记录操作日志
        log_operation(st.session_state['username'], "INFO","数据恢复", f"文件名: {uploaded_file.name}")

        return True
    except Exception as e:
        log_operation(st.session_state['username'], "ERROR","数据恢复失败", f"错误信息: {str(e)}")
        raise e
