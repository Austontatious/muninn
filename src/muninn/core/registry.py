from __future__ import annotations

from dataclasses import dataclass, field

from .specs import AppSpec, BundleSpec, MemorySpec


@dataclass
class AppRegistry:
    apps: dict[str, AppSpec] = field(default_factory=dict)

    def register_app(self, app: AppSpec) -> None:
        if app.app_id in self.apps:
            raise ValueError(f"app_already_registered:{app.app_id}")
        self.apps[app.app_id] = app

    def get_app(self, app_id: str) -> AppSpec:
        if app_id not in self.apps:
            raise ValueError(f"app_not_registered:{app_id}")
        return self.apps[app_id]

    def get_memory_spec(self, app_id: str, memory_type: str) -> MemorySpec:
        app = self.get_app(app_id)
        if memory_type not in app.memory_types:
            raise ValueError(f"memory_type_not_registered:{app_id}:{memory_type}")
        return app.memory_types[memory_type]

    def get_bundle_spec(self, app_id: str, bundle_name: str | None) -> BundleSpec:
        app = self.get_app(app_id)
        name = bundle_name or app.default_bundle
        if not name:
            raise ValueError(f"bundle_not_set:{app_id}")
        if name not in app.bundles:
            raise ValueError(f"bundle_not_registered:{app_id}:{name}")
        return app.bundles[name]
