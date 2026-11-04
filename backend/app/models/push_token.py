"""Push notification token store.

One document per (user_id, token) pair so the same user can have
multiple devices registered. `token` is the FCM/APNs/Expo push token.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PushPlatform(str, Enum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class PushToken(BaseModel):
    id: Optional[str] = None
    user_id: str
    token: str = Field(min_length=10, max_length=512)
    platform: PushPlatform = PushPlatform.ANDROID
    device_id: Optional[str] = None
    app_version: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True


class PushTokenRegister(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    platform: PushPlatform = PushPlatform.ANDROID
    device_id: Optional[str] = None
    app_version: Optional[str] = None


class PushTokenResponse(PushToken):
    pass


__all__ = [
    "PushPlatform",
    "PushToken",
    "PushTokenRegister",
    "PushTokenResponse",
]
