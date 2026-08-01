from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Channel:
    id: str
    name: str
    url: str
    number: str = ""
    logo: str = ""
    group: str = ""


@dataclass
class Programme:
    channel_id: str
    start: datetime
    stop: datetime
    title: str
    subtitle: str = ""
    description: str = ""
    category: List[str] = field(default_factory=list)
    icon: str = ""
    episode: str = ""


@dataclass
class ChannelGuide:
    channel: Channel
    now: Optional[Programme] = None
    next: Optional[Programme] = None
    programmes: List[Programme] = field(default_factory=list)
