import os
import sys
from typing import Optional

from flask import Flask, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config.settings import get_settings
from database.db_manager import (
    create_complaint,
    create_user,
    get_all_complaints,
    get_user_by_email,
    get_user_by_id,
    init_db,
    update_complaint_status,
)
from services.ai_service import AIService
from services.analytics_service import AnalyticsService
from services.notifications import NotificationService
from services.reports import ReportService

# Initialize app and services at module level
settings = get_settings()
app = Flask(__name__)
app.secret_key = settings.secret_key

ai_service = AIService()
analytics_service = AnalyticsService()
notification_service = NotificationService()
report_service = ReportService()

# Ensure DB is initialized on module load (works for both Flask and Streamlit)
init_db()


def _normalize_complaints(complaints: list[dict]) -> list[dict]:
    normalized = []
    for complaint in complaints:
        complaint_data = dict(complaint)
        if not complaint_data.get("urgency_score"):
            analysis = ai_service.analyze_complaint(
                complaint_data.get("title", ""), complaint_data.get("description", "")
            )
            complaint_data["urgency_score"] = analysis["urgency_score"]
            complaint_data["department"] = analysis["department"]
            complaint_data["dispatch_status"] = analysis["dispatch_status"]
        if complaint_data.get("assigned_department") is None and complaint_data.get("department"):
            complaint_data["assigned_department"] = complaint_data.get("department")
        normalized.append(complaint_data)
    return normalized


def _current_user() -> Optional[dict]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(int(user_id))


def _can_access_admin(user: Optional[dict]) -> bool:
    if not user:
        return False
    return user.get("role") in {"admin", "department_admin"}


def _visible_complaints(user: Optional[dict], complaints: list[dict]) -> list[dict]:
    if not user or user.get("role") == "admin":
        return complaints
    if user.get("role") == "department_admin":
        department = (user.get("department") or "").lower()
        return [
            complaint
            for complaint in complaints
            if (complaint.get("assigned_department") or complaint.get("department") or "").lower() == department
        ]
    return complaints


def resolve_coordinates(location: str):
    location_lower = (location or "").lower()
    known_locations = {
        "qasimabad": (25.3923, 68.3270),
        "latifabad": (25.3924, 68.3550),
        "hyderabad": (25.3960, 68.3578),
        "karachi": (24.8607, 67.0011),
    }
    for key, coords in known_locations.items():
        if key in location_lower:
            return coords
    return known_locations["hyderabad"]


def _render_streamlit_dashboard() -> None:
    import pandas as pd
    import streamlit as st

    st.set_page_config(page_title="AI Civic Services — Dashboard", layout="wide", page_icon="🏛️")

    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background: #f0f2f6; }
        [data-testid="stSidebar"] { background: #1a1f36; }
        [data-testid="stSidebar"] * { color: #c9d1d9 !important; }
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stTextInput label { color: #8b949e !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: .06em; }

        .kpi-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 20px 24px;
            box-shadow: 0 1px 4px rgba(0,0,0,.08);
            border-left: 4px solid #4f46e5;
        }
        .kpi-card.red   { border-left-color: #ef4444; }
        .kpi-card.amber { border-left-color: #f59e0b; }
        .kpi-card.green { border-left-color: #10b981; }
        .kpi-label { font-size: 0.78rem; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 6px; }
        .kpi-value { font-size: 2rem; font-weight: 700; color: #111827; line-height: 1; }
        .kpi-sub   { font-size: 0.75rem; color: #9ca3af; margin-top: 4px; }

        .badge {
            display: inline-block; border-radius: 999px;
            font-size: 0.72rem; font-weight: 600;
            padding: 2px 10px; line-height: 1.6;
        }
        .badge-high   { background:#ffebe9; color:#cf222e; }
        .badge-medium { background:#fff8c5; color:#9a6700; }
        .badge-low    { background:#dafbe1; color:#116329; }
        .badge-cat    { background:#ddf4ff; color:#0969da; }
        .badge-urgent { background:#ffecd2; color:#bc4c00; }

        .complaint-row {
            background: #fff; border-radius: 10px; padding: 14px 18px;
            margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.06);
            border: 1px solid #e5e7eb;
        }
        .complaint-title { font-size: 0.95rem; font-weight: 600; color: #111827; }
        .complaint-meta  { font-size: 0.78rem; color: #6b7280; margin-top: 4px; }

        .section-header {
            font-size: 1rem; font-weight: 700; color: #374151;
            border-bottom: 2px solid #e5e7eb; padding-bottom: 6px;
            margin: 18px 0 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h1 style='font-size:1.6rem;font-weight:800;color:#1a1f36;margin-bottom:2px;'>"
        "🏛️ AI Civic Services</h1>"
        "<p style='color:#6b7280;font-size:0.85rem;margin-top:0;'>"
        "Adaptive civic operations · Automated dispatch · SLA monitoring</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    all_complaints = _normalize_complaints(get_all_complaints())
    stats = analytics_service.get_statistics(all_complaints)
    sla_ranked = analytics_service.get_sla_ranking(all_complaints)
    sla_summary = analytics_service.get_sla_summary(sla_ranked)

    with st.sidebar:
        st.markdown(
            "<div style='font-size:1.1rem;font-weight:700;color:#fff;"
            "padding:12px 0 18px;border-bottom:1px solid #2d3454;margin-bottom:16px;'>"
            "🔍 Filters</div>",
            unsafe_allow_html=True,
        )

        categories = ["All"] + sorted({c.get("category", "General") for c in all_complaints if c.get("category")})
        selected_category = st.selectbox("Category", categories)

        priorities = ["All", "High", "Medium", "Low"]
        selected_priority = st.selectbox("Priority", priorities)

        search_query = st.text_input("Search complaints", placeholder="Title, location, keyword…")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.78rem;color:#8b949e;'>"
            f"Showing filtered results from <b style='color:#c9d1d9;'>{len(all_complaints)}</b> total complaints</div>",
            unsafe_allow_html=True,
        )

    complaints = all_complaints
    if selected_category != "All":
        complaints = [c for c in complaints if c.get("category") == selected_category]
    if selected_priority != "All":
        complaints = [c for c in complaints if c.get("priority") == selected_priority]
    if search_query:
        q = search_query.lower()
        complaints = [
            c for c in complaints
            if q in (c.get("title") or "").lower()
            or q in (c.get("location") or "").lower()
            or q in (c.get("description") or "").lower()
        ]

    col1, col2, col3, col4 = st.columns(4)
    kpis = [
        (col1, "Total Complaints", stats.get("total", 0), "All time", "blue"),
        (col2, "High Priority", stats.get("high_priority", 0), "Requires attention", "red"),
        (col3, "Urgent SLA", sla_summary.get("urgent", 0), "Within SLA breach window", "amber"),
        (col4, "Overdue", sla_summary.get("overdue", 0), "Past SLA deadline", "red"),
    ]
    for col, label, value, sub, color in kpis:
        col.markdown(
            f"<div class='kpi-card {color}'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{value}</div>"
            f"<div class='kpi-sub'>{sub}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div class='section-header'>📋 Complaints ({len(complaints)} results)</div>",
        unsafe_allow_html=True,
    )

    def _priority_badge(priority: str) -> str:
        p = (priority or "").strip().lower()
        if p == "high":
            return "<span class='badge badge-high'>High</span>"
        if p == "medium":
            return "<span class='badge badge-medium'>Medium</span>"
        return "<span class='badge badge-low'>Low</span>"

    def _category_badge(category: str) -> str:
        return f"<span class='badge badge-cat'>{category or 'General'}</span>"

    def _urgency_badge(score: int) -> str:
        score = score or 0
        if score >= 75:
            return f"<span class='badge badge-urgent'>🔴 {score}</span>"
        if score >= 45:
            return f"<span class='badge badge-medium'>🟡 {score}</span>"
        return f"<span class='badge badge-low'>🟢 {score}</span>"

    view_mode = st.radio("View", ["Card View", "Table View"], horizontal=True, label_visibility="collapsed")

    if not complaints:
        st.info("No complaints match the current filters.")
    elif view_mode == "Table View":
        df = pd.DataFrame([
            {
                "ID": c.get("id", ""),
                "Title": c.get("title", ""),
                "Location": c.get("location", ""),
                "Category": c.get("category", "General"),
                "Priority": c.get("priority", "Low"),
                "Urgency": c.get("urgency_score", 0),
                "Status": c.get("status", ""),
                "Department": c.get("assigned_department") or c.get("department", ""),
                "Dispatch": c.get("dispatch_status", ""),
            }
            for c in complaints
        ])
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Urgency": st.column_config.ProgressColumn(
                    "Urgency Score", min_value=0, max_value=100, format="%d"
                ),
            },
        )
    else:
        for complaint in complaints[:20]:
            st.markdown(
                f"<div class='complaint-row'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
                f"  <div class='complaint-title'>#{complaint.get('id','')} — {complaint.get('title','Complaint')}</div>"
                f"  <div>{_priority_badge(complaint.get('priority',''))} {_category_badge(complaint.get('category',''))}</div>"
                f"</div>"
                f"<div class='complaint-meta'>"
                f"  📍 {complaint.get('location','')} &nbsp;|&nbsp; "
                f"  🏢 {complaint.get('assigned_department') or complaint.get('department','—')} &nbsp;|&nbsp; "
                f"  Urgency: {_urgency_badge(complaint.get('urgency_score', 0))} &nbsp;|&nbsp; "
                f"  {complaint.get('dispatch_status','')}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        if len(complaints) > 20:
            st.caption(f"Showing 20 of {len(complaints)} complaints. Use filters to narrow results.")


@app.route("/", methods=["GET"])
def index():
    complaints = _normalize_complaints(get_all_complaints())
    stats = analytics_service.get_statistics(complaints)
    sla_summary = analytics_service.get_sla_summary(analytics_service.get_sla_ranking(complaints))
    insights = ai_service.generate_insights(complaints)
    statistical_insights = analytics_service.get_statistical_insights(complaints)
    return render_template(
        "index.html",
        complaints=complaints,
        stats=stats,
        sla_summary=sla_summary,
        insights=insights,
        statistical_insights=statistical_insights,
        current_user=_current_user(),
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "citizen")
        department = request.form.get("department", "").strip()
        if not name or not email or not password:
            return render_template("register.html", error="Please enter your name, email, and password.", current_user=_current_user())
        if get_user_by_email(email):
            return render_template("register.html", error="An account with that email already exists.", current_user=_current_user())
        user = create_user(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            department=department if role == "department_admin" else None,
        )
        session["user_id"] = user["id"]
        return redirect(url_for("index"))
    return render_template("register.html", current_user=_current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if user and check_password_hash(user.get("password_hash", ""), password):
            session["user_id"] = user["id"]
            return redirect(request.args.get("next") or url_for("index"))
        return render_template("login.html", error="Invalid email or password.", current_user=_current_user())
    return render_template("login.html", current_user=_current_user())


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/submit", methods=["POST"])
@app.route("/submit-complaint", methods=["POST"])
def submit_complaint_route():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    reporter_name = request.form.get("reporter_name", "").strip()
    reporter_email = request.form.get("reporter_email", "").strip()
    reporter_phone = request.form.get("reporter_phone", "").strip()
    citizen_count = max(1, int(request.form.get("citizen_count", "1") or 1))
    category_override = request.form.get("category_override", "").strip()

    analysis = ai_service.analyze_complaint(title, description)
    category = category_override or analysis["category"]
    priority = analysis["priority"]
    urgency_score = analysis["urgency_score"]
    department = analysis["department"]
    dispatch_status = analysis["dispatch_status"]

    image_file = request.files.get("image")
    image_analysis = {}
    if image_file and image_file.filename:
        image_analysis = ai_service.analyze_image(image_file.read(), image_file.filename)

    raw_latitude = request.form.get("latitude", "").strip()
    raw_longitude = request.form.get("longitude", "").strip()
    if raw_latitude and raw_longitude:
        try:
            latitude = float(raw_latitude)
            longitude = float(raw_longitude)
        except ValueError:
            latitude, longitude = resolve_coordinates(location)
    else:
        latitude, longitude = resolve_coordinates(location)
    
    duplicate_result = ai_service.detect_duplicate(get_all_complaints(), f"{title} {description}")

    ai_output_str = f"Category: {category} | Priority: {priority} | Urgency Score: {urgency_score}/100 | Assigned Dept: {department}"

    complaint = create_complaint(
        title=title,
        description=description,
        location=location,
        reporter_name=reporter_name,
        reporter_email=reporter_email,
        category=category,
        priority=priority,
        status=dispatch_status,
        latitude=latitude,
        longitude=longitude,
        citizen_count=citizen_count,
        image_summary=image_analysis.get("summary"),
        image_label=image_analysis.get("label"),
        image_confidence=image_analysis.get("confidence"),
        visual_severity=image_analysis.get("severity", image_analysis.get("confidence")),
        assigned_department=department,
        duplicate_of=duplicate_result.get("duplicate_id") if duplicate_result.get("is_duplicate") else None,
        reporter_phone=reporter_phone or None,
        ai_output=ai_output_str,
    )
    complaint["urgency_score"] = urgency_score
    complaint["department"] = department
    complaint["dispatch_status"] = dispatch_status
    complaint["assigned_department"] = department
    notification_service.send_registration_notification(complaint.get("id"), reporter_email, reporter_phone or None)
    return redirect(url_for("index"))


@app.route("/admin", methods=["GET"])
def admin():
    current_user_data = _current_user()
    if not _can_access_admin(current_user_data):
        return redirect(url_for("login", next=url_for("admin")))
    complaints = _normalize_complaints(get_all_complaints())
    visible = _visible_complaints(current_user_data, complaints)
    ranked_complaints = analytics_service.get_sla_ranking(visible)
    return render_template("admin.html", complaints=ranked_complaints, copilot_result=None, current_user=current_user_data)


@app.route("/admin/<int:complaint_id>", methods=["POST"])
def update_admin(complaint_id: int):
    current_user_data = _current_user()
    if not _can_access_admin(current_user_data):
        return redirect(url_for("login", next=url_for("admin")))
    status = request.form.get("status", "In Progress")
    priority = request.form.get("priority", "High")
    update_complaint_status(complaint_id, status, priority)
    if current_user_data:
        notification_service.send_status_update(complaint_id, status, current_user_data.get("email", ""))
    return redirect(url_for("admin"))


@app.route("/admin/copilot", methods=["POST"])
@app.route("/assistant", methods=["POST"])
def admin_copilot():
    current_user_data = _current_user()
    query = request.form.get("query", "").strip()
    complaints = _normalize_complaints(get_all_complaints())
    visible = _visible_complaints(current_user_data, complaints)
    result = ai_service.answer_civic_question(query, visible)

    if request.path == "/assistant":
        from flask import jsonify
        return jsonify(result)

    ranked_complaints = analytics_service.get_sla_ranking(visible)
    return render_template("admin.html", complaints=ranked_complaints, copilot_result=result, current_user=current_user_data)



@app.route("/map")
def map_view():
    complaints = _normalize_complaints(get_all_complaints())
    geo_points = analytics_service.get_geospatial_points(complaints)
    return render_template("map.html", complaints=complaints, geo_points=geo_points, current_user=_current_user())


@app.route("/report/pdf")
def download_report():
    complaints = _normalize_complaints(get_all_complaints())
    stats = analytics_service.get_statistics(complaints)
    pdf_bytes = report_service.generate_pdf(complaints, stats)
    return send_file(
        __import__("io").BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="civic_report.pdf",
    )


if __name__ == "__main__":
    if "streamlit" in sys.modules:
        _render_streamlit_dashboard()
    else:
        app.run(debug=True, host="0.0.0.0", port=5000)