from pathlib import Path

from music_manager_backend.infrastructure.soundcloud.public_html_parser import (
    PublicPlaylistHtmlParser,
)

FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "soundcloud_html" / "rendered_playlist.html"
)
SOURCE_URL = "https://soundcloud.com/riccardo-tordini/sets/21_futurfunk_nudisco"


def test_parser_extracts_rendered_playlist_fixture() -> None:
    playlist = PublicPlaylistHtmlParser().parse(FIXTURE_PATH.read_text(), source_url=SOURCE_URL)

    assert playlist.source_url == SOURCE_URL
    assert playlist.title == "21_futurfunk_nudisco"
    assert playlist.warnings == ()
    assert len(playlist.tracks) == 3

    first = playlist.tracks[0]
    assert first.position == 1
    assert first.title == "Galactica Airlines"
    assert first.uploader == "Iden Kai"
    assert first.uploader_url == "https://soundcloud.com/iden_kai"
    assert first.playlist_track_url == (
        "https://soundcloud.com/iden_kai/galactica-airlines"
        "?in=riccardo-tordini/sets/21_futurfunk_nudisco"
    )
    assert first.canonical_track_url == "https://soundcloud.com/iden_kai/galactica-airlines"
    assert first.artwork_url == "https://i1.sndcdn.com/artworks-abc-t120x120.jpg"
    assert first.play_count == 85_400
    assert first.duration_seconds is None
    assert first.raw["track_href"] == (
        "/iden_kai/galactica-airlines?in=riccardo-tordini/sets/21_futurfunk_nudisco"
    )


def test_parser_preserves_non_ascii_titles_and_metric_play_counts() -> None:
    playlist = PublicPlaylistHtmlParser().parse(FIXTURE_PATH.read_text(), source_url=SOURCE_URL)

    second = playlist.tracks[1]
    third = playlist.tracks[2]

    assert second.uploader == "Luanmer, サクラSAKURA-LEE"
    assert second.play_count == 9_609
    assert third.title == "ミカヅキBIGWAVE - Emotional Prism 感情的なプリズム [PNTSS0202]"
    assert third.play_count == 3_560_000
    assert third.artwork_url is None


def test_parser_reports_empty_html_without_crashing() -> None:
    playlist = PublicPlaylistHtmlParser().parse("<html><body></body></html>", source_url=SOURCE_URL)

    assert playlist.tracks == ()
    assert "soundcloud_public_html_missing_playlist_title" in playlist.warnings
    assert "soundcloud_public_html_no_track_rows" in playlist.warnings


def test_parser_extracts_hydrated_playlist_when_rendered_rows_are_absent() -> None:
    html = """
    <html>
      <head><meta property="og:title" content="Hydrated Set | SoundCloud"></head>
      <body>
        <script>
          window.__sc_hydration = [
            {
              "hydratable": "playlist",
              "data": {
                "track_count": 2,
                "tracks": [
                  {
                    "id": 123,
                    "urn": "soundcloud:tracks:123",
                    "title": "Hydrated Song",
                    "permalink_url": "https://soundcloud.com/artist/hydrated-song",
                    "artwork_url": "https://i1.sndcdn.com/artwork.jpg",
                    "playback_count": 9001,
                    "full_duration": 181000,
                    "publisher_metadata": {"artist": "Metadata Artist"},
                    "user": {
                      "username": "Uploader",
                      "permalink_url": "https://soundcloud.com/artist"
                    }
                  },
                  {
                    "id": 456,
                    "kind": "track"
                  }
                ]
              }
            }
          ];
        </script>
      </body>
    </html>
    """

    playlist = PublicPlaylistHtmlParser().parse(html, source_url=SOURCE_URL)

    assert playlist.title == "Hydrated Set"
    assert len(playlist.tracks) == 1
    assert playlist.tracks[0].position == 1
    assert playlist.tracks[0].title == "Hydrated Song"
    assert playlist.tracks[0].uploader == "Metadata Artist"
    assert playlist.tracks[0].uploader_url == "https://soundcloud.com/artist"
    assert playlist.tracks[0].canonical_track_url == "https://soundcloud.com/artist/hydrated-song"
    assert playlist.tracks[0].playlist_track_url == (
        "https://soundcloud.com/artist/hydrated-song"
        "?in=riccardo-tordini/sets/21_futurfunk_nudisco"
    )
    assert playlist.tracks[0].artwork_url == "https://i1.sndcdn.com/artwork.jpg"
    assert playlist.tracks[0].play_count == 9001
    assert playlist.tracks[0].duration_seconds == 181
    assert "soundcloud_hydration_track_2_missing_title_or_url" in playlist.warnings
    assert "soundcloud_hydration_incomplete_track_data" in playlist.warnings
    assert "soundcloud_public_html_no_track_rows" not in playlist.warnings


def test_parser_extracts_schema_tracklist_when_hydration_is_unavailable() -> None:
    html = """
    <html>
      <head><title>Schema Set | SoundCloud</title></head>
      <body>
        <section class="tracklist">
          <article itemprop="track">
            <h2 itemprop="name">
              <a href="/artist/schema-song" itemprop="url">Schema Song</a>
              <a href="/artist">Schema Artist</a>
            </h2>
            <meta itemprop="duration" content="PT00H03M58S">
          </article>
        </section>
      </body>
    </html>
    """

    playlist = PublicPlaylistHtmlParser().parse(html, source_url=SOURCE_URL)

    assert playlist.title == "Schema Set"
    assert len(playlist.tracks) == 1
    assert playlist.tracks[0].title == "Schema Song"
    assert playlist.tracks[0].uploader == "Schema Artist"
    assert playlist.tracks[0].uploader_url == "https://soundcloud.com/artist"
    assert playlist.tracks[0].canonical_track_url == "https://soundcloud.com/artist/schema-song"
    assert playlist.tracks[0].duration_seconds == 238
    assert "soundcloud_schema_tracklist_used" in playlist.warnings
    assert "soundcloud_public_html_no_track_rows" not in playlist.warnings


def test_parser_skips_malformed_track_rows_with_warning() -> None:
    html = """
    <html>
      <head><title>Broken Set | SoundCloud</title></head>
      <body>
        <ul>
          <li class="trackList__item">
            <a class="trackItem__username" href="/artist">Artist</a>
          </li>
        </ul>
      </body>
    </html>
    """

    playlist = PublicPlaylistHtmlParser().parse(html, source_url=SOURCE_URL)

    assert playlist.title == "Broken Set"
    assert playlist.tracks == ()
    assert "soundcloud_public_html_missing_eof_marker" in playlist.warnings
    assert "soundcloud_track_row_1_missing_track_title" in playlist.warnings
