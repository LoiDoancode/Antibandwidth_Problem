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


@pytest.mark.parametrize("encoding", ["direct", "scl", "commander", "seqcounter"])
def test_main_cli_rejects_direct_optimization_for_sat(encoding):
    result = subprocess.run(
        [sys.executable, "main.py", "--encoding", encoding, "--method", "direct_optimize"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "direct_optimize" in result.stderr
    assert "CP-SAT" in result.stderr
    assert "RESULT SUMMARY" not in result.stdout


@pytest.mark.parametrize("selector", ["--encoding", "--solver"])
def test_main_cli_preserves_cpsat_direct_optimization(selector, tmp_path):
    graph_path = tmp_path / "p6.txt"
    graph_path.write_text("6 6 5\n1 2\n2 3\n3 4\n4 5\n5 6\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "main.py", "--input", str(graph_path), selector, "cpsat", "--method", "direct_optimize"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Optimal Antibandwidth B*(G): 3" in result.stdout


@pytest.mark.parametrize("mode", ["check", "optimize", "batch"])
def test_main_cli_reports_external_solver_failure(mode, tmp_path, monkeypatch, capsys):
    import main as main_cli

    graph_path = tmp_path / "p6.txt"
    graph_path.write_text("6 6 5\n1 2\n2 3\n3 4\n4 5\n5 6\n", encoding="utf-8")
    argv = ["main.py", "--input", str(graph_path)]
    if mode == "batch":
        other_path = tmp_path / "other_p6.txt"
        other_path.write_text(graph_path.read_text(encoding="utf-8"), encoding="utf-8")
        argv.append(str(other_path))
    argv.extend(["--external-solver", "failing-solver"])
    if mode == "check":
        argv.extend(["--check-k", "3"])
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(
        "src.solver.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", "invalid solver option"),
    )

    with pytest.raises(SystemExit) as error:
        main_cli.main()

    output = capsys.readouterr()
    assert error.value.code == 1
    assert "[Error]" in output.out
    assert "invalid solver option" in output.out
    assert "UNSATISFIABLE" not in output.out
    assert "RESULT SUMMARY" not in output.out
    assert "pip install" not in output.out
    assert "Traceback" not in output.err

