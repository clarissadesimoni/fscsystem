from datetime import date, datetime, timedelta
from todoist.api import TodoistAPI
import json, MyTodoist

utils = json.load(open('creds_and_info.json'))
token = utils['todoist_token']
api = TodoistAPI(token)
api.sync()
labelsDict = {label['name']:label['id'] for label in api.state['labels']}
projectsDict = {project['name']:project['id'] for project in api.state['projects']}


def getLabel(name):
    return labelsDict[name]


def getAllLabels():
    return labelsDict


def getProject(name):
    return projectsDict.get(name, 0)


def getAllProjects():
    return projectsDict


def getSection(name, project_id):
    return getAllSections(project_id).get(name, None)


def getAllSections(project_id):
    return {s['name']:s['id'] for s in list(filter(lambda s: s['project_id'] == project_id, api.state['sections']))}


def getTaskIdByName(name):
    api = TodoistAPI(token)
    api.sync()
    res = list(filter(lambda t: name in MyTodoist.getItemAttribute(t, 'content') and not MyTodoist.getItemAttribute(t, 'checked') and isinstance(MyTodoist.getItemAttribute(t, 'id'), int), api.state['items']))
    return res[0]['id']


def createDueObj(duedate, duetime=None, is_recurring=False):
    if duetime is None:
        duestr = duedate.strftime('%d %b %Y')
        due = {
            "date": date.strftime(duedate, '%Y-%m-%d'),
            "timezone": None,
            "string": duestr,
            "lang": "en",
            "is_recurring": is_recurring
        }
        return due
    else:
        duedatetime = datetime.combine(duedate, duetime)
        duestr = duedatetime.strftime('%d %b %Y at %I:%M %p')
        due = {
            "date": duedatetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "timezone": "Europe/Rome",
            "string": duestr,
            "lang": "en",
            "is_recurring": is_recurring
        }
        return due


def clearStartedTasks():
    ls = 'Started'
    tasks = MyTodoist.getTodoist(filter=[ls]).listTaskIDs()
    for id in tasks:
        item = api.items.get(id)
        labels = item.get('labels', item.get('item').get('labels'))
        labels.remove(getLabel(ls))
        item.update(labels=labels)
        api.commit()


def addTask(name, description='', project=None, duedate=None, duetime=None, priority=None, section=None, labels=[]):
    if duedate is not None:
        api.items.add(name, description=description, project_id=getProject(project), due=createDueObj(duedate, duetime), priority=priority, section_id=getSection(section, getProject(project)), labels=[getLabel(l) for l in labels])
    else:
        api.items.add(name, description=description, project_id=getProject(project), priority=priority, section_id=getSection(section, getProject(project)), labels=[getLabel(l) for l in labels])
    api.commit()


def postponeTask(tid, dueObj):
    task = api.items.get_by_id(tid)
    task.update(due=dueObj)
    api.commit()
