"""Pydantic schemas for structured tip extraction. This IS the extraction contract."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ParsedTip(BaseModel):
    course: str = Field(description="Racecourse name as written, e.g. 'Kempton', 'Ascot'")
    race_time: str = Field(description="Race start time as written in the tip, 24h HH:MM local UK/IE time")
    horse_name: str = Field(description="The horse's name exactly as written")
    side: Literal["BACK", "LAY"] = Field(description="BACK to bet on the horse, LAY to bet against it. Default BACK unless the tip clearly says lay.")
    tipped_price: Optional[float] = Field(default=None, description="Decimal odds mentioned in the tip (e.g. 4.5), or null if no price given. Convert fractional odds: 7/2 -> 4.5")
    rating: Optional[str] = Field(default=None, description="Any stake/confidence advice as written: '2pts', 'NAP', '5 stars', or null")
    each_way: bool = Field(default=False, description="True if the tip says each-way/E/W")
    confidence: float = Field(ge=0, le=1, description="Your confidence (0-1) that ALL fields above are correctly extracted")


class ParsedMessage(BaseModel):
    is_tip: bool = Field(description="True only if the message contains at least one actionable horse-racing bet tip. Chatter, results recaps, banter, adverts -> false.")
    tips: list[ParsedTip] = Field(default_factory=list, description="Every distinct tip in the message; empty if is_tip is false")
    notes: Optional[str] = Field(default=None, description="Anything ambiguous or noteworthy about the extraction")
