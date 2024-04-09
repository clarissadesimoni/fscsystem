from datetime import datetime, date, time, timedelta
from typing import List, Union
import  re, sys, math, platform, pyperclip
import todoist_interface
tlist = None
today = date.today()
is_mobile = 'macOS' not in platform.platform()

def backend():
    global tlist
    data = todoist_interface.get_data()
    tlist = todoist_interface.get_todoist(data)
    data = list(set(tlist.list_task_ids()) - set(data))
    if len(data) > 0:
        todoist_interface.update_data(data, todoist_interface.to_del)
    todoist_interface.update_file(tlist)

def discord_timestamp(dt: datetime):
    return f'<t:{int(dt.timestamp())}:t>'

def get_events():
    try:
        ev = open('events.txt').read().split('\n')
    except:
        ev = []
    ev = list(filter(lambda l: len(l), ev))
    # length = 0
    for i in range(len(ev)):
        try:
            start = ev[i].split(' @ ')[1].split(' - ')[0].split(':')
            start = time(int(start[0]), int(start[1]))
            if ev[i].split(' - ')[-1] == '...':
                started = datetime.combine(today, start) <= datetime.now()
                completed = False
            else:
                end = ev[i].split(' - ')[-1].split(':')
                end = time(int(end[0]), int(end[1]))
                completed = datetime.combine(today, end) <= datetime.now()
                started = datetime.combine(today, start) <= datetime.now() <= datetime.combine(today, end)
            tmp = ':blank::mdot_darkblue' + ('comp' if completed else 'start' if started else '') + ': ' + str(ev[i])
            ev[i] = [tmp, len(tmp) + todoist_interface.emotes_offset * 2]
        except:
            tmp = ':blank::mdot_blossom: ' + str(ev[i]) + ' - All day'
            ev[i] = [tmp, len(tmp) + todoist_interface.emotes_offset * 2]
    ev.insert(0, ['**EVENTS:**', len('**EVENTS:**')])
    ev.append(['', 0])
    return ev

def create_string(tlist: todoist_interface.TaskList, vc: bool = False, deadline_vc: Union[datetime, None] = None):
    comp_count_all = tlist.completion_count()
    completion_all = tlist.completion()
    comp_count_normal = tlist.completion_count(count_habits=False)
    completion_normal = tlist.completion(count_habits=False)
    hline_num = 17
    em = [':mdot_red:', ':mdot_yellowstart:', ':mdot_greencomp:'][math.floor(completion_normal * 2)]
    body: List[List[str, int]] = []
    if vc:
        string = f'**TODO LIST** (to finish before {discord_timestamp(deadline_vc)})'
        body.append([string, len(string)])
    else:
        string = (':hline:' * hline_num) + '\n' + f"{em} **{today.strftime('%d/%m/%Y')}** Last update: {re.sub('^(0)', '', datetime.now().strftime('%I:%M %p'))} ({discord_timestamp(datetime.now())}) {em}" + '\n' + (':hline:' * hline_num) + '\n'
        body.append([string, (hline_num * 2 + 2) * todoist_interface.emotes_offset + len(string)])
        body += get_events()
        string = '**TASKS:**'
        body.append([string, len(string)])
    for p in tlist.projects_to_use():
        body.extend(p.to_string(vc=vc))
    string = f'\nDone: {comp_count_all[0]}/{comp_count_all[1]}: {completion_all:.2%} {todoist_interface.generate_progress_bar(completion_normal)}' #\nNormal tasks: {compCountNormal[0]}/{compCountNormal[1]}: {completionNormal:.2%}'
    body.append([string, len(string) + 10 * todoist_interface.emotes_offset])
    i = 0
    while i < len(body) - 1:
        if body[i][1] + body[i + 1][1] <= 1999:
            if body[i][0].startswith('\n'):
                body[i] = [':blank:' + body[i][0], 7 + todoist_interface.emotes_offset + body[i][1]]
            body[i] = [body[i][0] + '\n' + body[i + 1][0], body[i][1] + 1 + body[i + 1][1]]
            body.pop(i + 1)
        else:
            i += 1
    for i in range(len(body)):
        if body[i][0].startswith('\n'):
            body[i] = [todoist_interface.indent_str + body[i][0], len(todoist_interface.indent_str) + todoist_interface.emotes_offset + body[i][1]]
    return [b[0] for b in body]

def print_strings(strings):
    length: int = len(strings)
    print(f"There {'are' if length > 1 else 'is'} {length} segment{'s' if length > 1 else ''}")
    for i, s in enumerate(strings):
        pyperclip.copy(s)
        if i < len(strings) - 1:
            input('Press enter to continue...')
    print('Finished!')

def tasklist(publish=True, mobile=False, vc=False, deadline_vc: Union[datetime, None] = None):
    backend()
    if mobile:
        if publish:
            print('\n\n'.join(create_string(tlist)))
        print('\n\n')
        if vc:
            print('\n\n'.join(create_string(tlist, vc=vc, deadline_vc=deadline_vc)))
    else:
        if publish:
            print_strings(create_string(tlist))
        if vc:
            if publish:
                input('Press enter to continue to vc...')
            print_strings(create_string(tlist, vc=vc, deadline_vc=deadline_vc))


if __name__ == '__main__':
    tasklist(publish='publish' in sys.argv or is_mobile, mobile='mobile' in sys.argv, vc='vc' in sys.argv, deadline_vc=datetime.strptime(sys.argv[-1], '%Y-%m-%dT%H:%M:%S') if 'vc' in sys.argv else None)