from typing import Dict, Any, List
from src.adapters.base import BaseSourceAdapter

class RestrictedSourceAdapter(BaseSourceAdapter):
    """
    Adapter representing institutional, academic, or paywalled data providers.
    Formally records source capabilities, licensing terms, and access restrictions
    without attempting unauthorized scraping, secret exfiltration, or paywall bypass.
    """
    def __init__(
        self,
        source_id: str,
        provider_name: str,
        source_type: str,
        licensing: str,
        supported_airports: List[str],
        restriction_reason: str,
        notes: str
    ):
        super().__init__(
            source_id=source_id,
            provider_name=provider_name,
            source_type=source_type,
            licensing=licensing,
            supported_airports=supported_airports,
            data_nature="restricted_access"
        )
        self.restriction_reason = restriction_reason
        self.notes = notes

    def check_access_status(self) -> Dict[str, Any]:
        """
        Reports documented access status and constraints.
        """
        return {
            "source_id": self.source_id,
            "provider_name": self.provider_name,
            "source_type": self.source_type,
            "access_status": "blocked_unauthorized",
            "restriction_reason": self.restriction_reason,
            "licensing": self.licensing,
            "notes": self.notes
        }

def get_restricted_sources() -> List[RestrictedSourceAdapter]:
    return [
        RestrictedSourceAdapter(
            source_id="opensky_network",
            provider_name="OpenSky Network Historical API",
            source_type="academic_adsb_archive",
            licensing="Academic / Non-commercial research agreement",
            supported_airports=["OSDI", "OSAP", "OSLK", "OSDZ", "OSKL"],
            restriction_reason="HTTP 403 Forbidden: Anonymous access to historical Syrian flight states is blocked. Requires verified institutional academic researcher credentials and Trino cluster access.",
            notes="No automated credential bypass attempted. Licensing terms respected."
        ),
        RestrictedSourceAdapter(
            source_id="flightaware_aeroapi",
            provider_name="FlightAware AeroAPI",
            source_type="commercial_proprietary_api",
            licensing="Commercial proprietary enterprise contract",
            supported_airports=["DAM", "ALP", "LTK", "DEZ", "KAC"],
            restriction_reason="Commercial paywall: Historical airport movements older than 7 days require a paid commercial AeroAPI subscription ($100+/mo).",
            notes="No automated subscription bypass attempted. Commercial terms respected."
        ),
        RestrictedSourceAdapter(
            source_id="adsb_exchange",
            provider_name="ADS-B Exchange Historical Feeds",
            source_type="commercial_adsb_archive",
            licensing="Commercial proprietary enterprise license",
            supported_airports=["Syria Airspace"],
            restriction_reason="Commercial paywall: Historical REST API endpoints require a RapidAPI enterprise subscription ($100-$1000/mo). Web tracking frontend terms prohibit automated scraping.",
            notes="No automated scraping attempted. Terms of service strictly respected."
        )
    ]
