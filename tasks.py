from datetime import datetime, date, time, timedelta
import  sys, math, platform, pyperclip
import MyTodoist
tlist = None
today = date.today()
is_mobile = 'Darwin' in platform.platform()

def debugger_is_active() -> bool:
    gettrace = getattr(sys, 'gettrace', lambda : None)
    return gettrace() is not None

def backend():
    global tlist
    data = MyTodoist.getData()
    tlist = MyTodoist.getTodoist(data)
    data = list(set(tlist.listTaskIDs()) - set(data))
    if len(data) > 0:
        MyTodoist.updateData(data)

# OLD
# def backend():
#     global tlist
#     tlist = MyTodoist.getTodoist(MyTodoist.getFile())
#     MyTodoist.updateFile(tlist.listTaskIDs())


def getEvents():
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
                completed = datetime.combine(today, start) <= datetime.now()
            else:
                end = ev[i].split(' - ')[-1].split(':')
                end = time(int(end[0]), int(end[1]))
                completed = datetime.combine(today, end) <= datetime.now()
            tmp = ':blank::mdot_darkblue' + ('x' if completed else '') + ': ' + str(ev[i])
            ev[i] = [tmp, len(tmp) + MyTodoist.emotes_offset + MyTodoist.tab_to_spaces]
        except:
            tmp = ':blank::mdot_blossom: ' + str(ev[i]) + ' - All day'
            ev[i] = [tmp, len(tmp) + MyTodoist.emotes_offset * 2 + MyTodoist.tab_to_spaces]
    ev.insert(0, ['**EVENTS:**', len('**EVENTS:**')])
    ev.append(['', 0])
    return ev


def createString(tlist):
    compCountAll = tlist.completionCount()
    completionAll = tlist.completion()
    compCountNormal = tlist.completionCount(countHabits=False)
    completionNormal = tlist.completion(countHabits=False)
    hlineNum = 25
    headerEmojiDict = {
        0: ':mdot_red:',
        1: ':mdot_yellowstart:',
        2: ':mdot_greencomp:'
    }
    body = []
    string = (':hline:' * hlineNum) + '\n' + f"**DAILY TASKS {today.strftime('%d/%m/%Y')}** Last update: {datetime.now().strftime('%H:%M')} {MyTodoist.generate_progress_bar(completionNormal)}" + '\n' + (':hline:' * hlineNum) + '\n'
    body.append([string, (hlineNum * 2 + 10) * MyTodoist.emotes_offset + len(string)])
    body += getEvents()
    string = '**TASKS:**'
    body.append([string, len(string)])
    for p in tlist.projectsToUse():
        body.extend(p.toString())
    string = f'\nDone: {compCountAll[0]}/{compCountAll[1]}: {completionAll:.2%}' #\nNormal tasks: {compCountNormal[0]}/{compCountNormal[1]}: {completionNormal:.2%}'
    body.append([string, len(string)])
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
        MyTodoist.printStrings(createString(tlist))
    if mobile:
        res = '\n\n\n'.join(createString(tlist))
        if is_mobile:
            print(res)
            open('/Users/clarissadesimoni/Desktop/tasklist.txt', 'w').write(res)
        else:
            pyperclip.copy(res)
            open('/Users/clarissadesimoni/Desktop/tasklist.txt', 'w').write(res)

if __name__ == '__main__':
    tasklist(publish='publish' in sys.argv or is_mobile or debugger_is_active(), mobile='mobile' in sys.argv)