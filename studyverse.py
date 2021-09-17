from datetime import date, datetime, timedelta
from todoist.api import TodoistAPI
import pyperclip, json

utils = json.load(open('creds_and_info.json'))
token = utils['todoist_token']
api = TodoistAPI(token)
api.sync()
labelsDict = {label['name']:label['id'] for label in api.state['labels']}

def getLabel(name):
    return labelsDict[name]

lo = getLabel('Oral')
ld = getLabel('Discord')
le = getLabel('Easy')
lm = getLabel('Medium')
lh = getLabel('Hard')
lr = getLabel('Habit')

def try_parsing_datetime(text):
    if text is None:
        return date.today() + timedelta(days=1)
    if text == datetime.strftime(datetime.now(), "%Y-%m-%d"):
        text += "T00:00:00"
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.today() + timedelta(days=1)

def getItemAttribute(item, attribute):
    try:
        return item[attribute]
    except:
        try:
            return item['item'][attribute]
        except:
            try:
                return item['data'][attribute]
            except:
                return item.data.get(attribute, '')

class MyTask:
    def __init__(self, id):
        self.id = id #int
        t = api.items.get_by_id(id)
        self.name = getItemAttribute(t, 'content') #str
        self.due = try_parsing_datetime(getItemAttribute(t, 'due')['date']) #datetime
        self.recurring = getItemAttribute(t, 'due')['is_recurring'] #bool
        self.mig = self.recurring is False and (self.due.date() > date.today()) #bool
        self.labels = getItemAttribute(t, 'labels') #List[int]
        self.priority = 5 - getItemAttribute(t, 'priority') #int
        self.completed = getItemAttribute(t, 'checked') == 1 or (self.recurring is True and self.due.date() > date.today()) #bool
        self.isOral = lo in self.labels
        self.category = 'easy' if le in self.labels else 'med' if lm in self.labels else 'hard' if lh in self.labels else 'OOF'
        self.bullet = {'easy': ':adot_green: ', 'med': ':adot_yellow: ', 'hard': ':adot_pink: '}.get(self.category, '')
    
    def __str__(self):
        return self.bullet + self.name + (' (oral)' if self.isOral else '')

def getTodoist():
    api.sync()
    data = {'easy': [], 'med': [], 'hard': [], 'OOF': []}
    for item in api.state['items']:
        if getItemAttribute(item, 'checked') == 0 and getItemAttribute(item, 'due') is not None and ld in getItemAttribute(item, 'labels')and lr not in getItemAttribute(item, 'labels'):
            if try_parsing_datetime(getItemAttribute(item, 'due')['date']).date() <= date.today():
                t = MyTask(item['id'])
                data[t.category].append(t)
    keys = list(data.keys())[:]
    for cat in keys:
        if len(data[cat]):
            data[cat].sort(key=lambda x: (int(x.completed), int(x.recurring), -x.priority, x.due))
            data[cat] = list(map(lambda x: str(x), data[cat]))
        else:
            del data[cat]
    return data

def tasklist(clear=True):
    api.sync()
    data = getTodoist()
    if clear:
        pyperclip.copy('=tdeleteall')
        input('Deleting old list. Press enter to continue...')
        pyperclip.copy('=confirm')
        input('Confirming the deletion. Press enter to continue...')
    print('There are ' + str(len(data.keys())) + ' types of tasks today')
    for key, value in data.items():
        pyperclip.copy('=t' + key + ' ' + '//'.join(value))
        input('Pres Enter to continue...')
    print('Finished!')

if __name__ == '__main__':
    tasklist()