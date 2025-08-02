# -*- coding: utf-8 -*-
#  author: ict
import io
import os
import tempfile
from bs4 import BeautifulSoup

import PyPDF2
import docx
from fastapi import FastAPI, UploadFile

from config.log_config import app_logger
from utils.converted2html_util import DocumentConverter

app = FastAPI(title="文件文本提取器", description="从上传的DOCX和PDF文件中提取文本内容")


def extract_text_from_pdf(file_content: bytes) -> str:
    """从PDF文件内容中提取文本"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page_num].extract_text() + "\n"
        return text
    except Exception as e:
        e = f"PDF处理错误: {str(e)}"
        app_logger.info(f"{e}")
        return ""


def extract_text_from_docx(file_content: bytes) -> str:
    """从DOCX文件内容中提取文本"""
    try:
        doc = docx.Document(io.BytesIO(file_content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        e = f"DOCX处理错误: {str(e)}"
        app_logger.info(f"{e}")
        return ""


def extract_text_from_wps(file_content: bytes) -> str:
    """
    从WPS文件内容中提取文本
    采用迂回方式：先将WPS文件转换为HTML，再从HTML中提取文本
    """
    temp_file_path = None
    try:
        # 创建临时文件保存WPS内容
        with tempfile.NamedTemporaryFile(suffix='.wps', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # 使用DocumentConverter将WPS转换为HTML
        html_content = DocumentConverter.convert_word_to_html(temp_file_path)
        
        # 使用BeautifulSoup从HTML中提取纯文本
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除script和style标签
        for script in soup(["script", "style"]):
            script.decompose()
            
        # 提取文本内容
        text = soup.get_text()
        
        # 清理文本：移除多余的空白字符
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        app_logger.info(f"WPS文件文本提取成功，提取文本长度: {len(text)}")
        return text
        
    except Exception as e:
        error_msg = f"WPS处理错误: {str(e)}"
        app_logger.error(error_msg)
        return ""
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                app_logger.warning(f"删除临时文件失败: {str(e)}")


def extract_text_from_wpt(file_content: bytes) -> str:
    """
    从WPT文件内容中提取文本
    采用迂回方式：先将WPT文件转换为HTML，再从HTML中提取文本
    """
    temp_file_path = None
    try:
        # 创建临时文件保存WPT内容
        with tempfile.NamedTemporaryFile(suffix='.wpt', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # 使用DocumentConverter将WPT转换为HTML
        html_content = DocumentConverter.convert_word_to_html(temp_file_path)
        
        # 使用BeautifulSoup从HTML中提取纯文本
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除script和style标签
        for script in soup(["script", "style"]):
            script.decompose()
            
        # 提取文本内容
        text = soup.get_text()
        
        # 清理文本：移除多余的空白字符
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        app_logger.info(f"WPT文件文本提取成功，提取文本长度: {len(text)}")
        return text
        
    except Exception as e:
        error_msg = f"WPT处理错误: {str(e)}"
        app_logger.error(error_msg)
        return ""
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                app_logger.warning(f"删除临时文件失败: {str(e)}")


# 在 file_text_extractor_util.py 中添加

def extract_text_from_upload_file(file: UploadFile) -> dict:
    """从 UploadFile 对象中提取文本内容，不影响原文件指针"""
    try:
        # 使用 file.file 直接操作底层文件对象，避免异步调用
        file_obj = file.file

        # 保存当前位置
        current_position = file_obj.tell() if hasattr(file_obj, 'tell') else 0

        # 重置到开始位置
        file_obj.seek(0)

        # 读取文件内容
        contents = file_obj.read()

        # 重置文件指针到原始位置
        file_obj.seek(current_position)

        # 根据文件扩展名选择适当的提取方法
        if file.filename.endswith('.pdf'):
            text = extract_text_from_pdf(contents)
            file_type = "PDF"
        elif file.filename.endswith(('.docx', '.docm', '.dotx', '.dotm')):
            text = extract_text_from_docx(contents)
            if not text:
                return {}
            file_type = "DOCX"
        elif file.filename.endswith('.wps'):
            text = extract_text_from_wps(contents)
            file_type = "WPS"
        elif file.filename.endswith('.wpt'):
            text = extract_text_from_wpt(contents)
            file_type = "WPT"
        else:
            text = ""
            file_type = ""

        # 构建响应
        return {
            "filename": file.filename,
            "file_type": file_type,
            "text_length": len(text),
            "text_preview": text[:1000] + "..." if len(text) > 1000 else text,
            "full_text": text
        }

    except Exception as e:
        app_logger.error(f"提取文本失败: {str(e)}")
        return {
            "filename": file.filename,
            "file_type": "",
            "text_length": 0,
            "text_preview": "",
            "full_text": "",
            "error": str(e)
        }


def extract_text_from_file_content(content: bytes, filename: str) -> dict:
    """从文件内容字节流中提取文本内容"""
    try:
        # 根据文件扩展名选择适当的提取方法
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(content)
            file_type = "PDF"
        elif filename.endswith(('.docx', '.docm', '.dotx', '.dotm')):
            text = extract_text_from_docx(content)
            file_type = "DOCX"
        elif filename.endswith('.wps'):
            text = extract_text_from_wps(content)
            file_type = "WPS"
        elif filename.endswith('.wpt'):
            text = extract_text_from_wpt(content)
            file_type = "WPT"
        else:
            text = ""
            file_type = ""

        # 构建响应
        return {
            "filename": filename,
            "file_type": file_type,
            "text_length": len(text),
            "text_preview": text[:1000] + "..." if len(text) > 1000 else text,
            "full_text": text
        }

    except Exception as e:
        app_logger.error(f"提取文本失败: {str(e)}")
        return {
            "filename": filename,
            "file_type": "",
            "text_length": 0,
            "text_preview": "",
            "full_text": "",
            "error": str(e)
        }


def test_extract_pdf_text():
    """测试从PDF文件中提取文本"""
    try:
        # 从配置文件获取静态文件路径
        from config.app_config import STATIC_FILE_PATH
        
        # 构建PDF文件路径
        pdf_file_path = os.path.join(
            STATIC_FILE_PATH, 
            "knowledge", 
            "银行业从业人员职业操守和行为准则.pdf"
        )
        
        # 检查文件是否存在
        if not os.path.exists(pdf_file_path):
            # print(f"错误：文件不存在 - {pdf_file_path}")
            return
        
        # print(f"正在处理PDF文件: {pdf_file_path}")
        
        # 读取PDF文件内容
        with open(pdf_file_path, 'rb') as file:
            file_content = file.read()
        
        # print(f"文件大小: {len(file_content)} 字节")
        
        # 提取文本
        result = extract_text_from_file_content(file_content, "银行业从业人员职业操守和行为准则.pdf")
        

        print(f"文件名: {result['filename']}")
        print(f"文件类型: {result['file_type']}")
        print(f"文本长度: {result['text_length']} 字符")
        
        if 'error' in result:
            print(f"错误信息: {result['error']}")
        else:
            print("\n文本预览:")
            print("-"*30)
            print(result['text_preview'])
            
            # 保存完整文本到文件
            output_file = "extracted_text.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result['full_text'])
            print(f"\n完整文本已保存到: {output_file}")
        
        print("="*50)
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")


if __name__ == '__main__':
    test_extract_pdf_text()
    