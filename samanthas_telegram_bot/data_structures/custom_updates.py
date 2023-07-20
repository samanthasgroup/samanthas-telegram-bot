from dataclasses import dataclass


@dataclass
class ChatwootUpdate:
    """Simple dataclass to wrap a custom update type"""

    data: dict[str, str]
