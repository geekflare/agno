"""
Geekflare Tools
=============================

Demonstrates Geekflare tools for web search (including the full Google results page),
page scraping, and website diagnostics.

Requires GEEKFLARE_API_KEY (get one at https://dash.geekflare.com).
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.geekflare import GeekflareTools

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------


# Example 1: Search and scrape (default tools)
research_agent = Agent(
    model=OpenAIChat(id="gpt-5.6-luna"),
    tools=[GeekflareTools()],
    markdown=True,
)

# Example 2: Website diagnostics only
diagnostics_agent = Agent(
    model=OpenAIChat(id="gpt-5.6-luna"),
    tools=[GeekflareTools(enable_search=False, enable_scrape=False, enable_diagnostics=True)],
    markdown=True,
)

# Example 3: All Geekflare tools
agent = Agent(
    model=OpenAIChat(id="gpt-5.6-luna"),
    tools=[GeekflareTools(all=True)],
    markdown=True,
)

# ---------------------------------------------------------------------------
# Run Agent
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    research_agent.print_response(
        "What does the Google results page show for 'best project management software' in London? Cite sources."
    )

    diagnostics_agent.print_response("Is the TLS setup on example.com healthy? When does the certificate expire?")

    agent.print_response("Get the brand colors and logo for https://stripe.com.")
