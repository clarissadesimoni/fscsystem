from typing import Dict, Union, List, Tuple
import re, os
import backend, cla_utils
from datetime import datetime
from todoist_interface import emotes_offset

def process_start_of_day():
    check: bool = any(re.match(r'^20[0-9]{6}.txt$', f) and f != backend.file_name for f in next(os.walk(backend.file_dir))[2])
    if check:
        for el in filter(lambda f: re.match(r'^20[0-9]{6}.txt$', f) and f != backend.file_name, next(os.walk(backend.file_dir))[2]):
            os.remove(el)
    open(backend.file_name, 'a')

def retrieve_data() -> Dict[str, Union[str, None]]:
    res: Dict[str,Union[str, None]] = {}
    process_start_of_day()
    ids = open(backend.file_name).read()
    if len(ids) > 0:
        res.update({el[0]: (el[1] if len(el[1]) else None) for el in map(lambda x: x.split('-'), ids.split('\n'))})
    return res

def insert_data():
    process_start_of_day()
    open(backend.file_name, 'w').write('\n'.join(['-'.join([x[0], x[1] if x[1] else '']) for x in backend.imported_task_data.items()]))

def get_events() -> List[Tuple[str, int]]:
    try:
        ev = open('events.txt').read().split('\n')
    except:
        ev = []
    ev = list(filter(lambda l: len(l), ev))
    res: List[Tuple[str, int]] = []
    for i in range(len(ev)):
        try:
            start = ev[i].split(' @ ')[1].split(' - ')[0]
            start = cla_utils.get_time(start)
            if ev[i].split(' - ')[-1] == '...':
                started = datetime.combine(backend.today, start) <= datetime.now()
                completed = False
            else:
                end = ev[i].split(' - ')[-1]
                end = cla_utils.get_time(end)
                completed = datetime.combine(backend.today, end) <= datetime.now()
                started = datetime.combine(backend.today, start) <= datetime.now() <= datetime.combine(backend.today, end)
            tmp = ':blank::mdot_darkblue' + ('comp' if completed else 'start' if started else '') + ': ' + str(ev[i])
            res.append((tmp, len(tmp) + emotes_offset * 2))
        except:
            tmp = ':blank::mdot_blossom: ' + str(ev[i]) + ' - All day'
            res.append((tmp, len(tmp) + emotes_offset * 2))
    res.insert(0, ('**EVENTS:**', len('**EVENTS:**')))
    res.append(('', 0))
    return res