import utils
import CalendarUtils as cu
from datetime import datetime, date, timedelta
import pickle, re, json
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

today = date.today()
info_utils = json.load(open('creds_and_info.json'))

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
sheetIds = info_utils['sheetIds']
sheetNames = {
    'challenge': today.strftime('%B') + '!',
    'mine': today.strftime('%B') + ' time tracker!',
    'fight': 'PhoenixFighter!',
    'friends': 'Friends!'
}
summarySheet = "'Poms Tracker'"
credFile = 'credsSheets.json'
tokenFile = 'tokenSheets.pickle'
challengeFirstRow = 22
challengeLastRow = 113
categories = {}

firstDay = date(today.year, today.month, 1)
while int(firstDay.strftime('%w')) != 1:
    firstDay += timedelta(days=1)
firstDay -= timedelta(days=7)
offset = (date(today.year, today.month, 1) - firstDay).days

colNames = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ', 'AK', 'AL', 'AM', 'AN', 'AO', 'AP', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AV', 'AW', 'AX', 'AY', 'AZ', 'BA', 'BB', 'BC', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ', 'BK', 'BL', 'BM', 'BN', 'BO', 'BP', 'BQ', 'BR', 'BS', 'BT', 'BU', 'BV', 'BW', 'BX', 'BY', 'BZ', 'CA', 'CB', 'CC', 'CD', 'CE', 'CF', 'CG', 'CH', 'CI', 'CJ', 'CK', 'CL', 'CM', 'CN', 'CO', 'CP', 'CQ', 'CR', 'CS', 'CT', 'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DA', 'DB', 'DC', 'DD', 'DE', 'DF', 'DG', 'DH', 'DI', 'DJ', 'DK', 'DL', 'DM', 'DN', 'DO', 'DP', 'DQ', 'DR', 'DS', 'DT', 'DU', 'DV', 'DW', 'DX', 'DY', 'DZ']

class Activity:
    def __init__(self, data=None, name=None, code=None, start=None, end=None):
        if data is not None:
            self.name, self.duration, self.code = data
        else:
            if name is None:
                self.name = input('Insert name of activity: ')
            else:
                self.name = name
            if code is None:
                self.code = categories['mine'][utils.safeInputChoice(categories['mine'].keys(), 'Insert the category: ')]
            else:
                self.code = code
            if start is None:
                start = datetime.combine(today, utils.safeInputTime('Insert the start time: ', True))
            self.start = start
            if end is None:
                end = datetime.combine(today, utils.safeInputTime('Insert the end time: ', True))
            self.end = end
            self.duration = end - start
            self.duration = self.duration.seconds // 60
    
    def __repr__(self):
        return f"Activity(data=[{self.name}, {self.duration}, {self.code}])"
    
    def __str__(self):
        return f"{self.name};{self.duration};{self.code}"
    
    def sheetValues(self):
        return [self.name, self.duration, self.code]
    
    def sheetStart(self):
        rem = self.start.minute % 10
        if rem <= 5:
            return self.start - timedelta(minutes=rem)
        else:
            return self.start + timedelta(minutes=rem)
    
    def sheetEnd(self):
        rem = self.end.minute % 10
        if rem <= 5:
            return self.end - timedelta(minutes=rem)
        else:
            return self.end + timedelta(minutes=rem)
    
    def addDuration(self, start=None, end=None):
        if start is None:
            start = datetime.combine(today, utils.safeInputTime('Insert the start time: ', True))
        self.start = start
        if end is None:
            end = datetime.combine(today, utils.safeInputTime('Insert the end time: ', True))
        self.end = end
        tmp = end - start
        self.duration += (tmp.seconds // 60)


def getSheets():
    creds = None
    if os.path.exists(tokenFile):
        with open(tokenFile, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                flow = InstalledAppFlow.from_client_secrets_file(credFile, SCOPES)
                creds = flow.run_console()
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credFile, SCOPES)
            creds = flow.run_console()
        with open(tokenFile, 'wb') as token:
            pickle.dump(creds, token)

    return build('sheets', 'v4', credentials=creds).spreadsheets()


sheets = getSheets()


def getCoordinates(day=today.day, firstDay=offset):
    day += firstDay - 1
    actColIndex = day % 7
    actColIndex = 9 + actColIndex * 17
    actRowIndex = day // 7
    actRowIndex = 5 + actRowIndex * 27
    numActivities = int(sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=f"{sheetNames['mine']}{colNames[actColIndex + 2]}{actRowIndex - 1}").execute().get('values', [])[0][0])
    timesheetRange = {
        'cols': colNames[actColIndex - 7:actColIndex - 1],
        'rows': [i for i in range(actRowIndex - 2, actRowIndex + 22)]
    }
    activities = {
        'nameCol': colNames[actColIndex],
        'valueCol': colNames[actColIndex + 1],
        'codeCol': colNames[actColIndex + 2],
        'startRow': actRowIndex,
        'currentRow': actRowIndex + numActivities,
        'endRow': actRowIndex + 11,
        'colIndex': actColIndex
    }
    pomsheetRange = {
        'startRow': 6 + (day // 7) * 15,
        'currentRow': 6 + numActivities + (day // 7) * 15,
        'endRow': 17 + (day // 7) * 15,
        'catCol': colNames[1 + (day % 7) * 4],
        'nameCol': colNames[2 + (day % 7) * 4],
        'valueCol': colNames[3 + (day % 7) * 4]
    }
    sumCell = f"{activities['valueCol']}{activities['startRow'] - 1}"
    return {
        'timesheetRange': timesheetRange,
        'timesheetFirstFreeCell': f"{colNames[actColIndex - 1]}{timesheetRange['rows'][0]}",
        'pomsheetRange': pomsheetRange,
        'hadBreakfast': f"{colNames[actColIndex + 3]}{activities['endRow'] + 10}",
        'hadLunch': f"{colNames[actColIndex + 4]}{activities['endRow'] + 10}",
        'hadDinner': f"{colNames[actColIndex + 6]}{activities['endRow'] + 10}",
        'activities': activities,
        'catQty': f"{colNames[actColIndex + 2]}{activities['startRow'] - 2}",
        'catNameCol': f"{colNames[actColIndex + 3]}",
        'catCodeCol': f"{colNames[actColIndex + 4]}",
        'sumCell': sumCell
    }


def calculateRange(startRow, startCol, endRow, endCol):
    return f'{startCol}{startRow}:{endCol}{endRow}'


myCategoryQuantity = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=sheetNames['mine'] + getCoordinates()['catQty']).execute().get('values', [])
coordinates = getCoordinates()
try:
    myCategoryQuantity = int(myCategoryQuantity[0][0])
except:
    myCategoryQuantity = 6
categories['mine'] = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=sheetNames['mine'] + calculateRange(coordinates['activities']['startRow'] - 1, coordinates['catNameCol'], coordinates['activities']['startRow'] + myCategoryQuantity - 1, coordinates['catCodeCol'])).execute().get('values', [])
categories['mine'] = {c[0]:c[1] for c in categories['mine']}
categories['challenge'] = []
categories['challenge'] = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range='Categories!B6:B30', majorDimension='COLUMNS').execute().get('values', [])
if len(categories['challenge']):
    categories['challenge'] = categories['challenge'][0]


def getOffset(day=date.today()):
    start = date(2021, 4, 1)
    td = day - start
    return str(challengeFirstRow + 1 + td.days)


def logStars():
    stage, streak, lastLog = sheets.values().get(spreadsheetId=sheetIds['Database'], range=sheetNames['fight'] + 'A1:C1').execute().get('values', [])[0]
    levelup = {
        '1': 14,
        '2': 21,
        '3': 28
    }
    grace = {
        '1': 1,
        '2': 2,
        '3': 3
    }
    streak = int(streak)
    def due(over):
        print(f"You're {'over' if over else ''}due for a level-up!")
    if streak >= levelup[stage]:
        due(streak >= levelup[stage])
    streak = streak + 1 if datetime.strptime(lastLog, '%d/%m/%Y').date() + timedelta(days=grace[stage] + 1) >= date.today() else 1
    if streak >= levelup[stage]:
        due(streak >= levelup[stage])
    sheets.values().update(spreadsheetId=sheetIds['Database'], range=sheetNames['fight'] + 'A1:C1', body={"range": sheetNames['fight'] + 'A1:C1', "values": [[stage, str(streak), date.today().strftime('%d/%m/%Y')]]}, valueInputOption='USER_ENTERED').execute()


def upgradeStage():
    stage = sheets.values().get(spreadsheetId=sheetIds['Database'], range=sheetNames['fight'] + 'stage').execute().get('values', [])[0][0]
    sheets.values().update(spreadsheetId=sheetIds['Database'], range=sheetNames['fight'] + 'A1:C1', body={"range": sheetNames['fight'] + 'A1:C1', "values": [[int(stage) + 1, 0, date.today().strftime('%d/%m/%Y')]]}, valueInputOption='USER_ENTERED').execute()


def getMyLoggedActivitiesDict(timesheet=None):
    if timesheet is None:
        timesheet = getCoordinates()
    activities = timesheet['activities']
    try:
        lst = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=f"{sheetNames['mine']}{activities['nameCol']}{activities['startRow']}:{activities['codeCol']}{activities['endRow']}").execute().get('values', [])
        return {i:item for i, item in enumerate(lst)}
    except:
        return dict()


def getChallengeLoggedActivitiesDict(timesheet=None):
    if timesheet is None:
        timesheet = getCoordinates()
    pomsheetRange = timesheet['pomsheetRange']
    try:
        lst = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=f"{sheetNames['challenge']}{pomsheetRange['nameCol']}{pomsheetRange['startRow']}:{pomsheetRange['valueCol']}{pomsheetRange['endRow']}").execute().get('values', [])
        return {i:item for i, item in enumerate(lst)}
    except:
        return dict()


def compressActivities(prev, name):
    
    class LectureParser:
        def __init__(self, string):
            self.strItems = string.split(' ')
            for i in range(len(self.strItems) - 1):
                if self.strItems[i][-1] == ',':
                    self.strItems[i:i + 2] = [self.strItems[i] + ' ' + self.strItems[i + 1]]
            if 'AR' in self.strItems:
                self.strItems[2:4] = [self.strItems[2] + ' ' + self.strItems[3]]
    
    prev = LectureParser(prev).strItems
    name = LectureParser(name).strItems
    res = []
    for i in range(min(len(prev), len(name))):
        if prev[i] == name[i]:
            res.append(name[i])
        else:
            if i >= 2 and prev[1] != name[1]:
                break
            else:
                res.append(prev[i] + ', ' + name[i])
    return ' '.join(res)


def addActivity(timesheet=None, name=None, data=None, start=None, end=None, addDuration=True):
    if timesheet is None:
        timesheet = getCoordinates()
    activitiesDict = getMyLoggedActivitiesDict(timesheet)
    activitiesList = [v[0] for v in activitiesDict.values()]
    compress = -1
    if data is not None:
        name = data[0]
        if re.match(r'[LPS][AEW][CESW]\s[LP][0-9]{1,2}', name):
            sameSubjectAndMode = list(filter(lambda a: name[:5] in a, activitiesList))
            if len(sameSubjectAndMode):
                compress = activitiesList.index(sameSubjectAndMode[0])
        if name in activitiesList:
            tmp = activitiesDict[activitiesList.index(name)]
            tmp[1] = int(tmp[1].split(' ')[0])
            a = Activity(data=tmp)
            a.addDuration(start=start, end=end)
            tmp[1] = f'{tmp[1]} m'
            index = list(activitiesDict.values()).index(tmp)
            timesheet['pomsheetRange']['old'] = index
            sheetRange = f"{sheetNames['mine']}{timesheet['activities']['valueCol']}{timesheet['activities']['startRow'] + index}"
            sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [[a.duration]]}, valueInputOption='USER_ENTERED').execute()
        elif compress >= 0:
            sameSubjectAndMode = list(filter(lambda a: name[:5] in a, activitiesList))
            tmp = activitiesDict[activitiesList.index(sameSubjectAndMode[0])]
            tmp[1] = int(tmp[1].split(' ')[0])
            a = Activity(data=tmp)
            a.addDuration(start=start, end=end)
            a.name = compressActivities(sameSubjectAndMode[0], name)
            tmp[1] = f'{tmp[1]} m'
            index = list(activitiesDict.values()).index(tmp)
            timesheet['pomsheetRange']['old'] = index
            sheetRange = f"{sheetNames['mine']}{timesheet['activities']['nameCol']}{timesheet['activities']['startRow'] + index}:{timesheet['activities']['codeCol']}{timesheet['activities']['startRow'] + index}"
            sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [a.sheetValues()]}, valueInputOption='USER_ENTERED').execute()
        else:
            data[1] = 0
            a = Activity(data=data)
            a.addDuration(start=start, end=end)
            sheetRange = f"{sheetNames['mine']}{timesheet['activities']['nameCol']}{timesheet['activities']['currentRow']}:{timesheet['activities']['codeCol']}{timesheet['activities']['currentRow']}"
            sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [a.sheetValues()]}, valueInputOption='USER_ENTERED').execute()
    else:
        if name is None:
            name = input('Insert name of activity: ')
        if name in activitiesList:
            tmp = activitiesDict[activitiesList.index(name)]
            tmp[1] = int(tmp[1].split(' ')[0])
            a = Activity(data=tmp)
            a.addDuration(start=start, end=end)
            index = list(activitiesDict.values()).index(tmp)
            timesheet['pomsheetRange']['old'] = index
            sheetRange = f"{sheetNames['mine']}{timesheet['activities']['valueCol']}{timesheet['activities']['startRow'] + index}"
            sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [[a.duration]]}, valueInputOption='USER_ENTERED').execute()
        else:
            a = Activity(name=name, start=start, end=end)
            sheetRange = f"{sheetNames['mine']}{timesheet['activities']['nameCol']}{timesheet['activities']['currentRow']}:{timesheet['activities']['codeCol']}{timesheet['activities']['currentRow']}"
            sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [a.sheetValues()]}, valueInputOption='USER_ENTERED').execute()
    addToPomsheet(timesheet=timesheet, category=('Andrea' if a.code == categories['mine']['Andrea'] else 'classes' if a.code == categories['mine']['classes'] else 'swe project') if a.code in [categories['mine']['Andrea'], categories['mine']['classes'], categories['mine']['swe project']] else None, name=a.name, duration=a.duration, isOldIndex='old' in timesheet['pomsheetRange'])
    addToTimesheet(start=a.sheetStart(), end=a.sheetEnd(), code=a.code)


def addToPomsheet(timesheet=None, category=None, name=None, duration=None, isOldIndex=False):
    if timesheet is None:
        timesheet = getCoordinates()
    timesheet = timesheet['pomsheetRange']
    if category is None and isOldIndex is False:
        category = utils.safeInputChoice(categories['challenge'], 'Insert the challenge category (available: ' + ', '.join(categories['challenge']) + '): ')
    if name is None:
        name = input('Insert name of activity: ')
    if duration is None:
        duration = utils.safeInputInt(prompt='Insert duration in minutes: ')
    if isOldIndex:
        tmp = [name, str(duration)]
        sheetRange = f"{sheetNames['challenge']}{timesheet['nameCol']}{timesheet['startRow'] + timesheet['old']}:{timesheet['valueCol']}{timesheet['startRow'] + timesheet['old']}"
    else:
        tmp = [category, name, str(duration)]
        sheetRange = f"{sheetNames['challenge']}{timesheet['catCol']}{timesheet['currentRow']}:{timesheet['valueCol']}{timesheet['currentRow']}"
    sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [tmp]}, valueInputOption='USER_ENTERED').execute()


def addToTimesheet(startCell=None, start=None, end=None, code=None, timesheet=None, fill=False):
    if timesheet is None:
        timesheet = getCoordinates()
    end -= timedelta(minutes=1)
    if code is None:
        code = 'pr'
    if fill:
        fullRow = [code, code, code, code, code, code]
        startCol = ''.join(list(filter(lambda l: not l.isdigit(), startCell)))
        startRow = int(''.join(list(filter(lambda l: l.isdigit(), startCell))))
        endRow = end.hour
        endCol = end.minute // 10
        if timesheet['timesheetRange']['rows'][endRow] > startRow:
            sheetRange1 = sheetNames['mine'] + calculateRange(startRow, startCol, startRow, timesheet['timesheetRange']['cols'][5])
            toInsert = []
            for _ in range(timesheet['timesheetRange']['rows'][endRow] - startRow - 1):
                toInsert.append(fullRow)
            sheetRange2 = sheetNames['mine'] + calculateRange(startRow + 1, timesheet['timesheetRange']['cols'][0], timesheet['timesheetRange']['rows'][endRow - 1], timesheet['timesheetRange']['cols'][5])
            sheetRange3 = sheetNames['mine'] + calculateRange(timesheet['timesheetRange']['rows'][endRow], timesheet['timesheetRange']['cols'][0], timesheet['timesheetRange']['rows'][endRow], timesheet['timesheetRange']['cols'][endCol])
            sheets.values().batchUpdate(spreadsheetId=sheetIds['Challenge'], body={"data": [{"range": sheetRange1, "values": [fullRow[timesheet['timesheetRange']['cols'].index(startCol):]]}, {"range": sheetRange2, "values": toInsert}, {"range": sheetRange3, "values": [fullRow[:endCol + 1]]}], "valueInputOption": 'USER_ENTERED'}).execute()
        else:
            sheetRange = sheetNames['mine'] + calculateRange(startRow, startCol, timesheet['timesheetRange']['rows'][endRow], timesheet['timesheetRange']['cols'][endCol])
            sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [fullRow[timesheet['timesheetRange']['cols'].index(startCol):endCol + 1]]}, valueInputOption='USER_ENTERED').execute()
    else:
        startRow = start.hour
        startCol = start.minute // 10
        endRow = end.hour
        endCol = end.minute // 10
        firstCell = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=sheetNames['mine'] + timesheet['timesheetFirstFreeCell']).execute()['values'][0][0]
        firstRow = int(''.join(list(filter(lambda l: l.isdigit(), firstCell))))
        firstCol = ''.join(list(filter(lambda l: not l.isdigit(), firstCell)))
        startCell = f"{timesheet['timesheetRange']['cols'][startCol]}{timesheet['timesheetRange']['rows'][startRow]}"
        if firstRow < timesheet['timesheetRange']['rows'][startRow]:
            fillInGaps(end=start, startCell=firstCell, code='pr')
        elif firstCol < timesheet['timesheetRange']['cols'][startCol]:
            fillInGaps(end=start, startCell=firstCell, code='pr')
        fullRow = [code, code, code, code, code, code]
        if endRow > startRow:
            sheetRange1 = sheetNames['mine'] + calculateRange(timesheet['timesheetRange']['rows'][startRow], timesheet['timesheetRange']['cols'][startCol], timesheet['timesheetRange']['rows'][startRow], timesheet['timesheetRange']['cols'][5])
            toInsert = []
            for _ in range(startRow + 1, endRow):
                toInsert.append(fullRow)
            sheetRange2 = sheetNames['mine'] + calculateRange(timesheet['timesheetRange']['rows'][startRow + 1], timesheet['timesheetRange']['cols'][0], timesheet['timesheetRange']['rows'][endRow - 1], timesheet['timesheetRange']['cols'][5])
            sheetRange3 = sheetNames['mine'] + calculateRange(timesheet['timesheetRange']['rows'][endRow], timesheet['timesheetRange']['cols'][0], timesheet['timesheetRange']['rows'][endRow], timesheet['timesheetRange']['cols'][endCol])
            sheets.values().batchUpdate(spreadsheetId=sheetIds['Challenge'], body={"data": [{"range": sheetRange1, "values": [fullRow[startCol:]]}, {"range": sheetRange2, "values": toInsert}, {"range": sheetRange3, "values": [fullRow[:endCol + 1]]}], "valueInputOption": 'USER_ENTERED'}).execute()
        else:
            sheetRange = sheetNames['mine'] + calculateRange(timesheet['timesheetRange']['rows'][startRow], timesheet['timesheetRange']['cols'][startCol], timesheet['timesheetRange']['rows'][endRow], timesheet['timesheetRange']['cols'][endCol])
            sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [fullRow[startCol:endCol + 1]]}, valueInputOption='USER_ENTERED').execute()
    sheetRange = sheetNames['mine'] + timesheet['timesheetFirstFreeCell']
    sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [[f"{timesheet['timesheetRange']['cols'][(endCol + 1) % 6]}{timesheet['timesheetRange']['rows'][endRow + (1 if endCol + 1 >= 6 and endRow < 23 else 0)]}"]]}, valueInputOption='USER_ENTERED').execute()


def fillInGaps(end, startCell=None, code='pr', timesheet=None):
    if timesheet is None:
        timesheet = getCoordinates()
    if startCell is None:
        startCell = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=sheetNames['mine'] + timesheet['timesheetFirstFreeCell']).execute()['values'][0][0]
    addToTimesheet(startCell=startCell, end=end, code=code, fill=True)


def getCategoryCode(name):
    return categories['mine'].get(name, name)


def getAllCategoryNames():
    return categories['mine'].keys()


def viewStats():
    startOfWeek = today
    while startOfWeek.strftime('%w') != '1':
        startOfWeek -= timedelta(days=1)
    endOfWeek = startOfWeek + timedelta(days=6)
    startOfMonth = date(today.year, today.month, 1)
    endOfMonth = date(today.year, today.month + 1, 1)
    endOfMonth -= timedelta(days=1)
    data = {
        'dayDone': summarySheet + '!D' + getOffset(),
        'dayGoal': summarySheet + '!E' + getOffset(),
        'weekDone': summarySheet + f'!D{max(challengeFirstRow, int(getOffset(startOfWeek)))}:D{min(challengeLastRow, int(getOffset(endOfWeek)))}',
        'weekGoal': summarySheet + f'!E{max(challengeFirstRow, int(getOffset(startOfWeek)))}:E{min(challengeLastRow, int(getOffset(endOfWeek)))}',
        'monthDone': summarySheet + f'!D{max(challengeFirstRow, int(getOffset(startOfMonth)))}:D{min(challengeLastRow, int(getOffset(endOfMonth)))}',
        'monthGoal': summarySheet + f'!E{max(challengeFirstRow, int(getOffset(startOfMonth)))}:E{min(challengeLastRow, int(getOffset(endOfMonth)))}',
        'currBal': summarySheet + '!D8',
        'totalDone': summarySheet + '!D9',
        'currLevel': summarySheet + '!D17',
        'pomsToNextLevel': summarySheet + '!D11'
    }
    values = sheets.values().batchGet(spreadsheetId=sheetIds['Challenge'], ranges=list(data.values())).execute()['valueRanges']
    values = {e['range']:e['values'] for e in values}
    data = {k:values[v] for k, v in data.items()}
    dayDone = float(data['dayDone'][0][0].split(' ')[0])
    dayGoal = int(data['dayGoal'][0][0].split(' ')[0])
    weekDone = data['weekDone']
    weekGoal = data['weekGoal']
    weekDone = sum([float(row[0].split(' ')[0]) for row in weekDone])
    weekGoal = sum([int(row[0].split(' ')[0]) for row in weekGoal])
    monthDone = data['monthDone']
    monthGoal = data['monthGoal']
    monthDone = sum([float(row[0].split(' ')[0]) for row in monthDone])
    monthGoal = sum([int(row[0].split(' ')[0]) for row in monthGoal])
    currBal = int(data['currBal'][0][0].split(' ')[0])
    totalDone = float(data['totalDone'][0][0].split(' ')[0])
    currLevel = data['currLevel'][0][0].split(' ')[1]
    pomsToNextLevel = data['pomsToNextLevel'][0][0].split(' ')[0]
    rankingData = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range='Friends!D7:H9', majorDimension='COLUMNS').execute()['values']
    rankingData = sorted([[d[0], float(d[2].split(' ')[0])] for d in rankingData], key=lambda x: x[1], reverse=True)
    rankingData = [f"{d[0]}: {d[1]:.2f}" for d in rankingData]
    print(f'Current balance: {currBal}')
    print(f'Poms already done today: {dayDone:.2f}')
    print(f"Today's goal: {dayGoal}. Progress: {dayDone / dayGoal * 100:.2f}%")
    print(f"This week's goal: {weekGoal}. Progress: {(weekDone / weekGoal) * 100:.2f}%")
    print(f"This month's goal: {monthGoal}. Progress: {(monthDone / monthGoal) * 100:.2f}%")
    print(f"Current level: {currLevel}. Poms to next level: {pomsToNextLevel}")
    print(f"Poms to Rainbow: {1295 - totalDone:.2f}. Progress: {(totalDone / 1295) * 100:.2f}%")
    print('\n\t'.join(['Current ranking:'] + rankingData))


def isStartOfDay():
    coords = getCoordinates()
    ts = coords['timesheetRange']
    res = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=sheetNames['mine'] + f"{ts['cols'][0]}{ts['rows'][0]}").execute().get('values', []) == []
    free = f"{ts['cols'][0]}{ts['rows'][0]}"
    if res:
        sheetRange = sheetNames['mine'] + coords['timesheetFirstFreeCell']
        sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=sheetRange, body={"range": sheetRange, "values": [[free]]}, valueInputOption='USER_ENTERED').execute()
    return res


def clearSheets():
    sheets.values().batchClear(spreadsheetId=sheetIds['Database'], body={"ranges": ["Sheets!A:B", "Todoist!A:C", "Calendar!A:C"]}).execute()


def getDailyPoms():
    sheetRange = sheetNames['mine'] + getCoordinates()['sumCell']
    return sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=sheetRange).execute()['values'][0][0].split(' ')[0]


def insertActivities(sheet, activities):
    lastCol = {
        "Procrastination": "B",
        "Sheets": "B",
        "TodoistInProgress": "B",
        "Todoist": "C",
        "Calendar": "D"
    }
    sheets.values().batchClear(spreadsheetId=sheetIds['Database'], body={"ranges": [f"{sheet}!A:{lastCol[sheet]}"]}).execute()
    sheets.values().batchUpdate(spreadsheetId=sheetIds['Database'], body={"valueInputOption": "USER_ENTERED", "data": [{"range": f"{sheet}!A:{lastCol[sheet]}", "values": activities}]}).execute()


def getActivities(sheet):
    lastCol = {
        "Sheets": "B",
        "TodoistInProgress": "B",
        "Todoist": "C",
        "Calendar": "D"
    }
    return sheets.values().get(spreadsheetId=sheetIds['Database'], range=f"{sheet}!A:{lastCol[sheet]}").execute().get("values", [])


def haveBreakfast():
    cell = sheetNames['mine'] + getCoordinates()['hadBreakfast']
    start = datetime.combine(today, utils.safeInputTime(prompt='At what time have you started breakfast? ', returnObj=True))
    end = datetime.combine(today, utils.safeInputTime(prompt='At what time have you finished breakfast? ', returnObj=True))
    addToTimesheet(start=start, end=end, code='b')
    sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=cell, body={"range": cell, "values": [["=true"]]}, valueInputOption='USER_ENTERED').execute()
    cu.insert('Breakfast', start, end)


def hadBreakfast():
    cell = sheetNames['mine'] + getCoordinates()['hadBreakfast']
    values = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=cell).execute().get('values', [])
    if len(values):
        return values[0][0].upper() == 'TRUE'
    else:
        return False


def haveLunch():
    cell = sheetNames['mine'] + getCoordinates()['hadLunch']
    start = datetime.combine(today, utils.safeInputTime(prompt='At what time have you started lunch? ', returnObj=True))
    end = datetime.combine(today, utils.safeInputTime(prompt='At what time have you finished lunch? ', returnObj=True))
    addToTimesheet(start=start, end=end, code='b')
    sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=cell, body={"range": cell, "values": [["=true"]]}, valueInputOption='USER_ENTERED').execute()
    cu.insert('Lunch', start, end)


def hadLunch():
    cell = sheetNames['mine'] + getCoordinates()['hadLunch']
    values = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=cell).execute().get('values', [])
    if len(values):
        return values[0][0].upper() == 'TRUE'
    else:
        return False


def haveDinner():
    cell = sheetNames['mine'] + getCoordinates()['hadDinner']
    start = datetime.combine(today, utils.safeInputTime(prompt='At what time have you started dinner? ', returnObj=True))
    end = datetime.combine(today, utils.safeInputTime(prompt='At what time have you finished dinner? ', returnObj=True))
    addToTimesheet(start=start, end=end, code='b')
    sheets.values().update(spreadsheetId=sheetIds['Challenge'], range=cell, body={"range": cell, "values": [["=true"]]}, valueInputOption='USER_ENTERED').execute()
    cu.insert('Dinner', start, end)


def hadDinner():
    cell = sheetNames['mine'] + getCoordinates()['hadDinner']
    values = sheets.values().get(spreadsheetId=sheetIds['Challenge'], range=cell).execute().get('values', [])
    if len(values):
        return values[0][0].upper() == 'TRUE'
    else:
        return False


def getProcrastinationTimes():
    return sheets.values().get(spreadsheetId=sheetIds['Database'], range="Procrastination!A:B").execute().get("values", [])


def clearProcrastinationTimes():
    return sheets.values().batchClear(spreadsheetId=sheetIds['Database'], body={"ranges": ["Procrastination!A:B"]}).execute()
