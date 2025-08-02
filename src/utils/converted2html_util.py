# -*- coding: utf-8 -*-
#  author: ict

import os
import re
import tempfile
import uuid
from io import BytesIO

from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text_to_fp
from spire.doc import Document, FileFormat

from config.app_config import STATIC_FILE_PATH
from config.log_config import app_logger



class ConversionExtraUtil:
    @staticmethod
    def replace_div_with_p(html_content):
        # 解析 HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 找到所有 div 标签
        divs = soup.find_all('div')

        for div in divs:
            # 创建一个新的 p 标签，并复制 div 的内容和属性
            p_tag = soup.new_tag('p')

            # 复制 div 的所有属性到 p 标签
            for attr, value in div.attrs.items():
                p_tag[attr] = value

            # 复制 div 的所有子元素到 p 标签
            p_tag.extend(div.contents)

            # 用 p 标签替换 div 标签
            div.replace_with(p_tag)

        # 返回修改后的 HTML
        return str(soup)
    @staticmethod
    def remove_div_tags(html_content):
        # 解析 HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 找到 body 标签
        body = soup.body
        if not body:
            return html_content  # 如果没有 body 标签，直接返回原内容

        # 遍历 body 下的所有直接子标签
        for child in list(body.children):
            # 如果是 div 标签，则提取其内容并替换
            if child.name == 'div':
                # 用 div 的内容替换 div 标签本身
                child.unwrap()

        # 返回处理后的 HTML
        return str(soup)

    @staticmethod
    def remove_page_numbers(html_content):
        # 解析 HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 找到 body 标签
        body = soup.body
        if not body:
            return html_content  # 如果没有 body 标签，直接返回原内容

        # 改进1：使用 string 参数替代已废弃的 text 参数
        # 改进2：扩展匹配模式，包括 "Page:"、"Page " 等多种形式
        # 改进3：同时查找包含页码的 div 标签
        page_patterns = [
            lambda s: s and any(s.strip().startswith(p) for p in ['Page ', 'Page:', 'Page：']),
            lambda s: s and any(p in s.strip() for p in ['Page ', 'Page:', 'Page：'])
        ]

        # 查找所有包含页码文本的标签
        for pattern in page_patterns:
            for tag in body.find_all(string=pattern):
                # 移除包含页码的整个父标签（通常是div或span）
                parent = tag.parent
                if parent:
                    parent.decompose()

        # 额外处理：查找包含页码链接的标签（如 <a href="#1">1</a>）
        for a_tag in body.find_all('a', href=lambda x: x and x.startswith('#')):
            if a_tag.string and a_tag.string.isdigit():
                parent_div = a_tag.find_parent('div')
                if parent_div and any(p in parent_div.get_text() for p in ['Page', 'page']):
                    parent_div.decompose()

        # 返回处理后的 HTML
        return str(soup)
    @staticmethod
    def remove_all_class_attributes(html_content):
        """
        去除 HTML body 中所有标签的 class 属性

        参数:
            html_content (str): 原始 HTML 内容

        返回:
            str: 处理后的 HTML 内容
        """
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 找到 body 标签，如果不存在则处理整个文档
        body = soup.find('body')
        target = body if body else soup

        # 找到目标范围内的所有标签并移除 class 属性
        for tag in target.find_all(True):  # True 表示匹配所有标签
            if 'class' in tag.attrs:
                del tag.attrs['class']

        # 返回处理后的 HTML 字符串
        return str(soup)


    @staticmethod
    def handling_fonts_and_lines(html_content: str) -> str:
        """
        处理HTML内容：
        1. 转换特定字体族
        2. 将黑色线条改为红色
        """
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. 处理字体转换
        font_mapping = {
            'simhei': '黑体',
            'simsun-bold': '宋体',
            'fangsong_gb2312': '仿宋'
        }

        for span in soup.find_all('span', style=True):
            style = span['style']

            # 处理字体转换（忽略大小写）
            font_family_match = re.search(r'font-family:\s*([^;]+)', style, re.IGNORECASE)
            if font_family_match:
                original_font = font_family_match.group(1).lower()
                for key, value in font_mapping.items():
                    if key in original_font:
                        # 替换字体
                        new_style = re.sub(
                            r'(font-family:\s*)([^;]+)',
                            f'\\1"{value}"',
                            style,
                            flags=re.IGNORECASE
                        )
                        span['style'] = new_style
                        break

            # 2. 处理线条颜色（将黑色改为红色）
            if 'border:' in style and 'black' in style:
                span['style'] = style.replace('black', 'red')

        return str(soup)


class DocumentConverter:

    @staticmethod
    def convert_word_to_html(word_file: str):
        """
        将 Word 文档转换为 HTML，并将结果保存到内存中
        :param word_file: Word 文件路径
        :return: 转换后的 HTML 内容
        """
        # 检查文件是否存在
        if not os.path.exists(word_file):
            raise FileNotFoundError(f"文件不存在: {word_file}")

        # 使用临时目录处理文件转换
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 在临时目录中生成 HTML 文件名
                temp_html_file = os.path.join(temp_dir, f"{uuid.uuid4()}.html")
                
                # 加载 Word 文档
                doc = Document()
                doc.LoadFromFile(word_file)
                
                # 将 Word 文档保存为 HTML 文件到临时目录
                doc.SaveToFile(temp_html_file, FileFormat.Html)
                doc.Close()
                
                # 读取 HTML 文件内容并去掉水印信息
                with open(temp_html_file, 'r', encoding='utf-8') as f:
                    data = f.read()
                    data = data.replace('Evaluation Warning: The document was created with Spire.Doc for Python.', '')
                
                # 处理 HTML 内容并返回
                res = ConversionExtraUtil.remove_all_class_attributes(data)
                app_logger.info(f"Word转HTML完成，临时文件已自动清理: {temp_html_file}")
                return res
                
            except Exception as e:
                app_logger.error(f"Word转HTML失败: {str(e)}")
                raise
            # 临时目录和其中的所有文件会在 with 语句结束时自动删除

    def truncate_log_content(self, content: str, max_length: int = 500) -> str:
        """
        截断日志内容，避免过长的HTML或其他内容影响日志可读性

        Args:
            content: 需要截断的内容
            max_length: 最大长度，默认500字符

        Returns:
            截断后的内容
        """
        if not content or not isinstance(content, str):
            return str(content)

        # 去除多余的空白字符
        content = re.sub(r'\s+', ' ', content.strip())

        if len(content) <= max_length:
            return content

        # 截断内容并添加省略号
        truncated = content[:max_length]
        return f"{truncated}...[内容已截断，总长度：{len(content)}字符]"
    def convert_pdf_to_html(self, pdf_file: str, ):

        if not os.path.exists(pdf_file):
            raise FileNotFoundError(f"文件不存在: {pdf_file}")

        output_buffer = BytesIO()

        # Convert the PDF to HTML and write the HTML to the buffer
        with open(pdf_file, 'rb') as pdf_file:
            extract_text_to_fp(pdf_file, output_buffer, output_type='html')

        # Retrieve the HTML content from the buffer
        html_content = output_buffer.getvalue().decode('utf-8')
        html_content = ConversionExtraUtil.remove_div_tags(html_content)
        res = ConversionExtraUtil.remove_page_numbers(html_content)
        res = ConversionExtraUtil.remove_all_class_attributes(res)
        app_logger.info("开始转换字体和线条")
        res = ConversionExtraUtil.handling_fonts_and_lines(res)

        app_logger.info(f"PDF转成HTML：{self.truncate_log_content(res)}")
        return res

if __name__ == '__main__':
    # file_dir = "D://H2025//docu//公文测试文档//数字政务发展规划.wpt"
    # file_dir = "D://H2025//docu//公文测试文档//中国电子首席.docx"
    file_dir = "D://H2025//docu//公文测试文档//中国电子首席科学家TEST.wps"
    # D:\H2025\docu\公文测试文档
    res = DocumentConverter.convert_word_to_html(file_dir)
    print(res)
    from spire.doc import *
    from spire.doc.common import *

    # Create a Document object
    document = Document()

    # Load a Word file from disk
    document.LoadFromFile(file_dir)

    # Save the Word file in txt format
    document.SaveToFile("docxToTxt.txt", FileFormat.Txt)
    document.Close()




