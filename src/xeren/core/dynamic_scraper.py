"""Dynamic Scraper: Automatically scrapes open-source APIs (Wikipedia, GitHub, DuckDuckGo) for real-world knowledge."""

import json
import logging
import urllib.parse
import urllib.request
import re
from typing import Optional

logger = logging.getLogger("xeren.core.dynamic_scraper")

def _fetch_json(url: str, headers: Optional[dict] = None) -> Optional[dict]:
    if headers is None:
        headers = {'User-Agent': 'XerenAgent/1.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.debug(f"Fetch error for {url}: {e}")
        return None

def scrape_wikipedia(query: str) -> Optional[str]:
    """Search Wikipedia for factual topics."""
    try:
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&utf8=&format=json"
        data = _fetch_json(search_url)
        if data and data.get('query', {}).get('search'):
            title = data['query']['search'][0]['title']
            extract_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exsentences=3&exlimit=1&titles={urllib.parse.quote(title)}&explaintext=1&formatversion=2&format=json"
            ext_data = _fetch_json(extract_url)
            if ext_data and 'query' in ext_data and 'pages' in ext_data['query']:
                extract = ext_data['query']['pages'][0].get('extract', '')
                if extract:
                    return f"### 🌍 Live Knowledge (Wikipedia)\n\n**{title}**\n{extract}"
    except Exception as e:
        logger.debug(f"Wikipedia scrape failed: {e}")
    return None

def scrape_github(query: str) -> Optional[str]:
    """Search GitHub repositories for tech/open-source specific queries."""
    lower_query = query.lower()
    if not any(k in lower_query for k in ("github", "repo", "library", "framework", "open source", "package")):
        return None
        
    clean_query = query.replace("github", "").replace("repo", "").strip()
    if not clean_query:
        clean_query = query
        
    try:
        encoded_query = urllib.parse.quote(f"{clean_query} in:name,description")
        search_url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&order=desc&per_page=1"
        data = _fetch_json(search_url)
        if data and data.get('items'):
            repo = data['items'][0]
            name = repo.get('full_name', '')
            desc = repo.get('description', 'No description provided.')
            url = repo.get('html_url', '')
            stars = repo.get('stargazers_count', 0)
            return f"### 💻 Open-Source GitHub Repository\n\n**[{name}]({url})** (⭐ {stars})\n{desc}"
    except Exception as e:
        logger.debug(f"GitHub scrape failed: {e}")
    return None

def scrape_duckduckgo_lite(query: str) -> Optional[str]:
    """Scrape DuckDuckGo Lite HTML for general current-events."""
    try:
        url = f"https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({'q': query}).encode('utf-8')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            snippet_start = html.find('class="result-snippet"')
            if snippet_start != -1:
                start = html.find('>', snippet_start) + 1
                end = html.find('</td>', start)
                snippet = html[start:end].strip()
                clean_snippet = re.sub('<[^<]+>', '', snippet).strip()
                if clean_snippet:
                    return f"### 🔍 Web Search (DuckDuckGo)\n\n{clean_snippet}"
    except Exception as e:
        logger.debug(f"DDG scrape failed: {e}")
    return None

def scrape_real_world_data(query: str) -> Optional[str]:
    """Attempt to scrape real world data from GitHub, Wikipedia, or DuckDuckGo."""
    gh_result = scrape_github(query)
    if gh_result:
        return gh_result
        
    wiki_result = scrape_wikipedia(query)
    if wiki_result:
        return wiki_result
        
    ddg_result = scrape_duckduckgo_lite(query)
    if ddg_result:
        return ddg_result
        
    return None
