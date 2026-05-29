"""Explicit owner-export installer for the FlowPilot router skeleton.

This module replaces hundreds of hand-written public wrappers in
``flowpilot_router.py`` with one auditable registry installer. The registry data
lives in ``flowpilot_router_facade_export_manifest`` so this module stays focused
on resolving and installing owner exports.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any, Callable

from flowpilot_router_facade_export_manifest import OWNER_EXPORTS, PUBLIC_EXPORT_NAMES

def _owner_target(module_name: str, target_name: str, router_module: ModuleType, bind_router: bool) -> Callable[..., Any]:
    module = importlib.import_module(module_name)
    if bind_router and hasattr(module, "_bind_router"):
        module._bind_router(router_module)
    return getattr(module, target_name)

def _make_proxy(
    public_name: str,
    module_name: str,
    target_name: str,
    *,
    router_module: ModuleType,
    bind_router: bool,
    inject_router: bool,
) -> Callable[..., Any]:
    def _proxy(*args: Any, **kwargs: Any) -> Any:
        target = _owner_target(module_name, target_name, router_module, bind_router)
        if inject_router:
            return target(router_module, *args, **kwargs)
        return target(*args, **kwargs)

    _proxy.__name__ = public_name
    _proxy.__qualname__ = public_name
    _proxy.__module__ = router_module.__name__
    _proxy.__doc__ = f"Transitional owner export for {module_name}.{target_name}."
    return _proxy

def resolve_facade_export(name: str, router_module: ModuleType) -> Callable[..., Any]:
    for (module_name, bind_router, inject_router), exports in OWNER_EXPORTS.items():
        for public_name, target_name in exports:
            if public_name == name:
                return _make_proxy(public_name, module_name, target_name, router_module=router_module, bind_router=bind_router, inject_router=inject_router)
    raise AttributeError(name)

def install_facade_exports(router_module: ModuleType, namespace: dict[str, Any]) -> None:
    for (module_name, bind_router, inject_router), exports in OWNER_EXPORTS.items():
        for public_name, target_name in exports:
            namespace[public_name] = _make_proxy(public_name, module_name, target_name, router_module=router_module, bind_router=bind_router, inject_router=inject_router)
