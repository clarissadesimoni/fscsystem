from datetime import datetime, date, time, timedelta
import SheetsUtils as su
import TodoistUtils as tu
import LectureUtils as lu
import CalendarUtils as cu
import utils, pyperclip, pytz, re, tasks, completed, studyverse, fsctodo
import requests as req

from todoist_api_python.api import TodoistAPI

token = utils['todoist_token']
today = date.today()
todayStr = today.strftime('%Y-%m-%d')
api = TodoistAPI(token)
api.sync()
isDone = False


def startOfDay():
    tu.clear_started_tasks()
    su.clearSheets()
    lu.addLectures()
    startWorking = datetime.combine(today, utils.safeInputTime('At what time did you wake up? ', True))
    coords = su.getCoordinates(today.day)['timesheetRange']
    su.fillInGaps(end=startWorking, startCell=f"{coords['cols'][0]}{coords['rows'][0]}", code='x')
    cu.insert('Sleep', datetime.combine(today, time()), startWorking)
    allDay, timed = cu.getEvents(list(set(cu.get_cal_names()) - {'Todoist', 'Daily tracking'}))
    print('All day events:\n' + '\n'.join([repr(e) for e in allDay]) + '\nTimed events:\n' + '\n'.join([repr(e) for e in sorted(timed, key=lambda e: e.start)]) + '\n\n')
    while not utils.safeInputBool('Have you planned the tasks on Todoist for the day? '):
        print('Do it now!')
    tasks.tasklist(utils.safeInputBool('Do you want to post your to-do list? '))
    if utils.safeInputBool('Do you want to post your tasks on Studyverse? '):
        studyverse.tasklist()
    if utils.safeInputBool('Do you want to post your tasks on FSC? '):
        fsctodo.tasklist()


def menu():
    global isDone
    actionsDict = [
        'Post your tasklist',
        'Post your completed tasks',
        'Post your tasks on FSC',
        'Post your tasks on Studyverse',
        'Participate in lecture',
        'Choose next task',
        'Create a task',
        'Complete a task',
        'View your stats',
        'Take a break',
        'See upcoming events',
        'Insert an event to the calendar',
        'Log stars',
        'Upgrade stage'
    ]
    if not hadBreakfast():
        actionsDict.append('Have breakfast')
    if hadBreakfast() and not hadLunch():
        actionsDict.append('Have lunch')
    if hadLunch() and not hadDinner():
        actionsDict.append('Have dinner')
    if hadDinner():
        actionsDict.append('End of day')
    proc = su.getProcrastinationTimes()
    if not len(proc):
        actionsDict.append('Start procrastinating')
    else:
        if len(proc[-1]) == 1:
            actionsDict.append('End procrastinating')
        else:
            actionsDict.append('Start procrastinating')
    actionsDict.sort()
    actionSelection = {str(i + 1):a for i, a in enumerate(actionsDict)}
    choice = utils.safeInputChoice(actionSelection.keys(), 'Choose your next action:\n\t' + '\n\t'.join([': '.join(item) for item in actionSelection.items()]) + '\n\tc: Fine\n', canExit='c')
    if choice == 'c':
        isDone = True
        return
    doChosenTask(actionSelection[choice])


def doChosenTask(choice):
    if choice == 'Post your tasklist':
        tasks.tasklist()
    elif choice == 'Post your completed tasks':
        completed.tasklist()
    elif choice == 'Post your tasks on Studyverse':
        studyverse.tasklist()
    elif choice == 'Post your tasks on FSC':
        fsctodo.tasklist()
    elif choice == 'Participate in lecture':
        attendLecture()
    elif choice == 'Choose next task':
        chooseNextTask()
    elif choice == 'Complete a task':
        completeTask()
    elif choice == 'Create a task':
        createTask()
    elif choice == 'View your stats':
        viewStats()
    elif choice == 'Have breakfast':
        haveBreakfast()
    elif choice == 'Have lunch':
        haveLunch()
    elif choice == 'Have dinner':
        haveDinner()
    elif choice == 'Take a break':
        haveBreak()
    elif choice == 'See upcoming events':
        getUpcomingEvents()
    elif choice == 'Insert an event to the calendar':
        addEvent()
    elif choice == 'Log stars':
        logStars()
    elif choice == 'Upgrade stage':
        upgradeStage()
    elif choice == 'Start procrastinating':
        startProcrastinating()
    elif choice == 'End procrastinating':
        endProcrastinating()
    elif choice == 'End of day':
        endOfDay()


def getUpcomingEvents():
    start, end = datetime.now(), datetime.combine(today + timedelta(days=1), time())
    if not utils.safeInputBool('Do you want to get your upcoming events for today? '):
        start = datetime.combine(utils.safeInputDate('Insert start date: '), utils.safeInputTime('Insert start time: '))
        end = datetime.combine(utils.safeInputDate('Insert end date: '), utils.safeInputTime('Insert end time: '))
    allDay, timed = cu.getEvents(start=start, end=end)
    print('All day events:\n' + '\n'.join([repr(e) for e in allDay]) + '\n\nUpcoming events:\n' + '\n'.join([repr(e) for e in sorted(timed, key=lambda f: f.start)]) + '\n\n')


def addEvent():
    name = input('Insert the name of the event: ')
    start = None
    end = None
    if utils.safeInputBool('Is it gonna be an all-day event? '):
        start = utils.safeInputDate('Insert start date: ')
        end = utils.safeInputDate('Insert end date: ')
    else:
        start = datetime.combine(utils.safeInputDate('Insert start date: ', returnObj=True), utils.safeInputTime('Insert start time: ', returnObj=True))
        end = datetime.combine(utils.safeInputDate('Insert end date: ', returnObj=True), utils.safeInputTime('Insert end time: ', returnObj=True))
    calName = utils.safeInputChoice(cu.get_cal_names(), 'Insert the name of the calendar: (available: ' + ', '.join(cu.get_cal_names()) + ')\n')
    cu.insert(name, start, end, calendar_name=calName)


def startProcrastinating():
    proc = su.getProcrastinationTimes()
    proc.append([utils.safeInputTime('When did you start procrastinating? ')])
    su.insertActivities('Procrastination', proc)


def endProcrastinating():
    proc = su.getProcrastinationTimes()
    proc[-1].append(utils.safeInputTime('When did you end procrastinating? '))
    su.insertActivities('Procrastination', proc)


def isTaskAlreadyStarted(idTask):
    data = su.getActivities('TodoistInProgress')
    data = {d[0]:int(d[1]) for d in data}
    return data.get(idTask, -1)


def chooseNextTaskTodoist():
    api.sync()
    tasks = []
    if utils.safeInputBool('Do you want to filter task by one or more labels? '):
        labels = []
        availableLabels = list(tu.getAllLabels().keys())
        labels.append(utils.safeInputChoice(availableLabels, 'These are the available labels: ' + ', '.join(availableLabels) + '\n'))
        availableLabels.remove(labels[-1])
        while utils.safeInputBool('Do you want to filter task by more labels? ') and len(availableLabels):
            labels.append(utils.safeInputChoice(availableLabels, 'These are the available labels: ' + ', '.join(availableLabels) + '\n'))
            availableLabels.remove(labels[-1])
        tasks = getUncompletedTasks(labels)
        if not len(tasks):
            print('There are no tasks to start following these criteria.')
            return
    else:
        tasks = getUncompletedTasks()
        if not len(tasks):
            print('There are no tasks to start following these criteria.')
            return
    if utils.safeInputBool('Do you want to filter task by a project? '):
        pid = tu.get_project(utils.safeInputChoice(tu.get_all_projects(), 'Insert the project name: '))
        tasks = list(filter(lambda t: t.project == pid, tasks))
        if not len(tasks):
            print('There are no tasks to start following these criteria.')
            return
        if utils.safeInputBool('Do you want to filter task by a section? '):
            sid = tu.get_section(utils.safeInputChoice(tu.get_all_sections(pid), 'Insert the section name: '), pid)
            tasks = list(filter(lambda t: t.section == sid, tasks))
            if not len(tasks):
                print('There are no tasks to start following these criteria.')
                return
    tasks.sort(key=lambda t: (t.priority, t.due))
    taskSelection = {str(i + 1):t for i, t in enumerate(tasks)}
    choice = taskSelection[utils.safeInputChoice(taskSelection.keys(), '\nChoose your next task:\n\t' + '\n\t'.join([': '.join([k, v.name]) for k, v in taskSelection.items()]) + '\n')]
    toUpdate = api.items.get_by_id(choice.id)
    data = su.getActivities('Todoist')
    nextTask = [choice.name, choice.id, utils.safeInputTime('At what time did you start the task? ')]
    data.append(nextTask)
    su.insertActivities('Todoist', data)
    toUpdate.update(labels=choice.labels + [tu.getLabel('Started')])
    api.commit()


def chooseNextTaskSheets():
    tasks = su.getActivities('Sheets')
    tasks = list(filter(lambda t: len(t) == 1, tasks))
    if not len(tasks):
        print('There are no tasks to start.')
        return
    taskSelection = [e[0] for e in tasks]
    taskSelection.sort()
    taskSelection = {str(i + 1):t for i, t in enumerate(taskSelection)}
    choice = taskSelection[utils.safeInputChoice(taskSelection.keys(), '\nChoose your next task:\n\t' + '\n\t'.join([': '.join([k, v]) for k, v in taskSelection.items()]) + '\n')]
    tasks.remove([choice])
    tasks.append([choice, utils.safeInputTime('At what time did you start the task? ')])
    su.insertActivities('Sheets', tasks)


def chooseNextTaskCalendar():
    events = cu.getEvents(list(set(cu.get_cal_names()) - {'Todoist', 'Daily tracking'}))[1]
    events = {repr(e):e for e in events}
    eventsSelection = list(events.keys())
    eventsSelection.sort(key=lambda e: events[e].start)
    eventsSelection = {str(i + 1):t for i, t in enumerate(eventsSelection)}
    choice = eventsSelection[utils.safeInputChoice(eventsSelection.keys(), '\nChoose your next task:\n\t' + '\n\t'.join([': '.join([k, v]) for k, v in eventsSelection.items()]) + '\n')]
    ev = events[choice]
    if utils.safeInputBool(f"Did you start the task at {ev.start.strftime('%H:%M')}? "):
        start = ev.start.strftime('%H:%M')
    else:
        start = utils.safeInputTime('Insert the right time: ')
    su.insertActivities('Calendar', su.getActivities('Calendar') + [[ev.name, ev.calId, ev.id, start]])


def chooseNextTask():
    if utils.safeInputBool('Do you want to choose it from Todoist? '):
        chooseNextTaskTodoist()
    elif utils.safeInputBool('Do you want to choose it from Calendar? '):
        chooseNextTaskCalendar()
    else:
        chooseNextTaskSheets()
            

def createTaskTodoist(name):
    api.sync()
    project_id = 0
    section_id = 0
    if utils.safeInputBool('Do you want to assign it to a project? '):
        project_id = tu.get_project(utils.safeInputChoice(tu.get_all_projects().keys(), f"Insert the name of the project (available: {', '.join(tu.get_all_projects().keys())}): "))
        if len(tu.get_all_sections(project_id)):
            if utils.safeInputBool('Do you want to assign it to a section? '):
                section_id = tu.get_section(utils.safeInputChoice(tu.get_all_sections(project_id).keys(), f"Insert the name of the section (available: {', '.join(tu.get_all_sections(project_id).keys())}): "), project_id)
    labels = []
    due = None
    priority = 4
    startTime = ''
    if utils.safeInputBool('Do you want to add any labels? '):
        availableLabels = list(tu.getAllLabels().keys())
        labels.append(utils.safeInputChoice(availableLabels, 'These are the available labels: ' + ', '.join(availableLabels) + '\n'))
        availableLabels.remove(labels[-1])
        while utils.safeInputBool('Do you want to add any more labels? ') and len(availableLabels):
            labels.append(utils.safeInputChoice(availableLabels, 'These are the available labels: ' + ', '.join(availableLabels) + '\n'))
            availableLabels.remove(labels[-1])
    labels = [tu.getLabel(l) for l in labels]
    if utils.safeInputBool('Do you want to assign a due date? '):
        duedate = utils.safeInputDate('Insert the date: ', returnObj=True)
        duetime = None
        if utils.safeInputBool('Do you want to add a time? '):
            duetime = utils.safeInputTime('Insert the time: ', returnObj=True)
        due = tu.create_due_obj(duedate, due_time=duetime)
    if utils.safeInputBool('Do you want to set a priority? '):
        priority = utils.safeInputInt(list(range(1, 5)), 'Insert a number between 1 and 4: ')
    if utils.safeInputBool('Have you started the task? '):
        startTime = utils.safeInputTime('Insert the time you started the task: ')
        labels.append(tu.getLabel('Started'))
    api.items.add(name, project_id=project_id, due=due, priority=(5 - priority), section_id=section_id, labels=labels)
    api.commit()
    task = list(filter(lambda t: t['content'] == name, api.state['items']))[-1]
    toWrite = [[task['content'], task['id'], startTime]]
    if not len(toWrite[0][-1]):
        toWrite.pop()
    su.insertActivities('Todoist', su.getActivities('Todoist') + toWrite)


def createTaskSheets(name):
    data = su.getActivities('Sheets')
    toWrite = [name]
    if utils.safeInputBool('Have you started the task? '):
        toWrite.append(utils.safeInputTime('Insert the time you started the task: '))
    data.append(toWrite)
    su.insertActivities('Sheets', data)


def createTask():
    name = input('Insert the name of the task: ')
    if utils.safeInputBool('Do you want to add it to Todoist? '):
        createTaskTodoist(name)
    else:
        createTaskSheets(name)


def shiftPriorities():
    tasks = getUncompletedTasks()
    lh = tu.getLabel('Habit')
    if any(t.priority == 1 for t in tasks):
        print("There's already a task that is first priority")
        return
    else:
        second = list(filter(lambda t: t.priority == 2, tasks))
        third = list(filter(lambda t: t.priority == 3, tasks))
        fourth_tmp = list(filter(lambda t: t.priority == 4 and lh not in t.labels, tasks))
        fourth_tmp = {str(i + 1):t for i, t in enumerate(fourth_tmp)}
        fourth = []
        if len(fourth_tmp):
            choice = utils.safeInputChoice(fourth_tmp.keys(), 'Choose the new third priority task:\n\t' + '\n\t'.join([f"{k}: {v.name}" for k, v in fourth_tmp.items()]) + ' \n')
            fourth.append(fourth_tmp[choice])
            del fourth_tmp[choice]
            while utils.safeInputBool('Do you want to add more tasks? '):
                fourth_tmp = {str(i + 1):t for i, t in enumerate(list(fourth_tmp.values()))}
                choice = utils.safeInputChoice(fourth_tmp.keys(), 'Choose the new third priority task:\n\t' + '\n\t'.join([f"{k}: {v.name}" for k, v in fourth_tmp.items()]) + ' \n')
                fourth.append(fourth_tmp[choice])
                del fourth_tmp[choice]
        toUpdate = second + third + fourth
        for t in toUpdate:
            t.priority -= 1
            task = api.items.get_by_id(t.id)
            task.update(priority=5 - t.priority)
        api.commit()


def completeTaskTodoist():
    api.sync()
    tasksData = su.getActivities('Todoist')
    if not len(tasksData):
        print('There are no tasks to complete.')
        return
    tasksData.sort(key=lambda t: t[0])
    taskSelection = {str(i + 1):t for i, t in enumerate(tasksData)}
    choice = utils.safeInputChoice(taskSelection.keys(), 'Choose the task:\n\t' + '\n\t'.join([': '.join([k, v[0]]) for k, v in taskSelection.items()]) + '\n')
    choice = taskSelection[choice]
    choice[1] = int(choice[1])
    mytask = tu.MyTask(choice[1])
    isAlreadyStarted = isTaskAlreadyStarted(mytask.id)
    isFinished = utils.safeInputBool("Did you finish the whole task? ")
    if not isFinished and isAlreadyStarted < 0:
        mytask.name += " #1"
        tmp = su.getActivities('TodoistInProgress')
        tmp.append([str(mytask.id), str(max([isAlreadyStarted + 1, 1]))])
        su.insertActivities('TodoistInProgress', tmp)
    if isAlreadyStarted >= 0:
        mytask.name += f" #{isAlreadyStarted + 1}"
        tmp = su.getActivities('TodoistInProgress')
        if not isFinished:
            for i in range(len(tmp)):
                if tmp[i][0] == mytask.id:
                    tmp[i][1] = str(int(tmp[i][1]) + 1)
                    break
        su.insertActivities('TodoistInProgress', tmp)
    if isAlreadyStarted and isFinished:
        tmp = su.getActivities('TodoistInProgress')
        for i in range(len(tmp)):
            if tmp[i][0] == mytask.id:
                tmp.pop(i)
                break
        su.insertActivities('TodoistInProgress', tmp)
    labels = mytask.labels
    if tu.getLabel('Started') in labels:
        labels.remove(tu.getLabel('Started'))
    tasksData.remove(choice)
    if re.match(r'[LPS][AEW][CESW]\s[LP][0-9]{1,2}', mytask.name) and isFinished:
        lu.completeTask(mytask.name)
    cet = pytz.timezone('Europe/Rome')
    start = cet.localize(datetime.combine(today, time.fromisoformat(choice[-1])))
    end = cet.localize(datetime.combine(today, utils.safeInputTime('Insert the time of completion: ', returnObj=True)))
    proc = su.getProcrastinationTimes()
    if len(proc):
        proc.insert(0, [start.time().isoformat()])
        proc.append([end.time().isoformat()])
        for i in range(len(proc) - 1):
            cu.addActivity(f"{mytask.name.replace('#', 'p')}{('.' if '#' in mytask.name else ' p')}{i + 1}", datetime.combine(today, time.fromisoformat(proc[i][-1])), datetime.combine(today, time.fromisoformat(proc[i + 1][0])))
    else:
        cu.addActivity(mytask.name, start, end)
    su.clearProcrastinationTimes()
    su.insertActivities('Todoist', tasksData)
    if utils.safeInputBool('Do you want to add it to Sheets? '):
        su.addActivity(name=mytask.name.replace('#', 'p'), start=start, end=end)
    task = api.items.get_by_id(choice[1])
    task.update(labels=labels)
    api.commit()
    if isFinished:
        try:
            task.close()
        except:
            print('\nCheck off this task in Todoist!\n')
    api.commit()
    if isFinished:
        if utils.safeInputBool('Do you want to shift priorities? '):
            shiftPriorities()
    tasks.tasklist(utils.safeInputBool('Do you want to update your Discord tasklist? '))


def completeTaskSheets():
    tasksData = su.getActivities('Sheets')
    if not len(tasksData):
        print('There are no tasks to complete.')
        return
    tasksData.sort(key=lambda t: t[0])
    taskSelection = {str(i + 1):t for i, t in enumerate(tasksData)}
    choice = utils.safeInputChoice(taskSelection.keys(), 'Choose the task:\n\t' + '\n\t'.join([': '.join([k, v[0]]) for k, v in taskSelection.items()]) + '\n')
    choice = taskSelection[choice]
    tasksData.remove(choice)
    su.insertActivities('Sheets', tasksData)
    start = datetime.combine(today, time.fromisoformat(choice[-1]))
    end = datetime.combine(today, utils.safeInputTime('Insert the time of completion: ', returnObj=True))
    proc = su.getProcrastinationTimes()
    if len(proc):
        proc.insert(0, [start.isoformat()])
        proc.append([end.isoformat()])
        for i in range(len(proc) - 1):
            cu.addActivity(f'{choice[0]} p{i + 1}', time.fromisoformat(proc[i][-1]), time.fromisoformat(proc[i + 1][0]))
    else:
        cu.addActivity(choice[0], start, end)
    su.clearProcrastinationTimes()
    su.addActivity(name=choice[0], start=start, end=end)


def completeTaskCalendar():
    tasksData = su.getActivities('Calendar')
    if not len(tasksData):
        print('There are no tasks to complete.')
        return
    tasksData.sort(key=lambda t: t[0])
    taskSelection = {str(i + 1):t for i, t in enumerate(tasksData)}
    choice = utils.safeInputChoice(taskSelection.keys(), 'Choose the task:\n\t' + '\n\t'.join([': '.join([k, v[0]]) for k, v in taskSelection.items()]) + '\n')
    choice = taskSelection[choice]
    tasksData.remove(choice)
    su.insertActivities('Calendar', tasksData)
    start = datetime.combine(today, time.fromisoformat(choice[-1]))
    start = pytz.timezone('Europe/Rome').localize(start)
    ev = cu.getEvent(choice[1], choice[2])
    if utils.safeInputBool(f"Did you end at {ev.end.strftime('%H:%M')}? "):
        end = ev.end
    else:
        end = datetime.combine(today, utils.safeInputTime('Insert the right time: ', returnObj=True))
        end = pytz.timezone('Europe/Rome').localize(end)
    proc = su.getProcrastinationTimes()
    if len(proc):
        proc.insert(0, [start.isoformat()])
        proc.append([end.isoformat()])
        for i in range(len(proc) - 1):
            cu.addActivity(f'{choice[0]} p{i + 1}', time.fromisoformat(proc[i][-1]), time.fromisoformat(proc[i + 1][0]))
    else:
        cu.addActivity(choice[0], start, end)
    su.clearProcrastinationTimes()
    su.addActivity(data=[choice[0], (end - start).seconds // 60, su.getCategoryCode(utils.safeInputChoice(su.getAllCategoryNames(), 'Insert the category: '))], start=start, end=end)


def completeTask():
    if utils.safeInputBool('Do you want to choose it from Todoist? '):
        completeTaskTodoist()
    elif utils.safeInputBool('Do you want to choose it from Calendar? '):
        completeTaskCalendar()
    else:
        completeTaskSheets()
    print(f'Current procrastination time: {utils.getDuration(cu.getProcrastinationTime())}')


def attendLecture():
    lectureEvents = cu.getEvents(['University timetable'])[1]
    lectureEvents.sort(key=lambda e: e.start)
    taskSelection = {str(i + 1):t for i, t in enumerate(lectureEvents)}
    choice = utils.safeInputChoice(taskSelection.keys(), 'Choose the task:\n\t' + '\n\t'.join([': '.join([k, v.name]) for k, v in taskSelection.items()]) + '\n')
    choice = taskSelection[choice]
    choice.name = choice.name[4:] if 'LAB' in choice.name else choice.name
    su.addActivity(data=[choice.name, (choice.end - choice.start).seconds // 60, su.getCategoryCode('classes')], start=choice.start, end=choice.end)
    cu.addActivity(name = choice.name, start=choice.start, end=choice.end)


def logStars():
    su.logStars()


def upgradeStage():
    su.upgradeStage()


def viewStats():
    su.viewStats()
    print(f'Current procrastination time: {utils.getDuration(cu.getProcrastinationTime())}')


def getUncompletedTasks(labels=None):
    return tu.getTodoist(filter=labels).getUncompletedTasks()


def hadBreakfast():
    return su.hadBreakfast()


def haveBreakfast():
    su.haveBreakfast()


def hadLunch():
    return su.hadLunch()


def haveLunch():
    su.haveLunch()


def hadDinner():
    return su.hadDinner()


def haveDinner():
    su.haveDinner()


def haveBreak():
    start = datetime.combine(today, utils.safeInputTime('When did you start the break? ', returnObj=True))
    end = datetime.combine(today, utils.safeInputTime('When did you end the break? ', returnObj=True))
    su.addToTimesheet(start=start, end=end, code='b')
    cu.insert('Break', start, end)


def endOfDay():
    su.fillInGaps(end=datetime.combine(today + timedelta(days=1), time(hour=0, minute=0)), code='x')
    cu.addActivity('Sleep', cu.getLastEventEndTime(datetime.combine(today + timedelta(days=1), time())), datetime.combine(today + timedelta(days=1), time()))
    daily = su.getDailyPoms()
    print(f'={daily} studying')
    pyperclip.copy(f'={daily} studying')
    input('Press enter to continue...')
    completed.tasklist()
    for task in tu.getTodoist().getUncompletedTasks():
        if task.recurring:
            api.items.get_by_id(task.id).close()
        else:
            tu.postpone_task(task.id, tu.create_due_obj(today + timedelta(days=1)))
    api.commit()


if __name__ == '__main__':
    if su.isStartOfDay():
        startOfDay()
    while not isDone:
        menu()
