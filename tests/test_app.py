from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def restore_participants():
    original_participants = {
        activity_name: deepcopy(activity["participants"])
        for activity_name, activity in activities.items()
    }

    yield

    for activity_name, participants in original_participants.items():
        activities[activity_name]["participants"] = participants


def test_root_redirects_to_static_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_details(client):
    response = client.get("/activities")

    assert response.status_code == 200
    activity = response.json()["Chess Club"]
    assert activity["max_participants"] == 12
    assert activity["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_participant(client):
    email = "new.student@mergington.edu"

    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for Chess Club"
    }
    assert email in activities["Chess Club"]["participants"]


def test_duplicate_signup_returns_bad_request(client):
    email = "michael@mergington.edu"
    participants_before = activities["Chess Club"]["participants"].copy()

    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": email},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }
    assert activities["Chess Club"]["participants"] == participants_before


def test_signup_for_unknown_activity_returns_not_found(client):
    response = client.post(
        "/activities/Robotics Club/signup",
        params={"email": "new.student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_removes_participant(client):
    email = "michael@mergington.edu"

    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from Chess Club"
    }
    assert email not in activities["Chess Club"]["participants"]


@pytest.mark.parametrize(
    ("activity_name", "email", "detail"),
    [
        (
            "Robotics Club",
            "new.student@mergington.edu",
            "Activity not found",
        ),
        (
            "Chess Club",
            "not.registered@mergington.edu",
            "Student is not signed up for this activity",
        ),
    ],
)
def test_unregister_errors_return_not_found(client, activity_name, email, detail):
    participants_before = activities["Chess Club"]["participants"].copy()

    response = client.delete(
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": detail}
    assert activities["Chess Club"]["participants"] == participants_before
