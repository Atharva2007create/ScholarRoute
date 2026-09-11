from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from scholarroute.application.media.enrichment import MediaCandidate, validate_candidate


def _response(url: str, content: bytes, content_type: str) -> httpx.Response:
    return httpx.Response(
        200,
        content=content,
        headers={"content-type": content_type},
        request=httpx.Request("GET", url),
    )


def candidate(asset_url: str = "https://media.example.edu/logo.png") -> MediaCandidate:
    return MediaCandidate(
        "INSTITUTION",
        "TEST",
        asset_url,
        "https://example.edu/about",
        "example.edu",
        "Official test asset.",
    )


def test_validated_official_media_retains_provenance() -> None:
    client = Mock()
    client.get.side_effect = [
        _response("https://example.edu/about", b"<html>Official institute</html>", "text/html"),
        _response(
            "https://media.example.edu/logo.png",
            b"\x89PNG\r\n\x1a\n" + (b"0" * 3000),
            "image/png",
        ),
    ]
    content_type, content_length, checksum = validate_candidate(client, candidate())
    assert content_type == "image/png"
    assert content_length > 2048
    assert len(checksum) == 64


def test_untrusted_media_url_is_rejected_before_fetch() -> None:
    client = Mock()
    with pytest.raises(ValueError, match="official domain"):
        validate_candidate(client, candidate("https://attacker.invalid/logo.png"))
    client.get.assert_not_called()


def test_non_image_response_is_rejected() -> None:
    client = Mock()
    client.get.side_effect = [
        _response("https://example.edu/about", b"<html>Official institute</html>", "text/html"),
        _response("https://media.example.edu/logo.png", b"not-an-image" * 300, "text/plain"),
    ]
    with pytest.raises(ValueError, match="supported image"):
        validate_candidate(client, candidate())
