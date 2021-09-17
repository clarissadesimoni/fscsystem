from pprint import pprint
from datetime import datetime, date, time, timedelta
import pickle, os.path, re, pytz
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']
credFile = 'credsCalendar.json'
tokenFile = 'tokenCalendar.pickle'
today = date.today()


class Event:
    def __init__(self, data, calId):
        self.name = data['summary']
        self.id = data['id']
        self.calId = calId
        self.calendar = data['organizer']['displayName']
        self.isAllDay = False
        self.isPr = data.get('colorId', '') == '4'
        fmt = '%Y-%m-%dT%H:%M:%S%z'
        if re.fullmatch(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$', data['start'].get('date', data['start'].get('dateTime', today.isoformat()))):
            self.isAllDay = True
            fmt = '%Y-%m-%d'
        self.start = datetime.strptime(data['start'].get('date', data['start'].get('dateTime', today.isoformat())), fmt)
        self.end = datetime.strptime(data['end'].get('date', data['end'].get('dateTime', today.isoformat())), fmt)
        self.duration = self.end - self.start
    
    def __repr__(self):
        return self.name + (f" (from {self.start.strftime('%H:%M')} to {self.end.strftime('%H:%M')})" if not self.isAllDay else '')

    def __add__(self, other):
        res = self
        res.duration = self.duration + other.duration
        res.end = res.start + res.duration
        return res


def getCalendars():
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
        # Save the credentials for the next run
        with open(tokenFile, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


calendars = getCalendars()


calendarIds = {c['summary']:c['id'] for c in list(filter(lambda cal: 'owner' in cal['accessRole'], calendars.calendarList().list().execute()['items']))}


def getCalId(name):
    return calendarIds.get(name, 'primary')


def getCalNames():
    return calendarIds.keys()


def delete(calId, eventId):
    calendars.events().delete(calendarId=calId, eventId=eventId).execute()


def insert(name, start, end, calendarName='Daily tracking', isPr=False):
    cet = pytz.timezone('Europe/Rome')
    dateKey = 'date'
    if isinstance(start, datetime):
        dateKey = 'dateTime'
        if start.tzinfo is None:
            start = cet.localize(start)
        if end.tzinfo is None:
            end = cet.localize(end)
    body = {
        "end": {
            dateKey: end.isoformat()
        },
        "kind": "calendar#event",
        "start": {
            dateKey: start.isoformat()
        },
        "summary": name,
    }
    if isPr:
        body['colorId'] = '4'
    calendars.events().insert(calendarId=getCalId(calendarName), body=body).execute()


def getEvents(calNames=None, start=datetime.combine(today, time()), end=datetime.combine(today + timedelta(days=1), time()), filt=None):
    if calNames is None:
        calNames = calendarIds.keys()
    tmp = []
    res = []
    cet = pytz.timezone('Europe/Rome')
    if start.tzinfo is None:
        start = cet.localize(start)
    if end.tzinfo is None:
        end = cet.localize(end)
    for cal in calNames:
        tmp += [[calendars.events().list(calendarId=getCalId(cal), orderBy='startTime', singleEvents=True, timeMax=end.isoformat(), timeMin=start.isoformat()).execute().get('items', []), getCalId(cal)]]
    for t in tmp:
        res += [Event(r, t[1]) for r in t[0]]
    if filt is not None:
        res = list(filter(lambda e: e.name == filt and ('LAB' in e.name) == ('LAB' in filt), res))
    allDay = list(filter(lambda e: e.isAllDay, res))
    timed = list(filter(lambda e: not e.isAllDay, res))
    return allDay, timed


def getProcrastinationTime():
    events = getEvents(['Daily tracking'])[1]
    events = list(filter(lambda e: e.isPr, events))
    if len(events):
        return sum(events[1:], events[0]).duration
    else:
        return timedelta()


def getLastEventEndTime(bound):
    events = getEvents(['Daily tracking'], end=bound)[1]
    events.sort(key=lambda e: e.end)
    return events[-1].end


def addActivity(name, start, end, calendarName='Daily tracking'):
    lastEnd = getLastEventEndTime(start)
    if start.tzinfo is None:
        start = pytz.timezone('Europe/Rome').localize(start)
    if lastEnd < start:
        insert('Procrastinating', lastEnd, start, isPr=True)
    insert(name, start, end, calendarName=calendarName)


def getEvent(calId, evId):
    return Event(calendars.events().get(calendarId=calId, eventId=evId).execute(), calId)