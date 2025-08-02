#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件下载和处理功能
"""

import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.file_download_util import process_file_list, MinioFileDownloader, get_minio_config
from config.app_config import STATIC_FILE_PATH

def test_file_processing():
    """测试文件处理功能"""
    print("=== 测试文件处理 ===")
    
    # 模拟文件列表数据 - 使用正确的knowledge_id
    test_file_list = [
        {
            "file_bucket_name": "6ab1e2f9c5aa2ac7cb772531e6880d83_d0635d16840f42e7ab7623da516d9ad4.docx",
            "file_id": "a29ceaeea545f3f759f932beefabc86b",
            "file_location": "http://localhost:9700/cedc-smart-apps/cc1a99ab1b5544e297650f0f33c653b7/6ab1e2f9c5aa2ac7cb772531e6880d83_d0635d16840f42e7ab7623da516d9ad4.docx",
            "file_name": "中国建设银行(亚洲)文化及行为标准.docx",
            "knowledge_id": "cc1a99ab1b5544e297650f0f33c653b7",
            "knowledge_name": "银行领域知识库"
        },
    ]
    
    # 测试文件处理
    knowledge_dir = os.path.join(STATIC_FILE_PATH, 'knowledge')
    print(f"知识库目录: {knowledge_dir}")
    
    try:
        available_files = process_file_list(test_file_list, knowledge_dir)
        print(f"可用文件数量: {len(available_files)}")
        for file_path in available_files:
            print(f"  可用文件: {file_path}")
    except Exception as e:
        print(f"文件处理失败: {e}")

def test_direct_download():
    """测试直接下载功能"""
    print("=== 测试直接下载 ===")
    
    try:
        # 获取MinIO配置
        config = get_minio_config()
        downloader = MinioFileDownloader(config)
        
        # 测试URL - 使用正确的knowledge_id
        test_url = "http://localhost:9700/cedc-smart-apps/cc1a99ab1b5544e297650f0f33c653b7/6ab1e2f9c5aa2ac7cb772531e6880d83_d0635d16840f42e7ab7623da516d9ad4.docx"
        
        # 测试提取object_name
        object_name = downloader.extract_object_name_from_url(test_url)
        print(f"提取的object_name: {object_name}")
        
        # 测试下载到内存
        file_data = downloader.download_by_url(test_url)
        print(f"下载成功，文件大小: {len(file_data)} 字节")
        
        # 测试下载到本地
        test_path = "test_downloaded_file.docx"
        downloader.download_by_url(test_url, test_path)
        print(f"文件已保存到: {test_path}")
        
    except Exception as e:
        print(f"直接下载测试失败: {e}")

def test_list_objects():
    """测试列出对象功能"""
    print("=== 测试列出对象 ===")
    
    try:
        config = get_minio_config()
        downloader = MinioFileDownloader(config)
        
        # 列出桶中的对象
        objects = downloader.list_objects()
        print(f"找到 {len(objects)} 个对象:")
        
        # 查找目标文件（包含文件夹路径）
        target_file = "ccla99ab1b5544e297650f0f33c653b7/6ab1e2f9c5aa2ac7cb772531e6880d83_d0635d16840f42e7ab7623da516d9ad4.docx"
        found = False
        
        for obj in objects:
            if target_file in obj:
                print(f"找到目标文件: {obj}")
                found = True
                break
        
        if not found:
            print(f"未找到目标文件: {target_file}")
            
            # 搜索包含目标文件名的对象
            target_filename = "6ab1e2f9c5aa2ac7cb772531e6880d83_d0635d16840f42e7ab7623da516d9ad4.docx"
            matching_objects = []
            
            for obj in objects:
                if target_filename in obj:
                    matching_objects.append(obj)
            
            if matching_objects:
                print(f"找到包含目标文件名的对象:")
                for obj in matching_objects:
                    print(f"  - {obj}")
            else:
                print(f"未找到包含文件名 '{target_filename}' 的对象")
                print("前10个文件:")
                for obj in objects[:10]:
                    print(f"  - {obj}")
        
    except Exception as e:
        print(f"列出对象测试失败: {e}")

def test_search_by_knowledge_id():
    """测试按knowledge_id搜索"""
    print("=== 测试按knowledge_id搜索 ===")
    
    try:
        config = get_minio_config()
        downloader = MinioFileDownloader(config)
        
        # 按knowledge_id搜索 - 使用正确的knowledge_id
        knowledge_id = "cc1a99ab1b5544e297650f0f33c653b7"
        objects = downloader.list_objects(prefix=knowledge_id)
        
        print(f"找到 {len(objects)} 个属于knowledge_id '{knowledge_id}' 的对象:")
        for obj in objects[:20]:  # 显示前20个
            print(f"  - {obj}")
        
        if len(objects) > 20:
            print(f"  ... 还有 {len(objects) - 20} 个对象")
        
    except Exception as e:
        print(f"按knowledge_id搜索失败: {e}")

def test_find_actual_files():
    """测试查找实际存在的文件"""
    print("=== 测试查找实际文件 ===")
    
    try:
        config = get_minio_config()
        downloader = MinioFileDownloader(config)
        
        # 列出所有对象
        objects = downloader.list_objects()
        print(f"总共找到 {len(objects)} 个对象")
        
        # 搜索包含特定关键词的文件
        search_keywords = [
            "中国建设银行",
            "建设银行",
            "文化及行为标准",
            "6ab1e2f9c5aa2ac7cb772531e6880d83",
            "d0635d16840f42e7ab7623da516d9ad4"
        ]
        
        for keyword in search_keywords:
            matching_objects = []
            for obj in objects:
                if keyword in obj:
                    matching_objects.append(obj)
            
            if matching_objects:
                print(f"\n包含关键词 '{keyword}' 的文件 ({len(matching_objects)} 个):")
                for obj in matching_objects[:5]:  # 只显示前5个
                    print(f"  - {obj}")
                if len(matching_objects) > 5:
                    print(f"  ... 还有 {len(matching_objects) - 5} 个")
            else:
                print(f"\n未找到包含关键词 '{keyword}' 的文件")
        
        # 搜索.docx文件
        docx_files = [obj for obj in objects if obj.endswith('.docx')]
        print(f"\n找到 {len(docx_files)} 个.docx文件")
        
        # 显示一些.docx文件的示例
        if docx_files:
            print("前10个.docx文件:")
            for obj in docx_files[:10]:
                print(f"  - {obj}")
        
    except Exception as e:
        print(f"查找实际文件失败: {e}")

def test_download_existing_file():
    """测试下载一个实际存在的文件"""
    print("=== 测试下载实际存在的文件 ===")
    
    try:
        config = get_minio_config()
        downloader = MinioFileDownloader(config)
        
        # 获取一个实际存在的文件进行测试
        objects = downloader.list_objects()
        if objects:
            # 选择一个.docx文件进行测试
            test_object = None
            for obj in objects:
                if obj.endswith('.docx'):
                    test_object = obj
                    break
            
            if test_object:
                print(f"测试下载文件: {test_object}")
                
                # 下载文件
                file_data = downloader.download_file_to_bytes(test_object)
                print(f"下载成功，文件大小: {len(file_data)} 字节")
                
                # 保存到本地测试
                test_path = f"test_download_{os.path.basename(test_object)}"
                downloader.download_file_to_local(test_object, test_path)
                print(f"文件已保存到: {test_path}")
                
                return test_object
            else:
                print("未找到.docx文件进行测试")
        else:
            print("桶中没有文件")
            
    except Exception as e:
        print(f"下载实际文件失败: {e}")
        return None

if __name__ == "__main__":
    test_list_objects()
    print("\n" + "="*50 + "\n")
    test_search_by_knowledge_id()
    print("\n" + "="*50 + "\n")
    test_direct_download()
    print("\n" + "="*50 + "\n")
    test_file_processing()
    print("\n" + "="*50 + "\n")
    test_find_actual_files()
    print("\n" + "="*50 + "\n")
    test_download_existing_file()
    
    print("\n=== 测试完成 ===") 