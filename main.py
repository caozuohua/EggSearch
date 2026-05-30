import os
import httpx
from fastapi import FastAPI, HTTPException, Query, Response
from duckduckgo_search import DDGS

app = FastAPI(
    title="AI Agent 统一搜索网关",
    description="聚合 Tavily、Jina 和 DDG 的搜索服务"
)

# ================= 配置 =================
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

class AgentSearchAggregator:
    def __init__(self, tavily_key: str):
        self.tavily_key = tavily_key

    async def _search_tavily(self, client: httpx.AsyncClient, query: str) -> str:
        """调用 Tavily API"""
        if not self.tavily_key:
            raise ValueError("Tavily API Key 未配置")

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": "basic",      # basic 或 advanced
            "max_results": 6,
            "include_answer": True,
            "include_raw_content": False
        }

        response = await client.post(url, json=payload, timeout=8.0)
        response.raise_for_status()
        data = response.json()

        # 格式化返回结果
        formatted = f"[Source: Tavily]\nAI Summary: {data.get('answer', '无摘要')}\n\n"
        for r in data.get("results", [])[:5]:
            formatted += f"• {r.get('title')}\n  {r.get('url')}\n  {r.get('content', '')[:280]}...\n\n"
        
        return formatted.strip()

    async def _search_jina(self, client: httpx.AsyncClient, query: str) -> str:
        url = f"https://r.jina.ai/{query}"   # 推荐使用 r.jina.ai
        response = await client.get(url, timeout=6.0)
        response.raise_for_status()
        return f"[Source: Jina Reader]\n{response.text[:2800]}"

    def _search_ddg(self, query: str) -> str:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=4))
        if not results:
            raise Exception("DuckDuckGo 无结果")
        
        formatted = "[Source: DuckDuckGo]\n"
        for r in results:
            formatted += f"• {r['title']}\n  {r['href']}\n  {r['body'][:200]}...\n\n"
        return formatted.strip()

    async def aggregate_search(self, query: str, strategy: str = "fallback") -> str:
        query = query.strip()
        if not query:
            return "❌ 搜索关键词不能为空"

        async with httpx.AsyncClient() as client:
            # 优先尝试 Tavily
            if self.tavily_key:
                try:
                    return await self._search_tavily(client, query)
                except Exception as e:
                    print(f"[Tavily 失败] {e}")

            # 尝试 Jina
            try:
                return await self._search_jina(client, query)
            except Exception as e:
                print(f"[Jina 失败] {e}")

            # 最终兜底 DuckDuckGo
            try:
                return self._search_ddg(query)
            except Exception as e:
                return f"❌ 所有搜索通道均失败。最后错误: {str(e)[:150]}"


# ================= 初始化 =================
aggregator = AgentSearchAggregator(tavily_key=TAVILY_API_KEY)

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "message": "Unified Search API for Agents is running.",
        "tavily_configured": bool(TAVILY_API_KEY),
        "tavily_key_length": len(TAVILY_API_KEY) if TAVILY_API_KEY else 0
    }

@app.get("/search")
async def api_search(
    response: Response,
    q: str = Query(..., description="搜索关键词"),
    strategy: str = Query("fallback", description="搜索策略")
):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = await aggregator.aggregate_search(q, strategy=strategy)

    # 成功结果才缓存
    if "❌" not in result and len(result) > 50:
        response.headers["Cache-Control"] = "public, s-maxage=600, stale-while-revalidate=120"

    return {
        "query": q,
        "strategy": "tavily" if TAVILY_API_KEY and "Tavily" in result else "fallback",
        "result": result
    }
