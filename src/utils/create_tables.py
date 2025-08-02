# -*- coding: utf-8 -*-
"""数据库表创建脚本"""

from config.db_config import engine, Base
from config.log_config import app_logger
from model.paper import Paper, UserAnswer


def create_all_tables():
    """
    创建所有数据库表
    """
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        app_logger.info(" 数据库表创建成功")
        
        # 打印创建的表信息
        tables = Base.metadata.tables.keys()
        for table_name in tables:
            app_logger.info(f"   - 表 {table_name} 已创建")
            
    except Exception as e:
        app_logger.error(f" 数据库表创建失败: {str(e)}")
        raise


def drop_all_tables():
    """
    删除所有数据库表（谨慎使用）
    """
    try:
        Base.metadata.drop_all(bind=engine)
        app_logger.warning("  所有数据库表已删除")
    except Exception as e:
        app_logger.error(f" 删除数据库表失败: {str(e)}")
        raise


if __name__ == "__main__":
    import sys
    
    # if len(sys.argv) > 1 and sys.argv[1] == "drop":
        # 删除表
    # drop_all_tables()
    
    # 创建表
    create_all_tables()
    print("数据库表创建完成！") 