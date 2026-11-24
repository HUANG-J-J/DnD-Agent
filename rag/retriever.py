"""规则书向量检索。

建索引（项目根目录，先跑过 python -m rag.ingest）：
    python -m rag.retriever

在代码里用：
    retriever = Retriever()
    retriever.search("grapple a creature", k=5)
"""

import json
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

RAG_DIR = Path(__file__).resolve().parent
CHUNKS_PATH = RAG_DIR / "chunks.jsonl"
EMB_PATH = RAG_DIR / "embeddings.npy"
CACHE_DIR = RAG_DIR.parent / ".cache" / "fastembed"
MODEL_NAME = "BAAI/bge-small-en-v1.5"


def load_chunks():
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def chunk_to_text(chunk):
    # 标题路径一起参与向量化：正文里不一定会重复标题里的关键词
    return f"{chunk['title']}\n{chunk['text']}"


def load_model():
    return TextEmbedding(MODEL_NAME, cache_dir=str(CACHE_DIR))


def build_index():
    chunks = load_chunks()
    model = load_model()
    # batch_size 默认 256，长块多时内存会爆（onnxruntime 报 bad allocation），调小
    texts = [chunk_to_text(c) for c in chunks]
    vectors = np.array(list(model.embed(texts, batch_size=32)), dtype=np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)   # 归一化后，点积就是余弦相似度
    np.save(EMB_PATH, vectors)
    print(f"{len(chunks)} 块 → {vectors.shape}，写入 {EMB_PATH}")


class Retriever:
    def __init__(self):
        self.chunks = load_chunks()
        self.vectors = np.load(EMB_PATH)
        if len(self.chunks) != len(self.vectors):
            raise RuntimeError("chunks.jsonl 和 embeddings.npy 数量对不上，请重新运行 python -m rag.retriever")
        self.model = load_model()

    def search(self, query: str, k: int = 5) -> list[dict]:
        q = np.array(next(iter(self.model.query_embed(query))), dtype=np.float32)
        q /= np.linalg.norm(q)
        scores = self.vectors @ q                   # 和每一块的相似度，一次算完
        top = np.argsort(-scores)[:k]
        return [{**self.chunks[i], "score": float(scores[i])} for i in top]


if __name__ == "__main__":
    build_index()
