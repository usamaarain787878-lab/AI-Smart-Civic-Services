import sys
from pathlib import Path

# Dynamic Path Setup (Fixes import errors regardless of file location)
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR if (CURRENT_DIR / "app.py").exists() else CURRENT_DIR.parent

for path in (str(PROJECT_ROOT), str(PROJECT_ROOT / "ai_civic_services")):
    if path not in sys.path:
        sys.path.insert(0, path)

from database.db_manager import get_all_complaints
from services.ai_service import AIService
from services.analytics_service import AnalyticsService


def test_department_assignment_for_water_issues():
    analyzer = AIService()
    department = analyzer.assign_department("Water leak in street", "Pipe burst near main road")
    assert department == "Water & Sewerage Board"


def test_multilingual_roman_urdu_complaint_is_routed_to_water_department():
    analyzer = AIService()
    analysis = analyzer.analyze_complaint("Pani ki nali toot gayi", "Gali mein bohat paani aa raha hai")
    assert analysis["category"] in ("Water", "Water/Drainage", "Drainage")
    assert analysis["department"] == "Water & Sewerage Board"


def test_analytics_exposes_distribution_and_geospatial_points():
    analytics = AnalyticsService()
    complaints = [
        {
            "id": 1,
            "title": "Water leak",
            "description": "Burst pipe",
            "location": "Qasimabad",
            "category": "Water",
            "priority": "High",
            "latitude": 25.3923,
            "longitude": 68.3270,
            "status": "Submitted",
        },
        {
            "id": 2,
            "title": "Garbage pile",
            "description": "Overflowing waste",
            "location": "Latifabad",
            "category": "Sanitation",
            "priority": "Medium",
            "latitude": 25.3924,
            "longitude": 68.3550,
            "status": "In Progress",
        },
    ]

    distribution = analytics.get_frequency_distribution(complaints, "category")
    geo_points = analytics.get_geospatial_points(complaints)

    assert distribution["Water"] == 1
    assert geo_points[0]["location"] == "Qasimabad"
    assert geo_points[0]["priority"] == "High"


def test_submit_complaint_route_creates_record():
    from app import app

    client = app.test_client()
    response = client.post(
        "/submit-complaint",
        data={
            "title": "Water leakage",
            "description": "Burst pipe near school",
            "location": "Qasimabad",
            "reporter_name": "Ali",
            "reporter_email": "ali@example.com",
            "citizen_count": "2",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    complaints = get_all_complaints()
    assert any(complaint["title"] == "Water leakage" for complaint in complaints)


def test_auth_routes_render_templates_properly():
    from app import app

    client = app.test_client()
    res_login = client.get("/login")
    assert res_login.status_code == 200
    assert b"Account Login" in res_login.data

    res_reg = client.get("/register")
    assert res_reg.status_code == 200
    assert b"Create Account" in res_reg.data