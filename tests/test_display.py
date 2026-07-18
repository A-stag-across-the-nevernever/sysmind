import _bootstrap  # noqa: F401  (sys.path + isolated config)

from sysmind_display import render_dashboard

def test_dashboard():
    atlas = {
        "alerts": [{"level": "warn", "message": "Disk 85% full"}],
        "resources": {"disk_root_percent": 85, "memory_percent": 60, "load": 1.2},
    }
    out = render_dashboard(atlas)
    assert "Disk: 85%" in out
    assert "🟡" in out
    print("PASS: dashboard")

if __name__ == "__main__":
    test_dashboard()
