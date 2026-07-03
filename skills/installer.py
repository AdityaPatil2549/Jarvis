"""
skills/installer.py - Third-party skill installer for JARVIS-Lite.
Installs skills from GitHub into isolated virtual environments.

Source of truth: Implementation_plan.md §4.2.1, Architecture_Enhancements.md §4
Usage: python -m skills.installer <github-url>
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from utils.logger import JarvisLogger


logger = JarvisLogger()

THIRD_PARTY_DIR = Path("skills/third_party")


def install_skill(repo_url: str) -> bool:
    """
    Install a third-party skill from a GitHub repository.

    Steps:
    1. Clone into skills/third_party/<skill_name>
    2. Parse manifest.json and prompt user for capability approval
    3. Create isolated virtual environment
    4. Install requirements within that venv

    Args:
        repo_url: Git clone URL (e.g. https://github.com/user/jarvis-skill-x.git)

    Returns:
        True if installation succeeded
    """
    # Extract skill name from URL
    skill_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    skill_dir = THIRD_PARTY_DIR / skill_name

    if skill_dir.exists():
        logger.warning(f"Skill '{skill_name}' already installed at {skill_dir}",
                       component="installer")
        return False

    # Step 1: Clone repository
    logger.info(f"Cloning {repo_url}...", component="installer")
    THIRD_PARTY_DIR.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            ['git', 'clone', '--depth', '1', repo_url, str(skill_dir)],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone failed: {e.stderr}", component="installer")
        return False
    except FileNotFoundError:
        logger.error("git not found. Install git to use skill installer.",
                     component="installer")
        return False

    # Step 2: Parse manifest and prompt for approval
    manifest_path = skill_dir / "manifest.json"
    if not manifest_path.exists():
        logger.error(f"No manifest.json found in {skill_name}. Aborting.",
                     component="installer")
        shutil.rmtree(skill_dir)
        return False

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid manifest.json: {e}", component="installer")
        shutil.rmtree(skill_dir)
        return False

    capabilities = manifest.get('capabilities', [])
    if capabilities:
        print(f"\n⚠  Skill '{skill_name}' requests the following capabilities:")
        for cap in capabilities:
            print(f"   • {cap}")
        approval = input("\nAllow? (Y/n): ").strip().lower()
        if approval not in ('y', 'yes', ''):
            logger.info("Installation cancelled by user", component="installer")
            shutil.rmtree(skill_dir)
            return False

    # Step 3: Create isolated virtual environment
    venv_dir = skill_dir / "venv"
    logger.info(f"Creating virtual environment for '{skill_name}'...",
                component="installer")
    try:
        subprocess.run(
            ['python', '-m', 'venv', str(venv_dir)],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"venv creation failed: {e}", component="installer")
        shutil.rmtree(skill_dir)
        return False

    # Step 4: Install requirements
    req_file = skill_dir / "requirements.txt"
    if req_file.exists():
        pip_path = venv_dir / ("Scripts" if os.name == 'nt' else "bin") / "pip"
        logger.info(f"Installing dependencies for '{skill_name}'...",
                    component="installer")
        try:
            subprocess.run(
                [str(pip_path), 'install', '-r', str(req_file)],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Some dependencies failed to install: {e}",
                           component="installer")

    logger.info(f"✓ Skill '{skill_name}' installed successfully",
                component="installer")
    return True


def uninstall_skill(skill_name: str) -> bool:
    """Remove a third-party skill."""
    skill_dir = THIRD_PARTY_DIR / skill_name
    if not skill_dir.exists():
        logger.warning(f"Skill '{skill_name}' not found", component="installer")
        return False

    shutil.rmtree(skill_dir)
    logger.info(f"Skill '{skill_name}' uninstalled", component="installer")
    return True


def list_installed() -> list:
    """List all installed third-party skills."""
    if not THIRD_PARTY_DIR.exists():
        return []
    return [d.name for d in THIRD_PARTY_DIR.iterdir() if d.is_dir()]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m skills.installer <github-url>")
        print("       python -m skills.installer --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        installed = list_installed()
        if installed:
            print("Installed third-party skills:")
            for name in installed:
                print(f"  • {name}")
        else:
            print("No third-party skills installed.")
    else:
        install_skill(sys.argv[1])
