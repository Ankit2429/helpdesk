"""
robots.txt compliance.

One RobotFileParser per domain, cached, plus crawl-delay extraction so the
crawler can throttle itself per the site's own stated preference (falling
back to config.CRAWL_DELAY_FALLBACK when the site doesn't specify one).
"""

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

import config
from scraper.logger import get_logger

log = get_logger(__name__)


class RobotsChecker:
    def __init__(self):
        self._parsers: dict[str, RobotFileParser] = {}
        self._delays: dict[str, float] = {}

    def _get_parser(self, domain: str) -> RobotFileParser:
        if domain in self._parsers:
            return self._parsers[domain]

        parser = RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        try:
            resp = requests.get(robots_url, headers={"User-Agent": config.USER_AGENT},
                                 timeout=config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
                log.info(f"Loaded robots.txt for {domain}")
            else:
                # No robots.txt / inaccessible -> treat as "allow all" per RFC convention.
                parser.parse([])
                log.info(f"No robots.txt at {domain} (status {resp.status_code}); allowing all")
        except requests.RequestException as e:
            log.warning(f"Could not fetch robots.txt for {domain}: {e}. Assuming allow-all.")
            parser.parse([])

        self._parsers[domain] = parser

        delay = parser.crawl_delay(config.USER_AGENT) or parser.crawl_delay("*")
        self._delays[domain] = float(delay) if delay else config.CRAWL_DELAY_FALLBACK
        return parser

    def is_allowed(self, url: str) -> bool:
        if not config.RESPECT_ROBOTS_TXT:
            return True
        domain = urlparse(url).netloc
        parser = self._get_parser(domain)
        allowed = parser.can_fetch(config.USER_AGENT, url)
        if not allowed:
            log.debug(f"robots.txt disallows: {url}")
        return allowed

    def crawl_delay(self, url: str) -> float:
        domain = urlparse(url).netloc
        if domain not in self._delays:
            self._get_parser(domain)
        return self._delays.get(domain, config.CRAWL_DELAY_FALLBACK)
