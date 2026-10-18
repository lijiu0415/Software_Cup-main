"""
Chroma向量库客户端 - RAG检索
"""
import os
import json
from typing import List, Optional, Dict
import chromadb
from chromadb.config import Settings
from config import settings


class ChromaClient:
    """Chroma向量库客户端"""

    def __init__(self):
        self.client = None
        self.collection = None

    def connect(self):
        """连接Chroma"""
        chroma_url = settings.CHROMA_URL.replace("http://", "")
        host, port = chroma_url.split(":") if ":" in chroma_url else (chroma_url, "8000")

        self.client = chromadb.HttpClient(
            host=host,
            port=int(port),
        )

        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, documents: List[str], metadatas: List[dict] = None):
        """添加文档到向量库"""
        if not self.collection:
            self.connect()

        ids = [f"doc_{i}" for i in range(len(documents))]
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas or [{}] * len(documents),
        )

    def query(self, query_text: str, n_results: int = 5) -> List[Dict]:
        """向量检索"""
        if not self.collection:
            self.connect()

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )

        formatted = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })
        return formatted

    def count(self) -> int:
        """获取文档数量"""
        if not self.collection:
            self.connect()
        return self.collection.count()


# 全局客户端
chroma_client = ChromaClient()
_rag_initialized = False


async def ensure_rag_ready():
    """确保RAG已初始化（懒加载，首次查询时自动触发）"""
    global _rag_initialized
    if not _rag_initialized:
        try:
            if chroma_client.count() == 0:
                await init_rag_data()
        except Exception:
            pass
        _rag_initialized = True


async def init_rag_data():
    """初始化RAG知识库数据"""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # backend/rag/

    # 兼容 Docker (knowledge_base → /app/knowledge_base) 和本地环境
    kb_dir = None
    for parent in [
        os.path.dirname(current_dir),                              # Docker: /app
        os.path.dirname(os.path.dirname(current_dir)),             # 本地: 项目根
    ]:
        candidate = os.path.join(parent, "knowledge_base")
        if os.path.exists(candidate):
            kb_dir = candidate
            break

    if not kb_dir:
        print("RAG: 未找到知识库目录")
        return

    documents = []
    metadatas = []

    # 读取章节讲义
    chapters_dir = os.path.join(kb_dir, "chapters")
    if os.path.exists(chapters_dir):
        for fname in os.listdir(chapters_dir):
            if fname.endswith(".md"):
                with open(os.path.join(chapters_dir, fname), "r", encoding="utf-8") as f:
                    content = f.read()
                    # 简单切片
                    chunks = _split_text(content, 500)
                    for chunk in chunks:
                        documents.append(chunk)
                        metadatas.append({"source": fname, "type": "chapter"})

    # 读取习题
    ex_file = os.path.join(kb_dir, "exercises", "exercises.json")
    if os.path.exists(ex_file):
        with open(ex_file, "r", encoding="utf-8") as f:
            exercises = json.load(f)
            for ex in exercises:
                doc = f"题目: {ex['question']}\n答案: {ex['answer']}"
                documents.append(doc)
                metadatas.append({"source": ex["ex_id"], "type": "exercise", "kp_id": ex.get("kp_id", "")})

    # 读取代码案例
    code_file = os.path.join(kb_dir, "code_demos", "code_demos.json")
    if os.path.exists(code_file):
        with open(code_file, "r", encoding="utf-8") as f:
            demos = json.load(f)
            for demo in demos:
                doc = f"代码: {demo['title']}\n{demo['code']}"
                documents.append(doc)
                metadatas.append({"source": demo["demo_id"], "type": "code", "kp_id": demo.get("kp_id", "")})

    if documents:
        chroma_client.add_documents(documents, metadatas)
        print(f"RAG知识库初始化完成: {len(documents)} 篇文档")
    else:
        print("RAG: 未找到知识库文档")


def _split_text(text: str, chunk_size: int = 500) -> List[str]:
    """简单文本切片"""
    chunks = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current += para + "\n\n"
        else:
            if current:
                chunks.append(current.strip())
            current = para + "\n\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks
