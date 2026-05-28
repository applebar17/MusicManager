from music_manager_backend.infrastructure.soundcloud.track_discovery import (
    PublicTrackDiscoveryProvider,
)


class FakeTrackHtmlFetcher:
    def fetch(self, url: str) -> str:
        return """
        <html>
          <head><meta property="og:title" content="Kapote - Berlin Boogie Town"></head>
          <body>
            <a class="userBadge__usernameLink">Kapote</a>
            <script src="https://a-v2.sndcdn.com/assets/app-abc123.js"></script>
          </body>
        </html>
        """


class FakeSoundCloudApiClient:
    def fetch_text(self, url: str) -> str:
        assert url == "https://a-v2.sndcdn.com/assets/app-abc123.js"
        return 'client_id:"test_client_id_123456"'

    def fetch_json(
        self, url: str, *, params: dict[str, str]
    ) -> dict[str, object] | list[object]:
        assert url == "https://api-v2.soundcloud.com/resolve"
        assert params == {
            "url": "https://soundcloud.com/toytonics/kapote-berlin-boogie-bounce-extended-mix",
            "client_id": "test_client_id_123456",
        }
        return {
            "id": 98765,
            "kind": "track",
            "title": "Kapote - Berlin Boogie Bounce Extended Mix",
            "purchase_title": "Buy",
            "purchase_url": "https://toy-tonics.lnk.to/BerlinBoogieTown",
            "user": {"username": "Toy Tonics"},
        }


def test_track_discovery_provider_enriches_purchase_url_from_public_api() -> None:
    provider = PublicTrackDiscoveryProvider(
        fetcher=FakeTrackHtmlFetcher(),
        api_client=FakeSoundCloudApiClient(),
    )

    discovery = provider.discover_track(
        "https://soundcloud.com/toytonics/kapote-berlin-boogie-bounce-extended-mix"
    )

    assert discovery.track_urn == "soundcloud:tracks:98765"
    assert discovery.artist == "Toy Tonics"
    assert discovery.purchase_url == "https://toy-tonics.lnk.to/BerlinBoogieTown"
    assert discovery.links[0].source == "api_purchase_url"
    assert "no_purchase_or_download_link_found" not in discovery.warnings
