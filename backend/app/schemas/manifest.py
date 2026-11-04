"""Manifest request/response schemas."""

from app.models.manifest import Manifest, ManifestCreate, ManifestUpdate


class ManifestCreateRequest(ManifestCreate):
    pass


class ManifestUpdateRequest(ManifestUpdate):
    pass


class ManifestResponse(Manifest):
    pass
