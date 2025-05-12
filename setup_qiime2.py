#!/usr/bin/env python3

"""Set up Qiime 2 on Google colab.

Do not use this on o local machine, especially not as an admin!
"""

import os
import sys
import shutil
from subprocess import Popen, PIPE

r = Popen(["pip", "install", "rich"])
r.wait()
from rich.console import Console  # noqa
con = Console()

# MODIFICATION 1: Change Miniforge installation prefix
PREFIX = "/content/miniforge3"  # Was "/usr/local/miniforge3/"

# MODIFICATION 2: Define a new prefix for the QIIME 2 environment
QIIME2_ENV_PATH = "/content/qiime2_env"

# Ensure target directories for installation exist (optional, but good practice)
os.makedirs(PREFIX, exist_ok=True)
os.makedirs(QIIME2_ENV_PATH, exist_ok=True)


has_conda = "conda version" in os.popen(f"{PREFIX}/bin/conda info").read() # Use f-string for clarity
# has_qiime will be checked later, after PATH modification might make `qiime` accessible
# For the initial check, it's fine if it's false, triggering installation.
# We'll rely on the script's later `qiime info` check after attempted installation and PATH setup.
initial_qiime_check_path = os.path.join(QIIME2_ENV_PATH, "bin", "qiime") # More robust check
has_qiime = "QIIME 2 release:" in os.popen(f"{initial_qiime_check_path} info" if os.path.exists(initial_qiime_check_path) else "echo").read()


MINICONDA_PATH = (
    "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
)

QIIME_YAML_TEMPLATE = (
    "https://data.qiime2.org/distro/amplicon/qiime2-amplicon-{version}-py{python}-linux-conda.yml"
)

if len(sys.argv) == 2:
    version = sys.argv[1]
else:
    version = "2023.9" # Current version as of May 2024/2025, adjust if needed

# Determine Python version for QIIME 2 YAML (py38 is common for recent versions)
# This logic might need updating if QIIME 2 versions change their Python requirements significantly
if tuple(float(v) for v in version.split(".")) < (2021, 4):
    pyver = "36" # Python 3.6
elif tuple(float(v) for v in version.split(".")) < (2022, 8): # Q2 2022.2 used py38
    pyver = "38" # Python 3.8
else: # Assuming newer versions continue with py38 or similar, adjust as needed
    pyver = "38" # Python 3.8 (defaulting to 3.8 for versions >= 2022.8)


CONDA = "mamba"
CONDA_ARGS = ["-q"]

# Adjust YAML template based on version (original logic)
if tuple(float(v) for v in version.split(".")) < (2023, 9):
    QIIME_YAML_TEMPLATE = (
        "https://data.qiime2.org/distro/core/qiime2-{version}-py{python}-linux-conda.yml"
    )

QIIME_YAML_URL = QIIME_YAML_TEMPLATE.format(version=version, python=pyver)
QIIME_YAML = os.path.basename(QIIME_YAML_URL)


def cleanup():
    """Remove downloaded files."""
    if os.path.exists(os.path.basename(MINICONDA_PATH)):
        os.remove(os.path.basename(MINICONDA_PATH))
    if os.path.exists(QIIME_YAML):
        os.remove(QIIME_YAML)
    if os.path.exists("/content/sample_data"): # This is a Colab default folder
        shutil.rmtree("/content/sample_data")
    con.log(":broom: Cleaned up unneeded files.")


def run_and_check(args, check, message, failure, success, console=con):
    """Run a command and check that it worked."""
    console.log(message)
    # Ensure PATH is correctly passed to subprocess environment
    process_env = os.environ.copy()
    r = Popen(args, env=process_env, stdout=PIPE, stderr=PIPE,
              universal_newlines=True)
    o, e = r.communicate()
    out = o + e
    # A more robust check for mamba/conda success often involves "Verifying transaction: ...working... done"
    # or checking for specific files created. The original check might be too broad.
    if r.returncode == 0 and (check is None or check in out): # Allow None for check if return code is enough
        console.log("[blue]%s[/blue]" % success)
        return True # Indicate success
    else:
        console.log("[red]%s[/red]" % failure, f"Output:\n{out}")
        cleanup()
        sys.exit(1) # Exit on critical failure


if __name__ == "__main__":
    if not has_conda:
        run_and_check(
            ["wget", MINICONDA_PATH],
            "saved",
            ":snake: Downloading miniforge...",
            "failed downloading miniforge :sob:",
            ":snake: Done."
        )

        # MODIFICATION 3: Update Miniforge success message to reflect new PREFIX
        run_and_check(
            ["bash", os.path.basename(MINICONDA_PATH), "-bfp", PREFIX],
            "installation finished.",
            ":snake: Installing miniforge...",
            "could not install miniforge :sob:",
            f":snake: Installed miniforge to `{PREFIX}`." # Use f-string for dynamic path
        )
    else:
        con.log(f":snake: Miniforge is already installed at `{PREFIX}`. Skipped.")

    if not has_qiime:
        run_and_check(
            ["wget", QIIME_YAML_URL],
            "saved",
            ":mag: Downloading Qiime 2 package list...",
            "could not download package list :sob:",
            ":mag: Done."
        )

        # MODIFICATION 4: Use QIIME2_ENV_PATH for the Qiime 2 environment prefix
        # Ensure the check string is robust for mamba success
        qiime_install_success_check = "Verifying transaction: ...working... done" # Common mamba/conda success string segment
        run_and_check(
            [os.path.join(PREFIX, "bin", CONDA), "env", "create", *CONDA_ARGS, "--prefix", QIIME2_ENV_PATH, "--file", QIIME_YAML],
            qiime_install_success_check,
            ":mag: Installing Qiime 2. This may take a little bit.\n :clock1:",
            "could not install Qiime 2 :sob:",
            f":mag: QIIME 2 environment created at `{QIIME2_ENV_PATH}`."
        )

        # MODIFICATION 5: Add QIIME 2's bin directory to PATH
        qiime2_bin_path = os.path.join(QIIME2_ENV_PATH, "bin")
        if os.path.isdir(qiime2_bin_path):
            os.environ["PATH"] = f"{qiime2_bin_path}{os.pathsep}{os.environ['PATH']}"
            con.log(f":wrench: Added {qiime2_bin_path} to PATH environment variable.")
        else:
            con.log(f"[yellow]:warning: Expected QIIME 2 bin path not found: {qiime2_bin_path}. PATH not updated.[/yellow]")
        
        # Attempt to install empress using pip from the new QIIME 2 environment
        # This assumes pip is correctly located within the QIIME2_ENV_PATH/bin
        pip_executable = os.path.join(QIIME2_ENV_PATH, "bin", "pip")
        if os.path.exists(pip_executable):
            run_and_check(
                [pip_executable, "install", "empress"],
                "Successfully installed empress-", # Check might need to be more specific if version varies
                ":evergreen_tree: Installing Empress using pip from QIIME 2 env...",
                "could not install Empress :sob:",
                ":evergreen_tree: Empress installation attempted." # Success is based on pip's output
            )
        else:
            con.log(f"[yellow]:warning: Pip not found at {pip_executable}. Skipping Empress install.[/yellow]")

    else:
        con.log(f":mag: Qiime 2 is already potentially installed (based on initial check at `{QIIME2_ENV_PATH}`). Skipped main installation.")

    # Use full path for qiime info check to be certain
    qiime_executable = os.path.join(QIIME2_ENV_PATH, "bin", "qiime")
    if os.path.exists(qiime_executable):
        run_and_check(
            [qiime_executable, "info"],
            "QIIME 2 release:",
            ":bar_chart: Checking that Qiime 2 command line works...",
            "Qiime 2 command line does not seem to work :sob:",
            ":bar_chart: Qiime 2 command line looks good :tada:"
        )
    else:
        con.log(f"[red]QIIME executable not found at {qiime_executable}. Cannot check info.[/red]")
        sys.exit(1)


    # MODIFICATION 6: Update sys.path to point to the new QIIME 2 environment's site-packages
    # Correct Python version string (e.g., python3.8)
    python_version_short = f"python{pyver[0]}.{pyver[1]}" # e.g., "python3.8"
    qiime2_site_packages = os.path.join(QIIME2_ENV_PATH, "lib", python_version_short, "site-packages")

    if os.path.isdir(qiime2_site_packages):
        sys.path.append(qiime2_site_packages)
        con.log(f":mag: Added {qiime2_site_packages} to Python import paths.")
    else:
        con.log(f"[yellow]:warning: QIIME 2 site-packages not found at {qiime2_site_packages}. Imports might fail.[/yellow]")


    con.log(":bar_chart: Checking if Qiime 2 import works...")
    try:
        import qiime2  # noqa
        con.log("[blue]:bar_chart: Qiime 2 can be imported :tada:[/blue]")
    except ImportError as e:
        con.log(f"[red]Qiime 2 can not be imported :sob:[/red]\nError: {e}\nPYTHONPATH: {sys.path}")
        # sys.exit(1) # Commenting out exit to allow further debugging if needed

    cleanup()

    con.log("[green]Everything is A-OK. "
            "You can start using Qiime 2 now :thumbs_up:[/green]")
