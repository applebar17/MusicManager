from music_manager_backend.infrastructure.soundcloud.track_discovery_parser import (
    SoundCloudTrackDiscoveryHtmlParser,
    merge_soundcloud_api_track_discovery,
)


def test_track_discovery_parser_extracts_purchase_description_links_and_metadata() -> None:
    html = """
    <html>
      <head><meta property="og:title" content="Premiere Alarico - Carnal Fever [PI03]"></head>
      <body>
        <a class="reportContent"
          href="/pages/report-content?content_urn=soundcloud%3Atracks%3A1803520185&amp;content_permalink_url=https%3A//soundcloud.com/hate_music/premiere-alarico-carnal-fever-pi03">
          Report
        </a>
        <div class="purchaseLink__container">
          <a href="https://gate.sc?url=https%3A%2F%2Fprimalinstinctrec.bandcamp.com%2Falbum%2Fcarnal-fever&amp;token=abc"
             aria-label="Buy"
             class="soundActions__purchaseLink">Buy</a>
        </div>
        <a class="userBadge__usernameLink"><span class="sc-truncate">HATE</span></a>
        <div class="truncatedAudioInfo__content">
          <div class="sc-type-small sc-text-body">
            <p>Support the label, buy it here:
              <a href="https://gate.sc?url=https%3A%2F%2Fprimalinstinctrec.bandcamp.com%2Falbum%2Fcarnal-fever&amp;token=def"
                 title="https://primalinstinctrec.bandcamp.com/album/carnal-fever">Bandcamp</a>
            </p>
            <p>Follow Alarico:
              <a href="https://gate.sc?url=https%3A%2F%2Fwww.instagram.com%2Falarico___%2F&amp;token=ghi"
                 title="https://www.instagram.com/alarico___/">Instagram</a>
            </p>
            <p>
              DISCLAIMER: All tracks are uploaded in a low quality
              for promotional purposes only.
            </p>
          </div>
          <div class="soundTags">
            <span class="sc-tagContent">Techno</span>
            <span class="sc-tagContent">Primal Instinct</span>
          </div>
          <dl class="listenInfo__releaseList">
            <dt>Released by:</dt><dd>Primal Instinct Rec.</dd>
            <dt>Release date:</dt><dd>3 May 2024</dd>
          </dl>
        </div>
      </body>
    </html>
    """

    discovery = SoundCloudTrackDiscoveryHtmlParser().parse(
        html,
        source_url="https://soundcloud.com/hate_music/premiere-alarico-carnal-fever-pi03",
    )

    assert discovery.track_urn == "soundcloud:tracks:1803520185"
    assert discovery.title == "Premiere Alarico - Carnal Fever [PI03]"
    assert discovery.artist == "HATE"
    assert discovery.purchase_url == "https://primalinstinctrec.bandcamp.com/album/carnal-fever"
    assert discovery.tags == ("Techno", "Primal Instinct")
    assert discovery.release_metadata == {
        "Released by": "Primal Instinct Rec.",
        "Release date": "3 May 2024",
    }
    assert "promotional_low_quality_notice" in discovery.warnings
    assert [link.url for link in discovery.links] == [
        "https://primalinstinctrec.bandcamp.com/album/carnal-fever",
        "https://www.instagram.com/alarico___/",
    ]
    assert discovery.links[0].kind == "buy_or_download"
    assert discovery.links[0].source == "description"
    assert discovery.links[1].kind == "artist_social"


def test_track_discovery_parser_warns_when_free_download_is_text_only() -> None:
    html = """
    <html>
      <body>
        <a class="reportContent"
          href="/pages/report-content?content_urn=soundcloud%3Atracks%3A209060476">
          Report
        </a>
        <div class="purchaseLink__container"></div>
        <a class="userBadge__usernameLink">Cennamo</a>
        <div class="truncatedAudioInfo__content">
          <div class="sc-type-small sc-text-body">
            <p>Lucio Battisti - La Canzone Della Terra (Giuseppe Cennamo Edit)// Free Download</p>
          </div>
        </div>
      </body>
    </html>
    """

    discovery = SoundCloudTrackDiscoveryHtmlParser().parse(
        html,
        source_url="https://soundcloud.com/giuseppecennamo/lucio-battisti-la-canzone",
    )

    assert discovery.track_urn == "soundcloud:tracks:209060476"
    assert discovery.artist == "Cennamo"
    assert discovery.links == ()
    assert "free_download_mentioned_without_link" in discovery.warnings
    assert "no_purchase_or_download_link_found" in discovery.warnings


def test_track_discovery_merges_api_purchase_url_when_static_html_has_none() -> None:
    discovery = SoundCloudTrackDiscoveryHtmlParser().parse(
        """
        <html>
          <head><meta property="og:title" content="Kapote - Berlin Boogie Town"></head>
          <body>
            <a class="userBadge__usernameLink">Kapote</a>
            <script src="https://a-v2.sndcdn.com/assets/1-a1b2c3.js"></script>
          </body>
        </html>
        """,
        source_url="https://soundcloud.com/toytonics/kapote-berlin-boogie-bounce-extended-mix",
    )

    merged = merge_soundcloud_api_track_discovery(
        discovery,
        {
            "id": 12345,
            "kind": "track",
            "title": "Kapote - Berlin Boogie Bounce Extended Mix",
            "permalink_url": "https://soundcloud.com/toytonics/kapote-berlin-boogie-bounce-extended-mix",
            "purchase_title": "Buy",
            "purchase_url": "https://toy-tonics.lnk.to/BerlinBoogieTown",
            "user": {"username": "Toy Tonics"},
            "genre": "House",
            "tag_list": '"Berlin Boogie" Disco',
        },
    )

    assert merged.track_urn == "soundcloud:tracks:12345"
    assert merged.artist == "Toy Tonics"
    assert merged.purchase_url == "https://toy-tonics.lnk.to/BerlinBoogieTown"
    assert merged.links[0].url == "https://toy-tonics.lnk.to/BerlinBoogieTown"
    assert merged.links[0].source == "api_purchase_url"
    assert merged.links[0].kind == "buy"
    assert merged.tags == ("House", "Berlin Boogie", "Disco")
    assert "no_purchase_or_download_link_found" not in merged.warnings
