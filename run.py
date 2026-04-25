"""
run.py - Claude Code launcher com troca de provider

Uso:
  python run.py                       # roda Claude Code com provider ativo
  python run.py status                # mostra provider ativo
  python run.py proxy                 # inicia proxy Anthropic->OpenAI
  python run.py --provider openai     # troca para OpenAI
  python run.py --provider local      # troca para LLM local
  python run.py status --provider local  # troca e mostra status
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
ENV_ACTIVE    = ROOT / ".env.local"
PROVIDERS_DIR = ROOT / "providers"
ACTIVE_FILE   = ROOT / ".active-provider"
BUN           = Path(r"C:\Users\rafha\.bun\bin\bun.exe")
PYTHON        = Path(sys.executable)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict:
    """Le um arquivo .env e retorna dict com os valores."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", line)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env


def apply_env(path: Path):
    """Aplica variaveis de .env no processo atual."""
    for k, v in load_env(path).items():
        os.environ[k] = v


def active_provider() -> str:
    if ACTIVE_FILE.exists():
        return ACTIVE_FILE.read_text(encoding="utf-8").strip()
    return "unknown"


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_status():
    apply_env(ENV_ACTIVE)
    prov = active_provider()
    url   = os.environ.get("ANTHROPIC_BASE_URL", "-")
    model = os.environ.get("ANTHROPIC_MODEL", "-")
    fast  = os.environ.get("ANTHROPIC_SMALL_FAST_MODEL", "-")
    print()
    print(f"  Provider : {prov}")
    print(f"  URL      : {url}")
    print(f"  Model    : {model}")
    print(f"  Fast mdl : {fast}")
    print()


def cmd_switch(name: str):
    src = PROVIDERS_DIR / f"{name}.env"
    if not src.exists():
        available = [p.stem for p in PROVIDERS_DIR.glob("*.env")]
        print(f"Provider '{name}' nao encontrado. Disponiveis: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)
    shutil.copy2(src, ENV_ACTIVE)
    ACTIVE_FILE.write_text(name, encoding="utf-8")
    print(f"  Trocado para: {name}")


def cmd_proxy():
    proxy_script = ROOT / "proxy.py"
    print()
    print("  Proxy Anthropic->OpenAI em :4000")
    print("  Deixe este terminal aberto e abra outro para rodar: python run.py")
    print()
    os.execv(str(PYTHON), [str(PYTHON), str(proxy_script)])


def cmd_run(extra_args: list):
    if not BUN.exists():
        print(f"Bun nao encontrado em {BUN}", file=sys.stderr)
        print("Instale em: https://bun.sh", file=sys.stderr)
        sys.exit(1)

    if not ENV_ACTIVE.exists():
        print("  Sem provider ativo - padrao: openai")
        cmd_switch("openai")

    apply_env(ENV_ACTIVE)
    prov  = active_provider()
    model = os.environ.get("ANTHROPIC_MODEL", "?")
    url   = os.environ.get("ANTHROPIC_BASE_URL", "?")
    print()
    print(f"  Claude Code  provider={prov}  model={model}  url={url}")
    print()

    cmd = [
        str(BUN), "run",
        "--preload", str(ROOT / "preload.js"),
        str(ROOT / "src" / "entrypoints" / "cli.tsx"),
    ] + extra_args

    os.execv(str(BUN), cmd)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?", default="")
    parser.add_argument("--provider", "-p", default="")
    # Captura tudo que sobrar para passar ao CLI
    args, rest = parser.parse_known_args()

    # Troca de provider (pode combinar com outros comandos)
    if args.provider:
        cmd_switch(args.provider)

    if args.command == "status":
        cmd_status()
    elif args.command == "proxy":
        cmd_proxy()
    elif args.command == "":
        cmd_run(rest)
    else:
        # Passa o comando direto ao CLI (ex: python run.py chat)
        cmd_run([args.command] + rest)


if __name__ == "__main__":
    main()
