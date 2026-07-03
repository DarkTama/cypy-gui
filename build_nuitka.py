# build_nuitka.py
# ✦ Native C++ Standalone Compiler Script using Nuitka for CYPY ✦

import os
import sys
import shutil
import platform
import zipfile
import subprocess

def install_dependencies():
    # Ensure Nuitka is installed
    try:
        import nuitka
        print(f"[Build Nuitka] Nuitka is installed.")
    except ImportError:
        print("[Build Nuitka] Nuitka not found. Installing via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka"])
        except Exception as e:
            print(f"[Build Nuitka] Failed to install Nuitka: {e}")
            sys.exit(1)

def run_build():
    install_dependencies()

    project_root = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(project_root, "assets")
    entry_point = os.path.join(project_root, "cypy", "app.py")

    # Nuitka compilation flags
    # We use --standalone to create a self-contained folder that runs natively at C++ speed without temp extraction
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        f"--include-data-dir={assets_dir}=assets",
        "--follow-imports",
        "--output-dir=dist_nuitka",
        # Exclude large unused packages from compile search if possible
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=tensorboard",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=IPython",
        entry_point
    ]

    # Check if we should compile as single file
    if "--onefile" in sys.argv:
        cmd.append("--onefile")
        print("[Build Nuitka] Compiling in single-file mode (--onefile)...")
    else:
        print("[Build Nuitka] Compiling in standalone-directory mode (recommended for instant loading)...")

    # Add Windows specific settings
    if platform.system() == "Windows":
        cmd.append("--assume-yes-for-downloads") # Auto-download GCC/MinGW if missing

    print(f"[Build Nuitka] Running command:\n{' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("[Build Nuitka] Compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[Build Nuitka] Compilation failed with exit code: {e.returncode}")
        sys.exit(1)

    package_release(project_root)

def package_release(project_root):
    dist_dir = os.path.join(project_root, "dist_nuitka")
    releases_dir = os.path.join(project_root, "releases")
    os.makedirs(releases_dir, exist_ok=True)

    os_system = platform.system().lower()
    os_name = "macos" if os_system == "darwin" else os_system
    
    raw_arch = platform.machine().lower()
    arch = "x64" if raw_arch in ["amd64", "x86_64"] else ("x86" if raw_arch in ["i386", "i686"] else raw_arch)
    
    zip_name = f"cypy-nuitka-{os_name}-{arch}.zip"
    zip_path = os.path.join(releases_dir, zip_name)

    # Nuitka creates output in dist_nuitka/app.dist (standalone) or dist_nuitka/app.exe (onefile)
    # Let's find the output
    standalone_output = os.path.join(dist_dir, "app.dist")
    onefile_exe = os.path.join(dist_dir, "app.exe" if platform.system() == "Windows" else "app.bin")

    app_folder_path = os.path.join(dist_dir, "cypy_nuitka_pkg_temp")
    if os.path.exists(app_folder_path):
        shutil.rmtree(app_folder_path)
    os.makedirs(app_folder_path, exist_ok=True)

    if os.path.exists(standalone_output) and not ("--onefile" in sys.argv):
        print("[Build Nuitka] Packaging standalone directory...")
        for item in os.listdir(standalone_output):
            s = os.path.join(standalone_output, item)
            d = os.path.join(app_folder_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
    elif os.path.exists(onefile_exe):
        print("[Build Nuitka] Packaging onefile executable...")
        dest_exe_name = "cypy.exe" if platform.system() == "Windows" else "cypy"
        shutil.copy2(onefile_exe, os.path.join(app_folder_path, dest_exe_name))
        # Copy assets folder manually in onefile mode
        dest_assets = os.path.join(app_folder_path, "assets")
        shutil.copytree(os.path.join(project_root, "assets"), dest_assets)
    else:
        print("[Build Nuitka] Error: Could not locate compiled output files.")
        sys.exit(1)

    # Copy metadata docs
    for doc in ["README.md", "LICENSE", ".env.example"]:
        doc_path = os.path.join(project_root, doc)
        if os.path.exists(doc_path):
            shutil.copy(doc_path, os.path.join(app_folder_path, doc))

    # Zip output
    try:
        print(f"[Build Nuitka] Packaging to {zip_path}...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(app_folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, app_folder_path)
                    zipf.write(file_path, os.path.join("cypy", rel_path))
        print(f"[Build Nuitka] Packaged successfully to: {zip_path}")
        print(f"[Build Nuitka] Package size: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"[Build Nuitka] Packaging failed: {e}")
    finally:
        if os.path.exists(app_folder_path):
            shutil.rmtree(app_folder_path)

if __name__ == "__main__":
    run_build()
