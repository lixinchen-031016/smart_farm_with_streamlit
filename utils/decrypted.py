import cryptography
from cryptography.fernet import Fernet

# 读取密钥文件
with open("backup/encryption_key.txt", "rb") as key_file:
    key = key_file.read().strip()  # 去除可能的换行符/空格

# 初始化 Fernet
fernet = Fernet(key)

# 解密文件
try:
    with open("backup/backup.sql.encrypted", "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()

    decrypted_data = fernet.decrypt(encrypted_data)

    # 保存解密后的文件（根据原始文件类型选择写入模式）
    with open("backup.sql", "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

    print("文件解密成功！")

except FileNotFoundError:
    print("错误：找不到加密文件或密钥文件")
except cryptography.fernet.InvalidToken:
    print("错误：无效的密钥或损坏的加密文件")
