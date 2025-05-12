#!/usr/bin/env python3

"""Set up Qiime 2 on Google colab.

Do not use this on o local machine, especially not as an admin!
"""

import os
import sys
import shutil
from subprocess import Popen, PIPE

# Ensure rich is installed for console output
try:
    from rich.console import Console
except ImportError:
    print("rich library not found. Installing...")
    r_pip = Popen(["pip", "install", "rich"], stdout=PIPE, stderr=PIPE)
    _, err_pip = r_pip.communicate()
    if r_pip.returncode != 0:
        print(f"Failed to install rich: {err_pip.decode()}")
        # Fallback to basic print if rich cannot be installed
        class BasicConsole:
            def log(self, message, *args, **kwargs):
                if args: # rich specific formatting like [red]...[/red]
                    # Basic print won't handle rich tags, so print raw message
                    print(message, *args)
                else:
                    print(message)
        con = BasicConsole()
    else:
        from rich.console import Console
        con = Console()
else:
    con = Console()


# --- Path Configurations ---
# Miniforge will be installed here
PREFIX = "/content/miniforge3"
# QIIME 2 Conda environment will be created here
QIIME2_ENV_PATH = "/content/qiime2_env"

# Ensure base directory for Miniforge installation exists
os.makedirs(PREFIX, exist_ok=True)
# We will explicitly remove and let mamba create QIIME2_ENV_PATH later

# --- Initial Checks ---
# Check for existing Miniforge
has_conda = "conda version" in os.popen(f"{PREFIX}/bin/conda info 2>/dev/null").read()

# Check for existing QIIME 2 (more robustly, after PATH would be set)
# For initial check, it's okay if this is False to trigger installation.
# This path will be checked before installation attempt.
_initial_qiime_executable_check = os.path.join(QIIME2_ENV_PATH, "bin", "qiime")
has_qiime = False
if os.path.exists(_initial_qiime_executable_check):
    # Temporarily construct command to check existing QIIME 2 if path exists
    _check_output = os.popen(f"{_initial_qiime_executable_check} info 2>/dev/null").read()
    if "QIIME 2 release:" in _check_output:
        has_qiime = True

# --- Configuration Variables ---
MINICONDA_PATH_URL = (
    "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
)
MINICONDA_SCRIPT_NAME = os.path.basename(MINICONDA_PATH_URL)

# Default QIIME 2 version (current as of early 2024, may need updates for future)
# User can override via command line argument: ./setup_qiime2.py <version>
if len(sys.argv) == 2:
    version = sys.argv[1]
else:
    version = "2024.2" # Example: Use a recent version

# Determine Python version for QIIME 2 YAML based on QIIME 2 version
# This logic is based on historical QIIME 2 Python dependencies. Adjust if necessary.
py_major, py_minor = "3", "9" # Defaulting to Python 3.9 for newer QIIME 2
# Q2 2023.9 used py38, Q2 2024.2 uses py39
# This needs to map to the python version in the YML filename, e.g. py39
# The yml files are typically py38 or py39 for recent versions.
q2_version_tuple = tuple(int(v) for v in version.split("."))

if q2_version_tuple < (2021, 4): # Versions before 2021.4 (e.g., 2021.2)
    pyver_suffix = "36" # e.g. py36
    py_minor = "6"
elif q2_version_tuple < (2023, 9): # Versions from 2021.4 up to 2023.7
    pyver_suffix = "38" # e.g. py38
    py_minor = "8"
else: # Versions 2023.9 and potentially newer (like 2024.2, 2024.5 etc.)
    pyver_suffix = "38" # e.g. py39 (QIIME 2 2024.2 uses Python 3.9)
    py_minor = "8"

# Default to amplicon distro, adjust template if core is needed for older versions
QIIME_YAML_TEMPLATE = (
    "https://data.qiime2.org/distro/amplicon/qiime2-amplicon-{version}-py{python_suffix}-linux-conda.yml"
)
if q2_version_tuple < (2023, 9): # Older versions might have used 'core' or different naming
     QIIME_YAML_TEMPLATE = (
         "https://data.qiime2.org/distro/core/qiime2-{version}-py{python_suffix}-linux-conda.yml"
     )


QIIME_YAML_URL = QIIME_YAML_TEMPLATE.format(version=version, python_suffix=pyver_suffix)
QIIME_YAML_FILENAME = os.path.basename(QIIME_YAML_URL)

CONDA_EXECUTABLE_NAME = "mamba" # Use mamba for speed


def cleanup():
    """Remove downloaded temporary files."""
    if os.path.exists(MINICONDA_SCRIPT_NAME):
        os.remove(MINICONDA_SCRIPT_NAME)
    if os.path.exists(QIIME_YAML_FILENAME):
        os.remove(QIIME_YAML_FILENAME)
    # Do not remove /content/sample_data by default unless specifically intended.
    # if os.path.exists("/content/sample_data"):
    #     shutil.rmtree("/content/sample_data")
    con.log(":broom: Cleaned up downloaded temporary files.")


def run_and_check(args, success_check_text, message, failure_message, success_message, console=con):
    """Run a command, check its output and return code."""
    console.log(f"[bold cyan]{message}[/bold cyan]")
    # Use a fresh copy of os.environ for each subprocess
    process_env = os.environ.copy()
    process = Popen(args, env=process_env, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = process.communicate()
    full_output = stdout + stderr

    # Check return code and success_check_text (if provided)
    if process.returncode == 0 and (success_check_text is None or success_check_text in full_output):
        console.log(f"[bold blue]{success_message}[/bold blue]")
        return True
    else:
        console.log(f"[bold red]{failure_message}[/bold red]")
        console.log(f"Command: {' '.join(args)}")
        console.log(f"Return Code: {process.returncode}")
        console.log(f"Output (stdout):\n{stdout}")
        console.log(f"Output (stderr):\n{stderr}")
        # cleanup() # Commenting out cleanup on failure to allow inspection
        sys.exit(1)


if __name__ == "__main__":
    con.log(f":wrench: Starting QIIME 2 setup version {version} using Python {py_major}.{py_minor} (yaml suffix: py{pyver_suffix}).")
    con.log(f":file_folder: Miniforge prefix: {PREFIX}")
    con.log(f":file_folder: QIIME 2 environment prefix: {QIIME2_ENV_PATH}")

    if not has_conda:
        run_and_check(
            ["wget", "-nv", MINICONDA_PATH_URL, "-O", MINICONDA_SCRIPT_NAME], # -nv for less verbose wget, -O to specify name
            None, # Wget's success is usually by return code
            ":snake: Downloading Miniforge installer...",
            "Failed to download Miniforge installer :sob:",
            ":snake: Miniforge installer downloaded."
        )

        run_and_check(
            ["bash", MINICONDA_SCRIPT_NAME, "-bfp", PREFIX],
            "installation finished.", # Miniforge installer output
            ":snake: Installing Miniforge...",
            "Could not install Miniforge :sob:",
            f":snake: Miniforge installed to `{PREFIX}`."
        )
        # Update has_conda after successful installation
        has_conda = "conda version" in os.popen(f"{PREFIX}/bin/conda info 2>/dev/null").read()
    else:
        con.log(f":snake: Miniforge already detected at `{PREFIX}`. Skipping Miniforge installation.")

    if not has_qiime:
        run_and_check(
            ["wget", "-nv", QIIME_YAML_URL, "-O", QIIME_YAML_FILENAME],
            None,
            ":mag: Downloading QIIME 2 environment specification...",
            "Could not download QIIME 2 environment specification :sob:",
            f":mag: QIIME 2 specification `{QIIME_YAML_FILENAME}` downloaded."
        )

        # --- Explicitly remove QIIME2_ENV_PATH if it exists ---
        if os.path.exists(QIIME2_ENV_PATH):
            con.log(f":broom: Removing existing directory at `{QIIME2_ENV_PATH}` to ensure a clean state...")
            try:
                shutil.rmtree(QIIME2_ENV_PATH)
                con.log(f":white_check_mark: Successfully removed `{QIIME2_ENV_PATH}`.")
            except Exception as e:
                con.log(f"[bold red]Error removing `{QIIME2_ENV_PATH}`: {e}[/bold red]")
                sys.exit(1)
        # Mamba will create the prefix directory.

        # --- Use verbose arguments for mamba env create ---
        mamba_env_create_args = ["-vvv"] # Maximum verbosity
        mamba_exe_path = os.path.join(PREFIX, "bin", CONDA_EXECUTABLE_NAME)
        
        con.log(f":speech_balloon: Using verbose arguments for mamba: {mamba_env_create_args}")
        run_and_check(
            [mamba_exe_path, "env", "create", *mamba_env_create_args, "--prefix", QIIME2_ENV_PATH, "--file", QIIME_YAML_FILENAME],
            "Verifying transaction: ...working... done", # A common success indicator in conda/mamba
            f":mag: Installing QIIME 2 (version {version}) into `{QIIME2_ENV_PATH}`. This may take a while...\n :clock1:",
            "Could not install QIIME 2 :sob:",
            f":mag: QIIME 2 environment (version {version}) successfully created at `{QIIME2_ENV_PATH}`."
        )

        # Add QIIME 2's bin directory to the PATH environment variable
        qiime2_bin_path = os.path.join(QIIME2_ENV_PATH, "bin")
        if os.path.isdir(qiime2_bin_path):
            os.environ["PATH"] = f"{qiime2_bin_path}{os.pathsep}{os.environ['PATH']}"
            con.log(f":wrench: Added `{qiime2_bin_path}` to PATH environment variable.")
        else:
            con.log(f"[yellow]:warning: Expected QIIME 2 bin path not found: `{qiime2_bin_path}`. PATH not updated.[/yellow]")

        # Install Empress using pip from the newly created QIIME 2 environment
        pip_exe_path = os.path.join(QIIME2_ENV_PATH, "bin", "pip")
        if os.path.exists(pip_exe_path):
            run_and_check(
                [pip_exe_path, "install", "empress"],
                "Successfully installed empress", # More generic check
                ":evergreen_tree: Installing Empress using pip from QIIME 2 environment...",
                "Could not install Empress :sob:",
                ":evergreen_tree: Empress installation attempted."
            )
        else:
            con.log(f"[yellow]:warning: Pip not found at `{pip_exe_path}`. Skipping Empress installation.[/yellow]")
    else:
        con.log(f":mag: QIIME 2 already detected at `{QIIME2_ENV_PATH}` (or indicated by initial check). Skipping main installation.")

    # Final check: qiime info
    qiime_exe_path_final_check = os.path.join(QIIME2_ENV_PATH, "bin", "qiime") # Check specific path first
    if not os.path.exists(qiime_exe_path_final_check): # If not found, try generic 'qiime' (relying on PATH)
        qiime_exe_path_final_check = "qiime"

    run_and_check(
        [qiime_exe_path_final_check, "info"],
        "QIIME 2 release:", # Check for this string in output
        ":bar_chart: Verifying QIIME 2 installation...",
        "QIIME 2 `info` command failed or did not produce expected output :sob:",
        ":bar_chart: QIIME 2 installation verified successfully :tada:"
    )

    # Update Python's sys.path for import
    qiime2_site_packages_path = os.path.join(QIIME2_ENV_PATH, "lib", f"python{py_major}.{py_minor}", "site-packages")
    if os.path.isdir(qiime2_site_packages_path):
        # Add to path if not already there
        if qiime2_site_packages_path not in sys.path:
            sys.path.append(qiime2_site_packages_path)
            con.log(f":mag: Added `{qiime2_site_packages_path}` to Python import paths (sys.path).")
        else:
            con.log(f":mag: `{qiime2_site_packages_path}` already in Python import paths.")

    else:
        con.log(f"[yellow]:warning: QIIME 2 site-packages directory not found: `{qiime2_site_packages_path}`. Python imports might fail.[/yellow]")

    con.log(":bar_chart: Checking if QIIME 2 can be imported in Python...")
    try:
        import qiime2 # noqa
        con.log("[bold blue]:bar_chart: QIIME 2 can be imported successfully :tada:[/bold blue]")
    except ImportError as e:
        con.log(f"[bold red]QIIME 2 Python import failed :sob:[/bold red]\nImportError: {e}")
        con.log(f"Current sys.path: {sys.path}")
        # sys.exit(1) # Optionally exit on import failure

    cleanup() # Clean up downloaded script and yaml file

    con.log("[bold green]QIIME 2 setup script finished. Please check output for any errors. :thumbs_up:[/bold green]")
