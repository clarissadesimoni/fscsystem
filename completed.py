#!/usr/bin/env python

import pyperclip
import MyTodoist

def createString(tlist):
    string = '**COMPLETED TASKS:**'
    body = [[string, len(string)]]
    body += [p.toString(completed=True) for p in tlist.projectsToUse()]
    i = 0
    while i < len(body) - 1:
        if body[i][1] + body[i + 1][1] <= 1999:
            body[i] = [body[i][0] + '\n' + body[i + 1][0], body[i][1] + body[i + 1][1]]
            body.pop(i + 1)
        else:
            i += 1
    return [b[0] for b in body]


def tasklist():
    tlist = MyTodoist.getTodoist(MyTodoist.getFile())
    MyTodoist.updateFile(tlist.listTaskIDs())
    toCopy = createString(tlist)
    print('There are ' + str(len(toCopy)) + ' segments')
    for s in toCopy:
        pyperclip.copy(s)
        input('Press enter to continue...')
    print('Finished!')

if __name__ == '__main__':
    tasklist()
