"""WikiJsClient: keep request formats and response unpacking here."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import Settings
from ..models import RankedPage
from ..text import normalize_text

PAGE_QUERY = """
query PageContent($id: Int!) {
  pages {
    single(id: $id) {
      id
      path
      title
      description
      content
      render
      locale
      editor
      createdAt
      updatedAt
    }
  }
}
""".strip()


# Example: client = WikiJsClient(settings)
class WikiJsClient:
    """Fetch full Wiki.js pages through its GraphQL API."""

    # Example: client = WikiJsClient(settings)
    def __init__(self, settings: Settings) -> None:
        """Remember the endpoint and format its authorization header."""

        self.graphql_url = settings.wikijs_graphql_url
        token = settings.wikijs_api_token.strip()
        self.authorization = (
            token if token.lower().startswith("bearer ") else f"Bearer {token}"
        )

    # Example: page = client.fetch_page(ranked_page)
    def fetch_page(self, ranked_page: RankedPage) -> RankedPage:
        """Attach current Wiki.js content to one ranked page."""

        body = json.dumps(
            {"query": PAGE_QUERY, "variables": {"id": int(ranked_page.page_id)}}
        ).encode("utf-8")
        request = Request(
            self.graphql_url,
            data=body,
            method="POST",
            headers={
                "Authorization": self.authorization,
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Wiki.js returned HTTP {error.code}: {details}"
            ) from error
        except URLError as error:
            raise RuntimeError(f"Could not reach Wiki.js: {error.reason}") from error

        if result.get("errors"):
            messages = "; ".join(
                str(item.get("message", item)) for item in result["errors"]
            )
            raise RuntimeError(f"Wiki.js GraphQL error: {messages}")

        page_data = result.get("data", {}).get("pages", {}).get("single")
        if not page_data:
            raise RuntimeError(
                f"Wiki.js returned no page content for page {ranked_page.page_id}."
            )

        ranked_page.title = str(
            page_data.get("title") or ranked_page.title or ranked_page.page_id
        )
        ranked_page.path = str(page_data.get("path") or ranked_page.path)
        ranked_page.content = normalize_text(
            str(page_data.get("content") or page_data.get("render") or "")
        )
        return ranked_page
