"""
知识图谱引擎 - 前置校验、路径计算、掌握度追踪
"""
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, deque
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from db import crud
from db.models import KnowledgePoint, KpDependency, StudentMastery
from config import settings


class KnowledgeGraphEngine:
    """知识图谱引擎"""

    def __init__(self):
        self.threshold = settings.MASTERY_THRESHOLD

    async def check_prerequisites(
        self, db: AsyncSession, kp_id: str, student_id: str
    ) -> Tuple[bool, List[Dict]]:
        """
        前置知识点校验

        Returns:
            (是否可学习, 缺失的前置知识点列表)
        """
        # 获取所有强依赖前置知识点
        prereq_ids = await crud.get_prerequisites(db, kp_id)

        if not prereq_ids:
            return True, []

        # 查询每个前置知识点的掌握度
        lack_kps = []
        for pre_id in prereq_ids:
            mastery_record = await crud.get_student_mastery(db, student_id, pre_id)
            kp = await crud.get_knowledge_point(db, pre_id)

            current_mastery = mastery_record.mastery if mastery_record else 0.0

            if current_mastery < self.threshold:
                lack_kps.append({
                    "kp_id": pre_id,
                    "name": kp.name if kp else pre_id,
                    "mastery": current_mastery,
                    "threshold": self.threshold,
                })

        is_ok = len(lack_kps) == 0
        return is_ok, lack_kps

    async def compute_learning_path(
        self, db: AsyncSession, student_id: str,
        student_profile: Dict = None,
        course: str = None,
    ) -> List[Dict]:
        """
        自适应学习路径算法

        算法：DAG拓扑排序 + 掌握度加权 + 学习速度/风格适配
        筛选规则：掌握度 < 0.6 && 所有强前置知识点掌握度 >= 0.6
        排序规则：按知识点难度 + 依赖权重 + 学习速度偏好 综合排序
        """
        # 提取学生特征
        learn_speed = 3
        base_level = 3
        if student_profile:
            learn_speed = student_profile.get("learn_speed", 3)
            base_level = student_profile.get("base_level", 3)
        # 获取所有知识点（按课程过滤，course 为空时返回全部）
        all_kps = await crud.get_knowledge_points(db, course=course)
        if not all_kps:
            return []

        # 获取所有依赖关系
        all_deps = await crud.get_all_dependencies(db)

        # 获取学生所有掌握度
        all_masteries = await crud.get_all_student_masteries(db, student_id)
        mastery_map = {m.kp_id: m.mastery for m in all_masteries}
        completed_map = {m.kp_id: m.completed for m in all_masteries}

        # 构建邻接表和入度表
        adj = defaultdict(list)       # from -> [to]
        in_degree = defaultdict(int)
        dep_weights = {}              # (from, to) -> weight

        for dep in all_deps:
            adj[dep.from_kp_id].append(dep.to_kp_id)
            in_degree[dep.to_kp_id] += 1
            dep_weights[(dep.from_kp_id, dep.to_kp_id)] = dep.weight

        # 筛选可学习的知识点
        learnable = []
        for kp in all_kps:
            kp_id = kp.kp_id
            current_mastery = mastery_map.get(kp_id, 0.0)

            # 条件1: 已完成学习
            if completed_map.get(kp_id, False):
                continue

            # 条件2: 所有前置知识点已掌握
            prereq_ids = await crud.get_prerequisites(db, kp_id)
            all_prereqs_mastered = True
            for pre_id in prereq_ids:
                pre_mastery = mastery_map.get(pre_id, 0.0)
                if pre_mastery < self.threshold:
                    all_prereqs_mastered = False
                    break

            if all_prereqs_mastered:
                # 计算优先级分数
                avg_dep_weight = 0.5
                if prereq_ids:
                    weights = [dep_weights.get((p, kp_id), 0.5) for p in prereq_ids]
                    avg_dep_weight = sum(weights) / len(weights)

                # 速度偏好：学得快的学生，高难度内容权重更高
                speed_bonus = (learn_speed - 3) * 0.3
                # 基础水平：基础好的学生优先推送难度匹配的内容
                level_match = 1.0 - abs(kp.difficulty - base_level) * 0.15

                priority = ((6 - kp.difficulty) * avg_dep_weight + speed_bonus) * level_match

                learnable.append({
                    "kp_id": kp_id,
                    "name": kp.name,
                    "description": kp.description,
                    "chapter_id": kp.chapter_id,
                    "difficulty": kp.difficulty,
                    "mastery": current_mastery,
                    "completed": completed_map.get(kp_id, False),
                    "priority_score": round(priority, 2),
                })

        # 按优先级分数降序排列
        learnable.sort(key=lambda x: x["priority_score"], reverse=True)
        return learnable

    async def get_related_knowledge_points(
        self, db: AsyncSession, kp_id: str
    ) -> List[Dict]:
        """获取相关知识点（前置+后置）"""
        prereq_ids = await crud.get_prerequisites(db, kp_id)

        # 查询后置知识点
        result = await db.execute(
            select(KpDependency.from_kp_id).where(KpDependency.to_kp_id == kp_id)
        )
        post_ids = result.scalars().all()

        related_ids = list(set(prereq_ids + list(post_ids)))
        related = []
        for rid in related_ids[:10]:
            kp = await crud.get_knowledge_point(db, rid)
            if kp:
                related.append({
                    "kp_id": kp.kp_id,
                    "name": kp.name,
                    "description": kp.description,
                })
        return related

    async def update_mastery_after_learning(
        self, db: AsyncSession, student_id: str, kp_id: str, score: float, completed: bool = False
    ):
        """学习完成后更新掌握度"""
        if completed:
            new_mastery = 1.0
        else:
            existing = await crud.get_student_mastery(db, student_id, kp_id)
            if existing:
                new_mastery = existing.mastery * 0.6 + score * 0.4
            else:
                new_mastery = score * 0.4
            new_mastery = min(1.0, max(0.0, new_mastery))

        await crud.upsert_mastery(db, student_id, kp_id, new_mastery, completed=completed)
        await db.commit()


# 全局知识图谱引擎
kg_engine = KnowledgeGraphEngine()
