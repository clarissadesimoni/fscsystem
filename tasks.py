from datetime import datetime, date, time, timedelta
import  re, sys, math, platform, pyperclip
import MyTodoist
tlist = None
today = date.today()
is_mobile = 'iPhone' in platform.platform()

def debugger_is_active() -> bool:
    gettrace = getattr(sys, 'gettrace', lambda : None)
    return gettrace() is not None

def backend():
    global tlist
    data = MyTodoist.get_data()
    tlist = MyTodoist.get_todoist(data)
    data = list(set(tlist.list_task_ids()) - set(data))
    if len(data) > 0:
        MyTodoist.update_data(data, MyTodoist.to_del)
    MyTodoist.update_file(tlist)

# OLD
# def backend():
#     global tlist
#     tlist = MyTodoist.getTodoist(MyTodoist.getFile())
#     MyTodoist.updateFile(tlist.listTaskIDs())


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
            ev[i] = [tmp, len(tmp) + MyTodoist.emotes_offset * 2]
        except:
            tmp = ':blank::mdot_blossom: ' + str(ev[i]) + ' - All day'
            ev[i] = [tmp, len(tmp) + MyTodoist.emotes_offset * 2]
    ev.insert(0, ['**EVENTS:**', len('**EVENTS:**')])
    ev.append(['', 0])
    return ev


def create_string(tlist: MyTodoist.TaskList):
    comp_count_all = tlist.completion_count()
    completion_all = tlist.completion()
    comp_count_normal = tlist.completion_count(count_habits=False)
    completion_normal = tlist.completion(count_habits=False)
    hline_num = 17
    em = [':mdot_red:', ':mdot_yellowstart:', ':mdot_greencomp:'][math.floor(completion_normal * 2)]
    body = []
    string = (':hline:' * hline_num) + '\n' + f"{em} **{today.strftime('%d/%m/%Y')}** Last update: {re.sub('^(0)', '', datetime.now().strftime('%I:%M %p'))} (<t:{int(datetime.now().timestamp())}:t>) {em}" + '\n' + (':hline:' * hline_num) + '\n'
    body.append([string, (hline_num * 2 + 2) * MyTodoist.emotes_offset + len(string)])
    body += get_events()
    string = '**TASKS:**'
    body.append([string, len(string)])
    for p in tlist.projects_to_use():
        body.extend(p.to_string())
    string = f'\nDone: {comp_count_all[0]}/{comp_count_all[1]}: {completion_all:.2%} {MyTodoist.generate_progress_bar(completion_normal)}' #\nNormal tasks: {compCountNormal[0]}/{compCountNormal[1]}: {completionNormal:.2%}'
    body.append([string, len(string) + 10 * MyTodoist.emotes_offset])
    i = 0
    while i < len(body) - 1:
        if body[i][1] + body[i + 1][1] <= 1999:
            body[i] = [body[i][0] + '\n' + body[i + 1][0], body[i][1] + 1 + body[i + 1][1]]
            body.pop(i + 1)
        else:
            i += 1
    return [b[0] for b in body]

def tasklist(publish=True, mobile=False):
    backend()
    if publish:
        MyTodoist.print_strings(create_string(tlist))
    if mobile:
        res = '\n\n\n'.join(create_string(tlist))
        if is_mobile:
            print(res)
            open('/Users/clarissadesimoni/Desktop/tasklist.txt', 'w').write(res)
        else:
            pyperclip.copy(res)
            open('/Users/clarissadesimoni/Desktop/tasklist.txt', 'w').write(res)

if __name__ == '__main__':
    tasklist(publish='publish' in sys.argv or is_mobile or debugger_is_active(), mobile='mobile' in sys.argv)