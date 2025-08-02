# -*- coding: utf-8 -*-

from urllib.parse import quote_plus as urlquote

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config.app_config import CONFIG
from config.log_config import app_logger

# 尝试导入达梦数据库模块（可选依赖）
try:
    import dmPython
    DM_AVAILABLE = True
    app_logger.info("✅ 达梦数据库模块dmPython已加载")
except ImportError:
    DM_AVAILABLE = False
    app_logger.warning("⚠️  达梦数据库模块dmPython未安装，将跳过达梦数据库相关功能")

def get_database_url():
    """
    根据配置的数据库类型构建同步数据库连接URL
    """
    database_type = CONFIG.get('database_type', 'mysql')
    
    if database_type == 'dameng':
        if not DM_AVAILABLE:
            app_logger.error("❌ 配置要求使用达梦数据库，但dmPython模块未安装")
            raise ImportError("达梦数据库配置需要dmPython模块，请安装: pip install dmPython")
        
        # 达梦数据库连接
        username = CONFIG['username']
        password = CONFIG['password']
        host_port = CONFIG['database_uri']
        database_url = f"dm+dmPython://{username}:{password}@{host_port}"
        app_logger.info(f"同步连接使用达梦数据库: dm+dmPython://{username}:***@{host_port}")
        return database_url
    else:
        # MySQL数据库连接
        username = CONFIG.get('username_mysql', '')
        password = urlquote(CONFIG.get('password_mysql', ''))
        # 优先使用MySQL专用的URI配置，如果没有则使用通用配置
        database_uri = CONFIG.get('database_uri_mysql', '')
        database_url = f"mysql+pymysql://{username}:{password}@{database_uri}"
        app_logger.info(f"同步连接使用MySQL数据库: mysql+pymysql://{username}:***@{database_uri}")
        return database_url

def get_connect_args():
    """
    获取数据库特定的连接参数
    """
    database_type = CONFIG.get('database_type', 'mysql')
    
    if database_type == 'dameng':
        return {
            "local_code": 1,
            "connection_timeout": 15
        }
    else:
        return {}

# 应用dmSQLAlchemy路径修复（仅在使用达梦数据库且模块可用时）
if CONFIG.get('database_type') == 'dameng' and DM_AVAILABLE:
    try:
        import sys
        import types
        
        # 创建src模块路径映射
        if 'src' not in sys.modules:
            src_module = types.ModuleType('src')
            sys.modules['src'] = src_module
        
        # 将dmPython添加到src模块中
        sys.modules['src'].dmPython = dmPython
        sys.modules['src.dmPython'] = dmPython
        
        # 检查并创建DMDialect_dmPython类
        if not hasattr(dmPython, 'DMDialect_dmPython'):
            from sqlalchemy.dialects import registry
            from sqlalchemy.engine import default
            
            # 创建一个基本的达梦方言类
            class DMDialect_dmPython(default.DefaultDialect):
                name = 'dm'
                driver = 'dmPython'
                supports_alter = True
                supports_pk_autoincrement = True
                supports_default_values = True
                supports_empty_insert = True
                supports_unicode_statements = True
                supports_unicode_binds = True
                returns_unicode_strings = True
                description_encoding = None
                supports_native_boolean = False
                
                @classmethod
                def dbapi(cls):
                    return dmPython
                
                def create_connect_args(self, url):
                    opts = url.translate_connect_args(username='user')
                    opts.update(url.query)
                    return [], opts
                
                def get_columns(self, connection, table_name, schema=None, **kw):
                    # 基本的列信息获取实现
                    return []
                
                def get_table_names(self, connection, schema=None, **kw):
                    # 基本的表名获取实现
                    return []
            
            # 添加到dmPython模块
            dmPython.DMDialect_dmPython = DMDialect_dmPython
            
            app_logger.info("✅ 创建DMDialect_dmPython类成功")
        
        app_logger.info("✅ 达梦数据库路径映射修复成功")
    except Exception as e:
        app_logger.error(f"❌ 达梦数据库路径映射修复失败: {e}")

DATABASE_URL = get_database_url()
connect_args = get_connect_args()

engine = create_engine(
    DATABASE_URL, 
    pool_size=CONFIG.get('pool_size', 10),
    pool_pre_ping=True, 
    pool_recycle=3600,
    connect_args=connect_args,
    echo=False
)

metadata = MetaData()
try:
    metadata.reflect(bind=engine)
    app_logger.info("同步数据库表结构反射成功")
except Exception as e:
    app_logger.warning(f"同步数据库表结构反射失败: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    获取数据库会话的依赖注入函数
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
