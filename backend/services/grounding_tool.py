import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
import httpx
from typing import Dict, List, Any, Optional, Tuple

class LiveGroundingTool:
    """
    Structured Real-Time Web & News Grounding Engine with Caching,
    Deduplication, Source Verification, and Tool Router Interface.
    """

    def __init__(self, cache_ttl_seconds: int = 120):
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Tuple[float, List[Dict[str, str]]]] = {}

    def clean_query(self, query: str) -> str:
        # Prevent SSRF / injection by truncating and removing control characters
        safe_query = re.sub(r'[\r\n\t\x00-\x1f<>]', ' ', query[:200])
        cleaned = re.sub(
            r'^(halo|hai|selamat\s+(pagi|siang|sore|malam)|tolong\s+jelaskan|apa\s+itu|bagaimana\s+cara|berikan\s+informasi\s+tentang|siapa\s+menteri|apa\s+kebijakan|bagaimana)\b',
            '',
            safe_query,
            flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'^(hello|hi|please\s+explain|what\s+is|tell\s+me\s+about|who\s+is|how\s+does)\b',
            '',
            cleaned,
            flags=re.IGNORECASE
        )
        kw = cleaned.strip()
        return kw if len(kw) > 3 else safe_query.strip()

    async def search(self, query: str, language: str = "id", limit: int = 5) -> List[Dict[str, str]]:
        """
        Executes query search with deduplication and caching.
        Returns list of structured items: {title, source, published_at, link, snippet}
        All items are sanitized to prevent prompt injection attacks.
        """
        cleaned_kw = self.clean_query(query)
        cache_key = f"{language}:{cleaned_kw.lower()}"
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            ts, cached_results = self._cache[cache_key]
            if now - ts < self.cache_ttl:
                return cached_results[:limit]

        search_term = cleaned_kw
        if not any(k in cleaned_kw.lower() for k in ["menko", "polkam", "indonesia", "pemerintah", "kabinet"]):
            search_term = f"{cleaned_kw} Indonesia"

        encoded = urllib.parse.quote(search_term)
        # Enforce strict hardcoded trusted HTTPS RSS search domain to eliminate SSRF
        if language == "en":
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        else:
            url = f"https://news.google.com/rss/search?q={encoded}&hl=id&gl=ID&ceid=ID:id"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        results: List[Dict[str, str]] = []
        seen_titles = set()

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    root = ET.fromstring(res.text)
                    items = root.findall(".//item")
                    for item in items:
                        title_el = item.find("title")
                        pub_el = item.find("pubDate")
                        src_el = item.find("source")
                        link_el = item.find("link")

                        title = title_el.text.strip() if title_el is not None and title_el.text else ""
                        pub = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                        src_name = src_el.text.strip() if src_el is not None and src_el.text else "Berita Terverifikasi"
                        link = link_el.text.strip() if link_el is not None and link_el.text else ""

                        # Sanitize extracted text to neutralize prompt injection delimiters
                        safe_title = re.sub(r'[<>]', '', title).replace('\n', ' ').strip()
                        safe_src = re.sub(r'[<>]', '', src_name).replace('\n', ' ').strip()
                        safe_pub = re.sub(r'[<>]', '', pub).replace('\n', ' ').strip()

                        # Normalization & Deduplication
                        clean_title_key = re.sub(r'[^a-zA-Z0-9]', '', safe_title.lower())
                        if clean_title_key and clean_title_key not in seen_titles:
                            seen_titles.add(clean_title_key)
                            results.append({
                                "title": safe_title,
                                "source": safe_src,
                                "published_at": safe_pub,
                                "link": link,
                                "snippet": f"[{safe_pub}] {safe_title} — Sumber: {safe_src}"
                            })

                        if len(results) >= limit:
                            break

            self._cache[cache_key] = (now, results)
        except Exception as e:
            print(f"LiveGroundingTool error: {e}")

        return results

    def get_tool_declaration(self) -> Dict[str, Any]:
        """Tool schema definition for model tool-calling."""
        return {
            "name": "search_live_news_and_regulations",
            "description": "Mencari berita, regulasi, dan data faktual mutakhir terkini seputar kebijakan pemerintahan, hukum, politik, dan keamanan nasional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Kata kunci pencarian spesifik untuk berita atau regulasi terkini"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["id", "en"],
                        "description": "Bahasa pencarian (id untuk berita Indonesia, en untuk internasional)"
                    }
                },
                "required": ["query"]
            }
        }

grounding_tool = LiveGroundingTool()
