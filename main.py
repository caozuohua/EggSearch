import os
import time
from fastapi import FastAPI, HTTPException, Query, Response
from duckduckgo_search import DDGS
import httpx  # 引入异步请求库，防止 Vercel 10秒超时

app = FastAPI(
    title="AI Agent 统一搜索网关", 
    description="聚合 Tavily、Jina 和 DDG 的免额度/省额度路由搜索服务"
)

# --- 1. 升级后的异步聚合器类 ---
class AgentSearchAggregator:
    def __init__(self, tavily_key=None):
        self.tavily_key = tavily_key
        # 移除 self._cache = {}，因为 Serverless 环境下内存缓存会失效，改用 Vercel CDN 缓存

    async def _search_tavily(self, client: httpx.AsyncClient, query: str) -> str:
        if not self.tavily_key:
            raise ValueError("Tavily Key 未配置")
        url = "https://tavily.com"
        payload = {"api_key": self.tavily_key, "query": query, "include_answer": True}
        # 严格限制超时为 3.0 秒，防止堆叠超时触发 Vercel 10秒断开
        response = await client.post(url, json=payload, timeout=3.0)
        response.raise_for_status()
        data = response.json()
        formatted = f"[Source: Tavily AI]\nAI Summary: {data.get('answer', '')}\n\n"
        for r in data.get('results', [])[:3]:
            formatted += f"- {r['title']} ({r['url']}):\n  {r['content']}\n"
        return formatted

    async def _search_jina(self, client: httpx.AsyncClient, query: str) -> str:
        url = f"https://jina.ai{query}"
        # 严格限制超时为 3.0 秒
        response = await client.get(url, timeout=3.0)
        response.raise_for_status()
        return f"[Source: Jina Markdown Search]\n{response.text[:2500]}"

    def _search_ddg(self, query: str) -> str:
        # DDGS 目前主要基于同步，放在最后作为最终兜底
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
        if not results:
            raise Exception("DuckDuckGo 未返回任何结果")
        formatted = "[Source: DuckDuckGo Backup]\n"
        for r in results:
            formatted += f"- {r['title']} ({r['href']}):\n  {r['body']}\n"
        return formatted

    async def aggregate_search(self, query: str, strategy: str = "fallback") -> str:
        query = query.strip()
        if not query:
            return "❌ 搜索关键词不能为空"
        
        result = ""
        if strategy == "fallback":
            # 使用 httpx 异步客户端高效管理请求
            async with httpx.AsyncClient() as client:
                try:
                    result = await self._search_tavily(client, query)
                except Exception:
                    try:
                        result = await self._search_jina(client, query)
                    except Exception:
                        try:
                            result = self._search_ddg(query)
                        except Exception as de:
                            result = f"❌ 所有搜索聚合通道均已沦陷。错误根源: {de}"
        return result

# --- 2. 实例化并配置 API 路由 ---
TAVILY_KEY = os.getenv("TAVILY_API_KEY", "")
aggregator = AgentSearchAggregator(tavily_key=TAVILY_KEY)

@app.get("/search")
async def api_search(
    response: Response,  # 注入 Response 对象以操作响应头
    q: str = Query(..., description="搜索关键词"), 
    strategy: str = Query("fallback", description="搜索策略: fallback 或 fast_only")
):
    """
    智能体调用的统一搜索端点
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    result = await aggregator.aggregate_search(q, strategy=strategy)
    
    # 💡 核心优化：如果请求成功且不是报错，利用 Vercel 边缘网络进行 CDN 缓存
    # s-maxage=600 表示在 Vercel 节点上缓存 10 分钟。相同的关键词请求将由 CDN 直接秒回，完全不消耗任何 API 额度和运行时间！
    if result and "❌" not in result:
        response.headers["Cache-Control"] = "public, s-maxage=600, stale-while-revalidate=59"
        
    return {"query": q, "result": result}

@app.get("/")
async def root():
    return {"status": "healthy", "message": "Unified Search API for Agents is running."}
