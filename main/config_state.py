# config_state.py
resender_enabled = True
scheduler_enabled = True
tasks_enabled = {}      # состояние включения задач по id (ключ - str(id))
tasks_list = []          # список задач: [{"id": 1, "hour": 7, "minute": 0, "text": "..."}, ...]