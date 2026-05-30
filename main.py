import os
import httpx
from fastapi import FastAPI, HTTPException, Query, Response, Header
from duckduckgo_search import DDGS
from typing import Optional

app = FastAPI(
    title="AI Agent 统一搜索网关",
    description="聚合 Tavily、Jina 和 DDG 的搜索服务"
)

# ================= 安全配置 =================
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")   # ← 新增

# 如果没有设置密钥，发出警告
if not API_SECRET_KEY:
    print("⚠️ 警告：API_SECRET_KEY 未设置，接口处于公开状态，存在被刷风险！")

class AgentSearchAggregator:
    def __init__(self, tavily_key: str):
        self.tavily_key = tavily_key

    async def _search_tavily(self, client: httpx.AsyncClient, query: str) -> str:
        if not self.tavily_key:
            raise ValueError("Tavily API Key 未配置")
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 6,
            "include_answer": True,
        }

        response = await client.post(url, json=payload, timeout=8.0)
        response.raise_for_status()
        data = response.json()

        formatted = f"[Source: Tavily]\nAI Summary: {data.get('answer', '无摘要')}\n\n"
        for r in data.get("results", [])[:5]:
            formatted += f"• {r.get('title')}\n  {r.get('url')}\n  {r.get('content', '')[:280]}...\n\n"
        return formatted.strip()

    async def _search_jina(self, client: httpx.AsyncClient, query: str) -> str:
        url = f"https://r.jina.ai/{query}"
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

    async def aggregate_search(self, query: str) -> str:
        query = query.strip()
        if not query:
            return "❌ 搜索关键词不能为空"

        async with httpx.AsyncClient() as client:
            if self.tavily_key:
                try:
                    return await self._search_tavily(client, query)
                except Exception as e:
                    print(f"[Tavily 失败] {e}")

            try:
                return await self._search_jina(client, query)
            except Exception as e:
                print(f"[Jina 失败] {e}")

            try:
                return self._search_ddg(query)
            except Exception as e:
                return f"❌ 所有搜索通道均失败: {str(e)[:150]}"


# ================= 初始化 =================
aggregator = AgentSearchAggregator(tavily_key=TAVILY_API_KEY)

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "message": "Unified Search API for Agents is running.",
        "tavily_configured": bool(TAVILY_API_KEY),
        "api_key_protected": bool(API_SECRET_KEY)
    }

@app.get("/search")
async def api_search(
    response: Response,
   
