from typing import Dict, Union, List, Tuple
import re, os
import backend, cla_utils
from datetime import datetime
from todoist_interface import emotes_offset
import google_interface

def process_start_of_day():
    check: bool = any(re.match(r'^20[0-9]{6}.txt$', f) and f != backend.file_name.split('/')[-1] for f in next(os.walk(os.getcwd() if backend.is_mobile else backend.file_dir))[2])
    if check:
        for el in filter(lambda f: re.match(r'^20[0-9]{6}.txt$', f) and f != backend.file_name, next(os.walk(backend.file_dir))[2]):
            os.remove(el)
    try:
        open(backend.file_name, 'a')
    except:
        open(backend.file_name, 'x')

def retrieve_data() -> Dict[str, Union[str, None]]:
    res: Dict[str,Union[str, None]] = {}
    process_start_of_day()
    ids = open(backend.file_name).read()
    if len(ids) > 0:
        res.update({el[0]: (el[1] if len(el[1]) > 1 else False) for el in map(lambda x: x.split('-'), ids.split('\n'))})
    return res

def insert_data():
    process_start_of_day()
    open(backend.file_name, 'w').write('\n'.join(['-'.join([x[0], x[1] if x[1] else 'x']) for x in backend.imported_task_data.items()]))

def get_events() -> List[Tuple[str, int]]:
    if backend.is_windows:
        google_interface.main()
    try:
        ev = open(os.path.join(backend.file_dir, 'events.txt')).read().split('\n')
    except:
        ev = []
    ev = list(set(filter(lambda l: len(l), ev)))
    res: List[Tuple[str, int]] = []
    for i in range(len(ev)):
        ev[i], time_strs = ev[i].split(' @ ')
        time_strs = time_strs.split(' - ')
        try:
            start = datetime.combine(backend.today, cla_utils.get_time(time_strs[0]))
            time_strs[0] = f'{time_strs[0]} ({cla_utils.discord_timestamp(start)})'
            if time_strs[1] == '...':
                started = start <= datetime.now()
                completed = False
            else:
                end = datetime.combine(backend.today, cla_utils.get_time(time_strs[1]))
                time_strs[1] = f'{time_strs[1]} ({cla_utils.discord_timestamp(end)})'
                completed = end <= datetime.now()
                started = start <= datetime.now() <= end
            tmp = ':blank::mdot_darkblue' + ('comp' if completed else 'start' if started else '') + ': ' + ev[i] + ' @ ' + ' - '.join(time_strs)
            res.append((tmp, len(tmp) + emotes_offset * 2))
        except:
            tmp = ':blank::mdot_blossom: ' + str(ev[i]) + ' - All day'
            res.append((tmp, len(tmp) + emotes_offset * 2))
    res.sort(key=lambda x: x[0].split(' @ ')[1])
    res.insert(0, ('**EVENTS:**', len('**EVENTS:**')))
    res.append(('', 0))
    return res

if __name__ == '__main__':
    get_events()
