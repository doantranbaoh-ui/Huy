# --- app/models.py ---
"""
Shared data models
No external dependencies
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Proxy:
    ip: str
    port: int
    protocol: str = "http"
    country: Optional[str] = None
    speed: float = 0.0
    is_alive: bool = True
    last_checked: Optional[str] = None
    fail_count: int = 0
    anonymity: str = "unknown"
    
    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol,
            "country": self.country,
            "speed": self.speed,
            "is_alive": self.is_alive,
            "last_checked": self.last_checked,
            "fail_count": self.fail_count,
            "anonymity": self.anonymity
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Proxy':
        return cls(
            ip=data.get("ip", ""),
            port=data.get("port", 0),
            protocol=data.get("protocol", "http"),
            country=data.get("country"),
            speed=data.get("speed", 0.0),
            is_alive=data.get("is_alive", True),
            last_checked=data.get("last_checked"),
            fail_count=data.get("fail_count", 0),
            anonymity=data.get("anonymity", "unknown")
        )
    
    def __str__(self):
        return f"{self.protocol}://{self.ip}:{self.port}"
