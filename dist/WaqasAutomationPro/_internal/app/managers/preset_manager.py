"""
Preset Manager for Video Generation Config Presets (TikTok, Shorts, Cinematic, etc.).
"""

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class GenerationPreset:
    name: str
    model: str
    ratio: str
    duration: int
    description: str

DEFAULT_PRESETS: List[GenerationPreset] = [
    GenerationPreset(
        name="TikTok / Reels Default",
        model="Seedance 2.0",
        ratio="9:16",
        duration=10,
        description="Standard 9:16 vertical 10s video preset for TikTok, Instagram Reels, and YouTube Shorts."
    ),
    GenerationPreset(
        name="YouTube Widescreen",
        model="Seedance 2.0",
        ratio="16:9",
        duration=10,
        description="Standard 16:9 widescreen video format."
    ),
    GenerationPreset(
        name="Square Social",
        model="Seedance 2.0",
        ratio="1:1",
        duration=10,
        description="1:1 square ratio format for Instagram feed posts."
    )
]

class PresetManager:
    @staticmethod
    def get_all_presets() -> List[GenerationPreset]:
        return DEFAULT_PRESETS

    @staticmethod
    def get_preset_by_name(name: str) -> GenerationPreset:
        for p in DEFAULT_PRESETS:
            if p.name.lower() == name.lower():
                return p
        return DEFAULT_PRESETS[0]
