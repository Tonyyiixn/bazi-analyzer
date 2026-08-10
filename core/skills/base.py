from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    id: str
    title: str
    description: str
    icon: str
    system_prompt: str
