from .edge import EdgeProvider


class ProviderRegistry:
    """Small explicit registry for Production synthesis providers.

    Registration is dependency injection, not discovery. The engine never scans
    installed packages and never falls back to another provider.
    """

    def __init__(self, providers=None, include_edge=True):
        self._providers = {}
        if include_edge:
            self.register(EdgeProvider())
        for key, provider in (providers or {}).items():
            if getattr(provider, "name", None) != key:
                raise ValueError(
                    f"Provider registry key {key!r} differs from provider.name "
                    f"{getattr(provider, 'name', None)!r}"
                )
            self.register(provider)

    def register(self, provider):
        name = getattr(provider, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Provider must expose a non-empty name")
        if name in self._providers:
            raise ValueError(f"Duplicate provider registration: {name}")
        self._providers[name] = provider
        return provider

    def get(self, name):
        try:
            return self._providers[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._providers)) or "none"
            raise ValueError(
                f"Production provider {name!r} is unavailable; registered providers: {available}. "
                "No fallback is allowed."
            ) from exc

    def records(self, names):
        records = []
        for name in sorted(set(names)):
            provider = self.get(name)
            records.append({
                "name": name,
                "processing": getattr(provider, "processing", "unknown"),
            })
        return records
