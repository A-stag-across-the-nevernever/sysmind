import _bootstrap  # noqa: F401  (sys.path + isolated config)

from sysmind_common import (
    load_config, save_config, is_command_safe, contains_blocked,
    classify_command, is_approved, save_approval
)

def test_config_roundtrip():
    save_config({"level": 3, "model": "llama3.1:8b"})
    cfg = load_config()
    assert cfg["level"] == 3
    assert cfg["model"] == "llama3.1:8b"
    assert "budget" in cfg
    assert "approvals" in cfg
    print("PASS: config_roundtrip")

def test_safety():
    assert is_command_safe("apt update")
    assert not is_command_safe("rm -rf /")
    assert contains_blocked("dd if=/dev/zero of=/dev/sda")
    assert not contains_blocked("systemctl status ssh")
    assert not contains_blocked("dd if=/dev/zero of=/dev/sda", blocklist_enabled=False)
    print("PASS: safety")

def test_classify_command():
    base, sub, full = classify_command("apt update")
    assert base == "apt"
    assert sub == "apt:update"
    assert full == "apt update"
    
    base, sub, full = classify_command("systemctl restart ssh")
    assert base == "systemctl"
    assert sub == "systemctl:restart"
    assert full == "systemctl restart ssh"
    
    base, sub, full = classify_command("ls -la /home")
    assert base == "ls"
    assert sub == "ls:/home"
    assert full == "ls -la /home"
    
    # No args: base == sub == full
    base, sub, full = classify_command("htop")
    assert base == "htop"
    assert sub == "htop"
    assert full == "htop"
    print("PASS: classify_command")

def test_approval_independent_tiers():
    """Base does NOT cascade to sub or tertiary."""
    approvals = {
        "apt": {"level": 2},           # base: only bare 'apt' with no args
        "apt:update": {"level": 2},    # sub: any 'apt update ...'
        "apt update": {"level": 2},    # tertiary: exact match
    }
    
    # Tertiary approval matches exact command
    assert is_approved("apt update", 2, approvals)[0] == True
    
    # Sub approval matches same subcommand, different flags/args
    assert is_approved("apt update --allow-releaseinfo-change", 2, approvals)[0] == True
    
    # Base approval does NOT match commands with subcommands
    assert is_approved("apt upgrade", 2, approvals)[0] == False
    assert is_approved("apt autoremove", 2, approvals)[0] == False
    
    # Base approval ONLY matches bare command (base == sub == full)
    assert is_approved("apt", 2, approvals)[0] == True
    
    print("PASS: approval_independent_tiers")

def test_approval_level_gating():
    approvals = {
        "apt:update": {"level": 3},
    }
    # Approved at level 3, so level 2 should NOT auto-run
    assert is_approved("apt update", 2, approvals)[0] == False
    # Level 3+ should auto-run
    assert is_approved("apt update", 3, approvals)[0] == True
    assert is_approved("apt update", 4, approvals)[0] == True
    print("PASS: approval_level_gating")

def test_save_approval():
    cfg = load_config()
    key = save_approval(cfg, "apt update", "base", 2)
    assert key == "apt"
    assert cfg["approvals"]["apt"]["level"] == 2
    
    key = save_approval(cfg, "apt update", "sub", 2)
    assert key == "apt:update"
    assert cfg["approvals"]["apt:update"]["level"] == 2
    print("PASS: save_approval")

if __name__ == "__main__":
    test_config_roundtrip()
    test_safety()
    test_classify_command()
    test_approval_independent_tiers()
    test_approval_level_gating()
    test_save_approval()
