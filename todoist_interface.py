from datetime import datetime, date, time, timedelta
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task
from typing import Dict, List, Set, Union
import os, re, json, platform, math, requests, clipboard_interface, db_interface, cla_utils

is_mobile = 'macOS' not in platform.platform()

utils = json.load(open('creds_and_info.json'))
token = utils['todoist_token']
today = date.today()
file_dir = utils['file_dir']
file_name = f"{file_dir}/{today.strftime('%Y%m%d')}.txt"
api = TodoistAPI(token)

is_connected = True
uncompleted_tasks: List[Task] = []
uncompleted_tasks_dict: Dict[str, List[Task]] = {}
to_del = []
indent_offsets = {
    'project': 0,
    'section': 1,
    'task': lambda section_name, vc: 0 if vc else (2 if section_name else 1)
}


le = 'Easy'
lm = 'Medium'
lh = 'Hard'

lsp = 'spread'
lls = 'lecturespread'

emotes_offset = 20
tab_to_spaces = 4

indent_str = ':blank:'


class MyTask:
    def __init__(self, id: Union[str, None] = None, api_obj: Union[Task, None] = None):
            self.id: str = id if api_obj is None else api_obj.id
            t: Task = api.get_task(id) if api_obj is None else api_obj
            self.name: str = t.content
            self.parent: Union[int, None] = t.parent_id
            self.due: datetime = cla_utils.get_datetime(t.due.datetime) if t.due.datetime is not None else datetime.combine(cla_utils.get_date(t.due.date), time())
            self.recurring: bool = t.due.is_recurring
            self.is_habit: bool = 'Habit' in t.labels
            self.is_count: bool = 'Count' in t.labels
            self.mig: bool = self.recurring is False and (self.due.date() > today)
            self.labels: List[str] = t.labels
            self.priority: int = t.priority
            self.completed: bool = t.is_completed == 1 or (t.due.is_recurring is True and self.due.date() > today)
            self.category: str = 'easy' if le in self.labels else 'med' if lm in self.labels else 'hard' if lh in self.labels else 'OOF'
            self.bullet2: str = {'easy': ':mdot_green: ', 'med': ':mdot_yellow: ', 'hard': ':mdot_red: '}.get(self.category, '')
            self.order: int = t.order
            self.subtasks: List[MyTask] = [MyTask(api_obj=st) for st in uncompleted_tasks_dict.get(self.id, [])]
            self.num_of_sub_to_print: int = len(list(filter(lambda s: not s.is_count, self.subtasks)))
    
    def bullet(self):
        emotes = {
            1: ':mdot_red',
            2: ':mdot_yellow',
            3: ':mdot_blue',
            4: ':mdot_grey'
        }
        ls = 'Started'
        done, total = self.is_completed()
        if self.completed is True:
            return ':mdot_greencomp: '
        elif self.is_habit is True:
            return ':mdot_lavenderstart: ' if ls in self.labels else ':mdot_lavender: '
        elif 'Initial' not in self.labels:
            return ':mdot_rainbowstart: ' if ls in self.labels else ':mdot_rainbow: '
        elif self.recurring is False and self.due.date() > today:
            return emotes[5 - self.priority] + 'mig: '
        elif ls in self.labels or 0 < done < total:
            return emotes[5 - self.priority] + 'start: '
        else:
            return emotes[5 - self.priority] + ': '
    
    def to_string(self, is_section_named: bool, level: int = 0, vc: bool = False, chat: bool = False):
        self.subtasks.sort(key=lambda x: (int(x.completed), int(x.is_habit), -x.priority, x.due, x.order, int(x.name.split(' ')[-1]) if any(x.name.startswith(y) for y in ['PDF', 'Ex.', 'Es.']) else 0))
        comp = self.is_completed()
        # if lls in self.labels or lsp in self.labels or re.match(r'.*(|[0-9]+:)[0-9]{2}:[0-9]{2}.*', self.name):
        pb = generate_progress_bar(self.completion()) if (comp[1] >= 10 or (comp[0]/comp[1]) > 1) else generate_shorter_progress_bar(*comp)
        res = f'{self.bullet()}{self.name}' + (f' (Done: {comp[0]}/{comp[1]}: {comp[0]/comp[1] * 100:.2f}%) {pb}' if len(self.subtasks) else '')
        res = [(indent_str * (indent_offsets['task'](is_section_named, (vc or chat)) + level)) + res, ((pb.count(':') // 2) if len(self.subtasks) else 0) * (emotes_offset + 1) + len(res) + emotes_offset + ((indent_offsets['task'](is_section_named, (vc or chat)) + level) * (emotes_offset + len(indent_str))) - (2 * res.count('~1'))]
        if self.num_of_sub_to_print > 0:
            res = [res]
            for st in self.subtasks:
                if st.is_count:
                    continue
                if st.num_of_sub_to_print > 0:
                    res.extend(st.to_string(is_section_named, level + 1))
                else:
                    res.append(st.to_string(is_section_named, level + 1))
        return res

    def list_task_ids(self, completed=[False, True]):
        data = [self.id] if self.completed in completed else []
        for t in self.subtasks:
            data = data + t.list_task_ids()
        return data
    
    def is_completed(self):
        if len(self.subtasks):
            data = [s.is_completed() for s in self.subtasks]
            return [sum(d[0] for d in data), sum(d[1] for d in data)]
        else:
            return [int(self.completed or 'Split' in self.labels), 1]
    
    def is_completed_initial(self):
        if len(self.subtasks):
            data = [s.is_completed_initial() for s in self.subtasks]
            return [sum(d[0] for d in data), sum(d[1] for d in data)]
        else:
            return [int(self.completed or 'Split' in self.labels), int('Initial' in self.labels)]
    
    def completion(self):
        counts = self.is_completed()
        return counts[0]/counts[1]


class Section:
    def __init__(self, id: str):
        self.id = id
        self.name = api.get_section(id).name if id != 0 else 'No section'
        self.tasks: List[MyTask] = []
        self.completed_tasks: List[str] = []
        self.completed_initial_tasks_counter = 0
        self.completed_extra_tasks_counter = 0
        
    def add_task(self, t: Union[MyTask, str]):
        if isinstance(t, str):
            self.tasks.append(MyTask(id=t))
        else:
            self.tasks.append(MyTask(api_obj=t))
    
    def add_completed_task(self, tid: str, initial: bool = False):
        self.completed_tasks.append(tid)
        if initial:
            self.completed_initial_tasks_counter += 1
        else:
            self.completed_extra_tasks_counter += 1

    def priority_dict(self):
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
    
    def list_task_ids(self, completed=[False, True]):
        data = []
        for t in self.tasks:
            data = data + t.list_task_ids(completed=completed)
        return data + self.completed_tasks
    
    def get_completed_tasks(self):
        return list(filter(lambda t: t.completed, self.tasks))
    
    def completion_count(self, count_mig=False, count_habits=True):
        lh = 'Habit'
        tmp: List[MyTask] = []
        if not count_mig and not count_habits:
            tmp = list(filter(lambda t: not t.mig and lh not in t.labels, self.tasks))
        elif not count_mig and count_habits:
            tmp = list(filter(lambda t: not t.mig, self.tasks))
        elif count_mig and not count_habits:
            tmp = list(filter(lambda t: lh not in t.labels, self.tasks))
        elif count_mig and count_habits:
            tmp = self.tasks
        tmp = [t.is_completed_initial() for t in tmp]
        return [sum(t[0] for t in tmp) + self.completed_initial_tasks_counter + self.completed_extra_tasks_counter, sum(t[1] for t in tmp) + self.completed_initial_tasks_counter]
    
    def completion(self, count_mig=False, count_habits=True):
        counts = self.completion_count(count_mig=count_mig, count_habits=count_habits)
        if counts[1] == 0:
            raise ValueError('No initial tasks are set')
        else:
            return counts[0]/counts[1]
    
    def to_string(self, completed: bool = False, vc: bool = False, chat: bool = False):
        res = []
        if not vc and not chat:
            if not completed:
                comp_count = self.completion_count()
                comp = self.completion()
                pb = (" " + generate_progress_bar(comp)) if (comp_count[1] >= 10 or (comp_count[0]/comp_count[1]) > 1) else (" " + generate_shorter_progress_bar(*comp_count)) if comp_count[1] > 1 else ""
                res = f'**SECTION: {self.name}** (Done: {comp_count[0]}/{comp_count[1]}: {comp:.2%}){pb}'
            else:
                res = f'**SECTION: {self.name}**'
            res = [[(indent_str * indent_offsets['section']) + res, (pb.count(':') // 2) * emotes_offset + len(res) + (indent_offsets['section'] * (emotes_offset + len(indent_str)))]] if self.id else []
        self.tasks.sort(key=lambda x: (int(x.completed), int(x.is_habit), -x.priority, x.due, x.order))
        data = list(filter(lambda t: t.completed == completed, self.tasks))
        for d in data:
            if 'Split' in d.labels and not d.completed and all(s.completed for s in d.subtasks):
                continue
            if d.num_of_sub_to_print > 0:
                res.extend(d.to_string(self.id != 0, 0, vc=vc, chat=chat))
            else:
                res.append(d.to_string(self.id != 0, 0, vc=vc, chat=chat))
        return res
    
    def get_uncompleted_tasks(self, count_mig=False, count_habits=True):
        lh = 'Habit'
        if not count_mig and not count_habits:
            tmp = list(filter(lambda t: not t.mig and lh not in t.labels, self.tasks))
        elif not count_mig and count_habits:
            tmp = list(filter(lambda t: not t.mig, self.tasks))
        elif count_mig and not count_habits:
            tmp = list(filter(lambda t: lh not in t.labels, self.tasks))
        elif count_mig and count_habits:
            tmp = self.tasks
        return list(filter(lambda t: not t.completed, tmp))


class Project:
    def __init__(self, id: str):
        self.id = id
        self.name = api.get_project(id).name
        self.sections: Dict[str, Section] = {}    #(id: Section)
    
    def add_task(self, section_id: str, t: Union[MyTask, str]):
        if section_id is None:
            section_id = 0
        if section_id not in self.sections.keys():
            self.sections[section_id] = Section(section_id)
        self.sections[section_id].add_task(t)
    
    def add_completed_task(self, tid: str, section_id: str, initial: bool = False):
        section_id = section_id if section_id is not None else 0
        if section_id not in self.sections.keys():
            self.sections[section_id] = Section(section_id)
        self.sections[section_id].add_completed_task(tid, initial=initial)

    def priority_dict(self):
        data = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            'r': 0
        }
        for s in self.sections.values():
            tmp = s.priority_dict()
            for priority in data.keys():
                data[priority] += tmp[priority]
        return data
    
    def list_task_ids(self, completed=[False, True]):
        data = []
        for s in self.sections.values():
            data = data + s.list_task_ids(completed=completed)
        return data
    
    def completion_count(self, count_mig=False, count_habits=True):
        comp = 0
        total = 0
        countList = [s.completion_count(count_mig=count_mig, count_habits=count_habits) for s in self.sections.values()]
        for l in countList:
            comp += l[0]
            total += l[1]
        return [comp, total]
    
    def completion(self, count_mig=False, count_habits=True):
        counts = self.completion_count(count_mig=count_mig, count_habits=count_habits)
        if counts[1] == 0:
            return 1
        else:
            return counts[0]/counts[1]
    
    def to_string(self, completed: bool = False, vc: bool = False, chat: bool = False):
        res = ''
        if not completed:
            comp_count = self.completion_count()
            comp = self.completion()
            pb = (" " + generate_progress_bar(comp)) if (comp_count[1] >= 10 or (comp_count[0]/comp_count[1]) > 1) else (" " + generate_shorter_progress_bar(*comp_count)) if comp_count[1] > 1 else ""
            res = f'**PROJECT: {self.name}** (Done: {comp_count[0]}/{comp_count[1]}: {comp:.2%}){pb}'
        else:
            res = f'**PROJECT: {self.name}**'
        sec = sorted(self.sections.values(), key=lambda x: (x.priority_dict()[1], x.priority_dict()[2], x.priority_dict()[3], x.priority_dict()[4], x.priority_dict()['r']), reverse=True)
        res = [[res, (pb.count(':') // 2) * emotes_offset + len(res)]]
        for s in sec:
            res.extend(s.to_string(completed=completed, vc=vc, chat=chat))
        return res
    
    def get_uncompleted_tasks(self, count_mig=False, count_habits=True):
        res = []
        for s in self.sections.values():
            res += s.get_uncompleted_tasks(count_mig=count_mig, count_habits=count_habits)
        return res
    
    def clean_list(self):
        res = 0
        tmp = 0
        empty = []
        for s in self.sections.values():
            if (tmp := s.completion_count()[1]) == 0:
                empty.append(s.id)
            else:
                res += tmp
        for e in empty:
            del self.sections[e]
        return res


class TaskList:
    def __init__(self):
        self.projects: Dict[str, Project] = {}      #(id: Project)
    
    def add_task(self, project_id: str, section_id: str, t: Union[MyTask, str]):
        if today.strftime("%Y-%m-%d") not in t.due.date:
            to_del.append(t.id)
            return
        if project_id not in self.projects.keys():
            self.projects[project_id] = Project(project_id)
        self.projects[project_id].add_task(section_id, t)

    def add_completed_task(self, tid: str, project_id: str, section_id: str, initial: bool = False):
        if project_id not in self.projects.keys():
            self.projects[project_id] = Project(project_id)
        self.projects[project_id].add_completed_task(tid, section_id, initial=initial)
    
    def projects_to_use(self):
        return sorted(self.projects.values(), key=lambda x: (x.priority_dict()[1], x.priority_dict()[2], x.priority_dict()[3], x.priority_dict()[4], x.priority_dict()['r']), reverse=True)
    
    def list_task_ids(self, completed=[False, True]):
        data = []
        for p in self.projects.values():
            data = data + p.list_task_ids(completed=completed)
        return data
    
    def completion_count(self, count_mig=False, count_habits=True):
        comp = 0
        total = 0
        countList = [p.completion_count(count_mig=count_mig, count_habits=count_habits) for p in self.projects.values()]
        for l in countList:
            comp += l[0]
            total += l[1]
        return [comp, total]
    
    def completion(self, count_mig=False, count_habits=True):
        counts = self.completion_count(count_mig=count_mig, count_habits=count_habits)
        if counts[1] == 0:
            return 1
        else:
            return counts[0]/counts[1]
    
    def get_uncompleted_tasks(self):
        res = []
        for p in self.projects.values():
            res += p.get_uncompleted_tasks()
        return res
    
    def clean_list(self):
        empty = []
        for p in self.projects.values():
            if p.clean_list() == 0:
                empty.append(p.id)
        for e in empty:
            del self.projects[e]


def generate_progress_bar(percentage: float) -> str:
    if percentage < 0:
        raise ValueError('Percentage must be between greater than 0')
    res = (':es:' if percentage < 0.1 else ':rs:' if 0.1 <= percentage < 0.2 else ':fs:')
    res += ':fm:' * max(0, min(8, math.floor(percentage * 10) - 2))
    res += ':rm:' if 0.2 <= percentage < 1 else ''
    res += (':em:' * max(0, 9 - math.floor(percentage * 10))) if 0.1 <= percentage < 1 else ':em:' * 8 if percentage < 0.1 else ''
    res += ':ee:' if percentage < 1 else ':fe:' if percentage == 1 else ':be:'
    res += ':om:' * (max(0, math.floor((percentage - 1) * 10)) - 1)
    res += ':oe:' if percentage > 1 else ''
    return res


def generate_shorter_progress_bar(done: int, total: int) -> str:
    if total == 1:
        if done == 0:
            return ':es::ee:'
        else:
            return ':fs::fe:'
    remaining = total - done - (1 if done == 0 else 0)
    res = ':es:' if done == 0 else ':rs:' if done == 1 else ':fs:'
    res += ':fm:' * (done - 2)
    if done > 1 and done != total:
        res += ':rm:'
    res += ':em:' * (remaining - 1)
    res += ':fe:' if remaining == 0 else ':ee:'
    return res


def simplify_tasks(tasks: List[Task]) -> Dict[str, List[Task]]:
    tmp = map(lambda x: x.parent_id, tasks)
    return {x: [y for y in tasks if y.parent_id == x] for x in tmp}


def get_todoist(to_filter: Union[List[str], str, None] = None) -> TaskList:
    tlist = TaskList()
    global uncompleted_tasks, uncompleted_tasks_dict, to_del
    filter_str = 'today & @Discord' + (' & @'.join(to_filter) if isinstance(to_filter, list) else f' & @{to_filter}' if isinstance(to_filter, str) else '')
    uncompleted_tasks = sorted(api.get_tasks(filter=filter_str))

    completed_response = requests.get('https://api.todoist.com/sync/v9/completed/get_all', headers={"Authorization": f"Bearer {token}"}, params={"since": datetime.combine(date.today(), time()).isoformat(), "limit": 200})
    completed_tasks: List[Dict] = []
    if completed_response.status_code == 200:
        completed_tasks = completed_response.json().get('items', [])
        completed_tasks = list(map(lambda t: {'id': t['task_id'], 'project_id': t['project_id'], 'section_id': t.get('section_id'), 'initial': '@Initial' in t['content']}, filter(lambda y: '@Count' in y['content'], completed_tasks)))
    else:
        print(f"Error retrieving completed tasks: {completed_response.status_code}")
        print(completed_response.text)
    
    uncompleted_tasks_dict = simplify_tasks(uncompleted_tasks)
    for task in uncompleted_tasks_dict[None]:
        tlist.add_task(task.project_id, task.section_id, task)
    for task in completed_tasks:
        tlist.add_completed_task(task['id'], task['project_id'], task['section_id'], task['initial'])
    tlist.clean_list()
    return tlist


def is_start_of_day() -> bool:
    global is_connected
    if is_connected:
        try:
            return db_interface.get_last_update()
        except Exception:
            is_connected = False
            return is_start_of_day()
    return any(re.match(r'^20[0-9]{6}.txt$', f) and f != f"{today.strftime('%Y%m%d')}.txt" for f in next(os.walk(file_dir))[2])


def get_data() -> List[str]:
    ids = get_file()
    global is_connected
    if is_connected:
        try:
            if is_start_of_day():
                db_interface.delete_old_tasks()
                db_interface.set_last_update()
            else:
                ids = db_interface.get_tasks()
        except Exception:
            is_connected = False
    return ids


def get_file() -> List[str]:
    if is_start_of_day() or any(re.match(r'^20[0-9]{6}.txt$', f) and f != f"{today.strftime('%Y%m%d')}.txt" for f in next(os.walk(file_dir))[2]):
        for f in next(os.walk(file_dir))[2]:
            if re.match(r'^20[0-9]{6}.txt$', f) and f != f"{today.strftime('%Y%m%d')}.txt":
                os.remove(f)
        open(file_name, 'a')
    ids = open(file_name).read()
    if len(ids) > 0:
        return ids.split('\n')
    else:
        return []


def update_data(to_insert, to_delete):
    global is_connected
    if is_connected:
        try:
            db_interface.insert_new_tasks(to_insert)
        except Exception as e:
            pass
        if len(to_delete):
            db_interface.delete_tasks(to_delete)


def update_file(tlist: TaskList):
    open(file_name, 'w').write('\n'.join(tlist.list_task_ids()))
