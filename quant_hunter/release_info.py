from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseInfo:
    app_id: str
    internal_name: str
    product_name: str
    display_name: str
    company_name: str
    file_description: str
    product_version: str
    file_version: str
    startup_brand: str

    @property
    def branded_title(self) -> str:
        return f"{self.display_name} v{self.product_version}"


RELEASE_INFO = ReleaseInfo(
    app_id="9C7D2A28-B8F5-4D1A-BF3A-A0CB0B3F6D21",
    internal_name="quant_hunter",
    product_name="Quant Hunter Pro",
    display_name="量化猎手 Pro",
    company_name="Quant Hunter",
    file_description="Quant Hunter desktop trading workstation",
    product_version="2.3.0",
    file_version="2.3.0.0",
    startup_brand="QUANT HUNTER PRO",
)


def workspace_badge_prefix() -> str:
    return RELEASE_INFO.branded_title
