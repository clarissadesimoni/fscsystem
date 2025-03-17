import requests as r, json
from typing import List, Dict, Union
from datetime import date, datetime, timedelta
import backend

def get_last_update() -> bool:
    resp = r.get(f"{backend.utils['supabase']['url']}/info?key=eq.last_update&select=*",
        headers = {
            'Content-Type': 'application/json',
            "apikey": backend.utils['supabase']['secret'],
            "Authorization": f"Bearer {backend.utils['supabase']['secret']}"
        })
    backend.is_start_of_day = resp.json()[0]['value'] < date.today().strftime('%Y-%m-%d')
    return backend.is_start_of_day

def set_back_last_update():
    r.patch(f"{backend.utils['supabase']['url']}/info?key=eq.last_update",
        data = json.dumps({
            'value': (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        }),
        headers = {
            'Content-Type': 'application/json',
            "apikey": backend.utils['supabase']['secret'],
            "Authorization": f"Bearer {backend.utils['supabase']['secret']}"
        })

def set_last_update():
    r.patch(f"{backend.utils['supabase']['url']}/info?key=eq.last_update",
        data = json.dumps({
            'value': datetime.now().strftime("%Y-%m-%d")
        }),
        headers = {
            'Content-Type': 'application/json',
            "apikey": backend.utils['supabase']['secret'],
            "Authorization": f"Bearer {backend.utils['supabase']['secret']}"
        })
    
def delete_tasks(to_delete: List[str]):
    r.delete(f"{backend.utils['supabase']['url']}/tasks?task_id=in.{','.join(to_delete)}",
        headers = {
            'Content-Type': 'application/json',
            "apikey": backend.utils['supabase']['secret'],
            "Authorization": f"Bearer {backend.utils['supabase']['secret']}"
        })

def delete_old_tasks():
    r.delete(f"{backend.utils['supabase']['url']}/tasks?task_id=like.*",
        headers = {
            'Content-Type': 'application/json',
            "apikey": backend.utils['supabase']['secret'],
            "Authorization": f"Bearer {backend.utils['supabase']['secret']}"
        })

def insert_new_tasks():
    r.post(f"{backend.utils['supabase']['url']}/tasks",
        data = json.dumps([{
            "task_id": tid,
            "parent_id": pid if pid else None
        } for tid, pid in backend.imported_task_data.items()]),
        headers = {
            'Content-Type': 'application/json',
            "apikey": backend.utils['supabase']['secret'],
            "Authorization": f"Bearer {backend.utils['supabase']['secret']}"
        })

def get_tasks() -> Dict[str, Union[str, None]]:
    resp = r.get(f"{backend.utils['supabase']['url']}/tasks?select=*",
        headers = {
            'Content-Type': 'application/json',
            "apikey": backend.utils['supabase']['secret'],
            "Authorization": f"Bearer {backend.utils['supabase']['secret']}"
        })
    return {task['task_id']:(task['parent_id'] if task['parent_id'] is not None else False) for task in resp.json()}

def check_connection():
    if backend.is_connected:
        try:
            get_last_update()
        except Exception:
            backend.is_connected = False

if __name__ == '__main__':
    set_back_last_update()
    # for t in get_tasks():
    #     pass