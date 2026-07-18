import _bootstrap  # noqa: F401  (sys.path + isolated config)

from sysmind_orbit import classify_query, build_context

def test_classify():
    assert classify_query("why is disk full") == "disk"
    assert classify_query("update packages") == "packages"
    assert classify_query("security check") == "security"
    assert classify_query("random thing") == "general"
    print("PASS: classify")

def test_build_context():
    atlas = {
        "generated_at": "2026-06-09T00:00:00Z",
        "system": {"os": "Parrot OS", "kernel": "6.6", "uptime": "3 days"},
        "packages": {"installed": 100, "upgradable": 5},
        "resources": {"disk_root_percent": 72, "memory_percent": 45, "load": 0.4},
        "services": {"running": 30, "failed": 1, "failed_services": ["bluetooth"]},
        "security": {"open_ports": [22, 80]},
        "alerts": [{"level": "warn", "category": "disk", "message": "Disk 72% full"}],
        "parrot": {"anonsurf_available": True},
    }
    ctx = build_context("why is disk full", atlas, budget=4000)
    assert "Disk 72% full" in ctx
    assert "Root disk: 72%" in ctx
    assert "Parrot OS" in ctx
    print("PASS: build_context")

if __name__ == "__main__":
    test_classify()
    test_build_context()
