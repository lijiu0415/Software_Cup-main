"""
知识图谱数据初始化
加载《人工智能导论》《软件安全技术》双课程知识图谱（文档见 docs/ 目录）
"""
import json
import os
from sqlalchemy.ext.asyncio import AsyncSession
from db import crud

# 双课程加载：false 时同时加载《软件安全技术》知识图谱。
_EXCLUDE_SOFTWARE_SECURITY = False


def _find_json_files():
    """查找知识图谱JSON文件（默认排除软件安全技术）"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_files = []
    for parent in [os.path.dirname(current_dir),                          # Docker: /app
                   os.path.dirname(os.path.dirname(current_dir))]:        # 本地: 项目根
        docs_dir = os.path.join(parent, "docs")
        if os.path.exists(docs_dir):
            for fname in os.listdir(docs_dir):
                if fname.endswith("知识图谱.json") or fname.endswith("知识图谱数据.json"):
                    if _EXCLUDE_SOFTWARE_SECURITY and "软件安全" in fname:
                        continue
                    full_path = os.path.join(docs_dir, fname)
                    if full_path not in json_files:
                        json_files.append(full_path)
        if json_files:
            break
    return json_files


def _load_all_kg() -> list:
    """加载所有课程知识图谱，返回 [(course_name, kps, deps), ...]"""
    courses = []
    json_files = _find_json_files()

    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            course_name = data.get("course", os.path.basename(fpath))
            kps = data.get("knowledge_points", [])
            deps = data.get("dependencies", [])
            courses.append((course_name, kps, deps))
        except Exception as e:
            print(f"[KG] 加载失败: {fpath}: {e}")

    if not courses:
        courses.append(("人工智能导论", [], []))
    return courses


async def init_kg_data(db: AsyncSession):
    """初始化双课程知识图谱到数据库"""
    existing = await crud.get_knowledge_points(db)
    if existing:
        print(f"知识图谱已有 {len(existing)} 个知识点，跳过初始化")
        return

    courses = _load_all_kg()
    total_kps = 0
    total_deps = 0

    for course_name, kps, deps in courses:
        # 按课程名生成前缀
        prefix_map = {
            "人工智能导论": "ai_",
            "软件安全技术": "sc_",
        }
        prefix = prefix_map.get(course_name, "xx_")

        # 为知识点添加 course 字段 + ID 前缀
        for kp in kps:
            kp["course"] = course_name
            kp["kp_id"] = prefix + kp["kp_id"]
            kp["chapter_id"] = prefix + kp.get("chapter_id", "")

        # 为依赖添加 ID 前缀
        for dep in deps:
            dep["course"] = course_name
            dep["from_kp_id"] = prefix + dep["from_kp_id"]
            dep["to_kp_id"] = prefix + dep["to_kp_id"]
            dep.setdefault("edge_id", f"dep_{dep['from_kp_id']}_{dep['to_kp_id']}")

        if kps:
            await crud.bulk_create_kps(db, kps)
            total_kps += len(kps)
        if deps:
            await crud.bulk_create_dependencies(db, deps)
            total_deps += len(deps)

        print(f"[KG] {course_name}: {len(kps)} 知识点, {len(deps)} 依赖")

    await db.commit()
    print(f"知识图谱初始化完成: 共 {len(courses)} 门课程, {total_kps} 知识点, {total_deps} 依赖")
