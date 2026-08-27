import re
import requests
import trafilatura
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

class ContentScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_static(self, url: str) -> Optional[str]:
        # Fast 2.0-second non-blocking fetch
        if url.endswith('.pdf'):
            return None
        try:
            resp = requests.get(url, headers=self.headers, timeout=2.0)
            if resp.status_code == 200 and resp.text:
                extracted = trafilatura.extract(resp.text, include_links=False, include_images=False)
                if extracted and len(extracted.strip()) > 150:
                    return extracted.strip()
        except Exception:
            pass
        return None

    def fetch_content(self, url: str) -> str:
        text = self.fetch_static(url)
        return text if text else ""

    def fetch_batch_parallel(self, items: List[Any], max_workers: int = 8) -> List[Dict[str, Any]]:
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(self.fetch_content, item.url): item
                for item in items
            }
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    text = future.result()
                    if text and len(text.strip()) >= 150:
                        results.append({"item": item, "text": text})
                except Exception:
                    pass
        return results

scraper = ContentScraper()
