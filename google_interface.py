from datetime import datetime, date, time
import os.path, pytz, backend
from typing import Dict, List, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

cal_ids: Dict[str, str] = dict()
cals_to_avoid: List[str] = [
    'Festività italiane',
    'TV shows',
    'Andrea',
    'University study',
    'Skeleton',
    'Personal',
    'primary',
    'clarissa.de.simoni@gmail.com',
    'Random',
    'Exams',
    'Workouts',
    'C & L',
    'Cla & Leo',
    'Book releases',
    'Streams',
    'Quando non ci siamo',
    'NSC activities',
    'Family events'
]

def format_line(event: Dict[str, Union[str, Dict]], cal_id: str) -> str:
    name = event['summary']
    cal = cal_ids[cal_id]
    fmt = '%Y-%m-%dT%H:%M:%S%z'
    dt_start = datetime.strptime(event['start']['dateTime'], fmt)
    dt_end = datetime.strptime(event['end']['dateTime'], fmt)
    return f"{name} ({cal}) @ {dt_start.strftime('%H:%M')} - {dt_end.strftime('%H:%M')}"

def get_access():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(os.path.join(backend.file_dir, "token.json")):
        creds = Credentials.from_authorized_user_file(os.path.join(backend.file_dir, "token.json"), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(backend.file_dir, "credentials.json"), SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(os.path.join(backend.file_dir, "token.json"), "w") as token:
            token.write(creds.to_json())
    return creds

def main():
    try:
        service = build("calendar", "v3", credentials=get_access())

        events_strs: List[str] = []

        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get("items", [])
        for cal in calendars:
            if cal['summary'] not in cals_to_avoid:
                cal_ids[cal['id']] = cal['summary']

        start = pytz.timezone('Europe/Rome').localize(datetime.combine(date.today(), time(0, 0))).isoformat()
        end = pytz.timezone('Europe/Rome').localize(datetime.combine(date.today(), time(23, 59, 59))).isoformat()
        
        for cal_id in cal_ids:
            events_result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=start,
                    timeMax=end,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            events = '\n'.join(map(lambda e: format_line(e, cal_id), events))
            if len(events):
                events_strs.append(events)
        
            with open(os.path.join(backend.file_dir, 'events.txt'), 'w') as f:
                f.write('\n'.join(events_strs))

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()