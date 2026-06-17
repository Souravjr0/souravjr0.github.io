import argparse
import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from config import (
    ADVANCED_AI_ML_FRAMEWORK_ENTRYPOINT,
    ADVANCED_AI_ML_FRAMEWORK_PATH,
    ALGO_TRADING_ENGINE_ENTRYPOINT,
    ALGO_TRADING_ENGINE_PATH,
    AI_TRADING_PLATFORM_ENTRYPOINT,
    AI_TRADING_PLATFORM_PATH,
    NAUTILUS_TRADER_ENTRYPOINT,
    NAUTILUS_TRADER_PATH,
    QUANT_ENTRYPOINT,
    QUANT_PATH,
    DELTA_RISKBOT_ENTRYPOINT,
    DELTA_RISKBOT_PATH,
    EXTERNAL_FRAMEWORKS_DIR,
    INVESTING_ALGO_ENTRYPOINT,
    INVESTING_ALGO_PATH,
    TRADING_BOT_FRAMEWORK_ENTRYPOINT,
    TRADING_BOT_FRAMEWORK_PATH,
)


@dataclass(frozen=True)
class ExternalFramework:
    key: str
    name: str
    repo_url: str
    folder: str
    path_value: str
    entry_value: str
    path_env_name: str
    entry_env_name: str


FRAMEWORKS = [
    ExternalFramework(
        key="investing_algo",
        name="Investing Algorithm Framework",
        repo_url="https://github.com/coding-kitties/investing-algorithm-framework",
        folder="investing-algorithm-framework",
        path_value=INVESTING_ALGO_PATH,
        entry_value=INVESTING_ALGO_ENTRYPOINT,
        path_env_name="INVESTING_ALGO_PATH",
        entry_env_name="INVESTING_ALGO_ENTRYPOINT",
    ),
    ExternalFramework(
        key="trading_bot_framework",
        name="Trading Bot Framework",
        repo_url="https://github.com/pecan987/trading-bot-framework",
        folder="trading-bot-framework",
        path_value=TRADING_BOT_FRAMEWORK_PATH,
        entry_value=TRADING_BOT_FRAMEWORK_ENTRYPOINT,
        path_env_name="TRADING_BOT_FRAMEWORK_PATH",
        entry_env_name="TRADING_BOT_FRAMEWORK_ENTRYPOINT",
    ),
    ExternalFramework(
        key="algo_trading_engine",
        name="Algorithmic Trading Engine",
        repo_url="https://github.com/JohannesMeyerYC/AlgorithmicTradingEngine",
        folder="AlgorithmicTradingEngine",
        path_value=ALGO_TRADING_ENGINE_PATH,
        entry_value=ALGO_TRADING_ENGINE_ENTRYPOINT,
        path_env_name="ALGO_TRADING_ENGINE_PATH",
        entry_env_name="ALGO_TRADING_ENGINE_ENTRYPOINT",
    ),
    ExternalFramework(
        key="advanced_ai_ml_framework",
        name="Advanced AI/ML Trading Framework",
        repo_url="https://github.com/CodingEye/Advanced_AI_ML_Trading_Framework",
        folder="Advanced_AI_ML_Trading_Framework",
        path_value=ADVANCED_AI_ML_FRAMEWORK_PATH,
        entry_value=ADVANCED_AI_ML_FRAMEWORK_ENTRYPOINT,
        path_env_name="ADVANCED_AI_ML_FRAMEWORK_PATH",
        entry_env_name="ADVANCED_AI_ML_FRAMEWORK_ENTRYPOINT",
    ),
    ExternalFramework(
        key="delta_riskbot",
        name="Delta Risk Bot",
        repo_url="https://github.com/rickymagal/delta-riskbot",
        folder="delta-riskbot",
        path_value=DELTA_RISKBOT_PATH,
        entry_value=DELTA_RISKBOT_ENTRYPOINT,
        path_env_name="DELTA_RISKBOT_PATH",
        entry_env_name="DELTA_RISKBOT_ENTRYPOINT",
    ),
    ExternalFramework(
        key="nautilus_trader",
        name="Nautilus Trader",
        repo_url="https://github.com/nautechsystems/nautilus_trader",
        folder="nautilus_trader",
        path_value=NAUTILUS_TRADER_PATH,
        entry_value=NAUTILUS_TRADER_ENTRYPOINT,
        path_env_name="NAUTILUS_TRADER_PATH",
        entry_env_name="NAUTILUS_TRADER_ENTRYPOINT",
    ),
    ExternalFramework(
        key="quant",
        name="Quant (multi-market transformer POC)",
        repo_url="https://github.com/AryaaSk/quant",
        folder="quant",
        path_value=QUANT_PATH,
        entry_value=QUANT_ENTRYPOINT,
        path_env_name="QUANT_PATH",
        entry_env_name="QUANT_ENTRYPOINT",
    ),
    ExternalFramework(
        key="ai_trading_platform",
        name="AI Trading Platform",
        repo_url="https://github.com/gregorizeidler/ai-trading-platform",
        folder="ai-trading-platform",
        path_value=AI_TRADING_PLATFORM_PATH,
        entry_value=AI_TRADING_PLATFORM_ENTRYPOINT,
        path_env_name="AI_TRADING_PLATFORM_PATH",
        entry_env_name="AI_TRADING_PLATFORM_ENTRYPOINT",
    ),
]


def _resolve_base_dir() -> Path:
    return Path(EXTERNAL_FRAMEWORKS_DIR).expanduser().resolve()


def _resolve_path(framework: ExternalFramework) -> Path | None:
    if framework.path_value:
        return Path(framework.path_value).expanduser().resolve()
    base_dir = _resolve_base_dir()
    return base_dir / framework.folder


def _is_module_entrypoint(entry_value: str) -> bool:
    return entry_value.strip().lower().startswith("module:")


def _module_name(entry_value: str) -> str:
    return entry_value.split(":", 1)[1].strip()


def _resolve_entrypoint(framework: ExternalFramework) -> Path | str | None:
    if not framework.entry_value:
        return None
    if _is_module_entrypoint(framework.entry_value):
        return framework.entry_value
    entry_path = Path(framework.entry_value)
    if entry_path.is_absolute():
        return entry_path
    root = _resolve_path(framework)
    if root is None:
        return None
    return (root / entry_path).resolve()


def get_framework_statuses() -> list[dict]:
    statuses: list[dict] = []
    for framework in FRAMEWORKS:
        path = _resolve_path(framework)
        entrypoint = _resolve_entrypoint(framework)
        path_exists = bool(path and path.exists())
        if isinstance(entrypoint, Path):
            entry_exists = entrypoint.exists()
            entry_value = str(entrypoint)
        elif isinstance(entrypoint, str):
            module_name = _module_name(entrypoint) if _is_module_entrypoint(entrypoint) else entrypoint
            try:
                import contextlib
                import io
                with contextlib.redirect_stderr(io.StringIO()):
                    entry_exists = importlib.util.find_spec(module_name) is not None
                    if entry_exists and module_name == "nautilus_trader":
                        # Verify that the compiled core module is actually importable
                        import importlib
                        importlib.import_module("nautilus_trader.core")
            except Exception:
                entry_exists = False
            entry_value = entrypoint
        else:
            entry_exists = False
            entry_value = ""
        statuses.append(
            {
                "key": framework.key,
                "name": framework.name,
                "repo_url": framework.repo_url,
                "path": str(path) if path else "",
                "entrypoint": entry_value,
                "path_exists": path_exists,
                "entry_exists": entry_exists,
            }
        )
    return statuses


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    lines = [
        "  ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)),
        "  ".join("-" * widths[idx] for idx in range(len(headers))),
    ]
    for row in rows:
        lines.append("  ".join(row[idx].ljust(widths[idx]) for idx in range(len(headers))))
    return "\n".join(lines)


def list_frameworks() -> None:
    statuses = get_framework_statuses()
    rows: list[list[str]] = []
    for status in statuses:
        path_status = "ok" if status["path_exists"] else "missing"
        entry_status = "ok" if status["entry_exists"] else "missing"
        rows.append(
            [
                status["key"],
                path_status,
                entry_status,
                status["path"] or "-",
            ]
        )
    print(_format_table(["Framework", "Path", "Entrypoint", "Path Value"], rows))


_ACTIVE_PROCESS = None

def terminate_active_framework() -> None:
    global _ACTIVE_PROCESS
    if _ACTIVE_PROCESS and _ACTIVE_PROCESS.poll() is None:
        try:
            print(f"\n[Plugin Engine] Forcefully killing active plugin process (PID: {_ACTIVE_PROCESS.pid})...")
            _ACTIVE_PROCESS.kill()
            _ACTIVE_PROCESS.wait(timeout=2)
        except Exception:
            pass
        finally:
            _ACTIVE_PROCESS = None

def run_framework(key: str, extra_args: list[str]) -> None:
    global _ACTIVE_PROCESS
    framework = next((fw for fw in FRAMEWORKS if fw.key == key), None)
    if framework is None:
        raise ValueError(f"Unknown framework key: {key}")

    path = _resolve_path(framework)
    entrypoint = _resolve_entrypoint(framework)

    # Inject environment variables to force UTF-8 mode on Windows / Python 3.7+ child processes
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    cwd_dir = None
    if isinstance(entrypoint, str) and _is_module_entrypoint(entrypoint):
        module_name = _module_name(entrypoint)
        if importlib.util.find_spec(module_name) is None:
            raise FileNotFoundError(
                f"{framework.name} module not found. Install it and set {framework.entry_env_name}."
            )
        cmd = [sys.executable, "-m", module_name, *extra_args]
        cwd_dir = str(path) if path and path.exists() else None
    else:
        if not path or not path.exists():
            raise FileNotFoundError(
                f"{framework.name} path not found. Set {framework.path_env_name} or EXTERNAL_FRAMEWORKS_DIR."
            )
        if not entrypoint or not isinstance(entrypoint, Path) or not entrypoint.exists():
            raise FileNotFoundError(
                f"{framework.name} entrypoint not found. Set {framework.entry_env_name}."
            )
        cmd = [sys.executable, str(entrypoint), *extra_args]
        cwd_dir = str(path)

    # Use a new process group on Windows to prevent child from receiving Ctrl+C directly
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(cmd, cwd=cwd_dir, env=env, creationflags=creationflags)
    _ACTIVE_PROCESS = proc

    try:
        proc.communicate(timeout=45)
        ret = proc.poll()
        if ret != 0:
            raise subprocess.CalledProcessError(ret, cmd)
    except subprocess.TimeoutExpired as te:
        print(f"[TIMEOUT] [Plugin Engine] {framework.name} timed out after 45 seconds!")
        try:
            proc.kill()
            proc.wait(timeout=2)
        except Exception:
            pass
        raise te
    except (KeyboardInterrupt, SystemExit) as ke:
        try:
            proc.kill()
            proc.wait(timeout=2)
        except Exception:
            pass
        raise ke
    finally:
        _ACTIVE_PROCESS = None


def main() -> None:
    parser = argparse.ArgumentParser(description="External framework runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List external frameworks")

    run_parser = subparsers.add_parser("run", help="Run a framework entrypoint")
    run_parser.add_argument("framework", help="Framework key")
    run_parser.add_argument("args", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.command == "list":
        list_frameworks()
        return

    if args.command == "run":
        extra_args = args.args or []
        if extra_args and extra_args[0] == "--":
            extra_args = extra_args[1:]
        run_framework(args.framework, extra_args)


if __name__ == "__main__":
    main()
