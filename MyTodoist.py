from datetime import date, datetime, timedelta
from todoist.api import TodoistAPI
from pathlib import Path
import pyperclip, os, re, json

utils = json.load(open('creds_and_info.json'))
token = utils['todoist_token']
today = date.today()
file_dir = os.path.dirname(os.path.realpath(__file__))
file_name = f"{file_dir}/{today.strftime('%Y%m%d')}.txt"
api = TodoistAPI(token)
api.sync()
labelsDict = {label['name']:label['id'] for label in api.state['labels']}

all_tasks = []
tab_offsets = {
    'project': 0,
    'section': 1,
    'task': lambda section_name: 2 if section_name else 1
}

def getLabel(name):
    return labelsDict[name]


le = getLabel('Easy')
lm = getLabel('Medium')
lh = getLabel('Hard')

emotes_offset = 20
tab_to_spaces = 4


class TaskList:
    def __init__(self):
        self.projects = {}      #(id: Project)
    
    def addTask(self, project, section, t):
        if project not in self.projects.keys():
            self.projects[project] = Project(project)
        self.projects[project].addTask(section, t)
    
    def projectsToUse(self):
        return sorted(self.projects.values(), key=lambda x: (x.priorityDict()[1], x.priorityDict()[2], x.priorityDict()[3], x.priorityDict()[4], x.priorityDict()['r']), reverse=True)
    
    def listTaskIDs(self):
        data = []
        for p in self.projects.values():
            data = data + p.listTaskIDs()
        return data
    
    def completionCount(self, countMig=False, countHabits=True):
        comp = 0
        total = 0
        countList = [p.completionCount(countMig=countMig, countHabits=countHabits) for p in self.projects.values()]
        for l in countList:
            comp += l[0]
            total += l[1]
        return [comp, total]
    
    def completion(self, countmig=False, countHabits=True):
        counts = self.completionCount(countMig=countmig, countHabits=countHabits)
        return counts[0]/counts[1]
    
    def getUncompletedTasks(self):
        res = []
        for p in self.projects.values():
            res += p.getUncompletedTasks()
        return res


class Project:
    def __init__(self, id):
        self.id = id
        self.name = api.projects.get_by_id(id)['name']
        self.sections = {}    #(id: Section)
    
    def addTask(self, section, t):
        if section is None:
            section = 0
        if section not in self.sections.keys():
            self.sections[section] = Section(section)
        self.sections[section].addTask(t)
    
    def priorityDict(self):
        data = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            'r': 0
        }
        for s in self.sections.values():
            tmp = s.priorityDict()
            for priority in data.keys():
                data[priority] += tmp[priority]
        return data
    
    def listTaskIDs(self):
        data = []
        for s in self.sections.values():
            data = data + s.listTaskIDs()
        return data
    
    def completionCount(self, countMig=False, countHabits=True):
        comp = 0
        total = 0
        countList = [s.completionCount(countMig=countMig, countHabits=countHabits) for s in self.sections.values()]
        for l in countList:
            comp += l[0]
            total += l[1]
        return [comp, total]
    
    def completion(self, countmig=False, countHabits=True):
        counts = self.completionCount(countMig=countmig, countHabits=countHabits)
        return counts[0]/counts[1]
    
    def toString(self, completed=False):
        res = ''
        data = []
        if not completed:
            compCount = self.completionCount()
            res = [f'**PROJECT: {self.name}** (Done: {compCount[0]}/{compCount[1]}: {self.completion():.2%})']
            if self.completion() < 1:
                sec = sorted(self.sections.values(), key=lambda x: (x.priorityDict()[1], x.priorityDict()[2], x.priorityDict()[3], x.priorityDict()[4], x.priorityDict()['r']), reverse=True)
                data = [e.toString() for e in sec]
        else:
            res = [f'**PROJECT: {self.name}**']
            if self.completion() > 0:
                sec = sorted(self.sections.values(), key=lambda x: (x.priorityDict()[1], x.priorityDict()[2], x.priorityDict()[3], x.priorityDict()[4], x.priorityDict()['r']), reverse=True)
                data = [e.toString(completed=completed) for e in sec]
                data = list(filter(lambda e: len(e[0]) > 0, data))
        strings = [e[0] for e in data]
        res = ('\n' + '\t' * tab_offsets['section']).join(res + strings)
        length = sum([s[1] for s in data]) + len(strings) * tab_to_spaces * tab_offsets['section'] + len(res)
        return [res, length]
    
    def getUncompletedTasks(self, countMig=False, countHabits=True):
        res = []
        for s in self.sections.values():
            res += s.getUncompletedTasks(countMig=countMig, countHabits=countHabits)
        return res


class Section:
    def __init__(self, id):
        self.id = id
        self.name = api.sections.get_by_id(id)['name'] if id != 0 else 'No section'
        self.tasks = []
        
    def addTask(self, t):
        if isinstance(t, int):
            self.tasks.append(MyTask(id=t))
        else:
            self.tasks.append(MyTask(api_obj=t))
    
    def priorityDict(self):
        data = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            'r': 0
        }
        for t in self.tasks:
            if t.completed == 0:
                if t.recurring is True:
                    data['r'] += 1
                else:
                    data[5 - t.priority] += 1
        return data
    
    def listTaskIDs(self):
        data = []
        for t in self.tasks:
            data = data + t.listTaskIDs()
        return data
    
    def getCompletedTasks(self):
        return list(filter(lambda t: t.completed, self.tasks))
    
    def completionCount(self, countMig=False, countHabits=True):
        lh = getLabel('Habit')
        if not countMig and not countHabits:
            tmp = list(filter(lambda t: not t.mig and lh not in t.labels, self.tasks))
        elif not countMig and countHabits:
            tmp = list(filter(lambda t: not t.mig, self.tasks))
        elif countMig and not countHabits:
            tmp = list(filter(lambda t: lh not in t.labels, self.tasks))
        elif countMig and countHabits:
            tmp = self.tasks
        tmp = [t.isCompleted() for t in tmp]
        return [sum(t[0] for t in tmp), sum(t[1] for t in tmp)]
    
    def completion(self, countmig=False, countHabits=True):
        counts = self.completionCount(countMig=countmig, countHabits=countHabits)
        return counts[0]/counts[1]
    
    def toString(self, completed=False):
        res = ''
        offset = 0
        if not completed:
            compCount = self.completionCount()
            res = [f'**SECTION: {self.name}** (Done: {compCount[0]}/{compCount[1]}: {self.completion():.2%})'] if self.id else []
            if self.completion() < 1:
                self.tasks.sort(key=lambda x: (int(x.completed), int(x.recurring), -x.priority, x.due))
                data = list(map(lambda s: s.toString(self.id != 0, 1, completed), list(filter(lambda t: not t.completed, self.tasks))))
                res += [x[0] for x in data]
                offset += sum(x[1] for x in data) + len(res) * (tab_to_spaces * tab_offsets['task'](self.id != 0) + 1)
            res = ('\n' + '\t' * tab_offsets['task'](self.id != 0)).join(res)
        else:
            if self.completion() > 0:
                res = [f'**SECTION: {self.name}**'] if self.id else []
                self.tasks.sort(key=lambda x: (int(x.completed), int(x.recurring), -x.priority, x.due))
                data = list(map(lambda s: s.toString(self.id != 0, 1, completed), list(filter(lambda t: t.completed, self.tasks))))
                res += [x[0] for x in data]
                offset += sum(x[1] for x in data) + len(res) * (tab_to_spaces * tab_offsets['task'](self.id != 0) + 1)
            res = ('\n' + '\t' * tab_offsets['task'](self.id != 0)).join(res)
        return res, offset
    
    def getUncompletedTasks(self, countMig=False, countHabits=True):
        lh = getLabel('Habit')
        if not countMig and not countHabits:
            tmp = list(filter(lambda t: not t.mig and lh not in t.labels, self.tasks))
        elif not countMig and countHabits:
            tmp = list(filter(lambda t: not t.mig, self.tasks))
        elif countMig and not countHabits:
            tmp = list(filter(lambda t: lh not in t.labels, self.tasks))
        elif countMig and countHabits:
            tmp = self.tasks
        return list(filter(lambda t: not t.completed, tmp))


class MyTask:
    def __init__(self, id=None, api_obj=None):
            self.id = id if api_obj is None else api_obj.data['id'] #int
            t = api.items.get_by_id(id) if api_obj is None else api_obj
            self.name = t['content'] #str
            self.parent = t['parent_id'] #int or None
            self.due = try_parsing_datetime(t['due']['date']) #datetime
            self.recurring = t['due']['is_recurring'] #bool
            self.mig = self.recurring is False and (self.due.date() > today) #bool
            self.labels = t['labels'] #List[int]
            self.priority = t['priority'] #int
            self.completed = t['checked'] == 1 or (t['due']['is_recurring'] is True and self.due.date() > today) #bool
            self.category = 'easy' if le in self.labels else 'med' if lm in self.labels else 'hard' if lh in self.labels else 'OOF' #str
            self.bullet2 = {'easy': ':mdot_green: ', 'med': ':mdot_yellow: ', 'hard': ':mdot_red: '}.get(self.category, '') #str
            self.subtasks = [MyTask(api_obj=st) for st in all_tasks.get(self.id, [])]
    
    def bullet(self):
        emotes = {
            1: ':mdot_red',
            2: ':mdot_yellow',
            3: ':mdot_blue',
            4: ':mdot_grey'
        }
        ls = getLabel('Started')
        if self.completed is True:
            return ':mdot_greencomp: '
        elif self.recurring is True:
            if ls in self.labels:
                return ':mdot_lavenderstart: '
            else:
                return ':mdot_lavender: '
        elif self.recurring is False and self.due.date() > today:
            return emotes[5 - self.priority] + 'mig: '
        elif ls in self.labels:
            return emotes[5 - self.priority] + 'start: '
        else:
            return emotes[5 - self.priority] + ': '
    
    def toString(self, section_name, level=0, completed=False):
        data = [st.toString(section_name, level + 1) for st in list(filter(lambda t: t.completed == completed, self.subtasks))]
        comp = self.isCompleted()
        res = ('\n' + ('\t' * (tab_offsets['task'](section_name) + level))).join([self.bullet() + self.name + (f' (Done: {comp[0]}/{comp[1]}: {comp[0]/comp[1] * 100:.2f}%)' if len(self.subtasks) else '')] + [st[0] for st in data])
        return res, sum(e[1] for e in data) + len(data) * (tab_to_spaces * (tab_offsets['task'](section_name) + level) + 1) + emotes_offset
    
    def listTaskIDs(self):
        data = [self.id]
        for t in self.subtasks:
            data = data + t.listTaskIDs()
        return data
    
    def isCompleted(self):
        if len(self.subtasks):
            data = [s.isCompleted() for s in self.subtasks]
            return [sum(d[0] for d in data), sum(d[1] for d in data)]
        else:
            return [int(self.completed), 1]


def try_parsing_datetime(text):
    if text is None:
        return today + timedelta(days=1)
    if text == datetime.strftime(datetime.now(), '%Y-%m-%d'):
        text += 'T00:00:00'
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S'):
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


def simplifyTasks(tasks):
    tmp = map(lambda x: getItemAttribute(x, 'parent_id'), tasks)
    return {x: [y for y in tasks if getItemAttribute(y, 'parent_id') == x] for x in tmp}


def getTodoist(toCheck=[], to_filter=None):
    api.sync()
    tlist = TaskList()
    global all_tasks
    ld = getLabel('Discord')
    for item in api.state['items']:
        if getItemAttribute(item, 'id') in toCheck:
            all_tasks.append(item)
        elif getItemAttribute(item, 'due') is not None and ld in getItemAttribute(item, 'labels') and (isinstance(to_filter, list) and all(labelsDict[l] in item['labels'] for l in to_filter) or not isinstance(to_filter, list)):
            try:
                if try_parsing_datetime(getItemAttribute(item, 'due')['date']).date() <= today and getItemAttribute(item, 'checked') == 0:
                    all_tasks.append(item)
            except:
                print(item.data.items())
    all_tasks = simplifyTasks(all_tasks)
    for item in all_tasks[None]:
        tlist.addTask(item['project_id'], item['section_id'], item['id'])
    return tlist


def isStartOfDay():
    if not Path(file_name).is_file():
        return True
    else:
        return not len(open(file_name).read())


def getFile():
    if isStartOfDay():
        for f in next(os.walk(file_dir))[2]:
            if re.match(r'^20[0-9]{6}.txt$', f) and f != f"{today.strftime('%Y%m%d')}.txt":
                os.remove(f)
        open(file_name, 'w')
    f = open(file_name, 'r+')
    data = []
    lines = f.readlines()
    f.close()
    if len(lines) > 0:
        for line in lines:
            data.append(int(line))
    return data


def updateFile(tasks):
    f = open(file_name, 'w')
    for t in tasks:
        f.write(str(t) + '\n')


def printStrings(strings):
    print(f'There are {len(strings)} segments')
    for i, s in enumerate(strings):
        pyperclip.copy(s)
        if i < len(strings) - 1:
            input('Press enter to continue...')
    print('Finished!')
