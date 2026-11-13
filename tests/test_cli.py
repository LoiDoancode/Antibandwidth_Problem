"""Smoke tests for CLI interfaces in main.py and benchmark.py."""

import pytest
import subprocess
import sys


def test_main_cli_help():
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Antibandwidth" in result.stdout or "usage" in result.stdout.lower()


def test_benchmark_cli_help():
    result = subprocess.run(
        [sys.executable, "benchmark.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "benchmark" in result.stdout.lower() or "usage" in result.stdout.lower()

