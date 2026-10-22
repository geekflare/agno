import json
from os import getenv
from typing import Any, Dict, List, Literal, Optional

import httpx

from agno.tools import Toolkit
from agno.utils.log import log_debug, log_error

ScrapeFormat = Literal["markdown", "markdown-llm", "html", "html-llm", "text", "text-llm", "json"]
DnsRecordType = Literal["A", "AAAA", "CNAME", "MX", "NS", "SOA", "TXT", "CAA", "SRV"]


class GeekflareTools(Toolkit):
    """
    Geekflare is a toolkit for web search (including the full Google results page), page scraping,
    metadata, brand data, screenshots, URL-to-PDF, and website diagnostics.

    Args:
        api_key (Optional[str]): Geekflare API key. Retrieved from the GEEKFLARE_API_KEY env variable if not provided.
        enable_search (bool): Enable web search. Default is True.
        enable_scrape (bool): Enable page scraping. Default is True.
        enable_metadata (bool): Enable page metadata (title, description, Open Graph). Default is False.
        enable_brand (bool): Enable brand data (logos, colors, fonts, socials). Default is False.
        enable_screenshot (bool): Enable screenshots. Default is False.
        enable_pdf (bool): Enable URL-to-PDF conversion. Default is False.
        enable_diagnostics (bool): Enable website diagnostics (uptime, DNS, TLS, redirects,
            broken links, load time, Lighthouse). Default is False.
        all (bool): Enable all tools. Overrides individual flags when True. Default is False.
        base_url (str): Geekflare API base URL. Default is https://api.geekflare.com.
        timeout (int): Request timeout in seconds. Default is 180.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        enable_search: bool = True,
        enable_scrape: bool = True,
        enable_metadata: bool = False,
        enable_brand: bool = False,
        enable_screenshot: bool = False,
        enable_pdf: bool = False,
        enable_diagnostics: bool = False,
        all: bool = False,
        base_url: str = "https://api.geekflare.com",
        timeout: int = 180,
        **kwargs,
    ):
        self.api_key = api_key or getenv("GEEKFLARE_API_KEY")
        if not self.api_key:
            log_error("No Geekflare API key provided")
            raise ValueError(
                "No Geekflare API key provided. Please provide an api_key or set the GEEKFLARE_API_KEY environment variable."
            )
        self.base_url = base_url.rstrip("/")
        self.request_timeout = timeout

        tools: List[Any] = []
        if all or enable_search:
            tools.append(self.search_web)
        if all or enable_scrape:
            tools.append(self.scrape_url)
        if all or enable_metadata:
            tools.append(self.get_page_metadata)
        if all or enable_brand:
            tools.append(self.get_brand)
        if all or enable_screenshot:
            tools.append(self.take_screenshot)
        if all or enable_pdf:
            tools.append(self.url_to_pdf)
        if all or enable_diagnostics:
            tools.extend(
                [
                    self.check_site_status,
                    self.get_dns_records,
                    self.scan_tls,
                    self.check_redirects,
                    self.find_broken_links,
                    self.measure_load_time,
                    self.run_lighthouse_audit,
                ]
            )

        super().__init__(name="geekflare_tools", tools=tools, **kwargs)

    def _post(self, path: str, payload: Dict[str, Any]) -> str:
        """Call a Geekflare endpoint and return the JSON response, or an error message, as a string."""
        body = {k: v for k, v in payload.items() if v is not None}
        log_debug(f"Geekflare request: /{path} {body}")
        try:
            response = httpx.post(
                f"{self.base_url}/{path}",
                json=body,
                headers={"x-api-key": self.api_key or "", "Content-Type": "application/json"},
                timeout=self.request_timeout,
            )
        except httpx.HTTPError as e:
            log_error(f"Geekflare request to /{path} failed: {e}")
            return json.dumps({"error": f"Request to Geekflare failed: {e}"})

        try:
            data: Any = response.json()
        except ValueError:
            data = {"message": response.text}

        if response.status_code >= 400 or (isinstance(data, dict) and data.get("apiStatus") == "failure"):
            message = data.get("message") if isinstance(data, dict) else data
            log_error(f"Geekflare API error ({response.status_code}) on /{path}: {message}")
            return json.dumps({"error": f"Geekflare API error ({response.status_code}): {message}"})
        return json.dumps(data)

    # ---------------------------------------------------------------------------
    # Search and content
    # ---------------------------------------------------------------------------

    def search_web(
        self,
        query: str,
        limit: int = 10,
        source: Literal["web", "news", "images"] = "web",
        location: Optional[str] = None,
        city: Optional[str] = None,
        time: Optional[str] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        serp: bool = False,
    ) -> str:
        """Use this function to search the live web, news, or images and get titles, URLs, and snippets.
        Set serp=True to get the full Google results page (organic results, AI Overview, People Also Ask).

        Args:
            query (str): The search query.
            limit (int): Number of results, 1-100. Defaults to 10.
            source (str): One of "web", "news", "images". Defaults to "web".
            location (Optional[str]): Country code (ISO alpha-2) for localized results, e.g. "us".
            city (Optional[str]): City for localized results, e.g. "London,England,United Kingdom".
            time (Optional[str]): Recency filter: any, h, d, w, m, y, or with a count such as d7.
            include_domains (Optional[List[str]]): Only return results from these domains.
            exclude_domains (Optional[List[str]]): Exclude results from these domains.
            serp (bool): Return the full Google results page. Defaults to False.

        Returns:
            str: JSON string with the search results.
        """
        return self._post(
            "search",
            {
                "query": query,
                "limit": limit,
                "source": source,
                "location": location,
                "city": city,
                "time": time,
                "includeDomains": include_domains,
                "excludeDomains": exclude_domains,
                "serp": serp,
            },
        )

    def scrape_url(
        self,
        url: str,
        formats: Optional[List[ScrapeFormat]] = None,
        render_js: Optional[bool] = None,
        template: Optional[Literal["product", "contact"]] = None,
    ) -> str:
        """Use this function to fetch a public web page and get its content as Markdown (default), text, HTML, or JSON.

        Args:
            url (str): Full URL of the page.
            formats (Optional[List[str]]): Output formats, up to 3: markdown, markdown-llm, text, text-llm, html,
                html-llm, json. Defaults to markdown.
            render_js (Optional[bool]): Force JavaScript rendering on or off. Omit to decide automatically.
            template (Optional[str]): "product" (title, price, availability, images, ratings) or "contact"
                (emails, phones, social profiles) for structured data.

        Returns:
            str: JSON string with the page content.
        """
        return self._post(
            "webscraping",
            {
                "url": url,
                "format": formats,
                "renderJS": render_js,
                "template": template,
                "extractionMode": "template" if template else None,
            },
        )

    def get_page_metadata(self, url: str) -> str:
        """Use this function to get a page's title, description, canonical URL, Open Graph and Twitter Card tags.

        Args:
            url (str): Full URL of the page.

        Returns:
            str: JSON string with the page metadata.
        """
        return self._post("metascraping", {"url": url})

    def get_brand(self, url: str, mode: Literal["standard", "enriched"] = "standard") -> str:
        """Use this function to get a company's brand identity from its website: logos, colors, fonts, and socials.

        Args:
            url (str): Website URL or domain, e.g. "https://stripe.com".
            mode (str): "standard" or "enriched" (adds company intelligence). Defaults to "standard".

        Returns:
            str: JSON string with the brand data.
        """
        return self._post("brand", {"url": url, "mode": mode})

    def take_screenshot(
        self,
        url: str,
        full_page: bool = False,
        device: Literal["desktop", "mobile"] = "desktop",
        image_type: Literal["png", "jpeg", "webp"] = "png",
    ) -> str:
        """Use this function to take a screenshot of a web page. Returns a hosted image URL.

        Args:
            url (str): Full URL of the page.
            full_page (bool): Capture the whole page instead of the viewport. Defaults to False.
            device (str): "desktop" or "mobile". Defaults to "desktop".
            image_type (str): "png", "jpeg", or "webp". Defaults to "png".

        Returns:
            str: JSON string including the screenshot URL.
        """
        return self._post("screenshot", {"url": url, "fullPage": full_page, "device": device, "type": image_type})

    def url_to_pdf(
        self,
        url: str,
        paper_format: Literal["a4", "letter", "legal"] = "a4",
        orientation: Literal["portrait", "landscape"] = "portrait",
    ) -> str:
        """Use this function to convert a web page to a PDF. Returns a hosted download URL.

        Args:
            url (str): Full URL of the page.
            paper_format (str): "a4", "letter", or "legal". Defaults to "a4".
            orientation (str): "portrait" or "landscape". Defaults to "portrait".

        Returns:
            str: JSON string including the PDF URL.
        """
        return self._post("url2pdf", {"url": url, "format": paper_format, "orientation": orientation})

    # ---------------------------------------------------------------------------
    # Website diagnostics
    # ---------------------------------------------------------------------------

    def check_site_status(self, url: str) -> str:
        """Use this function to check whether a website is up or down and get its HTTP status.

        Args:
            url (str): Website URL or domain.

        Returns:
            str: JSON string with the status result.
        """
        return self._post("up", {"url": url})

    def get_dns_records(self, url: str, types: Optional[List[DnsRecordType]] = None) -> str:
        """Use this function to look up a domain's DNS records.

        Args:
            url (str): Website URL or domain.
            types (Optional[List[str]]): Record types to return (A, AAAA, CNAME, MX, NS, SOA, TXT, CAA, SRV).
                Defaults to all.

        Returns:
            str: JSON string with the DNS records.
        """
        return self._post("dnsrecord", {"url": url, "types": types})

    def scan_tls(self, url: str) -> str:
        """Use this function to inspect a domain's TLS/SSL setup: certificate details and expiry, and which
        protocol versions (SSLv2 to TLS 1.3) are supported.

        Args:
            url (str): Website URL or domain.

        Returns:
            str: JSON string with the TLS scan result.
        """
        return self._post("tlsscan", {"url": url})

    def check_redirects(self, url: str) -> str:
        """Use this function to trace every redirect hop of a URL with status codes.

        Args:
            url (str): Full URL.

        Returns:
            str: JSON string with the redirect chain.
        """
        return self._post("redirectcheck", {"url": url})

    def find_broken_links(self, url: str) -> str:
        """Use this function to find broken links on a web page.

        Args:
            url (str): Full URL of the page.

        Returns:
            str: JSON string with the broken links found.
        """
        return self._post("brokenlink", {"url": url})

    def measure_load_time(self, url: str) -> str:
        """Use this function to measure a page's load time, including DNS, connect, TLS, and first byte.

        Args:
            url (str): Full URL of the page.

        Returns:
            str: JSON string with the timing breakdown.
        """
        return self._post("loadtime", {"url": url})

    def run_lighthouse_audit(self, url: str, device: Literal["desktop", "mobile"] = "desktop") -> str:
        """Use this function to run a Google Lighthouse audit and get performance, SEO, accessibility, and
        best-practices scores. This can take a minute or more.

        Args:
            url (str): Full URL of the page.
            device (str): "desktop" or "mobile". Defaults to "desktop".

        Returns:
            str: JSON string with the Lighthouse scores.
        """
        return self._post("lighthouse", {"url": url, "device": device})
