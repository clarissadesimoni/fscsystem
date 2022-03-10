from datetime import date, datetime, timedelta
from todoist_api_python.api import TodoistAPI
from pathlib import Path
from pymongo import MongoClient
import os, re, json, platform

is_mobile = 'Darwin' in platform.platform()
if is_mobile:
	import clipboard
else:
	import pyperclip

utils = json.load(open('creds_and_info.json'))
token = utils['todoist_token']
today = date.today()
file_dir = os.path.dirname(os.path.realpath(__file__))
file_name = f"{file_dir}/{today.strftime('%Y%m%d')}.txt"
api = TodoistAPI(token)
labelsDict = {label.name:label.id for label in api.get_labels()}
client = MongoClient(utils['db_url'])
db = client.todoist_notion_discord

all_tasks = []
indent_offsets = {
    'project': 0,
    'section': 1,
    'task': lambda section_name: 2 if section_name else 1
}

def getLabel(name):
    return labelsDict[name]


le = getLabel('Easy')
lm = getLabel('Medium')
lh = getLabel('Hard')

lls = getLabel('lecturespread')

emotes_offset = 21
tab_to_spaces = 4

indent_str = ':blank:'


class TaskList:
    def __init__(self):
        self.projects = {}      #(id: Project)
    
    def addTask(self, project, section, t):
        if project not in self.projects.keys():
            self.projects[project] = Project(project)
        self.projects[project].addTask(section, t)
    
    def projectsToUse(self):
        return sorted(self.projects.values(), key=lambda x: (x.priorityDict()[1], x.priorityDict()[2], x.priorityDict()[3], x.priorityDict()[4], x.priorityDict()['r']), reverse=True)
    
    def listTaskIDs(self, completed=[False, True]):
        data = []
        for p in self.projects.values():
            data = data + p.listTaskIDs(completed=completed)
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
        self.name = api.get_project(id).name
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
    
    def listTaskIDs(self, completed=[False, True]):
        data = []
        for s in self.sections.values():
            data = data + s.listTaskIDs(completed=completed)
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
        if not completed:
            compCount = self.completionCount()
            res = f'**PROJECT: {self.name}** (Done: {compCount[0]}/{compCount[1]}: {self.completion():.2%})'
        else:
            res = f'**PROJECT: {self.name}**'
        sec = sorted(self.sections.values(), key=lambda x: (x.priorityDict()[1], x.priorityDict()[2], x.priorityDict()[3], x.priorityDict()[4], x.priorityDict()['r']), reverse=True)
        res = [[res, len(res)]]
        for s in sec:
            res.extend(s.toString(completed=completed))
        return res
    
    def getUncompletedTasks(self, countMig=False, countHabits=True):
        res = []
        for s in self.sections.values():
            res += s.getUncompletedTasks(countMig=countMig, countHabits=countHabits)
        return res


class Section:
    def __init__(self, id):
        self.id = id
        self.name = api.get_section(id).name if id != 0 else 'No section'
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
    
    def listTaskIDs(self, completed=[False, True]):
        data = []
        for t in self.tasks:
            data = data + t.listTaskIDs(completed=completed)
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
        if not completed:
            compCount = self.completionCount()
            res = f'**SECTION: {self.name}** (Done: {compCount[0]}/{compCount[1]}: {self.completion():.2%})'
        else:
            res = f'**SECTION: {self.name}**'
        res = [[(indent_str * indent_offsets['section']) + res, len(res) + (indent_offsets['section'] * (emotes_offset + len(indent_str)))]] if self.id else []
        self.tasks.sort(key=lambda x: (int(x.completed), int(x.isHabit), -x.priority, x.due))
        data = list(filter(lambda t: t.completed == completed, self.tasks))
        for d in data:
            if len(d.subtasks) > 0:
                res.extend(d.toString(self.id != 0, 0, completed))
            else:
                res.append(d.toString(self.id != 0, 0, completed))
        return res
    
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
            self.id = id if api_obj is None else api_obj.id #int
            t = api.get_task(id) if api_obj is None else api_obj
            self.name = t.content #str
            self.parent = t.parent_id #int or None
            self.due = try_parsing_datetime(t.due.date) #datetime
            self.recurring = t.due.recurring #bool
            self.isHabit = getLabel('Habit') in t.label_ids #bool
            self.mig = self.recurring is False and (self.due.date() > today) #bool
            self.labels = t.label_ids #List[int]
            self.priority = t.priority #int
            self.completed = t.completed == 1 or (t.due.recurring is True and self.due.date() > today) #bool
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
        done, total = self.isCompleted()
        if self.completed is True:
            return ':mdot_greencomp: '
        elif self.isHabit is True:
            return ':mdot_lavenderstart: ' if ls in self.labels else ':mdot_lavender: '
        elif self.recurring is False and self.due.date() > today:
            return emotes[5 - self.priority] + 'mig: '
        elif ls in self.labels or 0 < done < total:
            return emotes[5 - self.priority] + 'start: '
        else:
            return emotes[5 - self.priority] + ': '
    
    def toString(self, is_section_named, level=0, completed=False):
        self.subtasks.sort(key=lambda x: (int(x.completed), int(x.isHabit), -x.priority, x.due, int(x.name.split(' ')[-1]) if any(x.name.startswith(y) for y in ['PDF', 'Ex', 'Es']) else 0))
        data = list(filter(lambda t: t.completed == completed, self.subtasks))
        comp = self.isCompleted()
        if lls in self.labels:
            self.name = self.name.replace(':', '\\:')
        res = f'{self.bullet()}{self.name}' + (f' (Done: {comp[0]}/{comp[1]}: {comp[0]/comp[1] * 100:.2f}%)' if len(self.subtasks) else '')
        res = [(indent_str * (indent_offsets['task'](is_section_named) + level)) + res, len(res) + emotes_offset + ((indent_offsets['task'](is_section_named) + level) * (emotes_offset + len(indent_str)))]
        if len(data) > 0:
            res = [res]
            for st in data:
                if len(st.subtasks) > 0:
                    res.extend(st.toString(is_section_named, level + 1))
                else:
                    res.append(st.toString(is_section_named, level + 1))
        return res

    def listTaskIDs(self, completed=[False, True]):
        data = [self.id] if self.completed in completed else []
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
    tmp = map(lambda x: x.parent_id, tasks)
    return {x: [y for y in tasks if y.parent_id == x] for x in tmp}


def getTodoist(to_check=[], to_filter=None):
    tlist = TaskList()
    global all_tasks
    ld = getLabel('Discord')
    filter_str = 'today & @Discord' + (' & @'.join(to_filter) if isinstance(to_filter, list) else f' & @{to_filter}' if isinstance(to_filter, str) else '')
    all_tasks = sorted(api.get_tasks(filter=filter_str))
    missing = set(to_check) - {t.id for t in all_tasks}
    if len(to_check) > 0 and len(missing) > 0:
        for task in missing:
            all_tasks.append(api.get_task(task))
    i = 0
    while i < len(all_tasks) - 1:
        if all_tasks[i].id == all_tasks[i + 1].id:
            all_tasks.pop(i)
        else:
            i += 1
    all_tasks = simplifyTasks(all_tasks)
    for task in all_tasks[None]:
        tlist.addTask(task.project_id, task.section_id, task.id)
    return tlist


def isStartOfDay():
    last_update = db.info.find_one({
        '_id': 'last_update'
    })
    return last_update['value'] != date.today().strftime('%Y-%m-%d')


# OLD
# def isStartOfDay():
#     if not Path(file_name).is_file():
#         return True
#     else:
#         return not len(open(file_name).read())

def getData():
    if isStartOfDay():
        db.todoist.delete_many({})
        db.info.update_one({
        	'_id': 'last_update'
        	},
        	{
        		'$set': {
        			'_id': 'last_update',
        			'value': date.today().strftime('%Y-%m-%d')
        		}
        	},
        	upsert=True
        )
        ids = []
    else:
        ids = [int(el['_id']) for el in db.todoist.find({})]
    return ids

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


def updateData(tasks):
    db.todoist.insert_many([{'_id': el} for el in tasks])


def updateFile(tasks):
    f = open(file_name, 'w')
    for t in tasks:
        f.write(str(t) + '\n')


def printStrings(strings):
    print(f'There are {len(strings)} segments')
    for i, s in enumerate(strings):
        if is_mobile:
            clipboard.set(s)
        else:
            pyperclip.copy(s)
        if i < len(strings) - 1:
            input('Press enter to continue...')
    print('Finished!')