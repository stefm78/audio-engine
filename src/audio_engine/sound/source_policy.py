from urllib.parse import urlparse

OPEN_LICENSES = {
    "CC0-1.0": {"score": 20, "raw_redistribution": "allowed"},
    "PDM-1.0": {"score": 20, "raw_redistribution": "allowed"},
    "Public-Domain": {"score": 20, "raw_redistribution": "allowed"},
    "CC-BY-4.0": {"score": 16, "raw_redistribution": "allowed"},
    "CC-BY-3.0": {"score": 14, "raw_redistribution": "allowed"},
}

TRUSTED_PROVIDER_HOSTS = {
    "wikimedia-commons": {"commons.wikimedia.org", "upload.wikimedia.org"},
    "freesound": {"freesound.org", "www.freesound.org"},
    "openverse": {"openverse.org", "api.openverse.org"},
}

_PROVIDER_ALIASES = {
    "wikimedia commons": "wikimedia-commons",
    "commons": "wikimedia-commons",
    "wikimedia": "wikimedia-commons",
    "freesound.org": "freesound",
    "openverse.org": "openverse",
}


def normalize_provider(value):
    if not value:
        return None
    normalized = str(value).strip().lower().replace("_", "-")
    return _PROVIDER_ALIASES.get(normalized, normalized)


def assess_source_license(provider, source_page, license_id):
    provider_id = normalize_provider(provider)
    host = (urlparse(source_page).hostname or "").lower() if source_page else ""
    trusted_hosts = TRUSTED_PROVIDER_HOSTS.get(provider_id, set())
    provider_verified = bool(host and any(host == allowed or host.endswith("." + allowed) for allowed in trusted_hosts))
    license_policy = OPEN_LICENSES.get(license_id)
    license_allowed = license_policy is not None
    verified = provider_verified and license_allowed
    return {
        "provider": provider_id,
        "host": host or None,
        "provider_verified": provider_verified,
        "license_allowed": license_allowed,
        "verified": verified,
        "verification_method": "trusted-source-metadata" if verified else None,
        "license_score": license_policy["score"] if license_policy else 0,
        "policy_raw_redistribution": license_policy["raw_redistribution"] if license_policy else None,
    }
