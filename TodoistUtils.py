from datetime import date, datetime, timedelta
from todoist_api_python.api import TodoistAPI
import json, MyTodoist

utils = json.load(open('creds_and_info.json'))
token = utils['todoist_token']
api = TodoistAPI(token)
projectsDict = {project.name:project.id for project in api.get_projects()}


def get_project(name):
    return projectsDict.get(name, 0)


def get_all_projects():
    return projectsDict


def get_section(name, project_id):
    return get_all_sections(project_id).get(name, None)


def get_all_sections(project_id):
    return {s.name:s.id for s in list(filter(lambda s: s.project_id == project_id, api.get_sections()))}


def get_task_id_by_name(name):
    return next(filter(lambda t: name in t.content, api.get_tasks())).id


# def create_due_obj(due_date, due_time=None, is_recurring=False):
#     if due_time is None:
#         duestr = due_date.strftime('%d %b %Y')
#         due = {
#             "date": date.strftime(due_date, '%Y-%m-%d'),
#             "timezone": None,
#             "string": duestr,
#             "lang": "en",
#             "is_recurring": is_recurring
#         }
#         return due
#     else:
#         duedatetime = datetime.combine(due_date, due_time)
#         duestr = duedatetime.strftime('%d %b %Y at %I:%M %p')
#         due = {
#             "date": duedatetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
#             "timezone": "Europe/Rome",
#             "string": duestr,
#             "lang": "en",
#             "is_recurring": is_recurring
#         }
#         return due


def clear_started_tasks():
    ls = 'Started'
    tasks = MyTodoist.getTodoist(filter=[ls]).listTaskIDs()
    for id in tasks:
        t = api.get_task(id)
        t.labels.remove(ls)
        api.update_task(t.id, labels=t.labels)
