import os, pathlib, platform

is_mac = platform.platform().startswith('macOS')
is_windows = platform.platform().startswith('Windows')
is_mobile = not (is_mac or is_windows)

if is_mac:
    desktop_dir = os.path.join(pathlib.Path.home(), 'Desktop')
    fsc_dir = os.path.join(pathlib.Path.home(), 'Library', 'Mobile Documents', 'iCloud~com~omz-software~Pythonista3', 'Documents', 'fscsystem')
    syncthing_dir = os.path.join(desktop_dir, 'syncthing_dir')
elif is_windows:
    desktop_dir = os.path.join(pathlib.Path.home(), 'OneDrive', 'Desktop')
    fsc_dir = os.path.join(desktop_dir, 'fscsystem')
    syncthing_dir = os.path.join(desktop_dir, 'syncthing', 'syncthing_dir')
elif is_mobile:
    base_dir = pathlib.Path(os.getcwd()).parent
    fsc_dir = os.path.join(base_dir, 'fscsystem')
    syncthing_dir = os.path.join(base_dir, 'syncthing_dir')

files_dir = os.path.join(syncthing_dir, 'fscsystem_files')