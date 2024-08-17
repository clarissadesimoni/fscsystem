import requests as r, json
from typing import List
from datetime import date, datetime

utils = json.load(open('creds_and_info.json'))

def get_last_update():
    resp = r.get(f"{utils['supabase']['url']}/info?key=eq.last_update&select=*",
        headers={
            'Content-Type': 'application/json',
            "apikey": utils['supabase']['secret'],
            "Authorization": f"Bearer {utils['supabase']['secret']}"
        })
    return resp.json()[0]['value'] != date.today().strftime('%Y-%m-%d')

def set_last_update():
    r.patch(f"{utils['supabase']['url']}/info?key=eq.last_update",
        data=json.dumps({
            'value': datetime.now().strftime("%Y-%m-%d")
        }),
        headers={
            'Content-Type': 'application/json',
            "apikey": utils['supabase']['secret'],
            "Authorization": f"Bearer {utils['supabase']['secret']}"
        })
    
def delete_tasks(to_delete: List[str]):
    r.delete(f"{utils['supabase']['url']}/tasks?task_id=in.{','.join(to_delete)}",
        headers={
            'Content-Type': 'application/json',
            "apikey": utils['supabase']['secret'],
            "Authorization": f"Bearer {utils['supabase']['secret']}"
        })

def delete_old_tasks():
    r.delete(f"{utils['supabase']['url']}/tasks?task_id=like.*",
        headers={
            'Content-Type': 'application/json',
            "apikey": utils['supabase']['secret'],
            "Authorization": f"Bearer {utils['supabase']['secret']}"
        })

def insert_new_tasks(tasks: List[str]):
    r.post(f"{utils['supabase']['url']}/tasks",
        data=json.dumps([{
            "task_id": tid
        } for tid in tasks]),
        headers={
            'Content-Type': 'application/json',
            "apikey": utils['supabase']['secret'],
            "Authorization": f"Bearer {utils['supabase']['secret']}"
        })

def get_tasks():
    resp = r.get(f"{utils['supabase']['url']}/tasks?select=*",
        headers={
            'Content-Type': 'application/json',
            "apikey": utils['supabase']['secret'],
            "Authorization": f"Bearer {utils['supabase']['secret']}"
        })
    return {task['task_id'] for task in resp.json()}