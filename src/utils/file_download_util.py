# -*- coding: utf-8 -*-
#  author: ict
import io
import os
import sys
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import minio
from minio.error import S3Error
from config import log_config
from config.app_config import CONFIG


class MinioConfig:
    """Minio配置类"""

    def __init__(self, config_dict: dict):
        self.endpoint = config_dict.get("endpoint")
        self.access_key = config_dict.get("access_key")
        self.secret_key = config_dict.get("secret_key")
        self.schema = config_dict.get("schema", False)  # 是否使用HTTPS
        self.cert_check = config_dict.get("cert_check", True)
        self.bucket_name = config_dict.get("bucket_name")
        self.tmp_bucket_name = config_dict.get("tmp_bucket_name")


class MinioFileDownloader:
    """MinIO文件下载器 - 简化版本"""

    def __init__(self, config: MinioConfig):
        self.config = config
        self.minio_client = minio.Minio(
            endpoint=config.endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.schema,
            cert_check=config.cert_check,
        )

    def download_file_to_bytes(self, object_name: str, bucket_name: str = None) -> bytes:
        """
        从MinIO下载文件到内存
        
        Args:
            object_name: 对象名称（文件路径）
            bucket_name: 桶名称，默认为配置中的bucket_name
            
        Returns:
            文件内容的字节数据
        """
        if bucket_name is None:
            bucket_name = self.config.bucket_name

        try:
            log_config.app_logger.info(f"开始下载MinIO文件: bucket={bucket_name}, object={object_name}")
            
            # 获取文件对象
            response = self.minio_client.get_object(
                bucket_name=bucket_name,
                object_name=object_name
            )

            # 读取文件内容
            file_data = response.read()
            response.close()
            response.release_conn()

            log_config.app_logger.info(f"MinIO文件下载成功: {len(file_data)} 字节")
            return file_data

        except S3Error as e:
            log_config.app_logger.error(f"MinIO下载错误: {e}")
            raise
        except Exception as e:
            log_config.app_logger.error(f"下载文件时发生错误: {e}")
            raise

    def download_file_to_local(self, object_name: str, local_path: str, bucket_name: str = None) -> bool:
        """
        从MinIO下载文件到本地
        
        Args:
            object_name: 对象名称
            local_path: 本地保存路径
            bucket_name: 桶名称
            
        Returns:
            下载是否成功
        """
        try:
            # 下载文件内容
            file_data = self.download_file_to_bytes(object_name, bucket_name)
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # 保存到本地文件
            with open(local_path, 'wb') as f:
                f.write(file_data)
            
            log_config.app_logger.info(f"文件已保存到: {local_path}")
            return True
            
        except Exception as e:
            log_config.app_logger.error(f"下载文件到本地失败: {e}")
            return False

    def extract_object_name_from_url(self, file_url: str) -> str:
        """
        从文件URL中提取object_name
        
        根据MinIO界面显示，文件可能在文件夹下，object_name应该包含完整路径
        例如：http://localhost:9700/cedc-smart-apps/ccla99ab1b5544e297650f0f33c653b7/6ab1e2f9c5aa2ac7cb772531e6880d83_d0635d16840f42e7ab7623da516d9ad4.docx
        -> object_name: ccla99ab1b5544e297650f0f33c653b7/6ab1e2f9c5aa2ac7cb772531e6880d83_d0635d16840f42e7ab7623da516d9ad4.docx
        
        Args:
            file_url: 文件URL
            
        Returns:
            object_name (包含文件夹路径)
        """
        try:
            parsed_url = urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) >= 3:
                # 格式: /bucket_name/folder/filename
                # 取bucket_name之后的所有部分作为object_name (包含文件夹路径)
                object_name = '/'.join(path_parts[1:])
                log_config.app_logger.info(f"从URL提取object_name: {object_name}")
                return object_name
            else:
                raise ValueError(f"URL格式不正确，无法解析object_name: {file_url}")
                
        except Exception as e:
            log_config.app_logger.error(f"解析URL失败: {e}")
            raise

    def download_by_url(self, file_url: str, local_path: str = None) -> bytes:
        """
        通过URL下载文件
        
        Args:
            file_url: 文件URL
            local_path: 可选的本地保存路径
            
        Returns:
            文件内容的字节数据
        """
        try:
            # 提取object_name
            object_name = self.extract_object_name_from_url(file_url)
            
            # 下载文件
            file_data = self.download_file_to_bytes(object_name)
            
            # 如果指定了本地路径，保存到本地
            if local_path:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(file_data)
                log_config.app_logger.info(f"文件已保存到: {local_path}")
            
            return file_data
            
        except Exception as e:
            log_config.app_logger.error(f"通过URL下载文件失败: {e}")
            raise

    def list_objects(self, bucket_name: str = None, prefix: str = "") -> list:
        """
        列出桶中的对象
        
        Args:
            bucket_name: 桶名称
            prefix: 前缀过滤
            
        Returns:
            对象列表
        """
        if bucket_name is None:
            bucket_name = self.config.bucket_name

        try:
            objects = self.minio_client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]
        except Exception as e:
            log_config.app_logger.error(f"列出对象时发生错误: {e}")
            return []


def get_minio_config() -> MinioConfig:
    """
    从配置文件或环境变量获取MinIO配置
    
    Returns:
        MinioConfig对象
    """
    # 首先尝试从配置文件获取
    minio_config = CONFIG.get('minio', {})
    
    # 如果配置文件没有，尝试从环境变量获取
    if not minio_config:
        minio_config = {
            "endpoint": os.getenv("MINIO_ENDPOINT", "172.18.1.7:9700"),
            "access_key": os.getenv("MINIO_ACCESS_KEY", ""),
            "secret_key": os.getenv("MINIO_SECRET_KEY", ""),
            "schema": os.getenv("MINIO_SCHEMA", "false").lower() == "true",
            "cert_check": os.getenv("MINIO_CERT_CHECK", "true").lower() == "true",
            "bucket_name": os.getenv("MINIO_BUCKET_NAME", "cedc-smart-apps"),
            "tmp_bucket_name": os.getenv("MINIO_TMP_BUCKET_NAME", "cedc-smart-apps-tmp-dir")
        }
    
    # 确保配置完整性
    config_dict = {
        "endpoint": minio_config.get("endpoint", "172.18.1.7:9700"),
        "access_key": minio_config.get("access_key", ""),
        "secret_key": minio_config.get("secret_key", ""),
        "schema": minio_config.get("schema", False),
        "cert_check": minio_config.get("cert_check", True),
        "bucket_name": minio_config.get("bucket_name", "cedc-smart-apps"),
        "tmp_bucket_name": minio_config.get("tmp_bucket_name", "cedc-smart-apps-tmp-dir")
    }
    
    log_config.app_logger.info(f"MinIO配置: endpoint={config_dict['endpoint']}, bucket={config_dict['bucket_name']}")
    
    return MinioConfig(config_dict)


def download_file_from_minio(file_location: str, local_path: str) -> bool:
    """
    从MinIO下载文件到本地指定路径
    
    Args:
        file_location: 文件下载URL
        local_path: 本地保存路径
        
    Returns:
        下载是否成功
    """
    try:
        log_config.app_logger.info(f"开始从MinIO下载文件: {file_location} -> {local_path}")
        
        # 获取MinIO配置和下载器
        minio_config = get_minio_config()
        downloader = MinioFileDownloader(minio_config)
        
        # 通过URL下载文件
        downloader.download_by_url(file_location, local_path)
        
        log_config.app_logger.info(f"MinIO文件下载完成: {local_path}")
        return True
        
    except Exception as e:
        log_config.app_logger.error(f"从MinIO下载文件失败: {file_location}, 错误: {str(e)}")
        return False


def ensure_file_exists(file_name: str, file_location: str, knowledge_dir: str) -> Optional[str]:
    """
    确保文件存在，如果本地没有则从MinIO下载
    
    Args:
        file_name: 文件名
        file_location: 文件下载URL
        knowledge_dir: 知识库目录路径
        
    Returns:
        本地文件路径，如果失败返回None
    """
    # 构建本地文件路径
    local_file_path = os.path.join(knowledge_dir, file_name)
    
    # 检查本地文件是否存在
    if os.path.exists(local_file_path):
        log_config.app_logger.info(f"本地文件已存在: {local_file_path}")
        return local_file_path
    
    # 本地文件不存在，尝试从MinIO下载
    log_config.app_logger.info(f"本地文件不存在，尝试从MinIO下载: {file_name}")
    
    if download_file_from_minio(file_location, local_file_path):
        return local_file_path
    else:
        log_config.app_logger.error(f"文件下载失败: {file_name}")
        return None


def process_file_list(file_list: list, knowledge_dir: str) -> list:
    """
    处理文件列表，确保所有文件都可用
    
    Args:
        file_list: 文件信息列表，每个元素应包含file_name, file_location等字段
        knowledge_dir: 知识库目录路径
        
    Returns:
        可用的文件路径列表
    """
    available_files = []
    
    for file_info in file_list:
        if isinstance(file_info, dict):
            file_name = file_info.get('file_name', '')
            file_location = file_info.get('file_location', '')
            
            if file_name and file_location:
                # 确保文件存在
                local_path = ensure_file_exists(file_name, file_location, knowledge_dir)
                
                if local_path:
                    available_files.append(local_path)
                    log_config.app_logger.info(f"文件准备就绪: {file_name}")
                else:
                    log_config.app_logger.error(f"文件不可用: {file_name}")
            else:
                log_config.app_logger.warning(f"文件信息不完整: {file_info}")
        else:
            log_config.app_logger.warning(f"无效的文件信息格式: {file_info}")
    
    return available_files


if __name__ == "__main__":
    """测试MinIO下载功能"""
    
    # 创建test目录
    os.makedirs("test", exist_ok=True)
    
    log_config.app_logger.info("MinIO文件下载测试脚本")
    
    try:
        # 获取MinIO配置
        config = get_minio_config()
        downloader = MinioFileDownloader(config)
        
        # 测试1: 列出桶中的文件
        log_config.app_logger.info("=== 列出桶中的文件 ===")
        objects = downloader.list_objects()
        log_config.app_logger.info(f"找到 {len(objects)} 个文件:")
        for obj in objects[:10]:  # 只显示前10个
            log_config.app_logger.info(f"  - {obj}")
        
        # 测试2: 测试特定文件下载
        test_url = "http://172.18.1.7:9700/cedc-smart-apps/ccla99ab1b5544e297650f0f33c653b7/6able2f9c5aa2ac7cb772531e6880d83_d0635d16840f42e7ab7623da516d9ad4.docx"
        test_filename = "test_downloaded_file.docx"
        save_path = f"test/{test_filename}"
        
        log_config.app_logger.info(f"=== 测试下载文件: {test_url} ===")
        file_data = downloader.download_by_url(test_url, save_path)
        log_config.app_logger.info(f"下载成功，文件大小: {len(file_data)} 字节")
        
    except Exception as e:
        log_config.app_logger.error(f"测试过程中发生错误: {e}")