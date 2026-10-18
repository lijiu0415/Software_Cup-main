"""
智能体统一消息格式 - 基于Astron MCP协议
"""
import uuid
import time
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AgentMessage(BaseModel):
    """智能体间通信消息标准格式"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""                    # 发送者Agent名称
    receiver: str = ""                  # 接收者Agent名称
    timestamp: float = Field(default_factory=time.time)
    task_type: str = ""                 # 任务标识
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"             # pending/success/fail

    # payload 标准字段:
    # student_id: str
    # kp_id: str
    # student_profile: dict
    # mastery_data: list[dict{kp_id, mastery}]
    # content: str (生成内容)
    # resource_type: str (lesson/exercise/code/mindmap)


class AgentPayload(BaseModel):
    """消息载荷标准结构"""
    student_id: str = ""
    kp_id: str = ""
    student_profile: Dict[str, Any] = Field(default_factory=dict)
    mastery_data: List[Dict[str, float]] = Field(default_factory=list)
    content: str = ""
    resource_type: str = ""
    extra: Dict[str, Any] = Field(default_factory=dict)


def create_message(
    sender: str,
    receiver: str,
    task_type: str,
    payload: dict,
    status: str = "pending"
) -> AgentMessage:
    """创建标准消息"""
    return AgentMessage(
        sender=sender,
        receiver=receiver,
        task_type=task_type,
        payload=payload,
        status=status,
    )
