"""
敏感词过滤 - 集成讯飞星火敏感词过滤接口
对用户输入和AI输出进行检测
"""
import re
from typing import Tuple

# 基础敏感词列表（本地兜底）
SENSITIVE_WORDS = [
    "暴力", "色情", "赌博", "毒品", "诈骗", "黑客",
    "攻击", "破解", "盗版", "非法", "违禁",
]


def check_sensitive(text: str) -> Tuple[bool, str]:
    """
    检测文本是否包含敏感词

    Returns:
        (是否包含敏感词, 触发的敏感词)
    """
    if not text:
        return False, ""

    for word in SENSITIVE_WORDS:
        if word in text:
            return True, word

    return False, ""


def filter_sensitive(text: str) -> str:
    """过滤敏感词，替换为*"""
    result = text
    for word in SENSITIVE_WORDS:
        result = result.replace(word, "*" * len(word))
    return result


async def check_sensitive_async(text: str) -> Tuple[bool, str]:
    """异步检测（预留讯飞API接口）"""
    # TODO: 集成讯飞星火敏感词过滤API
    return check_sensitive(text)
