"""Regression coverage for public property and inquiry APIs."""
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")
load_dotenv(Path(__file__).parents[2] / "frontend" / ".env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


@pytest.fixture
def api_client():
    return requests.Session()


def test_get_properties_returns_expected_records(api_client):
    response = api_client.get(f"{BASE_URL}/api/properties", timeout=15)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    assert {"id", "name", "location", "price", "type", "listing"}.issubset(data[0])


def test_get_property_detail_and_not_found(api_client):
    response = api_client.get(f"{BASE_URL}/api/properties/p1", timeout=15)
    assert response.status_code == 200
    assert response.json()["id"] == "p1"
    missing = api_client.get(f"{BASE_URL}/api/properties/does-not-exist", timeout=15)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Property not found"


@pytest.mark.parametrize("params, expected", [
    ({"listing": "Rent"}, {"p3", "p5"}),
    ({"location": "Marina"}, {"p6"}),
    ({"property_type": "Villa"}, {"p1", "p5"}),
    ({"listing": "All", "location": "Dubai"}, {"p1", "p2", "p3", "p4", "p5", "p6"}),
])
def test_property_filters(api_client, params, expected):
    response = api_client.get(f"{BASE_URL}/api/properties", params=params, timeout=15)
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == expected


def test_create_inquiry_validates_and_returns_success(api_client):
    payload = {
        "name": "TEST_UI Reviewer",
        "phone": "+971500000001",
        "email": "test-ui-reviewer@example.com",
        "message": "TEST inquiry from regression suite",
    }
    response = api_client.post(f"{BASE_URL}/api/inquiries", json=payload, timeout=15)
    assert response.status_code == 200
    assert response.json()["success"] is True
    invalid = api_client.post(f"{BASE_URL}/api/inquiries", json={"name": "Incomplete"}, timeout=15)
    assert invalid.status_code == 422