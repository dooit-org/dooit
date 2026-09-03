import faker
from datetime import timedelta
from random import randint
from dooit.api import Todo, Project
from dooit.utils.database import delete_all_data


f = faker.Faker()


def gen_todo(parent):
    words = randint(2, 9)
    description = " ".join(f.words(nb=words))

    if randint(0, 4) == 1:
        description += " @" + f.word()

    due = f.date_between(start_date="-1y", end_date="+1y")
    priority = randint(1, 3) if randint(0, 10) == 5 else 0

    recurrence = timedelta(days=randint(1, 30)) if randint(0, 10) == 5 else None
    todo = Todo(
        description=description,
        due=due,
        priority=priority,
        pending=randint(1, 3) == 3 if recurrence is None else True,
        recurrence=recurrence,
        effort=randint(0, 3),
    )

    if isinstance(parent, Todo):
        todo.parent_todo = parent
        todo.due = None
    else:
        todo.parent_project = parent

    todo.save()
    return todo


def gen_todos(parent, count):
    return [gen_todo(parent) for _ in range(count)]


def gen_project(parent=None):
    words = randint(1, 2)
    description = " ".join(f.words(nb=words))

    project = Project(description=description, parent_project=parent)
    project.save()

    return project


def generate(session, test=True):
    delete_all_data(session)

    p1 = gen_project()
    p1_childs = [gen_project(p1) for _ in range(5)]

    p2 = gen_project()
    p3 = gen_project()

    t1 = gen_todos(p1, 5)
    gen_todos(t1[0], 7)
    gen_todos(t1[3], 3)

    _ = [gen_todos(p, randint(1, 20)) for p in p1_childs]
    gen_todos(p2, 20)
    gen_todos(p3, 30)


if __name__ == "__main__":  # pragma: no cover (not called in tests)
    from dooit.api import manager

    manager.connect()

    generate(manager.session, test=False)
    print("Data generated.")
