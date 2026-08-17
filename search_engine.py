import urllib.parse
import requests
from typing import List, Dict, Any
from urllib.parse import urlparse
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from config import settings
from models import SearchResultItem

TRUSTED_DOMAINS = {
    # 1. Peer-reviewed journals & Academic publishers
    "nature.com": 0.98,
    "arxiv.org": 0.98,
    "ieee.org": 0.98,
    "acm.org": 0.98,
    "springer.com": 0.98,
    "sciencedirect.com": 0.98,
    "mdpi.com": 0.95,
    "frontiersin.org": 0.95,
    "plos.org": 0.95,
    "cell.com": 0.98,
    "pnas.org": 0.98,
    "researchgate.net": 0.85,
    # 2. Government & University publications
    "edu": 0.95,
    "gov": 0.95,
    "gov.in": 0.95,
    "ac.in": 0.95,
    "icar.org.in": 0.95,
    "tn.gov.in": 0.95,
    "usda.gov": 0.95,
    "nih.gov": 0.95,
    # 3. International Organizations
    "fao.org": 0.90,
    "who.int": 0.90,
    "worldbank.org": 0.90,
    "un.org": 0.90,
    "unesco.org": 0.90,
    "org": 0.85,
    # 4. News & Industry
    "reuters.com": 0.80,
    "bloomberg.com": 0.80,
    "bbc.com": 0.80,
    "apnews.com": 0.80,
    "wsj.com": 0.80,
    "ft.com": 0.80,
    "wikipedia.org": 0.70
}

def compute_domain_score(url: str) -> float:
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Exact match
        if domain in TRUSTED_DOMAINS:
            return TRUSTED_DOMAINS[domain]
        
        # TLD match
        tld = domain.split(".")[-1]
        if tld in TRUSTED_DOMAINS:
            return TRUSTED_DOMAINS[tld]
            
        return 0.5
    except Exception:
        return 0.4

class SearchEngine:
    def __init__(self):
        self.primary_provider = settings.PRIMARY_SEARCH.lower()
        self.searxng_url = settings.SEARXNG_URL
        self.tavily_key = settings.TAVILY_API_KEY

    def search_ddgs(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        def _do_ddg():
            res = []
            with DDGS(timeout=4) as ddgs:
                for item in ddgs.text(query, max_results=max_results):
                    res.append({
                        "url": item.get("href", ""),
                        "title": item.get("title", ""),
                        "snippet": item.get("body", "")
                    })
            return res

        from concurrent.futures import ThreadPoolExecutor
        try:
            with ThreadPoolExecutor(max_workers=1) as exec:
                fut = exec.submit(_do_ddg)
                results = fut.result(timeout=5.0)
        except Exception as e:
            print(f"[SearchEngine] DDGS search timeout/error for '{query}': {e}")
        return results

    def search_searxng(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        try:
            params = {
                "q": query,
                "format": "json"
            }
            url = f"{self.searxng_url.rstrip('/')}/search"
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", [])[:max_results]:
                    results.append({
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "snippet": item.get("content", "")
                    })
        except Exception as e:
            print(f"[SearchEngine] SearxNG search error for '{query}': {e}")
        return results

    def search_tavily(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        if not self.tavily_key:
            return results
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "max_results": max_results
                },
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    results.append({
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "snippet": item.get("content", "")
                    })
        except Exception as e:
            print(f"[SearchEngine] Tavily search error for '{query}': {e}")
        return results

    def search(self, query: str, sub_question_id: str, max_results: int = 5) -> List[SearchResultItem]:
        raw_results = []
        
        # Provider execution chain
        if self.primary_provider == "searxng":
            raw_results = self.search_searxng(query, max_results)
            if not raw_results:
                raw_results = self.search_ddgs(query, max_results)
        elif self.primary_provider == "tavily":
            raw_results = self.search_tavily(query, max_results)
            if not raw_results:
                raw_results = self.search_ddgs(query, max_results)
        else:  # Default to ddgs
            raw_results = self.search_ddgs(query, max_results)
            if not raw_results:
                raw_results = self.search_searxng(query, max_results)

        items = []
        for res in raw_results:
            if res.get("url"):
                items.append(SearchResultItem(
                    url=res["url"],
                    title=res.get("title", "Untitled"),
                    snippet=res.get("snippet", ""),
                    sub_question_id=sub_question_id
                ))
        return items

search_engine = SearchEngine()
