"""Enumerations used across the application."""

from __future__ import annotations

from enum import Enum


class Mode(str, Enum):
    """Interaction modes."""

    ASK = "ask"
    GUIDE = "guide"
    SHOW = "show"
    GENERATE = "generate"
    DEBUG = "debug"
    TRANSLATE = "translate"


class Domain(str, Enum):
    """Engineering domains."""

    PCB = "pcb"
    FIRMWARE = "firmware"
    DEBUG = "debug"
    TRANSLATION = "translation"
    GENERAL = "general"


class EDATool(str, Enum):
    """Supported tools."""

    ALTIUM = "Altium Designer"
    KICAD = "KiCad"
    STM32 = "STM32CubeIDE/CubeMX"
    ESP_IDF = "ESP-IDF"
    UNKNOWN = "Unknown"


class AgentRole(str, Enum):
    """Agent roles."""

    PLANNER = "planner"
    TOOL_SPECIALIST = "tool_specialist"
    KNOWLEDGE = "knowledge"
    IMPLEMENTATION = "implementation"
    DEBUG = "debug"
    VALIDATION = "validation"
    TUTOR = "tutor"


class Persona(str, Enum):
    """User expertise level controlling verbosity."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class Verdict(str, Enum):
    """Screenshot analysis verdict."""

    MATCH = "match"
    MISMATCH = "mismatch"
    INCONCLUSIVE = "inconclusive"


class DocType(str, Enum):
    """Knowledge document type, ordered by retrieval priority."""

    OFFICIAL_DOC = "official_doc"
    REFERENCE_MANUAL = "reference_manual"
    DATASHEET = "datasheet"
    SDK_DOC = "sdk_doc"
    APP_NOTE = "app_note"
    EXAMPLE_PROJECT = "example_project"
    COMMUNITY = "community"

    @property
    def priority(self) -> int:
        """Lower number means higher authority."""
        order = list(DocType)
        return order.index(self)

    @property
    def is_secondary(self) -> bool:
        """Whether this source is secondary evidence only."""
        return self is DocType.COMMUNITY