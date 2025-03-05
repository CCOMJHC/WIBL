# Override package files as per
# https://docs.platformio.org/en/latest/scripting/examples/override_package_files.html
import sys
from pathlib import Path

Import("env")

PATCHES_PATH = 'platform-patches'
FRAMEWORK_DIR = env.PioPlatform().get_package_dir("framework-arduinoespressif32")

print("Patching PlatformIO files...")

patches = {
    Path(PATCHES_PATH, "1-framework-arduinoespressif32-webserver.patch"):
        Path(FRAMEWORK_DIR, "libraries", "WebServer", "src", "WebServer.cpp")
}

# Patching with patch.py is idempotent, so always apply patches to make sure all files are patched that ought to be. 
files_were_patched = False
for patch_file, original_file in patches.items():
    print(f"\tApplying patch '{patch_file}' to file '{original_file}'")
    assert original_file.is_file() and patch_file.is_file()
    res = env.Execute(f"python patch.py -d {str(original_file.parent)} {str(patch_file)}")
    if res == 0:
        print(f"\t\tSuccessfully applied patch '{patch_file}'")
        files_were_patched = True
    else:
        sys.exit(f"ERROR: Failed to patch file {original_file}, exiting...")

if not files_were_patched:
    print("\tNo patches to be applied.")
