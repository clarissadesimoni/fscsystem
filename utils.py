import re, sys
# import termios
from datetime import datetime, date, time, timedelta

def safeInputBool(prompt=''):
    accepted=['y', 'yes', 'n', 'no']
    res = input(prompt).lower()
    while res not in accepted:
        print('Invalid input.')
        res = input(prompt).lower()
    return res == 'y' or res == 'yes'


def safeInputInt(accepted=None, prompt=''):
    res = input(prompt)
    try:
        res = int(res)
    except:
        res = 'no'
    while res == 'no':
        print('Invalid input.')
        res = input(prompt)
        try:
            res = int(res)
            if accepted is not None:
                if res not in accepted:
                    res = 'no'
        except:
            res = 'no'
    return res


def safeInputDate(prompt='', returnObj=False):
    valid = False
    res = input(prompt)
    valid = res.count('-') == 2
    if valid:
        valid = valid and int(res.split('-')[0]) >= 2000
    while not valid:
        print('Invalid input.')
        res = input(prompt)
        valid = res.count('-') == 2
        if valid:
            valid = valid and int(res.split('-')[0]) >= 2000
    if returnObj:
        return datetime.strptime(res, '%Y-%m-%d').date()
    else:
        return res

def safeInputTime(prompt='', returnObj=False):
    valid = False
    res = input(prompt)
    shortPattern = '^([0-9]{1,2})$'
    longPattern = r'^([0-9]{1,2}[\.:\-_,;=][0-9]{1,2})$'
    complete = shortPattern + '|' + longPattern
    valid = re.match(complete, res)
    while not valid:
        print('Invalid input.')
        res = input(prompt)
        valid = re.match(complete, res)
    if re.match(shortPattern, res):
        res = ('0' * (2 - len(res))) + res + ':00'
    elif re.match(longPattern, res):
        items = re.split(r'[\.:\-_,;=]', res)
        items[0] = ('0' * (2 - len(items[0]))) + items[0]
        items[1] = items[1] + ('0' * (2 - len(items[1])))
        res = ':'.join(items)
    if returnObj:
        return time.fromisoformat(res)
    else:
        return res

def safeInputTimedelta(prompt='', returnObj=False):
    valid = False
    res = input(prompt)
    pattern = r'^([0-9]{1,2}[\.:\-_,;=][0-9]{1,2}[\.:\-_,;=][0-9]{1,2})$'
    valid = re.match(pattern, res)
    while not valid:
        print('Invalid input.')
        res = input(prompt)
        valid = re.match(pattern, res)
    res = '0' * (8 - len(res)) + res
    res = re.sub(r'[\.:\-_,;=]', ':', res)
    if returnObj:
        return timedelta(hours=int(res[:2]), minutes=int(res[3:5]), seconds=int(res[6:]))
    else:
        return res

def safeInputChoice(accepted, prompt='', canExit=''):
    res = input(prompt)
    while res not in accepted and not res == canExit:
        print('Invalid input.')
        res = input(prompt)
    return res

def getDuration(dur, worded=True):
    def stringify(val, singular):
        return f"{val} {singular}{'s' if val != 1 else ''}"
    if worded:
        total = dur.total_seconds()
        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = int((total % 3600) % 60)
        res = stringify(hours, 'hour') if hours > 0 else stringify(minutes, 'minute') if minutes > 0 else stringify(seconds, 'second')
        if 'hour' in res:
            res += f"{(', ' if seconds > 0 else ' and ') + stringify(minutes, 'minute') if minutes > 0 else ''}{' and ' + stringify(seconds, 'second') if seconds > 0 else ''}"
        elif 'minute' in res:
            res += f"{' and ' + stringify(seconds, 'second') if seconds > 0 else ''}"
        return res
    else:
        return str(dur)
