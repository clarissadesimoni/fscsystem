#!/usr/bin/env python

import sys, datetime, json
from todoist.api import TodoistAPI

utils = json.load(open('creds_and_info.json'))
token = utils['todoist_token']
filename = f"{datetime.date.strftime(datetime.date.today(), '%Y%m%d')}.txt"
api = TodoistAPI(token)
api.sync()
toDelList = []
idList = []
tot = int(input('Number of tasks to delete: '))
for i in range(tot):
    toDelList.append(input('Insert exact name of task: '))
for item in api.state['items']:
    if item['content'] in toDelList:
        idList.append(item['id'])
print(idList)
if len(sys.argv) > 1:
    lines = open(filename, 'r').read().split('\n')
    lines = list(filter(lambda l: len(l.strip()), lines))
    lines = list(filter(lambda l: int(l.strip()) not in idList, lines))
    open(filename, 'w').write('\n'.join(lines))