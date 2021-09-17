from datetime import datetime, date
import TodoistUtils as tu
import CalendarUtils as cu
import os, json, platform

today = date.today()
utils = json.load(open('creds_and_info.json'))

lectureNameToCode = {
    "Sicurezza informatica": 'SEC',
    "Amministrazione di sistemi": 'LAS',
    "Ingegneria del software": 'SWE',
    "Progettazione di app web": 'PAW'
}

lectureCodeToName = {
    'SEC': "Sicurezza informatica",
    'LAS': "Amministrazione di sistemi",
    'SWE': "Ingegneria del software",
    'PAW': "Progettazione di app web"
}


class Lecture:
    def __init__(self, string):
        if 'p' in string:
            string = string[:string.index(' p')]
        elif '#' in string:
            string = string[:string.index(' #')]
        self.code = string[:3]
        self.name = lectureCodeToName[self.code]
        self.mode = string[4]
        self.isLab = self.mode == 'P'
        self.number = string.split(' ')[1][1:]


def addLectures():
    lectures = cu.getEvents([utils['class_cal']])[1]
    for l in lectures:
        lectureNumber = len(cu.getEvents([utils['class_cal']], start=datetime(2021, 2, 17), filt=l.name)[1])
        cmd = f"touch {utils['classes_parent_folder']}/{(l.name if 'LAB' not in l.name else l.name[4:]).title().replace(' ', '')}/{lectureNameToCode[l.name if 'LAB' not in l.name else l.name[4:]].lower()}/L{lectureNumber}.md"
        if 'LAB' not in l.name:
            if platform.platform().split('-')[0].lower() == 'macos':
                os.system(cmd)
            elif platform.platform().split('-')[0].lower() == 'linux':
                os.system(f"ssh {utils['mac_host']} '{cmd}'")
        addLectureTasks(l.name if 'LAB' not in l.name else l.name[4:], lectureNumber=lectureNumber, isLab='LAB' in l.name)


def addLectureTasks(name=None, lectureNumber=None, isLab=False):
    if name is None:
        name = input('Insert name of lecture: ')
    if lectureNumber is None:
        lectureNumber = input('Insert number of lecture: ')
    tu.addTask(f"{lectureNameToCode[name]} {'P' if isLab else 'L'}{lectureNumber}", utils['class_proj'], duedate=date.today(), section=name, labels=['Discord'])


def completeTask(name):
    print('\nCheck it off in Notion and add the lecture to the database!\n')
