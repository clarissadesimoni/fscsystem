#!/usr/bin/env python

from datetime import datetime, date, time, timedelta
import  sys, math
import MyTodoist
tlist = None
today = date.today()

def backend():
    global tlist
    tlist = MyTodoist.getTodoist(MyTodoist.getFile())
    MyTodoist.updateFile(tlist.listTaskIDs())


def getEvents():
    ev = open('events.txt').read().split('\n')
    ev = list(filter(lambda l: len(l), ev))
    length = 0
    for i in range(len(ev)):
        try:
            end = ev[i].split(' - ')[1].split(':')
            end = time(int(end[0]), int(end[1]))
            if datetime.combine(today, end) <= datetime.now():
                ev[i] = '\t:mdot_darkbluex: ' + str(ev[i])
            else:
                ev[i] = '\t:mdot_darkblue: ' + str(ev[i])
        except:
            continue
    ev.insert(0, '**EVENTS:**')
    ev.append('')
    length += len(ev) + len(ev) * (MyTodoist.emotes_offset + MyTodoist.tab_to_spaces)
    ev = '\n'.join(ev)
    length += len(ev)
    return [ev, length]


def createString(tlist):
    compCountAll = tlist.completionCount()
    completionAll = tlist.completion()
    compCountNormal = tlist.completionCount(countHabits=False)
    completionNormal = tlist.completion(countHabits=False)
    hlineNum = 19
    headerEmojiDict = {
        0: ':mdot_red:',
        1: ':mdot_yellowstart:',
        2: ':mdot_greencomp:'
    }
    body = []
    string = (':hline:' * hlineNum) + '\n' + f"**{headerEmojiDict[math.floor(completionNormal * 2)]} DAILY TASKS {today.strftime('%d/%m/%Y')}** {headerEmojiDict[math.floor(completionNormal * 2)]} Last update: {datetime.now().strftime('%I:%M %p')}" + '\n' + (':hline:' * hlineNum) + '\n'
    body.append([string, hlineNum * 2 * 20 + len(string)])
    body.append(getEvents())
    string = '**TASKS:**'
    body.append([string, len(string)])
    body += [p.toString() for p in tlist.projectsToUse()]
    string = f'\nDone: {compCountAll[0]}/{compCountAll[1]}: {completionAll:.2%}\nNormal tasks: {compCountNormal[0]}/{compCountNormal[1]}: {completionNormal:.2%}'
    body.append([string, len(string)])
    i = 0
    while i < len(body) - 1:
        if body[i][1] + body[i + 1][1] <= 1999:
            body[i] = [body[i][0] + '\n' + body[i + 1][0], body[i][1] + body[i + 1][1]]
            body.pop(i + 1)
        else:
            i += 1
    return [b[0] for b in body]

def tasklist(publish=True, ssh=False):
    backend()
    if publish:
        MyTodoist.printStrings(createString(tlist))
    if ssh:
        open('tasklist.txt', 'w').write('\n\n\n'.join(createString(tlist)))

if __name__ == '__main__':
    tasklist(publish='publish' in sys.argv, ssh='ssh' in sys.argv)