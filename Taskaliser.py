from __future__ import print_function
from BTerm import *
from copy import copy
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client import file, client, tools
import datetime, threading


try:
    SCOPES = 'https://www.googleapis.com/auth/drive'

    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    drive_service = build('drive', 'v3', http=creds.authorize(Http()))
except BaseException as e:
    print(str(e))

class Task:
    def __init__(self, name, tasks=list(), complete=False, deadline=None, date=None):
        self.name = name
        self.tasks = copy(tasks)
        self.complete = complete
        self.deadline = deadline
        self.date = (None if deadline is None else datetime.datetime.now()) if date is None else date

    def calc_complete(self):
        for x in self.tasks:
            x.calc_complete()
        if len(self.tasks):
            self.complete = sum([x.complete for x in self.tasks]) == len(self.tasks)

    def add_task(self, task):
        self.tasks.append(task)
        self.calc_complete()

    def remove_task(self, index):
        del self.tasks[index]
        self.calc_complete()

    def set_complete(self, value):
        if self.complete != value:
            for x in self.tasks:
                x.set_complete(value)
        self.complete = value

    def set_inner_complete(self, index, value):
        if self.tasks[index].complete != value:
            for x in self.tasks[index].tasks:
                x.set_complete(value)
        self.tasks[index].complete = value
        self.calc_complete()

    def __str__(self):
        self.calc_complete()
        return "Task('" + self.name + "', " + str(self.tasks) + ", " + str(self.complete) + "," + str(self.deadline) + ", " + repr(self.date) + ")"

    __repr__ = __str__


mt = Task("Tasks", complete=True)
last_update = datetime.datetime(datetime.MINYEAR, 1, 1)
t = BTerm()

try:
    with open("tasks.txt", "r") as f:
        mt = eval(f.readline(), {"Task": Task, "datetime": datetime})
        last_update = eval(f.readline(), {"datetime": datetime})
except FileNotFoundError:
    print("file not found")


def display_tasks(term, task, indent=0, num=0):
    mt.calc_complete()
    percent = 0.0
    if task.complete:
        percent = 100
    elif len(task.tasks):
        percent = (sum([int(x.complete) for x in task.tasks]) * 100) / len(task.tasks)
    term.set_cursor(indent, term.cursor[1])
    term.print(((str(num) + ": ") if task.name != "Tasks" else "") + task.name + " " + str(percent) + "% " + (str(task.deadline-(datetime.datetime.now() - task.date).days) if task.date is not None else ""), True)
    for x, elem in enumerate(task.tasks):
        display_tasks(term, elem, indent + 4, x)


def check_updates():
    global mt
    global last_update
    global t
    try:
        http = creds.authorize(Http())
        result = str(drive_service.files().get_media(fileId="13w-GA2pbcUbtUiOxzN9loQwdwMLur5MC").execute(http=http), "ISO-8859-1")
        date = eval(result.split("\n")[1], {"datetime": datetime})
        if date < last_update:
            drive_service.files().update(
                fileId="13w-GA2pbcUbtUiOxzN9loQwdwMLur5MC",
                media_body=MediaFileUpload("tasks.txt", "text/plain")
            ).execute(http=http)
        elif date > last_update:
            mt = eval(result.split("\n")[0], {"Task": Task, "datetime": datetime})
            last_update = copy(date)
            with open("tasks.txt", "w") as f:
                f.write(str(mt) + "\n" + repr(last_update))
    except IndexError as e:
        print(str(e))
        t.clear()
        mt.calc_complete()
        display_tasks(t, mt)


check_updates()
timer_time = 30000
timer = Timer(timer_time)
t.clear()
display_tasks(t, mt)
while t.active:
    command = t.input()
    if command.lower() in ["exit", "quit"]:
        t.kill()
        break
    l = (command.split("\""))
    if len(l) == 3:
        l2 = l[2].split()
        del l[2]
        l += l2
    elif len(l) == 1:
        l = command.split()
    elif len(l) > 3:
        print("raise some error")
    if len(l):
        if l[0].lower() in ["add ", "add"]:
            try:
                if l[1].lower() in ["day ", "day"]:
                    try:
                        days = int(l[2])
                        try:
                            if l[3] in ["to", "to "]:
                                l = list(map(int, l[4:]))
                                task = mt.tasks[l[0]]
                                for x in l[1:]:
                                    task = task.tasks[x]
                                task.deadline = days
                                task.date = datetime.datetime.now()
                            else:
                                print("Missing location for deadline")
                        except IndexError:
                            print("Missing location for deadline")
                    except ValueError:
                        print("deadline not integer")
                    except IndexError:
                        print("no deadline specified")
                else:
                    word = l[1]
                    deadline = None
                    try:
                        deadline = int(l[2])
                        try:
                            if l[3] in ["to", "to "]:
                                l2 = list(map(int, l[4:]))
                                task = mt.tasks[l2[0]]
                                for x in l2[1:]:
                                    task = task.tasks[x]
                                task.add_task(Task(word, deadline=deadline))
                            else:
                                mt.add_task(Task(word, deadline=deadline))
                        except IndexError:
                            mt.add_task(Task(word, deadline=deadline))
                    except ValueError:
                        if l[2] in ["to", "to "]:
                            l = list(map(int, l[3:]))
                            task = mt.tasks[l[0]]
                            for x in l[1:]:
                                task = task.tasks[x]
                            task.add_task(Task(word, deadline=deadline))
                    except IndexError:
                        mt.add_task(Task(word, deadline=deadline))
            except IndexError:
                print("index 1")
        elif l[0].lower() in ["rem ", "rem", "remove ", "remove"]:
            try:
                task = mt
                l = list(map(int, l[1:]))
                for x in l[:-1]:
                    task = task.tasks[x]
                task.remove_task(l[-1])
            except IndexError:
                print("missing remove location")
        elif l[0].lower() in ["complete ", "complete"]:
            try:
                task = mt
                l = list(map(int, l[1:]))
                for x in l[:-1]:
                    task = task.tasks[x]
                task.set_inner_complete(l[-1], True)
            except IndexError:
                mt.set_complete(True)
        elif l[0].lower() in ["uncomplete ", "uncomplete"]:
            try:
                task = mt
                l = list(map(int, l[1:]))
                for x in l[:-1]:
                    task = task.tasks[x]
                task.set_inner_complete(l[-1], False)
            except IndexError:
                mt.set_complete(False)
        t.clear()
        mt.calc_complete()
        display_tasks(t, mt)
        with open("tasks.txt", "w") as f:
            last_update = datetime.datetime.now()
            f.write(str(mt) + "\n" + repr(last_update))
        thread = threading.Thread(target=check_updates)
        thread.daemon = True
        thread.start()
    if timer.passed():
        print("passed")
        timer = Timer(timer_time)
        thread = threading.Thread(target=check_updates)
        thread.daemon = True
        thread.start()
    t.update()