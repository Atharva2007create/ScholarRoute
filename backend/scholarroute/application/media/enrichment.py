from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from scholarroute.infrastructure.db.models import Institution, MediaAsset, ScholarshipProvider
from scholarroute.infrastructure.db.session import session_scope


@dataclass(frozen=True)
class MediaCandidate:
    entity_type: str
    canonical_code: str
    asset_url: str
    source_page_url: str
    official_domain: str
    usage_note: str


CANDIDATES = (
    MediaCandidate(
        "INSTITUTION",
        "JOSAA_102",
        "https://www.iitb.ac.in/sites/default/files/IITBLogo.png",
        "https://www.iitb.ac.in/article/iit-bombay-logo-and-diamond-jubilee-logo",
        "iitb.ac.in",
        "Official institute logo; ownership and usage terms remain with IIT Bombay.",
    ),
    MediaCandidate(
        "INSTITUTION",
        "JOSAA_104",
        "https://home.iitd.ac.in/images/logo-iit.png",
        "https://home.iitd.ac.in/",
        "iitd.ac.in",
        "Official institute logo hosted by IIT Delhi.",
    ),
    MediaCandidate(
        "INSTITUTION",
        "JOSAA_109",
        "https://iitk.ac.in/ipr/images/trademark/bluelogoR.png",
        "https://iitk.ac.in/ipr/trademarks-of-iit-kanpur",
        "iitk.ac.in",
        "Official registered institute logo; trademark remains with IIT Kanpur.",
    ),
    MediaCandidate(
        "INSTITUTION",
        "MCC_200510",
        "https://www.aiimsmangalagiri.edu.in/wp-content/themes/aiims-mangalgiri/assets/images/logo_new.png",
        "https://www.aiimsmangalagiri.edu.in/",
        "aiimsmangalagiri.edu.in",
        "Official institute logo hosted by AIIMS Mangalagiri.",
    ),
    MediaCandidate(
        "INSTITUTION",
        "MCC_200516",
        "https://aiimsrbl.edu.in/assets/images/brand/aiims.png",
        "https://aiimsrbl.edu.in/annual-report",
        "aiimsrbl.edu.in",
        "Official institute logo hosted by AIIMS Raebareli.",
    ),
    MediaCandidate(
        "SCHOLARSHIP_PROVIDER",
        "DOSJE",
        "https://socialjustice.gov.in/public/latest/images/government-logo.png",
        "https://socialjustice.gov.in/",
        "socialjustice.gov.in",
        "Official Government of India identity used by the provider website.",
    ),
)

BLOCKED_SOURCES = {
    "JOSAA_226": "MEDIA_SOURCE_BLOCKED: official NIT Trichy TLS chain is not trusted",
    "MCC_200521": "MEDIA_SOURCE_BLOCKED: official JIPMER TLS chain is not trusted",
}


def _official_url(value: str, official_domain: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    domain = official_domain.lower().rstrip(".")
    return parsed.scheme == "https" and (host == domain or host.endswith(f".{domain}"))


def _detected_image_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    prefix = content[:512].lstrip().lower()
    if prefix.startswith(b"<svg") or (prefix.startswith(b"<?xml") and b"<svg" in prefix):
        return "image/svg+xml"
    return None


def validate_candidate(
    client: httpx.Client, candidate: MediaCandidate
) -> tuple[str, int, str]:
    if not _official_url(candidate.asset_url, candidate.official_domain):
        raise ValueError("asset URL is not hosted on the declared official domain")
    if not _official_url(candidate.source_page_url, candidate.official_domain):
        raise ValueError("source page is not hosted on the declared official domain")
    source = client.get(candidate.source_page_url)
    source.raise_for_status()
    if "text/html" not in source.headers.get("content-type", ""):
        raise ValueError("source page did not return HTML")
    response = client.get(candidate.asset_url)
    response.raise_for_status()
    if len(response.content) < 2048:
        raise ValueError("media asset is too small to be usable")
    content_type = _detected_image_type(response.content)
    if content_type is None:
        raise ValueError("media response is not a supported image")
    return content_type, len(response.content), sha256(response.content).hexdigest()


def enrich() -> tuple[int, list[str]]:
    accepted = 0
    rejected: list[str] = []
    with httpx.Client(
        follow_redirects=True,
        timeout=40,
        headers={"User-Agent": "ScholarRouteMediaValidator/1.0"},
    ) as client, session_scope() as session:
        for candidate in CANDIDATES:
            try:
                content_type, content_length, checksum = validate_candidate(client, candidate)
                entity: Institution | ScholarshipProvider | None
                if candidate.entity_type == "INSTITUTION":
                    entity = session.scalar(
                        select(Institution).where(Institution.code == candidate.canonical_code)
                    )
                else:
                    entity = session.scalar(
                        select(ScholarshipProvider).where(
                            ScholarshipProvider.code == candidate.canonical_code
                        )
                    )
                if entity is None:
                    raise ValueError("canonical record is unavailable")
                asset = session.scalar(
                    select(MediaAsset).where(
                        MediaAsset.entity_type == candidate.entity_type,
                        MediaAsset.entity_id == entity.id,
                        MediaAsset.media_type == "LOGO",
                    )
                )
                values = {
                    "asset_url": candidate.asset_url,
                    "source_page_url": candidate.source_page_url,
                    "official_domain": candidate.official_domain,
                    "retrieved_at": datetime.now(UTC),
                    "validation_status": "VERIFIED",
                    "content_type": content_type,
                    "content_length": content_length,
                    "checksum_sha256": checksum,
                    "usage_note": candidate.usage_note,
                }
                if asset is None:
                    session.add(
                        MediaAsset(
                            entity_type=candidate.entity_type,
                            entity_id=entity.id,
                            media_type="LOGO",
                            **values,
                        )
                    )
                else:
                    for key, value in values.items():
                        setattr(asset, key, value)
                accepted += 1
            except (httpx.HTTPError, ValueError) as exc:
                rejected.append(f"{candidate.canonical_code}: {type(exc).__name__}")
    return accepted, rejected


def main() -> None:
    accepted, rejected = enrich()
    print(f"accepted={accepted}")
    print(f"rejected={len(rejected)}")
    for item in rejected:
        print(item)
    for code, reason in BLOCKED_SOURCES.items():
        print(f"{code}: {reason}")


if __name__ == "__main__":
    main()
