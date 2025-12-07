from todoist_api_python.models import Task
from typing import List, Dict, Union
from datetime import date
import json, platform, os, pathlib
from device_paths import files_dir, fsc_dir

is_mac = platform.platform().startswith('macOS')
is_windows = platform.platform().startswith('Windows')
is_desktop = is_mac or is_windows
is_mobile = not is_desktop
is_connected = True
is_start_of_day = True
tlist = None
today = date.today()
utils = json.load(open(os.path.join(fsc_dir, 'creds_and_info.json')))
file_name = os.path.join(files_dir, f"{today.strftime('%Y%m%d')}.txt")
imported_task_data: Dict[str, Union[str, None]] = {}
uncompleted_tasks: List[Task] = []
uncompleted_tasks_dict: Dict[Union[str, None], List[Task]] = {}
completed_tasks: List[Dict[str, Dict[str, Union[int, str, None]]]] = []
completed_tasks_dict: Dict[Union[str, None], List[Dict[str, Dict[str, Union[int, str, None]]]]] = {}
tasks_to_delete: List[str] = []

if is_mobile:
    import mobile_clipboard as cb
else:
    import desktop_clipboard as cb
