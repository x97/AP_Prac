from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.core.time import shanghai_date, utcnow
from app.services.study_plans import distribute_item_indexes
from app.users.models import AdminUser, QaReply, QaThread
from tests.conftest import login



def _clear_qa():
    with SessionLocal() as db:
        db.execute(QaReply.__table__.delete())
        db.execute(QaThread.__table__.delete())
        db.commit()


def _admin_login(client) -> str:
    username = f"plan_admin_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        db.add(
            AdminUser(
                username=username,
                email=f"{username}@example.com",
                password_hash=hash_password("StrongPass123!"),
                role="super_admin",
                status="active",
            )
        )
        db.commit()
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": username, "password": "StrongPass123!"},
    )
    assert response.status_code == 200, response.text
    return username


def _student_id(client) -> str:
    payload = client.get("/api/v1/me").json()
    return payload["user"]["id"]


def _taxonomy(client) -> dict:
    response = client.get("/api/v1/admin/content/taxonomy?subject=psychology")
    assert response.status_code == 200, response.text
    return response.json()


def _question_ids(client, topic_id: str, limit: int = 10) -> list[str]:
    response = client.get(
        "/api/v1/admin/content/questions",
        params={
            "subject": "psychology",
            "topic": topic_id,
            "section": "MCQ",
            "source": "all",
            "limit": min(limit, 200),
        },
    )
    assert response.status_code == 200, response.text
    return [row["question_id"] for row in response.json()["questions"]]


def _make_context(client):
    _admin_login(client)
    login(client)
    student_id = _student_id(client)
    taxonomy = _taxonomy(client)
    topic = next(
        item
        for unit in taxonomy["units"]
        for item in unit["topics"]
        if item["question_count"] >= 8
    )
    unit = next(
        unit for unit in taxonomy["units"] if unit["unit_id"] == topic["unit_id"]
    )
    ids = _question_ids(client, topic["topic_id"], limit=8)
    assert len(ids) >= 4
    return {
        "student_id": student_id,
        "unit_id": unit["unit_id"],
        "topic_id": topic["topic_id"],
        "question_ids": ids,
    }


def _create_homework(client, ctx, title: str, ids: list[str]):
    response = client.post(
        "/api/v1/admin/homeworks?subject=psychology",
        json={
            "title": title,
            "note": "课堂作业备注",
            "unit_id": ctx["unit_id"],
            "topic_id": ctx["topic_id"],
            "question_ids": ids,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_plan(client, ctx, homework_ids: list[str]):
    created = client.post(
        "/api/v1/admin/study-plans?subject=psychology",
        json={"title": "测试陪跑计划", "note": "计划备注", "color": "primary"},
    )
    assert created.status_code == 200, created.text
    plan_id = created.json()["id"]
    replaced = client.put(
        f"/api/v1/admin/study-plans/{plan_id}/items?subject=psychology",
        json={
            "items": [
                {"homework_id": homework_id}
                for homework_id in homework_ids
            ]
        },
    )
    assert replaced.status_code == 200, replaced.text
    return plan_id


def _assign(client, plan_id: str, student_id: str, start: date, end: date):
    response = client.post(
        f"/api/v1/admin/study-plans/{plan_id}/assign?subject=psychology",
        json={
            "student_ids": [student_id],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _calendar(client, month: str | None = None):
    params = {"subject": "psychology"}
    if month:
        params["month"] = month
    response = client.get("/api/v1/study-calendar", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _day(client, day: date):
    response = client.get(
        f"/api/v1/study-calendar/days/{day.isoformat()}",
        params={"subject": "psychology"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _answer_all(client, session_id: str):
    payload = client.get(f"/api/v1/practice-sessions/{session_id}")
    assert payload.status_code == 200, payload.text
    questions = payload.json()["questions"]
    assert questions
    last = None
    for question in questions:
        last = client.post(
            f"/api/v1/practice-sessions/{session_id}/answers",
            json={
                "question_id": question["question_id"],
                "selected_label": question["options"][0]["label"],
            },
        )
        assert last.status_code == 200, last.text
    assert last is not None
    assert last.json()["completed"] is True


def test_distribute_item_indexes():
    assert distribute_item_indexes(1, 30) == [0]
    assert distribute_item_indexes(3, 7) == [0, 3, 6]
    assert distribute_item_indexes(7, 3) == [0, 0, 1, 1, 1, 2, 2]
    assert distribute_item_indexes(5, 5) == [0, 1, 2, 3, 4]
    assert distribute_item_indexes(10, 1) == [0] * 10
    assert distribute_item_indexes(4, 10) == sorted(distribute_item_indexes(4, 10))
    assert distribute_item_indexes(4, 10)[0] == 0
    assert distribute_item_indexes(4, 10)[-1] == 9


def test_assignment_flow_and_unlock(client):
    ctx = _make_context(client)
    hw1 = _create_homework(client, ctx, "课堂作业一", ctx["question_ids"][:2])
    hw2 = _create_homework(client, ctx, "课堂作业二", ctx["question_ids"][2:4])
    plan_id = _create_plan(client, ctx, [hw1["id"], hw2["id"]])
    today = shanghai_date(utcnow())
    result = _assign(client, plan_id, ctx["student_id"], today, today + timedelta(days=3))
    assert len(result["assigned"]) == 1
    assert result["schedule"]["total_items"] == 2

    calendar = _calendar(client)
    assert calendar["has_ever_plan"] is True
    assert calendar["has_active_plan"] is True
    assert len(calendar["plans"]) == 1
    assert calendar["plans"][0]["total_items"] == 2
    assert calendar["plans"][0]["color"] == "primary"
    assert calendar["plans"][0]["current_task"]

    # First item is due today, second is locked until the first completes.
    first_day = _day(client, today)
    first_tasks = [task for group in first_day["assignments"] for task in group["tasks"]]
    assert first_tasks
    first = first_tasks[0]
    assert first["status"] in {"pending", "overdue"}
    assert first["locked"] is False

    started = client.post(
        f"/api/v1/study-calendar/tasks/{first['task_id']}/start",
        params={"subject": "psychology"},
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["session_id"]
    session_payload = client.get(f"/api/v1/practice-sessions/{session_id}").json()
    assert session_payload["homework"]["task_id"] == first["task_id"]
    assert session_payload["homework"]["plan_title"] == "测试陪跑计划"
    _answer_all(client, session_id)

    # The completed task and the next task are both visible now.
    first_day_after = _day(client, today)
    completed = [
        task
        for group in first_day_after["assignments"]
        for task in group["tasks"]
    ]
    assert any(task["status"] == "completed" for task in completed)
    calendar_after = _calendar(client)
    assert calendar_after["plans"][0]["completed_items"] == 1

    # The second item was scheduled a few days later and is now startable
    # even before its calendar date (completion-only gating).
    later = (today + timedelta(days=3)).isoformat()
    later_day = _day(client, date.fromisoformat(later))
    later_tasks = [task for group in later_day["assignments"] for task in group["tasks"]]
    second = next((task for task in later_tasks if task["task_id"] != first["task_id"]), None)
    if second is not None:
        assert second["locked"] is False
        assert second["early"] is True
        second_start = client.post(
            f"/api/v1/study-calendar/tasks/{second['task_id']}/start",
            params={"subject": "psychology"},
        )
        assert second_start.status_code == 200, second_start.text
        _answer_all(client, second_start.json()["session_id"])

    final = _calendar(client)
    plan = final["plans"][0]
    assert plan["completed_items"] == 2
    assert plan["status"] == "completed"


def test_cancel_assignment_hides_it(client):
    ctx = _make_context(client)
    hw = _create_homework(client, ctx, "待取消作业", ctx["question_ids"][:1])
    plan_id = _create_plan(client, ctx, [hw["id"]])
    today = shanghai_date(utcnow())
    result = _assign(client, plan_id, ctx["student_id"], today, today)
    assignment_id = result["assigned"][0]["assignment_id"]
    assert _calendar(client)["has_active_plan"] is True

    cancelled = client.post(
        f"/api/v1/admin/study-plan-assignments/{assignment_id}/cancel",
        json={"reason": "课程调整"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert _calendar(client)["has_active_plan"] is False
    assert _calendar(client)["plans"] == []


def test_duplicate_assignment_is_skipped(client):
    ctx = _make_context(client)
    hw = _create_homework(client, ctx, "重复指派作业", ctx["question_ids"][:1])
    plan_id = _create_plan(client, ctx, [hw["id"]])
    today = shanghai_date(utcnow())
    first = _assign(client, plan_id, ctx["student_id"], today, today)
    assert len(first["assigned"]) == 1
    second = _assign(client, plan_id, ctx["student_id"], today, today)
    assert second["assigned"] == []
    assert second["skipped"][0]["reason"] == "already_assigned"


def test_admin_homework_and_plan_validation(client):
    ctx = _make_context(client)
    bad = client.post(
        "/api/v1/admin/homeworks?subject=psychology",
        json={
            "title": "没有题目",
            "unit_id": ctx["unit_id"],
            "topic_id": ctx["topic_id"],
            "question_ids": [],
        },
    )
    assert bad.status_code == 422
    frq = client.get(
        "/api/v1/admin/content/questions",
        params={
            "subject": "psychology",
            "section": "FRQ",
            "source": "all",
            "limit": 1,
        },
    ).json()
    if frq["questions"]:
        rejected = client.post(
            "/api/v1/admin/homeworks?subject=psychology",
            json={
                "title": "FRQ 作业",
                "unit_id": ctx["unit_id"],
                "topic_id": ctx["topic_id"],
                "question_ids": [frq["questions"][0]["question_id"]],
            },
        )
        assert rejected.status_code == 400
        assert rejected.json()["code"] == "QUESTION_TYPE_UNSUPPORTED"


def test_question_ids_select_all_and_taxonomy(client):
    _admin_login(client)
    taxonomy = _taxonomy(client)
    topic = next(
        item
        for unit in taxonomy["units"]
        for item in unit["topics"]
        if item["question_count"] >= 4
    )
    response = client.get(
        "/api/v1/admin/content/questions/ids",
        params={
            "subject": "psychology",
            "topic": topic["topic_id"],
            "section": "MCQ",
            "max": 2000,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["question_ids"]
    assert len(payload["question_ids"]) == min(
        payload["total"], 2000
    )
    assert len(set(payload["question_ids"])) == len(payload["question_ids"])


def test_homework_edit_refreshes_pending_task_and_plan_delete_guard(client):
    ctx = _make_context(client)
    hw = _create_homework(client, ctx, "原标题", ctx["question_ids"][:1])
    plan_id = _create_plan(client, ctx, [hw["id"]])
    today = shanghai_date(utcnow())
    _assign(client, plan_id, ctx["student_id"], today, today)

    before = _day(client, today)
    task = next(
        task
        for group in before["assignments"]
        for task in group["tasks"]
    )
    assert task["homework_title"] == "原标题"
    assert task["note"] == "课堂作业备注"

    patched = client.patch(
        f"/api/v1/admin/homeworks/{hw['id']}?subject=psychology",
        json={"title": "新标题", "note": "新备注"},
    )
    assert patched.status_code == 200, patched.text
    after = _day(client, today)
    updated = next(
        task
        for group in after["assignments"]
        for task in group["tasks"]
    )
    assert updated["homework_title"] == "新标题"
    assert updated["note"] == "新备注"

    blocked = client.delete(f"/api/v1/admin/study-plans/{plan_id}?subject=psychology")
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "PLAN_IN_USE"


def test_student_list_has_active_plan_count(client):
    ctx = _make_context(client)
    hw = _create_homework(client, ctx, "列表计数作业", ctx["question_ids"][:1])
    plan_id = _create_plan(client, ctx, [hw["id"]])
    today = shanghai_date(utcnow())
    _assign(client, plan_id, ctx["student_id"], today, today)

    response = client.get("/api/v1/admin/students?limit=200")
    assert response.status_code == 200, response.text
    row = next(
        item for item in response.json()["students"] if item["id"] == ctx["student_id"]
    )
    assert row["active_plan_count"] == 1
    assert row["latest_plan_title"] == "测试陪跑计划"


def test_overdue_tasks_are_actionable_and_in_backlog(client):
    ctx = _make_context(client)
    hw1 = _create_homework(client, ctx, "逾期作业一", ctx["question_ids"][:1])
    hw2 = _create_homework(client, ctx, "逾期作业二", ctx["question_ids"][1:2])
    plan_id = _create_plan(client, ctx, [hw1["id"], hw2["id"]])
    today = shanghai_date(utcnow())
    start = today - timedelta(days=3)
    _assign(client, plan_id, ctx["student_id"], start, today)

    calendar = _calendar(client)
    assert calendar["overdue_days"] == 1
    assert len(calendar["backlog"]) == 2
    assert {task["status"] for task in calendar["backlog"]} == {"overdue", "pending"}
    assert all(task["locked"] is False for task in calendar["backlog"])

    # The today task is later in the sequence than an overdue task, but it is
    # still directly startable so the student can catch up in any order.
    detail = _day(client, today)
    today_tasks = [
        task for group in detail["assignments"] for task in group["tasks"]
    ]
    assert today_tasks and today_tasks[0]["locked"] is False
    started = client.post(
        f"/api/v1/study-calendar/tasks/{today_tasks[0]['task_id']}/start",
        params={"subject": "psychology"},
    )
    assert started.status_code == 200, started.text


def test_homework_qa_and_notifications(client):
    _clear_qa()
    ctx = _make_context(client)
    hw = _create_homework(client, ctx, "答疑演示作业", ctx["question_ids"][:2])
    plan_id = _create_plan(client, ctx, [hw["id"]])
    today = shanghai_date(utcnow())
    _assign(client, plan_id, ctx["student_id"], today, today)

    detail = _day(client, today)
    task = next(
        task for group in detail["assignments"] for task in group["tasks"]
    )
    started = client.post(
        f"/api/v1/study-calendar/tasks/{task['task_id']}/start",
        params={"subject": "psychology"},
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["session_id"]
    session_payload = client.get(f"/api/v1/practice-sessions/{session_id}").json()
    question_id = session_payload["questions"][0]["question_id"]

    created = client.post(
        "/api/v1/qa/questions?subject=psychology",
        json={
            "session_id": session_id,
            "question_id": question_id,
            "content": "老师，这里的强化和惩罚怎么区分？",
        },
    )
    assert created.status_code == 200, created.text
    thread_id = created.json()["id"]

    listed = client.get(
        f"/api/v1/qa/questions/{question_id}?session_id={session_id}"
    )
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["threads"]) == 1
    assert listed.json()["threads"][0]["is_mine"] is True

    preview = client.get(f"/api/v1/qa/threads/{thread_id}/question")
    assert preview.status_code == 200, preview.text
    preview_data = preview.json()
    assert preview_data["question_id"] == question_id
    assert preview_data["options"]
    assert "answer_text" not in preview_data
    assert "correct_label" not in preview_data
    assert all("is_correct" not in option for option in preview_data["options"])

    admin_unread = client.get("/api/v1/admin/qa/unread-count")
    assert admin_unread.status_code == 200, admin_unread.text
    assert admin_unread.json()["unread"] == 1

    replied = client.post(
        f"/api/v1/admin/qa/threads/{thread_id}/replies",
        json={"content": "强化增加行为，惩罚减少行为；看行为频率的变化。"},
    )
    assert replied.status_code == 200, replied.text
    assert replied.json()["is_teacher"] is True

    assert client.get("/api/v1/qa/unread-count").json()["unread"] == 1
    my_threads = client.get("/api/v1/qa/my-threads")
    assert my_threads.status_code == 200, my_threads.text
    assert my_threads.json()["threads"][0]["unread"] is True

    thread = client.get(f"/api/v1/qa/threads/{thread_id}")
    assert thread.status_code == 200, thread.text
    assert len(thread.json()["replies"]) == 1
    assert client.get("/api/v1/qa/unread-count").json()["unread"] == 0

    follow_up = client.post(
        f"/api/v1/qa/threads/{thread_id}/replies",
        json={"content": "明白了，谢谢老师！"},
    )
    assert follow_up.status_code == 200, follow_up.text
    assert client.get("/api/v1/admin/qa/unread-count").json()["unread"] == 1


def test_qa_unavailable_outside_homework_and_visible_to_classmates(client):
    _clear_qa()
    ctx = _make_context(client)
    hw = _create_homework(client, ctx, "同学可见作业", ctx["question_ids"][:1])
    plan_id = _create_plan(client, ctx, [hw["id"]])
    today = shanghai_date(utcnow())
    _assign(client, plan_id, ctx["student_id"], today, today)

    # A normal topic practice session cannot use Q&A.
    groups = client.get("/api/v1/practice-groups").json()
    topics = client.get(
        f"/api/v1/practice-groups/{groups[0]['group_id']}/topics"
    ).json()
    topic_session = client.post(
        "/api/v1/practice-sessions",
        json={"source": "topic", "topic_id": topics[0]["topic_id"]},
    ).json()
    topic_question = topic_session["questions"][0]["question_id"]
    blocked = client.post(
        "/api/v1/qa/questions?subject=psychology",
        json={
            "session_id": topic_session["session"]["id"],
            "question_id": topic_question,
            "content": "普通练习不应该能提问",
        },
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "QA_NOT_AVAILABLE"

    # First student asks in the homework.
    detail = _day(client, today)
    task = next(task for group in detail["assignments"] for task in group["tasks"])
    started = client.post(
        f"/api/v1/study-calendar/tasks/{task['task_id']}/start",
        params={"subject": "psychology"},
    )
    session_id = started.json()["session_id"]
    question_id = client.get(
        f"/api/v1/practice-sessions/{session_id}"
    ).json()["questions"][0]["question_id"]
    created = client.post(
        "/api/v1/qa/questions?subject=psychology",
        json={
            "session_id": session_id,
            "question_id": question_id,
            "content": "这道题为什么选 B？",
        },
    )
    assert created.status_code == 200, created.text

    # A classmate with the same assigned homework/question sees the thread.
    login(client)
    first_thread_id = created.json()["id"]
    blocked_preview = client.get(f"/api/v1/qa/threads/{first_thread_id}/question")
    assert blocked_preview.status_code == 404
    second_id = _student_id(client)
    _assign(client, plan_id, second_id, today, today)
    second_detail = _day(client, today)
    second_task = next(
        task for group in second_detail["assignments"] for task in group["tasks"]
    )
    second_started = client.post(
        f"/api/v1/study-calendar/tasks/{second_task['task_id']}/start",
        params={"subject": "psychology"},
    )
    assert second_started.status_code == 200, second_started.text
    second_session = second_started.json()["session_id"]
    visible = client.get(
        f"/api/v1/qa/questions/{question_id}?session_id={second_session}"
    )
    assert visible.status_code == 200, visible.text
    assert len(visible.json()["threads"]) == 1
    assert visible.json()["threads"][0]["is_mine"] is False
