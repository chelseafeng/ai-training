# -*- coding: utf-8 -*-
#  author: ict
import os
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
import json_repair
from config.app_config import CONFIG, STATIC_FILE_PATH
from config.log_config import app_logger
from utils.file_text_extractor_util import extract_text_from_file_content
from utils.paper_utils import convert_question_type_to_chinese

# 从配置文件获取AI服务配置，提供默认值
AI_SERVICE_CONFIG = CONFIG.get('ai_service', {})
AI_BASE_URL = AI_SERVICE_CONFIG.get('base_url', 'http://localhost:18203/v1')
AI_API_KEY = AI_SERVICE_CONFIG.get('key', '')
AI_MODEL_NAME = AI_SERVICE_CONFIG.get('model_name', 'Qwen3-235B-A22B-Instruct-2507-FP8')

client_check = OpenAI(
    api_key=AI_API_KEY,
    base_url=AI_BASE_URL
)


def load_prompt_template(prompt_file: str) -> str:
    """
    从prompts目录加载提示词模板
    
    Args:
        prompt_file: 提示词文件名
        
    Returns:
        提示词模板内容
    """
    prompt_path = os.path.join(STATIC_FILE_PATH, 'prompts', prompt_file)
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        app_logger.error(f"加载提示词模板失败 {prompt_file}: {str(e)}")
        raise


def load_knowledge_document(doc_file: str) -> str:
    """
    从knowledge_text目录加载知识文档
    
    Args:
        doc_file: 文档文件名
        
    Returns:
        文档内容
    """
    doc_path = os.path.join(STATIC_FILE_PATH, 'knowledge_text', doc_file)
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        app_logger.error(f"加载知识文档失败 {doc_file}: {str(e)}")
        raise


def extract_text_from_documents(doc_files: List[str]) -> str:
    """
    从knowledge目录下的多个文档文件中提取文本内容
    
    Args:
        doc_files: 文档文件名列表
        
    Returns:
        合并后的文档内容
    """
    combined_text = ""
    knowledge_dir = os.path.join(STATIC_FILE_PATH, 'knowledge')
    
    for doc_file in doc_files:
        doc_path = os.path.join(knowledge_dir, doc_file)
        
        if not os.path.exists(doc_path):
            app_logger.warning(f"文档文件不存在: {doc_path}")
            continue
            
        try:
            # 读取文件内容
            with open(doc_path, 'rb') as f:
                file_content = f.read()
            
            # 使用文件文本提取工具提取文本
            extraction_result = extract_text_from_file_content(file_content, doc_file)
            
            if 'error' in extraction_result:
                app_logger.error(f"提取文档 {doc_file} 失败: {extraction_result['error']}")
                continue
                
            extracted_text = extraction_result.get('full_text', '')
            if extracted_text:
                combined_text += f"\n\n=== 文档: {doc_file} ===\n{extracted_text}\n"
                app_logger.info(f"成功提取文档 {doc_file}，文本长度: {extraction_result['text_length']}")
            else:
                app_logger.warning(f"文档 {doc_file} 提取的文本为空")
                
        except Exception as e:
            app_logger.error(f"处理文档 {doc_file} 时发生错误: {str(e)}")
            continue
    
    if not combined_text.strip():
        raise ValueError("没有成功提取到任何文档内容")
    
    return combined_text


def get_available_documents() -> List[str]:
    """
    获取knowledge目录下可用的文档文件列表
    
    Returns:
        可用文档文件名列表
    """
    knowledge_dir = os.path.join(STATIC_FILE_PATH, 'knowledge')
    available_docs = []
    
    if not os.path.exists(knowledge_dir):
        app_logger.warning(f"knowledge目录不存在: {knowledge_dir}")
        return available_docs
    
    try:
        for filename in os.listdir(knowledge_dir):
            file_path = os.path.join(knowledge_dir, filename)
            if os.path.isfile(file_path):
                # 检查文件扩展名
                _, ext = os.path.splitext(filename.lower())
                if ext in ['.pdf', '.docx', '.doc', '.wps', '.wpt', '.txt']:
                    available_docs.append(filename)
        
        app_logger.info(f"找到 {len(available_docs)} 个可用文档")
        return available_docs
        
    except Exception as e:
        app_logger.error(f"获取可用文档列表失败: {str(e)}")
        return []


def get_available_text_documents() -> List[str]:
    """
    获取knowledge_text目录下可用的文本文档列表（保持向后兼容）
    
    Returns:
        可用文本文档文件名列表
    """
    knowledge_text_dir = os.path.join(STATIC_FILE_PATH, 'knowledge_text')
    available_docs = []
    
    if not os.path.exists(knowledge_text_dir):
        app_logger.warning(f"knowledge_text目录不存在: {knowledge_text_dir}")
        return available_docs
    
    try:
        for filename in os.listdir(knowledge_text_dir):
            file_path = os.path.join(knowledge_text_dir, filename)
            if os.path.isfile(file_path) and filename.lower().endswith('.txt'):
                available_docs.append(filename)
        
        app_logger.info(f"找到 {len(available_docs)} 个可用文本文档")
        return available_docs
        
    except Exception as e:
        app_logger.error(f"获取可用文档列表失败: {str(e)}")
        return []


def generate_training_questions(
    text: str = None, 
    doc_file: str = None, 
    doc_files: List[str] = None,
    prompt_file: str = "generate_paper.md"
) -> Dict[str, Any]:
    """
    根据知识文档生成培训测试题
    
    Args:
        text: 直接提供的文本内容（可选）
        doc_file: knowledge_text目录下的文档文件名（可选，保持向后兼容）
        doc_files: knowledge目录下的文档文件名列表（可选）
        prompt_file: prompts目录下的提示词文件名，默认为generate_paper.md
        
    Returns:
        生成的测试题JSON结果
    """
    start_time = time.time()
    app_logger.info("开始生成培训测试题...")
    
    # 从配置文件读取相关配置，提供合理的默认值
    model_name = AI_MODEL_NAME
    temperature = AI_SERVICE_CONFIG.get('temperature', 0.5)
    max_tokens = AI_SERVICE_CONFIG.get('max_tokens', 4000)
    
    # 确定输入文本来源
    if text:
        input_text = text
        app_logger.info("使用直接提供的文本内容")
    elif doc_files:
        # 新方式：从knowledge目录提取多个文档
        app_logger.info(f"开始从 {len(doc_files)} 个文档中提取文本...")
        input_text = extract_text_from_documents(doc_files)
        app_logger.info(f"文档文本提取完成，总长度: {len(input_text)} 字符")
    elif doc_file:
        # 旧方式：从knowledge_text目录读取单个txt文件（保持向后兼容）
        app_logger.info(f"从knowledge_text目录加载文档: {doc_file}")
        input_text = load_knowledge_document(doc_file)
    else:
        # 如果没有指定，使用默认文档
        available_docs = get_available_documents()
        if available_docs:
            default_doc = available_docs[0]
            app_logger.info(f"使用默认文档: {default_doc}")
            input_text = extract_text_from_documents([default_doc])
        else:
            # 尝试使用knowledge_text目录的文档作为后备
            available_text_docs = get_available_text_documents()
            if available_text_docs:
                default_doc = available_text_docs[0]
                app_logger.info(f"使用默认文本文档: {default_doc}")
                input_text = load_knowledge_document(default_doc)
            else:
                raise ValueError("没有可用的知识文档")
    
    # 从prompts目录加载提示词模板
    app_logger.info("加载提示词模板...")
    system_prompt = load_prompt_template(prompt_file)
    
    # 根据提示词模板构建消息
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请根据以下参考文档生成培训测试题：\n\n{input_text}"}
    ]

    try:
        # 第一次尝试
        try:
            app_logger.info("正在调用大模型生成试题，请稍候...")
            llm_start_time = time.time()
            
            response = client_check.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                # max_tokens=max_tokens
            )
            
            llm_end_time = time.time()
            llm_duration = llm_end_time - llm_start_time
            app_logger.info(f"大模型调用完成，耗时: {llm_duration:.2f}秒")
            
            cleaned_text = response.choices[0].message.content
            json_res = json_repair.loads(cleaned_text)
            app_logger.info(f"LLM培训题目生成输出: {json_res}")
            
        except Exception as e:
            # 第一次失败，进行重试
            app_logger.warning(f"JSON解析失败，准备重试: {str(e)}")
            app_logger.info("重新调用大模型生成试题...")
            
            try:
                # 重试一次
                llm_start_time = time.time()
                
                response = client_check.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    # max_tokens=max_tokens
                )
                
                llm_end_time = time.time()
                llm_duration = llm_end_time - llm_start_time
                app_logger.info(f"重试大模型调用完成，耗时: {llm_duration:.2f}秒")
                
                cleaned_text = response.choices[0].message.content
                json_res = json_repair.loads(cleaned_text)
                app_logger.info(f"重试LLM培训题目生成输出: {json_res}")
                
            except Exception as retry_e:
                # 重试也失败，抛出异常
                app_logger.error(f"重试后仍然失败，最终错误: {str(retry_e)}")
                raise retry_e
        
        # 转换题目类型为中文
        app_logger.info("转换题目类型为中文...")
        questions = json_res.get('questions', [])
        for question in questions:
            original_type = question.get('question_type', '')
            chinese_type = convert_question_type_to_chinese(original_type)
            question['question_type'] = chinese_type
            # app_logger.debug(f"题目类型转换: {original_type} -> {chinese_type}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        app_logger.info(f"培训测试题生成完成，总耗时: {total_duration:.2f}秒")
        
        return json_res
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        app_logger.error(f"培训题目生成失败，耗时: {total_duration:.2f}秒，错误: {str(e)}")
        raise


if __name__ == "__main__":
    # 运行测试程序

    def test_service():
        """
        测试服务功能
        """
        print("=== 智能训练题目生成服务测试 ===")

        # 测试1: 获取可用文档
        print("\n1. 获取可用文档列表:")
        available_docs = get_available_documents()
        print(f"knowledge目录可用文档: {available_docs}")
        
        available_text_docs = get_available_text_documents()
        print(f"knowledge_text目录可用文档: {available_text_docs}")

        # 测试2: 加载提示词模板
        print("\n2. 加载提示词模板:")
        try:
            prompt_content = load_prompt_template("generate_paper.md")
            print(f"提示词模板长度: {len(prompt_content)} 字符")
            print(f"提示词前100字符: {prompt_content[:100]}...")
        except Exception as e:
            print(f"加载提示词失败: {e}")

        # 测试3: 文档文本提取
        if available_docs:
            print(f"\n3. 测试文档文本提取 ({available_docs[0]}):")
            try:
                combined_text = extract_text_from_documents([available_docs[0]])
                print(f"提取文本长度: {len(combined_text)} 字符")
                print(f"文本前200字符: {combined_text[:200]}...")
            except Exception as e:
                print(f"文本提取失败: {e}")

        # 测试4: 生成培训题目（需要配置API密钥）
        print("\n4. 测试题目生成功能:")
        import time
        start_time = time.time()
        if AI_API_KEY:
            try:
                if available_docs:
                    # result = generate_training_questions(doc_files=[available_docs[0]])
                    result = generate_training_questions(doc_files=[available_docs[0]])
                    endtime = time.time() - start_time
                    print(f"耗时：{endtime}s”")
                    print("题目生成成功!")
                    print(f"生成的题目数量: {len(result.get('questions', []))}")
                    # 显示第一道题
                    if result.get('questions'):
                        first_question = result['questions'][0]
                        print(f"第一道题: {first_question.get('question_text', '')[:100]}...")
                else:
                    print("没有可用的文档进行测试")
            except Exception as e:
                print(f"题目生成失败: {e}")
        else:
            print("未配置AI服务API密钥，跳过题目生成测试")

        print("\n=== 测试完成 ===")


    test_service()
