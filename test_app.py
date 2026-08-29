#!/usr/bin/env python
"""Quick test to verify app structure."""
from app.main import app

print("✓ App imported successfully")
print(f"\nApp has {len(app.routes)} total routes:\n")
for i, route in enumerate(app.routes, 1):
    route_type = type(route).__name__
    path = getattr(route, 'path', '?')
    methods = getattr(route, 'methods', set())
    name = getattr(route, 'name', '?')
    
    if methods:
        print(f"{i:2}. [{route_type:15s}] {path:40s} {sorted(methods)}")
    else:
        # For routes without methods, check if it's an APIRoute
        if hasattr(route, 'endpoint'):
            print(f"{i:2}. [{route_type:15s}] {path:40s} {route.endpoint.__name__}")
        else:
            print(f"{i:2}. [{route_type:15s}] {path:40s} {name}")
