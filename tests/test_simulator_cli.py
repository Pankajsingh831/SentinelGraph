import os
import sys
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_generator_cli_help_exits_successfully():
    """Verify python -m simulator.generator --help exits with 0 and prints help without generating data."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    cmd = [sys.executable, "-m", "simulator.generator", "--help"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)

    assert res.returncode == 0, f"Command failed: {res.stderr}"
    assert "SentinelGraph synthetic fraud and payment transaction data generator." in res.stdout
    assert "--db-url" in res.stdout
    assert "--seed" in res.stdout
    assert "--dry-run" in res.stdout

    # Assert help does NOT generate data or connect to database
    assert "Generating entities..." not in res.stdout
    assert "Generating normal transactions..." not in res.stdout
    assert "Connecting to DB" not in res.stdout
    assert "Database persistence complete!" not in res.stdout


def test_generator_script_help_exits_successfully():
    """Verify python simulator/generator.py --help exits with 0 and prints help."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    cmd = [sys.executable, str(REPO_ROOT / "simulator" / "generator.py"), "--help"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)

    assert res.returncode == 0, f"Command failed: {res.stderr}"
    assert "SentinelGraph synthetic fraud and payment transaction data generator." in res.stdout
    assert "Generating entities..." not in res.stdout


def test_simulator_imports_from_repo_root():
    """Verify simulator and app.models can be imported from repo root without external PYTHONPATH."""
    code = (
        "import simulator; "
        "from simulator.generator import DataGenerator; "
        "from simulator.config import SimulationConfig; "
        "from app.models.customer import Customer; "
        "from app.models.transaction import Transaction; "
        "from app.models.ground_truth import GroundTruth; "
        "assert Customer is not None; "
        "assert Transaction is not None; "
        "assert GroundTruth is not None; "
        "print('SUCCESS')"
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env
    )

    assert res.returncode == 0, f"Import test failed: {res.stderr}"
    assert "SUCCESS" in res.stdout


def test_replay_cli_help_exits_successfully():
    """Verify python -m simulator.replay_events --help exits with 0 and displays options."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    cmd = [sys.executable, "-m", "simulator.replay_events", "--help"]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)

    assert res.returncode == 0, f"Command failed: {res.stderr}"
    assert "Replay simulated transactions to Kafka" in res.stdout
    assert "--limit" in res.stdout
    assert "--offset" in res.stdout
    assert "--topic" in res.stdout
    assert "--dry-run" in res.stdout


def test_simulation_config_characteristics_intact():
    """Verify simulation configuration values match verified specifications."""
    from simulator.config import SimulationConfig

    cfg = SimulationConfig()
    assert cfg.num_customers == 1000
    assert cfg.num_merchants == 200
    assert cfg.num_devices == 500
    assert cfg.num_instruments == 800
    assert cfg.num_ips == 600
    assert cfg.num_normal_transactions == 50000
    assert cfg.seed == 42
    assert cfg.num_shared_device_rings == 5
    assert cfg.num_velocity_abusers == 10
    assert cfg.num_account_farms == 3
    assert cfg.num_refund_abusers == 8
    assert cfg.num_network_expansions == 4
