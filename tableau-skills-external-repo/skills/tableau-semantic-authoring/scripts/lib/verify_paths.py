"""Verify script paths are accessible."""
import os
import sys


def verify_scripts():
    """Check if shared scripts are accessible."""
    required_scripts = [
        "discover_sdm.py",
        "create_calc_field.py",
        "create_metric.py",
    ]

    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    missing = []

    for script in required_scripts:
        path = os.path.join(script_dir, script)
        if not os.path.exists(path):
            missing.append(script)

    if missing:
        print(f"ERROR: Missing scripts: {missing}")
        print(f"Expected location: {script_dir}")
        print("Ensure tableau-next-author skill is installed and symlinks are created.")
        sys.exit(1)

    print("All required scripts accessible")
    return True


if __name__ == "__main__":
    verify_scripts()
