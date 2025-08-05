# -*- coding: utf-8 -*-
#  author: ict
import os
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
import json_repair
from config.app_config import CONFIG, STATIC_FILE_PATH
from config.log_config import app_logger

# 从配置文件获取AI服务配置，提供默认值
AI_SERVICE_CONFIG = CONFIG.get('ai_service', {})
AI_BASE_URL = AI_SERVICE_CONFIG.get('base_url', 'http://localhost:18203/v1')
AI_API_KEY = AI_SERVICE_CONFIG.get('key', '')
AI_MODEL_NAME = AI_SERVICE_CONFIG.get('model_name', 'Qwen3-235B-A22B-Instruct-2507-FP8')

client_check = OpenAI(
    api_key=AI_API_KEY,
    base_url=AI_BASE_URL
)


def load_prompt_template(prompt_file: str = "analyze_paper.md") -> str:
    """
    从prompts目录加载提示词模板
    
    Args:
        prompt_file: 提示词文件名，默认为analyze_paper.md
        
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


def calculate_question_score(analysis_task: Dict[str, Any]) -> Dict[str, Any]:
    """
    计算单个题目的得分和正确性
    
    Args:
        analysis_task: 分析任务，包含题目信息和用户答案
        
    Returns:
        包含得分和正确性的字典
    """
    question_type = analysis_task.get('question_type', '')
    user_answer = analysis_task.get('user_answer', '')
    options = analysis_task.get('options', [])
    
    # 每题基础分数
    base_score = 10.0
    
    # 题目类型映射（支持中英文）
    type_mapping = {
        'single_choice': '单选题',
        'multiple_choice': '多选题',
        'true_false': '判断题',
        'fill_blank': '填空题',
        # 反向映射，支持中文类型
        '单选题': '单选题',
        '多选题': '多选题',
        '判断题': '判断题',
        '填空题': '填空题'
    }
    
    # 获取中文题目类型
    chinese_type = type_mapping.get(question_type, question_type)
    
    # 判断题目类型（支持中英文）
    is_single_choice = question_type in ['single_choice', '单选题']
    is_multiple_choice = question_type in ['multiple_choice', '多选题']
    
    if is_single_choice:
        # 单选题：用户答案应该是字符串
        if isinstance(user_answer, list):
            user_answer = user_answer[0] if user_answer else ''
        else:
            user_answer = str(user_answer).strip()
        
        # 获取正确答案
        correct_options = [opt.get('id', '') for opt in options if opt.get('is_correct', False)]
        correct_answer = correct_options[0] if correct_options else ''
            
        # 找到用户选择的选项
        for option in options:
            if option.get('id', '') == user_answer:
                is_correct = option.get('is_correct', False)
                return {
                    'is_correct': is_correct,
                    'score': base_score if is_correct else 0.0,
                    'correct_answer': correct_answer,
                    'explanation': option.get('explanation', ''),
                    'chinese_type': chinese_type
                }
        
        # 用户答案不在选项中
        return {
            'is_correct': False,
            'score': 0.0,
            'correct_answer': correct_answer,
            'explanation': '答案格式错误',
            'chinese_type': chinese_type
        }
        
    elif is_multiple_choice:
        # 多选题：用户答案应该是列表
        if isinstance(user_answer, str):
            # 如果是字符串，转换为列表（兼容旧格式）
            # 处理逗号分隔的字符串，如 "A,B,C,D"
            user_options = set(user_answer.strip().split(','))
        elif isinstance(user_answer, list):
            # 如果是列表，直接使用
            user_options = set(user_answer)
        else:
            # 其他情况，转换为空集合
            user_options = set()
        
        # 获取所有正确答案
        correct_options = {opt.get('id', '') for opt in options if opt.get('is_correct', False)}
        correct_answer = sorted(list(correct_options))  # 返回列表格式
        
        # 检查是否有错误答案
        has_wrong_answer = len(user_options - correct_options) > 0
        # 检查是否答对了所有正确答案
        all_correct_answered = len(correct_options - user_options) == 0
        # 计算答对的正确答案数量
        correct_answered_count = len(user_options & correct_options)
        # 计算正确答案总数
        total_correct_count = len(correct_options)
        
        if has_wrong_answer:
            # 有一个错就是错，得0分
            is_correct = False
            score = 0.0
        elif all_correct_answered and len(user_options) == len(correct_options):
            # 全对且数量匹配，得10分
            is_correct = True
            score = base_score
        elif correct_answered_count > 0:
            # 答对部分正确答案，给5分
            is_correct = True
            score = 5.0
        else:
            # 其他情况，得0分
            is_correct = False
            score = 0.0
        
        return {
            'is_correct': is_correct,
            'score': score,
            'correct_answer': correct_answer,  # 列表格式
            'explanation': f"正确答案包含选项：{', '.join(correct_answer)}",
            'chinese_type': chinese_type
        }
    
    else:
        # 未知题目类型
        # 获取正确答案（如果有的话）
        correct_options = [opt.get('id', '') for opt in options if opt.get('is_correct', False)]
        correct_answer = ''.join(correct_options) if correct_options else ''
        
        return {
            'is_correct': False,
            'score': 0.0,
            'correct_answer': correct_answer,
            'explanation': '未知题目类型',
            'chinese_type': chinese_type
        }


def process_ai_analysis_results(ai_results: Dict[str, Any], analysis_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    处理AI分析结果，结合评分逻辑生成最终结果
    
    Args:
        ai_results: AI模型返回的分析结果
        analysis_tasks: 原始分析任务列表
        
    Returns:
        处理后的分析结果
    """
    # 获取AI返回的results数组
    ai_explanations = ai_results.get('results', [])
    
    # 创建题目ID到AI反馈的映射
    explanation_map = {}
    for item in ai_explanations:
        question_id = str(item.get('question_id', ''))
        explanation_map[question_id] = item.get('explanation', '')
    
    # 处理每个分析任务
    final_results = []
    total_score = 0.0
    correct_count = 0
    
    for task in analysis_tasks:
        question_id = str(task.get('question_id', ''))
        # question_type = task.get('type', '')
        question_text = task.get('question_text', '')
        user_answer = task.get('user_answer', '')
        
        # 计算得分和正确性
        score_info = calculate_question_score(task)
        
        # 获取AI生成的个性化反馈
        ai_feedback = explanation_map.get(question_id, '未能生成个性化反馈')
        
        # 构建最终结果
        result = {
            'question_id': question_id,
            'question_type': score_info['chinese_type'],  # 使用中文题目类型
            'question_text': question_text,
            'user_answer': user_answer,  # 保持原始格式（字符串或列表）
            'is_correct': score_info['is_correct'],
            'score': score_info['score'],
            'correct_answer': score_info['correct_answer'],
            'explanation': ai_feedback  # 使用AI生成的解释
        }
        
        final_results.append(result)
        total_score += score_info['score']
        if score_info['is_correct']:
            correct_count += 1
    
    # 生成整体反馈
    total_count = len(analysis_tasks)
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
    
    # 根据得分生成整体评价
    if total_score >= 90:
        overall_feedback = "专业功底扎实,细节把控近乎完美!"
    elif total_score >= 80:
        overall_feedback = "专业基础良好,对知识点掌握较为全面!"
    elif total_score >= 70:
        overall_feedback = "基本掌握相关知识,仍有提升空间!"
    elif total_score >= 60:
        overall_feedback = "部分知识点掌握,需要加强学习!"
    else:
        overall_feedback = "需要系统复习,建议重点关注错误题目!"
    
    return {
        'analysis_results': final_results,
        'total_score': total_score,
        'correct_count': correct_count,
        'total_count': total_count,
        'overall_feedback': overall_feedback
    }


def analyze_paper_answers(analysis_tasks: List[Dict[str, Any]], prompt_file: str = "analyze_paper.md"):
    """
    批量分析试卷答案，为每道题生成个性化反馈
    
    Args:
        analysis_tasks: 包含题目信息、用户答案和选项的列表
        prompt_file: prompts目录下的提示词文件名，默认为analyze_paper.md
        
    Returns:
        分析结果字典
    """
    start_time = time.time()
    app_logger.info("开始分析试卷答案...")
    
    # 从配置文件读取相关配置，提供合理的默认值
    model_name = AI_MODEL_NAME
    temperature = AI_SERVICE_CONFIG.get('temperature', 0.3)  # 分析任务使用较低的温度
    max_tokens = AI_SERVICE_CONFIG.get('max_tokens', 4000)
    
    # 从prompts目录加载提示词模板
    app_logger.info("加载提示词模板...")
    system_prompt = load_prompt_template(prompt_file)
    
    # 构建输入数据
    input_data = {
        "analysis_tasks": analysis_tasks
    }
    
    # 根据提示词模板构建消息
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请分析以下学员的答卷：\n\n{input_data}"}
    ]

    try:
        app_logger.info("正在调用大模型分析试题，请稍候...")
        llm_start_time = time.time()
        
        response = client_check.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        llm_end_time = time.time()
        llm_duration = llm_end_time - llm_start_time
        app_logger.info(f"大模型调用完成，耗时: {llm_duration:.2f}秒")
        
        result_text = response.choices[0].message.content
        ai_results = json_repair.loads(result_text)
        app_logger.info(f"LLM试卷分析原始输出: {result_text}")
        
        # 处理AI分析结果，结合评分逻辑
        app_logger.info("处理AI分析结果...")
        final_results = process_ai_analysis_results(ai_results, analysis_tasks)
        
        end_time = time.time()
        total_duration = end_time - start_time
        app_logger.info(f"试卷分析完成，总耗时: {total_duration:.2f}秒，总分: {final_results.get('total_score')}, 正确率: {final_results.get('correct_count')}/{final_results.get('total_count')}")
        
        return final_results
        
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time
        app_logger.error(f"试卷分析失败，耗时: {total_duration:.2f}秒，错误: {str(e)}")
        # 如果AI分析失败，使用本地分析作为备选方案



if __name__ == "__main__":

    def test_service():
        """
        测试服务功能
        """
        print("=== 智能训练试卷分析服务测试 ===")

        # 测试1: 加载提示词模板
        print("\n1. 加载提示词模板:")
        try:
            prompt_content = load_prompt_template("analyze_paper.md")
            print(f"提示词模板长度: {len(prompt_content)} 字符")
            print(f"提示词前100字符: {prompt_content[:100]}...")
        except Exception as e:
            print(f"加载提示词失败: {e}")

        # 测试2: 验证输入数据
        print("\n2. 测试输入数据验证:")
        test_tasks = [
            {
                "question_id": "1",
                "type": "single_choice",
                "question_text": "根据《银行业从业人员职业操守和行为准则》，以下哪类人员不属于本准则适用范围？",
                "user_answer": "C",
                "options": [
                    {"id": "A", "text": "境内银行业金融机构的正式员工", "is_correct": False,
                     "explanation": "根据第二条，境内银行业金融机构工作的人员属于本准则适用对象。"},
                    {"id": "B", "text": "被委派至境外分支机构工作的银行员工", "is_correct": False,
                     "explanation": "第二条明确规定，委派到国（境）外分支机构、控（参）股公司工作的人员应当适用本准则。"},
                    {"id": "C", "text": "银行外包服务公司的非派驻人员", "is_correct": True,
                     "explanation": "本准则适用于银行业金融机构及其委派人员，不包括外包公司中未被委派至银行岗位的普通外包人员。"},
                    {"id": "D", "text": "劳务派遣至银行业协会的工作人员", "is_correct": False,
                     "explanation": "第五十一条规定，银行业协会的工作人员及劳务派遣人员参照适用本准则。"}
                ]
            },
            {
                "question_id": "2",
                "type": "multiple_choice",
                "question_text": "关于客户权益保护，以下哪些做法符合《准则》要求？",
                "user_answer": "ADE",
                "options": [
                    {"id": "A", "text": "对残障客户提供优先服务通道", "is_correct": True,
                     "explanation": "第三十七条要求尽可能为残障者提供便利，体现公平对待。"},
                    {"id": "B", "text": "因客户年龄较大而拒绝为其办理复杂业务", "is_correct": False,
                     "explanation": "第三十七条禁止因年龄等因素歧视客户，应公平提供服务。"},
                    {"id": "C", "text": "向客户隐瞒产品可能亏损的风险以促成销售", "is_correct": False,
                     "explanation": "第三十九条严禁隐瞒风险或进行虚假陈述，必须充分披露信息。"},
                    {"id": "D", "text": "耐心处理客户投诉并及时反馈", "is_correct": True,
                     "explanation": "第四十条要求坚持客户至上，认真处理投诉并作出有效反馈。"},
                    {"id": "E", "text": "在客户提出不合理要求时，耐心说明并争取理解", "is_correct": True,
                     "explanation": "第三十六条要求对不合理要求耐心说明，取得理解和谅解。"}
                ]
            }
        ]

        # 测试3: 本地评分功能
        print("\n3. 测试本地评分功能:")
        for i, task in enumerate(test_tasks):
            score_info = calculate_question_score(task)
            print(f"题目{i+1}: 正确性={score_info['is_correct']}, 得分={score_info['score']}, 正确答案={score_info['correct_answer']}")

        # 测试4: AI分析功能（需要配置API密钥）
        print("\n4. 测试AI分析功能:")
        if AI_API_KEY:
            try:
                ai_results = analyze_paper_answers(test_tasks)
                print("AI分析成功!")
                print(f"总分: {ai_results.get('total_score')}")
                print(f"正确题数: {ai_results.get('correct_count')}/{ai_results.get('total_count')}")
                print(f"整体反馈: {ai_results.get('overall_feedback', '')[:100]}...")
            except Exception as e:
                print(f"AI分析失败: {e}")
        else:
            print("未配置AI服务API密钥，跳过AI分析测试")

        print("\n=== 测试完成 ===")
    # 运行测试程序
    test_service()
