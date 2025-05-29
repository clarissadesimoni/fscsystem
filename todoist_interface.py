from datetime import datetime, date, time, timedelta
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task, ApiDue
from typing import Dict, Iterator, List, Tuple, Union
import backend, cla_utils
import math, requests, re
from functools import reduce

token = backend.utils['todoist_token']
api = TodoistAPI(token)
indent_offsets = {
    'project': 0,
    'section': 1,
    'task': lambda section_name, vc: 0 if vc else (2 if section_name else 1)
}
lsp = 'spread'
lls = 'lecturespread'
emotes_offset = 20
tab_to_spaces = 4
indent_str = ':blank:'

is_next_day = False

class MyCompletedTask:
    def __init__(self, tid: str, name: str, parent_id: Union[str, None] = None):
        self.id: str = tid
        self.name: str = name
        self.is_initial: bool = 'Initial' in name
        self.parent_id: Union[str, None] = parent_id
        self.duration = reduce(lambda a, b: a + b, map(int, filter(lambda label: label.isdigit(), self.name.split(' @')[1:])), 0)
        if self.duration == 0:
            self.duration = 60
        self.subtasks: List[MyCompletedTask] = [MyCompletedTask(el['id'] if el['id'] is not None else '', el['name'] if el['name'] is not None else '', el['parent_id']) for el in backend.completed_tasks_dict.get(self.id, list())]
    
    def completion_count(self, count_initial: bool = False):
        if len(self.subtasks):
            data = [s.completion_count() for s in self.subtasks]
            return [sum(d[0] for d in data), sum(d[1] for d in data)]
        else:
            return [1, int(self.is_initial) if not count_initial else 1]

    def completion_count_duration(self, count_initial: bool = False):
        if len(self.subtasks):
            data = [s.completion_count_duration() for s in self.subtasks]
            return [sum(d[0] for d in data), sum(d[1] for d in data)]
        else:
            return [self.duration, int(self.is_initial) * self.duration if not count_initial else self.duration]

    def list_task_ids(self) -> Dict[str, Union[str, None]]:
        res: Dict[str, Union[str, None]] = {}
        for st in self.subtasks:
            res.update(st.list_task_ids())
        res[self.id] = self.parent_id
        return res

class MyTask:
    def __init__(self, t: Task):
        self.id: str = t.id
        self.name: str = t.content
        self.parent_id: Union[str, None] = t.parent_id
        self.project_id: str = t.project_id
        self.section_id: Union[str, None] = t.section_id
        self.due: datetime = datetime.min
        self.recurring: bool = False
        if t.due is not None:
            self.due = t.due.date
            self.recurring: bool = t.due.is_recurring
        self.is_habit: bool = 'Habit' in t.labels
        self.is_count: bool = 'Count' in t.labels
        self.is_initial: bool = 'Initial' in t.labels
        self.is_split: bool = 'Split' in t.labels
        self.is_started: bool = 'Started' in t.labels
        self.priority: int = t.priority
        self.completed: bool = t.is_completed == 1 or (self.recurring and self.due.date() > backend.today)
        self.order: int = t.order
        self.completed_subtasks: List[MyTask] = [MyTask.obj_constructor(st) for st in backend.completed_tasks_dict.get(self.id, [])]
        # self.completed_subtasks: List[MyCompletedTask] = [MyCompletedTask(el['id'] if el['id'] is not None else '', el['name'] if el['name'] is not None else '', el['parent_id']) for el in backend.completed_tasks_dict.get(self.id, list())]
        self.subtasks: List[MyTask] = [MyTask.obj_constructor(st) for st in backend.uncompleted_tasks_dict.get(self.id, [])]
        self.duration = t.duration.amount # reduce(lambda a, b: a + b, map(int, filter(lambda label: label.isdigit(), t.labels)), 0)
        if self.duration == 0:
            self.duration = 60
        self.num_of_sub_to_print: int = len(list(filter(lambda s: not s.is_count, self.subtasks)))

    @classmethod
    def id_constructor(cls, tid: str):
        t = api.get_task(tid)
        return cls(t)

    @classmethod
    def obj_constructor(cls, t: Task):
        return cls(t)
    
    def completion_count(self, count_initial: bool = False) -> List[int]:
        if len(self.subtasks) or len(self.completed_subtasks):
            data = [s.completion_count(count_initial=count_initial) for s in self.subtasks] + [s.completion_count(count_initial=count_initial) for s in self.completed_subtasks]
            return [sum(d[0] for d in data), sum(d[1] for d in data)]
        else:
            return [int(self.is_split or self.completed), int(self.is_initial) if not count_initial else 1]
    
    def completion_count_duration(self, count_initial: bool = False) -> List[int]:
        if len(self.subtasks) or len(self.completed_subtasks):
            data = [s.completion_count_duration(count_initial=count_initial) for s in self.subtasks] + [s.completion_count_duration(count_initial=count_initial) for s in self.completed_subtasks]
            return [sum(d[0] for d in data), sum(d[1] for d in data)]
        else:
            return [int(self.completed) * self.duration, int(self.is_initial) * self.duration if not count_initial else self.duration]
    
    def bullet(self) -> str:
        emotes = {
            1: ':mdot_red',
            2: ':mdot_yellow',
            3: ':mdot_blue',
            4: ':mdot_grey'
        }
        done, total = self.completion_count(count_initial=True)
        if self.completed is True or (done >= total and not len(self.subtasks)):
            return ':mdot_greencomp: '
        elif self.is_habit is True:
            return ':mdot_lavenderstart: ' if self.is_started else ':mdot_lavender: '
        elif not self.is_initial:
            return ':mdot_rainbowstart: ' if self.is_started else ':mdot_rainbow: '
        elif self.is_started or 0 < done < total:
            return emotes[5 - self.priority] + 'start: '
        else:
            return emotes[5 - self.priority] + ': '
    
    def to_string(self, is_section_named: bool, level: int = 0, vc: bool = False, chat: bool = False, habits: bool = False) -> List[Tuple[str, int]]:
        self.subtasks.sort(key=lambda x: (int(x.completed), int(x.is_habit), -x.priority, x.due, x.order, int(x.name.split(' ')[-1]) if any(x.name.startswith(y) for y in ['PDF', 'Ex.', 'Es.']) else 0))
        comp = self.completion_count(count_initial=True)
        comp_dur = self.completion_count_duration(count_initial=True)
        completion = comp_dur[0] / comp_dur[1]
        pb = generate_progress_bar(completion) if (comp_dur[1] >= 10 or completion > 1) else generate_shorter_progress_bar(*comp_dur)
        if (matches := re.findall(r'([0-9][0-9]?:[0-9][0-9]:[0-9][0-9])', self.name)) and len(matches):
            for m in matches:
                self.name = self.name.replace(m, m.replace(':', '\\:'))
        if (matches := re.findall(r'\*', self.name)) and len(matches):
            for m in matches:
                self.name = self.name.replace(m, m.replace('*', '\*'))
        title = f'{self.bullet()}{self.name}' + (f' (Done: {comp[0]}/{comp[1]}, {mins_to_hour_mins(comp_dur[0])}/{mins_to_hour_mins(comp_dur[1])}: {comp_dur[0]/comp_dur[1] * 100:.2f}%) {pb}' if len(self.subtasks) or len(self.completed_subtasks) else f' ({mins_to_hour_mins(comp_dur[1])})')
        res: List[Tuple[str, int]] = [((indent_str * (indent_offsets['task'](is_section_named, (vc or chat or habits)) + level)) + title, ((pb.count(':') // 2) if len(self.subtasks) else 0) * (emotes_offset + 1) + len(title) + emotes_offset + ((indent_offsets['task'](is_section_named, (vc or chat or habits)) + level) * (emotes_offset + len(indent_str))) - (2 * title.count('~1')))]
        if self.num_of_sub_to_print > 0:
            for st in self.subtasks:
                if st.is_count:
                    continue
                res.extend(st.to_string(is_section_named, level + 1))
        return res
    
    def list_task_ids(self, completed: List[bool] = [False, True]) -> Dict[str, Union[str, None]]:
        res: Dict[str, Union[str, None]] = {}
        if False in completed:
            for st in self.subtasks:
                res.update(st.list_task_ids())
        if True in completed:
            for st in self.completed_subtasks:
                res.update(st.list_task_ids())
        res[self.id] = self.parent_id if self.parent_id is not None else False
        return res

class Section:
    def __init__(self, id: str):
        self.id: str = id
        self.name: str = api.get_section(id).name if id != '0' else 'No section'
        self.tasks: List[MyTask] = []
        self.completed_tasks: List[MyTask] = []
    
    def add_task(self, t: Union[Task, str]):
        if isinstance(t, str):
            self.tasks.append(MyTask.id_constructor(t))
        elif isinstance(t, Task):
            if t.is_completed:
                self.completed_tasks.append(MyTask.obj_constructor(t))
            else:
                self.tasks.append(MyTask.obj_constructor(t))
    
    def priority_dict(self) -> Dict[Union[str, int], int]:
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
    
    def list_task_ids(self, completed: List[bool] = [False, True]) -> Dict[str, Union[str, None]]:
        res: Dict[str, Union[str, None]] = {}
        if False in completed:
            for t in self.tasks:
                res.update(t.list_task_ids())
        if True in completed:
            for t in self.completed_tasks:
                res.update(t.list_task_ids())
        return res
    
    def completion_count(self) -> List[int]:
        data = [t.completion_count() for t in self.tasks] + [t.completion_count() for t in self.completed_tasks]
        return [sum(d[0] for d in data), sum(d[1] for d in data)]
    
    def completion_count_duration(self) -> List[int]:
        data = [t.completion_count_duration() for t in self.tasks] + [t.completion_count_duration() for t in self.completed_tasks]
        return [sum(d[0] for d in data), sum(d[1] for d in data)]
    
    def to_string(self, vc: bool = False, chat: bool = False, habits: bool = False) -> List[Tuple[str, int]]:
        res = []
        if not vc and not chat and not habits:
            comp_count = self.completion_count()
            comp_dur = self.completion_count_duration()
            comp = comp_dur[0] / comp_dur[1]
            pb = (" " + generate_progress_bar(comp)) if (comp_dur[1] >= 10 or comp > 1) else (" " + generate_shorter_progress_bar(*comp_dur)) if comp_count[1] > 1 else ""
            title = f'**SECTION: {self.name}** (Done: {comp_count[0]}/{comp_count[1]}, {mins_to_hour_mins(comp_dur[0])}/{mins_to_hour_mins(comp_dur[1])}: {comp:.2%}){pb}'
            res: List[Tuple[str, int]] = [((indent_str * indent_offsets['section']) + title, (pb.count(':') // 2) * emotes_offset + len(title) + (indent_offsets['section'] * (emotes_offset + len(indent_str))))] if self.id != '0' else []
        self.tasks.sort(key=lambda x: (int(x.completed), int(x.is_habit), -x.priority, x.due, x.order))
        for t in self.tasks:
            if t.is_split and not t.completed and all(s.completed for s in t.subtasks):
                continue
            res.extend(t.to_string(self.id != '0', 0, vc=vc, chat=chat, habits=habits))
        return res

class Project:
    def __init__(self, id: str):
        self.id = id
        self.name = api.get_project(id).name
        self.sections: Dict[str, Section] = {}
    
    def add_task(self, section_id: Union[str, None], t: Union[Task, MyCompletedTask, str]):
        if section_id is None:
            section_id = '0'
        if section_id not in self.sections.keys():
            self.sections[section_id] = Section(section_id)
        self.sections[section_id].add_task(t)
    
    def priority_dict(self) -> Dict[Union[str, int], int]:
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
    
    def list_task_ids(self, completed: List[bool] = [False, True]) -> Dict[str, Union[str, None]]:
        res: Dict[str, Union[str, None]] = {}
        for s in self.sections.values():
            res.update(s.list_task_ids())
        return res
    
    def completion_count(self) -> List[int]:
        data = [s.completion_count() for s in self.sections.values()]
        return [sum(d[0] for d in data), sum(d[1] for d in data)]
    
    def completion_count_duration(self) -> List[int]:
        data = [s.completion_count_duration() for s in self.sections.values()]
        return [sum(d[0] for d in data), sum(d[1] for d in data)]
    
    def to_string(self, completed: bool = False, vc: bool = False, chat: bool = False, habits: bool = False) -> List[Tuple[str, int]]:
        res = ''
        if not completed:
            comp_count = self.completion_count()
            comp_dur = self.completion_count_duration()
            comp = comp_dur[0] / comp_dur[1]
            pb = (" " + generate_progress_bar(comp)) if (comp_dur[1] >= 10 or comp > 1) else (" " + generate_shorter_progress_bar(*comp_dur)) if comp_count[1] > 1 else ""
            res = f'**PROJECT: {self.name}** (Done: {comp_count[0]}/{comp_count[1]}, {mins_to_hour_mins(comp_dur[0])}/{mins_to_hour_mins(comp_dur[1])}: {comp:.2%}){pb}'
        else:
            res = f'**PROJECT: {self.name}**'
        sec = sorted(self.sections.values(), key=lambda x: (x.priority_dict()[1], x.priority_dict()[2], x.priority_dict()[3], x.priority_dict()[4], x.priority_dict()['r']), reverse=True)
        res = [(res, (pb.count(':') // 2) * emotes_offset + len(res))]
        for s in sec:
            res.extend(s.to_string(vc=vc, chat=chat, habits=habits))
        return res

class TaskList:
    def __init__(self):
        self.projects: Dict[str, Project] = {}
    
    def add_task(self, project_id: str, section_id: Union[str, None], t: Union[Task, MyCompletedTask, str]):
        if project_id not in self.projects.keys():
            self.projects[project_id] = Project(project_id)
        self.projects[project_id].add_task(section_id, t)

    def projects_to_use(self):
        return sorted(self.projects.values(), key=lambda x: (x.priority_dict()[1], x.priority_dict()[2], x.priority_dict()[3], x.priority_dict()[4], x.priority_dict()['r']), reverse=True)
    
    def list_task_ids(self, completed: List[bool] = [False, True]) -> Dict[str, Union[str, None]]:
        res: Dict[str, Union[str, None]] = {}
        for p in self.projects.values():
            res.update(p.list_task_ids(completed=completed))
        return res
    
    def completion_count(self) -> List[int]:
        data = [p.completion_count() for p in self.projects.values()]
        return [sum(d[0] for d in data), sum(d[1] for d in data)]
    
    def completion_count_duration(self) -> List[int]:
        data = [p.completion_count_duration() for p in self.projects.values()]
        return [sum(d[0] for d in data), sum(d[1] for d in data)]

def mins_to_hour_mins(mins: int) -> str:
    if mins == 0:
        return '0m'
    return (f'{mins // 60}h' if mins >= 60 else '') + (f'{mins % 60}m' if mins % 60 > 0 else '')

def parse_api_due(dt: ApiDue) -> datetime:
    date_str = dt.date
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass
    raise ValueError(f"Unrecognized date format: {date_str}")

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

def simplify_tasks(tasks: List[Task]) -> Dict[Union[str, None], List[Task]]:
    tmp = map(lambda x: x.parent_id, tasks)
    return {x: [y for y in tasks if y.parent_id == x] for x in tmp}

def simplify_completed_tasks(tasks: List[Dict[str, Union[str, None]]]) -> Dict[Union[str, None], List[Dict[str, Union[str, None]]]]:
    tmp = map(lambda x: x['parent_id'], tasks)
    return {x: [y for y in tasks if y['parent_id'] == x] for x in tmp}

def retrieve_data():
    backend.tlist = TaskList()
    filter_str = '(due before: +1 day) & @Discord'
    tmp_task_list: Iterator[List[Task]] = api.filter_tasks(query=filter_str, limit=200)
    for page in tmp_task_list:
        backend.uncompleted_tasks += page
    backend.uncompleted_tasks = sorted(backend.uncompleted_tasks, key=lambda x: x.due.date)
    backend.uncompleted_tasks_dict = simplify_tasks(backend.uncompleted_tasks)
    start_date_completed_tasks = date.today() - timedelta(days=1) if is_next_day else date.today()
    tmp_task_list = api.get_completed_tasks_by_due_date(since=datetime.combine(start_date_completed_tasks, time(6, 0)), until=datetime.now(), limit=200)
    for page in tmp_task_list:
        backend.completed_tasks += page
    missing_parents = set(map(lambda t: t.id, backend.completed_tasks)).difference(set(backend.imported_task_data.keys()))
    missing_tasks = set(backend.imported_task_data.keys()).difference(set(map(lambda t: t.id, backend.completed_tasks))).difference({t.id for t in backend.uncompleted_tasks})
    for tid in missing_parents.union(missing_tasks):
        try:
            obj: Task = api.get_task(tid)
            backend.imported_task_data[tid] = obj.parent_id if isinstance(obj.parent_id, str) and len(obj.parent_id) else False
            backend.completed_tasks.append(obj)
        except:
            backend.tasks_to_delete.append(tid)
    backend.completed_tasks_dict = simplify_tasks(backend.completed_tasks)
    if None in backend.uncompleted_tasks_dict:
        for task in backend.uncompleted_tasks_dict[None]:
            backend.tlist.add_task(task.project_id, task.section_id if task.section_id else '0', task)
    if None in backend.completed_tasks_dict:
        for task in backend.completed_tasks_dict[None]:
            backend.tlist.add_task(task.project_id, task.section_id if task.section_id else '0', task)
    if False in backend.completed_tasks_dict:
        for task in backend.completed_tasks_dict[False]:
            backend.tlist.add_task(task.project_id, task.section_id if task.section_id else '0', task)
    return backend.tlist
