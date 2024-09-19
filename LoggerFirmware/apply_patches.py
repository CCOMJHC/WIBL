# Override package files as per
# https://docs.platformio.org/en/latest/scripting/examples/override_package_files.html
from os.path import join, isfile

Import("env")

PATHES_PATH = 'platform-patches'

FRAMEWORK_DIR = env.PioPlatform().get_package_dir("framework-arduinoespressif32")
patchflag_path = join(FRAMEWORK_DIR, ".patching-done")

print("Patching PlatformIO files...")

patches = {
    join("platform-patches", "1-framework-arduinoespressif32-webserver.patch"):
        join(FRAMEWORK_DIR, "libraries", "WebServer", "src", "WebServer.cpp")
}

# patch files only if we didn't do it before
if not isfile(join(FRAMEWORK_DIR, ".patching-done")):
    files_were_patched = False
    for patch_file, original_file in patches.items():
        files_were_patched = True
        print(f"\tApplying patch '{patch_file}' to file '{original_file}'")
        assert isfile(original_file) and isfile(patch_file)
        env.Execute(f"patch {original_file} {patch_file}")

    if files_were_patched:
        with open(patchflag_path, "w") as fp:
            fp.write("")
    else:
        print("\tNo patches to be applied.")
else:
    print("\tPatches already applied")
