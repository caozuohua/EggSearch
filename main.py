import os
import time
import requests
from fastapi import FastAPI, HTTPException, Query
from duckduckgo_search import DDGS

app = FastAPI(
    title="AI Agent 统一搜索网关", 
    description="聚合 Tavily、Jina 和 DDG 的免额度/省额度路由搜索服务"
)

# --- 1. 把之前的聚合器类粘贴进来 ---
class AgentSearchAggregator:
    def __init__(self, tavily_key=None, cache_duration=600):
        self.tavily_key = tavily_key
        self.cache_duration = cache_duration
        self._cache = {}

    def _get_cached_result(self, query: str) -> str:
        query = query.strip()
        if query in self._cache:
            timestamp, cached_result = self._cache[query]
            if time.time() - timestamp < self.cache_duration:
                return cached_result
            del self._cache[query]
        return None

    def _set_cached_result(self, query: str, result: str):
        query = query.strip()
        if result and "❌" not in result:
            self._cache[query] = (time.time(), result)

    def _search_tavily(self, query: str) -> str:
        if not self.tavily_key:
            raise ValueError("Tavily Key 未配置")
        url = "https://api.tavily.com/search"
        payload = {"api_key": self.tavily_key, "query": query, "include_answer": True}
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        formatted = f"[Source: Tavily AI]\nAI Summary: {data.get('answer', '')}\n\n"
        for r in data.get('results', [])[:3]:
            formatted += f"- {r['title']} ({r['url']}):\n  {r['content']}\n"
        return formatted

    def _search_jina(self, query: str) -> str:
        url = f"https://s.jina.ai/{query}"
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        return f"[Source: Jina Markdown Search]\n{response.text[:2500]}"

    def _search_ddg(self, query: str) -> str:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
        if not results:
            raise Exception("DuckDuckGo 未返回任何结果")
        formatted = "[Source: DuckDuckGo Backup]\n"
        for r in results:
            formatted += f"- {r['title']} ({r['href']}):\n  {r['body']}\n"
        return formatted

    def aggregate_search(self, query: str, strategy: str = "fallback") -> str:
        query = query.strip()
        if not query:
            return "❌ 搜索关键词不能为空"
        
        cached_res = self._get_cached_result(query)
        if cached_res:
            return cached_res
        
        result = ""
        if strategy == "fallback":
            try:
                result = self._search_tavily(query)
            except Exception as e:
                try:
                    result = self._search_jina(query)
                except Exception:
                    try:
                        result = self._search_ddg(query)
                    except Exception as de:
                        result = f"❌ 所有搜索聚合通道均已沦陷。错误根源: {de}"
        
        if result:
            self._set_cached_result(query, result)
        return result

# --- 2. 实例化并配置 API 路由 ---
# 生产环境中，我们通过服务器的环境变量安全传入 Tavily 密钥
TAVILY_KEY = os.getenv("TAVILY_API_KEY", "")
aggregator = AgentSearchAggregator(tavily_key=TAVILY_KEY, cache_duration=600)

@app.get("/search")
async def api_search(
    q: str = Query(..., description="搜索关键词"), 
    strategy: str = Query("fallback", description="搜索策略: fallback 或 fast_only")
):
    """
    智能体调用的统一搜索端点
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    result = aggregator.aggregate_search(q, strategy=strategy)
    return {"query": q, "result": result}

@app.get("/")
async def root():
    return {"status": "healthy", "message": "Unified Search API for Agents is running."}
