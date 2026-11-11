"""Print the root folder (the one that holds Engine/) of the engine a .uproject uses.

Usage: python -I find_engine_root.py [<path to .uproject or a folder inside the project>]
Without an argument it searches the current folder and its parents for a .uproject.

EngineAssociation is resolved the way the launcher does:
  - a path (source build next to the project, or absolute)      -> that folder
  - a version such as "5.9" (launcher install)                  -> LauncherInstalled.dat, then
                                                                    HKLM\\SOFTWARE\\EpicGames\\Unreal Engine\\<version>
  - a GUID such as "{...}" (registered source build)            -> HKCU\\Software\\Epic Games\\Unreal Engine\\Builds
Exit 0 and the root on stdout, or exit 1 and the reason on stderr.
"""
import json
import os
import sys


def find_uproject(start):
    path = os.path.abspath(start)
    if os.path.isfile(path) and path.lower().endswith(".uproject"):
        return path
    folder = path if os.path.isdir(path) else os.path.dirname(path)
    while True:
        for name in os.listdir(folder):
            if name.lower().endswith(".uproject"):
                return os.path.join(folder, name)
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


def is_engine_root(folder):
    return bool(folder) and os.path.isdir(os.path.join(folder, "Engine", "Binaries"))


def from_launcher(version):
    dat = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "Epic", "UnrealEngineLauncher",
                       "LauncherInstalled.dat")
    try:
        with open(dat, encoding="utf-8-sig") as handle:
            for item in json.load(handle).get("InstallationList", []):
                if item.get("AppName") == f"UE_{version}":
                    return item.get("InstallLocation")
    except (OSError, ValueError):
        pass
    return None


def from_registry(association):
    try:
        import winreg
    except ImportError:
        return None
    lookups = [
        (winreg.HKEY_CURRENT_USER, r"Software\Epic Games\Unreal Engine\Builds", association),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\EpicGames\Unreal Engine\{association}", "InstalledDirectory"),
    ]
    for hive, key, value in lookups:
        try:
            with winreg.OpenKey(hive, key) as handle:
                return winreg.QueryValueEx(handle, value)[0]
        except OSError:
            continue
    return None


def main(argv):
    uproject = find_uproject(argv[1] if len(argv) > 1 else os.getcwd())
    if not uproject:
        print("no .uproject found", file=sys.stderr)
        return 1
    with open(uproject, encoding="utf-8-sig") as handle:
        association = json.load(handle).get("EngineAssociation", "")
    candidates = []
    if association and not association.startswith("{"):
        candidates.append(os.path.normpath(os.path.join(os.path.dirname(uproject), association)))
        candidates.append(from_launcher(association))
    candidates.append(from_registry(association))
    for root in candidates:
        if is_engine_root(root):
            print(os.path.normpath(root))
            return 0
    print(f"engine '{association}' of {uproject} is not installed or not registered", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
