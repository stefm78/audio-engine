from urllib.parse import urlparse

OPEN_LICENSES = {
    "CC0-1.0": {"score": 20, "raw_redistribution": "allowed"},
    "PDM-1.0": {"score": 20, "raw_redistribution": "allowed"},
    "Public-Domain": {"score": 20, "raw_redistribution": "allowed"},
    "CC-BY-4.0": {"score": 16, "raw_redistribution": "allowed"},
    "CC-BY-3.0": {"score": 14, "raw_redistribution": "allowed"},
}

# These providers expose enough upstream metadata for Audio Engine to make a
# machine-verifiable promotion decision. Aggregators such as Openverse are
# discovery sources, not final licence authorities.
AUTO_VERIFIED_PROVIDER_HOSTS = {
    "wikimedia-commons": {"commons.wikimedia.org", "upload.wikimedia.org"},
}

KNOWN_PROVIDER_HOSTS = {
    **AUTO_VERIFIED_PROVIDER_HOSTS,
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


def assess_source_license(provider, source_page, license_id, *, machine_observed=False):
    provider_id = normalize_provider(provider)
    host = (urlparse(source_page).hostname or "").lower() if source_page else ""
    known_hosts = KNOWN_PROVIDER_HOSTS.get(provider_id, set())
    host_matches = bool(host and any(host == allowed or host.endswith("." + allowed) for allowed in known_hosts))
    trusted_hosts = AUTO_VERIFIED_PROVIDER_HOSTS.get(provider_id, set())
    authority_matches = bool(host and any(host == allowed or host.endswith("." + allowed) for allowed in trusted_hosts))
    license_policy = OPEN_LICENSES.get(license_id)
    license_allowed = license_policy is not None
    verified = bool(machine_observed and authority_matches and license_allowed)
    return {
        "provider": provider_id,
        "host": host or None,
        "provider_known": host_matches,
        "provider_verified": bool(machine_observed and authority_matches),
        "license_allowed": license_allowed,
        "verified": verified,
        "verification_method": "upstream-api-metadata" if verified else None,
        "license_score": license_policy["score"] if license_policy else 0,
        "policy_raw_redistribution": license_policy["raw_redistribution"] if license_policy else None,
        "machine_observed": bool(machine_observed),
    }
