"""Robots.txt compliance handler using standard urllib robotparser."""

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from logger.logger import get_logger

logger = get_logger("robots_handler")


class RobotsHandler:
    """Parses and enforces robots.txt rules for target domains."""

    def __init__(self, user_agent: str = "*") -> None:
        self.user_agent = user_agent
        self.parsers: dict[str, RobotFileParser] = {}

    def fetch_robots(self, base_url: str) -> None:
        """Fetch and parse robots.txt for given base URL domain."""
        try:
            parsed = urlparse(base_url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{domain}/robots.txt"

            rfp = RobotFileParser()
            rfp.set_url(robots_url)
            rfp.read()
            self.parsers[parsed.netloc] = rfp
            logger.info(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            logger.debug(f"Could not load robots.txt for {base_url}: {e}")

    def is_allowed(self, url: str) -> bool:
        """Check if URL fetch is allowed by robots.txt."""
        try:
            parsed = urlparse(url)
            rfp = self.parsers.get(parsed.netloc)
            if rfp:
                return rfp.can_fetch(self.user_agent, url)
        except Exception:
            pass
        return True
