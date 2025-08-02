# 智能配置助手

## 项目简介

智能配置助手是某银行的核心业务系统，旨在提供智能化的配置管理、规则引擎和业务配置服务。系统支持配置模板管理、规则验证、配置版本控制等功能。

## 技术栈

- **后端框架**: FastAPI
- **数据库**: PostgreSQL
- **缓存**: Redis
- **消息队列**: RabbitMQ
- **文件存储**: MinIO
- **容器化**: Docker
- **部署**: Kubernetes

## 项目结构

```
smart-config-assistant/
├── bin/                          # 启动脚本目录
├── docs/                         # 项目文档
├── envs/                         # 环境配置文件
├── logs/                         # 日志文件
├── src/                          # 源代码主目录
│   ├── config/                   # 配置管理
│   ├── controller/               # 路由控制器
│   ├── service/                  # 业务逻辑层
│   ├── dao/                      # 数据访问层
│   ├── model/                    # 数据模型
│   ├── schemas/                  # Pydantic数据验证模型
│   ├── utils/                    # 工具函数
│   ├── core/                     # 核心模块
│   ├── static/                   # 静态文件
│   ├── main.py                   # 应用入口
│   └── gunicorn_conf.py          # Gunicorn配置
├── supervisor-start/             # Supervisor启动配置
├── Dockerfile                    # Docker镜像文件
├── docker-compose.yml            # Docker Compose配置
├── requirements.txt              # Python依赖
└── README.md                     # 项目说明
```

## 快速开始

1. 克隆项目
2. 安装依赖: `pip install -r requirements.txt`
3. 配置环境变量
4. 启动服务: `python src/main.py`

## 功能特性

- 智能配置管理
- 规则引擎
- 配置模板
- 版本控制
- 权限管理
- 审计日志
- API文档

# 环境准备

conda 环境创建
```
conda create -n smart-training python=3.10.14
```

conda 环境激活

```
conda activate smart-training
```

conda 环境退出

```
conda deactivate
```


python 模块安装

```
# 生成 requirements.txt
pip list --format=freeze > requirements.txt

# 根据 requirements.txt 安装
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 根据 requirements.txt 安装 忽略依赖冲突
pip install -r requirements.txt --no-dependencies

# pip 下载whl文件
pip wheel minio aiomysql zipstream -i https://mirrors.aliyun.com/pypi/simple/

```

# 项目启动

## 使用 python 命令启动

本地测试时，直接用 python 命令启动。
```

python main.py
```

## 使用 shell 脚本启动

在服务器上部署，可以使用 shell 脚本。

```
cd  [project dir]/bin
./bin/start.sh
```

# 查看接口

查看 swagger 页面

本地查看：http://localhost:15051/docs

# 生成实际依赖包
```
pipreqs "." --ignore=test --encoding=utf8 --savepath="deps.txt" --force

pip download -r deps.txt -d ./whl_packages --only-binary=:all:

pip download python-docx -d ./whl
```


# 容器启动
```
docker run -p 9440:9440 -d --name gxb-ict-document-d-server \
  2d82540887b1 \
  tail -f /dev/null 
```
 

# 导出openapi文件
```
from my_awesome_project.main import app  # 替换为你的 app 路径
import json

with open("../docs/openapi.json", "w") as f:
    json.dump(app.openapi(), f, indent=2)

print("openapi.json has been exported.")
```

