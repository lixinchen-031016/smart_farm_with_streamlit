1.云服务器里安装docker，docker-compose，git
sudo apt-get update && sudo apt-get install docker.io
apt  install docker-compose
sudo apt update && sudo apt install git
使用docker ps测试docker是否已安装

使用git命令将智能农场文件拉取下来
git clone https://github.com/lixinchen-031016/smart_farm_with_streamlit.git

2.使用cd进入云服务器中拉取下来的smart_farm_with_streamlit文件夹

3.使用ls查看文件夹内文件

4.在包含 docker-compose.yml 文件的目录下执行以下命令来启动服务：
docker-compose up

5.等待拉取MySQL镜像和制作智慧大棚镜像

6.如果存在网络问题，修改镜像源配置文件
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
"registry-mirrors": [
"https://0vmzj3q6.mirror.aliyuncs.com",
"https://docker.m.daocloud.io",
"https://mirror.baidubce.com",
"https://dockerproxy.com",
"https://mirror.iscas.ac.cn",
"https://huecker.io",
"https://dockerhub.timeweb.cloud",
"https://noohub.ru",
"https://vlgh0kqj.mirror.aliyuncs.com",
"http://hub-mirror.c.163.com",
"https://docker.nju.edu.cn",
"https://docker.mirrors.sjtug.sjtu.edu.cn",
"https://mirror.ccs.tencentyun.com"
]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker

如果镜像生成有问题，用docker-compose up命令重新生成

7.等待容器运行，如果容器启动有问题，重启docker并启动容器
sudo systemctl restart docker
docker-compose up

8.需要进入数据库容器运行intelligent_farm.sql才能正常使用
