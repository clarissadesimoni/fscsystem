import os

this_dir = os.path.dirname(__file__)
if os.getcwd() != this_dir:
    os.chdir(this_dir)

import backend, db_interface, file_interface, todoist_interface
from datetime import datetime, date, time
from typing import List, Tuple
import math, re, sys
import cla_utils

def retrieve_data() -> todoist_interface.TaskList:
    db_interface.check_connection()
    backend.imported_task_data = file_interface.retrieve_data()
    if backend.is_connected:
        if backend.is_start_of_day:
            db_interface.delete_old_tasks()
            db_interface.set_last_update()
        else:
            backend.imported_task_data.update(db_interface.get_tasks())
    return todoist_interface.retrieve_data()

def discord_timestamp(dt: datetime):
    return f'<t:{int(dt.timestamp())}:t>'

def get_habits() -> List[Tuple[str, int]]:
    try:
        return list(map(lambda h: (f':mdot_purple: {h}', todoist_interface.emotes_offset + len(f':mdot_purple: {h}')), open('habits.txt').read().split('\n')))
    except:
        return []

def create_strings(tlist: todoist_interface.TaskList, vc=False, deadline_vc: datetime = datetime.min, chat=False, deadline_chat: datetime = datetime.min, habits=False, deadline_habits: datetime = datetime.min) -> List[str]:
    comp = tlist.completion_count()
    comp_dur = tlist.completion_count_duration()
    if comp[1] == 0:
        return []
    completion = comp_dur[0] / comp_dur[1]
    hline_num = 16
    em = [':mdot_red:', ':mdot_yellowstart:', ':mdot_greencomp:'][min(2, math.floor(completion * 2))]
    body: List[Tuple[str, int]] = []
    if vc:
        string = f'**TODO LIST** (to finish before {cla_utils.discord_timestamp(deadline_vc)})'
        body.append((string, len(string)))
    elif chat:
        string = f'**TODO LIST** (to finish before {cla_utils.discord_timestamp(deadline_chat)})'
        body.append((string, len(string)))
    elif habits:
        string = "Today's habits:"
        body.append((string, len(string)))
        body.extend(get_habits())
        body.append(('', 0))
        string = f'**TODO LIST** (to finish before {cla_utils.discord_timestamp(deadline_habits)})'
        body.append((string, len(string)))
    else:
        string = (':hline:' * hline_num) + '\n' + f"{em} **{backend.today.strftime('%d/%m/%Y')}** Last update: {re.sub('^(0)', '', datetime.now().strftime('%I:%M %p'))} ({cla_utils.discord_timestamp(datetime.now())}) {em}" + '\n' + (':hline:' * hline_num) + '\n'
        body.append((string, (hline_num * 2 + 2) * todoist_interface.emotes_offset + len(string)))
        body += file_interface.get_events()
        string = '**TASKS:**'
        body.append((string, len(string)))
    for p in tlist.projects_to_use():
        body.extend(p.to_string(vc=vc, chat=chat, habits=habits))
    string = f'\nDone: {comp[0]}/{comp[1]}, {todoist_interface.mins_to_hour_mins(comp_dur[0])}/{todoist_interface.mins_to_hour_mins(comp_dur[1])}: {completion:.2%} {todoist_interface.generate_progress_bar(completion)}'
    body.append((string, len(string) + 10 * todoist_interface.emotes_offset))
    i = 0
    body[i] = (body[i][0], body[i][1] + 10)
    while i < len(body) - 1:
        if body[i][1] + 1 + body[i + 1][1] <= 1999:
            if body[i][0].startswith('\n'):
                body[i] = (':blank:' + body[i][0], 7 + todoist_interface.emotes_offset + body[i][1])
            body[i] = (body[i][0] + '\n' + body[i + 1][0], body[i][1] + 1 + body[i + 1][1])
            body.pop(i + 1)
        else:
            i += 1
    for i in range(len(body)):
        if body[i][0].startswith('\n'):
            body[i] = (todoist_interface.indent_str + body[i][0], len(todoist_interface.indent_str) + todoist_interface.emotes_offset + body[i][1])
    if vc:
        print('vc:')
    if chat:
        print('chat:')
    print(*list(map(lambda x: f'Segment {x[0] + 1}: {x[1][1]}', enumerate(body))), sep='\n')
    return [b[0] for b in body]

def print_strings(strings):
    length: int = len(strings)
    if length == 0:
        print('There are no tasks available!')
        return
    print(f"There {'are' if length > 1 else 'is'} {length} segment{'s' if length > 1 else ''}")
    for i, s in enumerate(strings):
        backend.cb.copy_to_clipboard(s)
        if i < len(strings) - 1:
            input('Press enter to continue...')
    print('Finished!')

def print_data(tlist: todoist_interface.TaskList, publish=True, vc=False, deadline_vc: datetime = datetime.min, chat=False, deadline_chat: datetime = datetime.min, habits=False, deadline_habits: datetime = datetime.min):
    if publish:
        print_strings(create_strings(tlist))
    if vc:
        if publish:
            input('Press enter to continue to vc...')
        print_strings(create_strings(tlist, vc=vc, deadline_vc=deadline_vc))
    if chat:
        if publish or vc:
            input('Press enter to continue to chat...')
        print_strings(create_strings(tlist, chat=chat, deadline_chat=deadline_chat))
    if habits:
        if publish or vc or chat:
            input('Press enter to continue to habits...')
        print_strings(create_strings(tlist, habits=habits, deadline_habits=deadline_habits))

def save_data(tlist: todoist_interface.TaskList):
    backend.imported_task_data = tlist.list_task_ids()
    file_interface.insert_data()
    if backend.is_connected:
        db_interface.delete_tasks(backend.tasks_to_delete)
        db_interface.insert_new_tasks()

def tasklist():
    publish: bool = False
    vc: bool = False
    deadline_vc: datetime = datetime.min
    chat: bool = False
    deadline_chat: datetime = datetime.min
    habits: bool = False
    deadline_habits: datetime = datetime.min
    if backend.is_mobile:
        publish = cla_utils.safe_input_bool('Do you want to publish your tasklist? ')
        vc = cla_utils.safe_input_bool('Do you want to publish your tasklist to a vc? ')
        if vc:
            deadline_vc = datetime.combine(backend.today, cla_utils.safe_input_time('Insert the vc deadline: '))
        chat = cla_utils.safe_input_bool('Do you want to publish your tasklist to a chat? ')
        if chat:
            deadline_chat = datetime.combine(backend.today, cla_utils.safe_input_time('Insert the vc deadline: '))
    else:
        for arg in sys.argv:
            if arg == '-p':
                publish = True
            if re.match(r'-v=[0-2]?[0-9]:[0-5][0-9]', arg):
                vc = True
                deadline_vc = datetime.combine(backend.today, cla_utils.get_time(arg.split('=')[1]))
            if re.match(r'-c=[0-2]?[0-9]:[0-5][0-9]', arg):
                chat = True
                deadline_chat = datetime.combine(backend.today, cla_utils.get_time(arg.split('=')[1]))
            if re.match(r'-h=[0-2]?[0-9]:[0-5][0-9]', arg):
                habits = True
                deadline_habits = datetime.combine(backend.today, cla_utils.get_time(arg.split('=')[1]))
    tlist: todoist_interface.TaskList = retrieve_data()
    print_data(tlist, publish, vc, deadline_vc, chat, deadline_chat, habits, deadline_habits)
    save_data(tlist)

if __name__ == "__main__":
    tasklist()
