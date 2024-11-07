from todoist_api_python.models import Task
from typing import List, Dict, Union
from datetime import date
import json, platform, os

is_mobile = 'macOS' not in platform.platform()
is_connected = True
is_start_of_day = True
tlist = None
today = date.today()
utils = json.load(open('creds_and_info.json'))
file_dir: str = os.getcwd() if is_mobile else utils['desktop_file_dir']
file_name = f"{file_dir}/{today.strftime('%Y%m%d')}.txt"
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
