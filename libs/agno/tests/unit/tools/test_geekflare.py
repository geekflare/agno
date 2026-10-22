"""Unit tests for GeekflareTools class."""

import json
from unittest.mock import Mock, patch

import httpx
import pytest

from agno.tools.geekflare import GeekflareTools

DIAGNOSTIC_FUNCTIONS = [
    "check_site_status",
    "get_dns_records",
    "scan_tls",
    "check_redirects",
    "find_broken_links",
    "measure_load_time",
    "run_lighthouse_audit",
]


def _response(status_code: int = 200, body=None) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = body if body is not None else {"apiStatus": "success", "data": {"ok": True}}
    return response


@pytest.fixture
def mock_post():
    with patch("agno.tools.geekflare.httpx.post") as mock_post:
        mock_post.return_value = _response()
        yield mock_post


def test_init_with_api_key():
    tools = GeekflareTools(api_key="test_key")
    assert tools.api_key == "test_key"


def test_init_with_env_var():
    with patch.dict("os.environ", {"GEEKFLARE_API_KEY": "env_key"}):
        tools = GeekflareTools()
        assert tools.api_key == "env_key"


def test_init_without_api_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="No Geekflare API key provided"):
            GeekflareTools()


def test_default_tools():
    tools = GeekflareTools(api_key="test_key")
    assert set(tools.functions) == {"search_web", "scrape_url"}


def test_all_tools():
    tools = GeekflareTools(api_key="test_key", all=True)
    assert len(tools.functions) == 13
    assert set(DIAGNOSTIC_FUNCTIONS) <= set(tools.functions)


def test_diagnostics_flag_only():
    tools = GeekflareTools(api_key="test_key", enable_search=False, enable_scrape=False, enable_diagnostics=True)
    assert set(tools.functions) == set(DIAGNOSTIC_FUNCTIONS)


def test_search_web_payload(mock_post):
    tools = GeekflareTools(api_key="test_key")
    result = json.loads(tools.search_web("best crm", limit=5, serp=True, city="London,England,United Kingdom"))

    assert result["data"] == {"ok": True}
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.geekflare.com/search"
    assert kwargs["headers"]["x-api-key"] == "test_key"
    assert kwargs["json"]["query"] == "best crm"
    assert kwargs["json"]["limit"] == 5
    assert kwargs["json"]["serp"] is True
    assert kwargs["json"]["city"] == "London,England,United Kingdom"
    assert "includeDomains" not in kwargs["json"]


def test_scrape_url_template(mock_post):
    tools = GeekflareTools(api_key="test_key")
    tools.scrape_url("https://example.com", formats=["markdown-llm"], template="product")

    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.geekflare.com/webscraping"
    assert kwargs["json"] == {
        "url": "https://example.com",
        "format": ["markdown-llm"],
        "template": "product",
        "extractionMode": "template",
    }


def test_screenshot_and_pdf_payloads(mock_post):
    tools = GeekflareTools(api_key="test_key", all=True)

    tools.take_screenshot("https://example.com", full_page=True, image_type="webp")
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.geekflare.com/screenshot"
    assert kwargs["json"]["fullPage"] is True
    assert kwargs["json"]["type"] == "webp"

    tools.url_to_pdf("https://example.com", paper_format="letter")
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.geekflare.com/url2pdf"
    assert kwargs["json"]["format"] == "letter"


@pytest.mark.parametrize(
    ("function", "path"),
    [
        ("check_site_status", "up"),
        ("get_dns_records", "dnsrecord"),
        ("scan_tls", "tlsscan"),
        ("check_redirects", "redirectcheck"),
        ("find_broken_links", "brokenlink"),
        ("measure_load_time", "loadtime"),
        ("run_lighthouse_audit", "lighthouse"),
        ("get_page_metadata", "metascraping"),
        ("get_brand", "brand"),
    ],
)
def test_endpoint_routing(mock_post, function, path):
    tools = GeekflareTools(api_key="test_key", all=True)
    getattr(tools, function)("https://example.com")

    args, kwargs = mock_post.call_args
    assert args[0] == f"https://api.geekflare.com/{path}"
    assert kwargs["json"]["url"] == "https://example.com"


def test_api_error_returns_error_json(mock_post):
    mock_post.return_value = _response(401, {"apiCode": 401, "message": "Invalid x-api-key"})
    tools = GeekflareTools(api_key="bad_key")

    result = json.loads(tools.search_web("x"))
    assert "Invalid x-api-key" in result["error"]


def test_network_error_returns_error_json(mock_post):
    mock_post.side_effect = httpx.ConnectError("connection refused")
    tools = GeekflareTools(api_key="test_key")

    result = json.loads(tools.scrape_url("https://example.com"))
    assert "connection refused" in result["error"]
