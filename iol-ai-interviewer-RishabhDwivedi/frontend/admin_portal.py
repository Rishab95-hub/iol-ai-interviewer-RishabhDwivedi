"""
Admin Portal - Streamlit UI for Phase 2
Manage jobs, review candidates, monitor interviews
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# Configuration
API_BASE_URL = "http://localhost:8001/api"

st.set_page_config(
    page_title="Admin Portal - AI Interviewer",
    page_icon="⚙️",
    layout="wide"
)

def api_get(endpoint: str):
    """Make GET request to API"""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def api_post(endpoint: str, json_data: dict = None):
    """Make POST request to API"""
    try:
        response = requests.post(f"{API_BASE_URL}{endpoint}", json=json_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def api_put(endpoint: str, json_data: dict = None):
    """Make PUT request to API"""
    try:
        response = requests.put(f"{API_BASE_URL}{endpoint}", json=json_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def api_delete(endpoint: str):
    """Make DELETE request to API"""
    try:
        response = requests.delete(f"{API_BASE_URL}{endpoint}")
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"API Error: {e}")
        return False

def dashboard_page():
    """Admin dashboard with key metrics"""
    st.title("📊 Admin Dashboard")
    
    # Fetch all jobs
    jobs = api_get("/jobs/") or []
    candidates_total = 0
    interviews_total = 0
    
    # Count active jobs
    active_jobs = len([j for j in jobs if j['status'] == 'ACTIVE'])
    
    # Get all candidates
    for job in jobs:
        candidates = api_get(f"/candidates/?job_id={job['id']}") or []
        candidates_total += len(candidates)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Jobs", len(jobs))
    with col2:
        st.metric("Active Jobs", active_jobs)
    with col3:
        st.metric("Total Candidates", candidates_total)
    with col4:
        st.metric("Interviews", interviews_total)
    
    # Recent activity
    st.markdown("---")
    st.markdown("### Recent Jobs")
    
    if jobs:
        recent_jobs = sorted(jobs, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
        
        for job in recent_jobs:
            with st.expander(f"📄 {job['title']} - {job['status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Department:** {job.get('department', 'N/A')}")
                    st.write(f"**Location:** {job.get('location', 'N/A')}")
                with col2:
                    st.write(f"**Posted:** {job.get('posted_at', 'N/A')[:10] if job.get('posted_at') else 'Not posted'}")
                    st.write(f"**Status:** {job['status']}")

def jobs_management_page():
    """Manage job postings"""
    st.title("💼 Job Management")
    
    tab1, tab2 = st.tabs(["All Jobs", "Create New Job"])
    
    with tab1:
        # List all jobs
        jobs = api_get("/jobs/") or []
        
        if not jobs:
            st.info("No jobs created yet. Create one in the 'Create New Job' tab.")
        else:
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All", "DRAFT", "ACTIVE", "PAUSED", "CLOSED"])
            
            # Filter jobs with case-insensitive comparison
            if status_filter != "All":
                jobs = [j for j in jobs if (j['status'].upper() if isinstance(j['status'], str) else str(j['status'])) == status_filter]
            
            st.write(f"Showing {len(jobs)} jobs")
            
            # Display jobs
            for job in jobs:
                with st.expander(f"📄 {job['title']} - {job['status']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**ID:** {job['id']}")
                        st.markdown(f"**Department:** {job.get('department', 'N/A')}")
                        st.markdown(f"**Location:** {job.get('location', 'N/A')}")
                        st.markdown(f"**Experience Level:** {job.get('experience_level', 'N/A')}")
                        st.markdown(f"**Interview Template:** {job.get('interview_template', 'N/A')}")
                        
                        if job.get('description'):
                            st.markdown("**Description:**")
                            st.write(job['description'][:200] + "...")
                    
                    with col2:
                        # Action buttons
                        job_status = job['status'].upper() if isinstance(job['status'], str) else str(job['status'])
                        
                        if job_status == 'DRAFT':
                            if st.button("Publish", key=f"pub_{job['id']}"):
                                api_post(f"/jobs/{job['id']}/publish")
                                st.success("Job published!")
                                st.rerun()
                        elif job_status == 'ACTIVE':
                            if st.button("Pause", key=f"pause_{job['id']}"):
                                # Update status to paused (lowercase for API)
                                update_data = {
                                    'status': 'paused'
                                }
                                api_put(f"/jobs/{job['id']}", json_data=update_data)
                                st.success("Job paused!")
                                st.rerun()
                            if st.button("Close", key=f"close_{job['id']}"):
                                api_post(f"/jobs/{job['id']}/close")
                                st.success("Job closed!")
                                st.rerun()
                        elif job_status == 'PAUSED':
                            if st.button("Activate", key=f"activate_{job['id']}"):
                                # Reactivate the job
                                update_data = {
                                    'status': 'active'
                                }
                                api_put(f"/jobs/{job['id']}", json_data=update_data)
                                st.success("Job activated!")
                                st.rerun()
                            if st.button("Close", key=f"close_{job['id']}"):
                                api_post(f"/jobs/{job['id']}/close")
                                st.success("Job closed!")
                                st.rerun()
                        
                        # View candidates
                        candidates = api_get(f"/candidates/?job_id={job['id']}") or []
                        st.metric("Applications", len(candidates))
    
    with tab2:
        # Create new job form
        st.markdown("### Create New Job Posting")
        
        with st.form("create_job_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Job Title*")
                department = st.text_input("Department")
                location = st.text_input("Location")
                job_type = st.selectbox("Job Type", ["Full-time", "Part-time", "Contract", "Internship"])
            
            with col2:
                experience_level = st.selectbox("Experience Level", ["Entry", "Mid", "Senior", "Lead", "Executive"])
                interview_template = st.selectbox("Interview Template", ["backend-engineer", "data-scientist", "frontend-engineer"])
                duration = st.number_input("Interview Duration (minutes)", min_value=15, max_value=120, value=60)
            
            description = st.text_area("Job Description*", height=150)
            
            st.markdown("### Requirements (one per line)")
            requirements_text = st.text_area("Requirements", height=100)
            
            st.markdown("### Nice to Have (one per line)")
            nice_to_have_text = st.text_area("Nice to Have", height=100)
            
            st.markdown("### Responsibilities (one per line)")
            responsibilities_text = st.text_area("Responsibilities", height=100)
            
            col1, col2 = st.columns(2)
            with col1:
                submit_draft = st.form_submit_button("Save as Draft")
            with col2:
                submit_publish = st.form_submit_button("Save & Publish", type="primary")
            
            if submit_draft or submit_publish:
                if not title or not description:
                    st.error("Please fill in Title and Description")
                else:
                    # Parse lists
                    requirements = [r.strip() for r in requirements_text.split('\n') if r.strip()]
                    nice_to_have = [n.strip() for n in nice_to_have_text.split('\n') if n.strip()]
                    responsibilities = [r.strip() for r in responsibilities_text.split('\n') if r.strip()]
                    
                    job_data = {
                        "title": title,
                        "department": department,
                        "location": location,
                        "job_type": job_type,
                        "experience_level": experience_level,
                        "description": description,
                        "requirements": requirements,
                        "nice_to_have": nice_to_have,
                        "responsibilities": responsibilities,
                        "interview_template": interview_template,
                        "interview_duration_minutes": duration,
                        "status": "ACTIVE" if submit_publish else "DRAFT"
                    }
                    
                    result = api_post("/jobs/", json_data=job_data)
                    
                    if result:
                        st.success(f"✅ Job created successfully! ID: {result['id']}")
                        st.balloons()

def candidates_review_page():
    """Review candidate applications"""
    st.title("👥 Candidate Review")
    
    # Get all jobs for filtering
    jobs = api_get("/jobs/") or []
    
    if not jobs:
        st.info("No jobs created yet.")
        return
    
    # Job selector
    job_titles = {j['id']: f"{j['title']} ({j['id']})" for j in jobs}
    selected_job_id = st.selectbox("Select Job", options=list(job_titles.keys()), format_func=lambda x: job_titles[x])
    
    # Fetch candidates for selected job
    candidates = api_get(f"/candidates/?job_id={selected_job_id}") or []
    
    if not candidates:
        st.info("No applications for this job yet.")
        return
    
    st.write(f"**{len(candidates)} applications**")
    
    # Display candidates
    for candidate in candidates:
        with st.expander(f"👤 {candidate['first_name']} {candidate['last_name']} - {candidate['status']}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Email:** {candidate['email']}")
                st.markdown(f"**Phone:** {candidate.get('phone', 'N/A')}")
                st.markdown(f"**LinkedIn:** {candidate.get('linkedin_url', 'N/A')}")
                st.markdown(f"**Applied:** {candidate['applied_at'][:10]}")
                st.markdown(f"**Status:** {candidate['status']}")
                
                if candidate.get('cover_letter'):
                    st.markdown("**Cover Letter:**")
                    st.write(candidate['cover_letter'])
                
                if candidate.get('resume_text'):
                    with st.expander("View Resume Text"):
                        st.text(candidate['resume_text'][:1000] + "..." if len(candidate['resume_text']) > 1000 else candidate['resume_text'])
            
            with col2:
                # Status update
                candidate_status_upper = candidate['status'].upper() if isinstance(candidate['status'], str) else str(candidate['status'])
                status_options = ["APPLIED", "INTERVIEW_SCHEDULED", "INTERVIEW_IN_PROGRESS", "INTERVIEW_COMPLETED", "UNDER_REVIEW", "REJECTED", "ACCEPTED"]
                
                try:
                    current_index = status_options.index(candidate_status_upper)
                except ValueError:
                    current_index = 0
                
                new_status = st.selectbox(
                    "Update Status",
                    status_options,
                    index=current_index,
                    key=f"status_{candidate['id']}"
                )
                
                if st.button("Update", key=f"update_{candidate['id']}"):
                    api_put(f"/candidates/{candidate['id']}/status", json_data={"status": new_status})
                    st.success("Status updated!")
                    st.rerun()
                
                # Schedule interview
                if st.button("📅 Schedule Interview", key=f"schedule_{candidate['id']}"):
                    st.session_state[f'scheduling_{candidate["id"]}'] = True
                
                # Show scheduling form if triggered
                if st.session_state.get(f'scheduling_{candidate["id"]}', False):
                    st.markdown("---")
                    st.markdown("#### Interview Scheduling")
                    
                    col_date, col_time = st.columns(2)
                    with col_date:
                        interview_date = st.date_input(
                            "Date",
                            key=f"date_{candidate['id']}"
                        )
                    with col_time:
                        interview_time = st.time_input(
                            "Time",
                            key=f"time_{candidate['id']}"
                        )
                    
                    interview_format = st.selectbox(
                        "Format",
                        ["video", "audio", "phone", "text"],
                        key=f"format_{candidate['id']}"
                    )
                    
                    meeting_link = None
                    if interview_format in ["video", "audio"]:
                        meeting_link = st.text_input(
                            "Meeting Link (Zoom, Teams, etc.)",
                            placeholder="https://zoom.us/j/...",
                            key=f"link_{candidate['id']}"
                        )
                    
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Confirm Schedule", key=f"confirm_{candidate['id']}"):
                            from datetime import datetime
                            scheduled_datetime = datetime.combine(interview_date, interview_time)
                            
                            job_for_template = next((j for j in jobs if j['id'] == selected_job_id), None)
                            interview_template = job_for_template.get('interview_template', 'backend-engineer') if job_for_template else 'backend-engineer'
                            
                            interview_data = {
                                "candidate_id": candidate['id'],
                                "job_id": selected_job_id,
                                "template_name": interview_template,
                                "scheduled_date": scheduled_datetime.isoformat(),
                                "interview_format": interview_format
                            }
                            
                            if meeting_link:
                                interview_data["meeting_link"] = meeting_link
                            
                            result = api_post("/interviews/", json_data=interview_data)
                            if result:
                                st.success(f"Interview scheduled for {interview_date} at {interview_time}!")
                                del st.session_state[f'scheduling_{candidate["id"]}']
                                st.rerun()
                    
                    with col_cancel:
                        if st.button("❌ Cancel", key=f"cancel_{candidate['id']}"):
                            del st.session_state[f'scheduling_{candidate["id"]}']
                            st.rerun()

def interviews_monitor_page():
    """Monitor ongoing interviews"""
    st.title("🎤 Interview Monitoring")
    
    # Get all interviews
    jobs = api_get("/jobs/") or []
    all_interviews = []
    
    for job in jobs:
        interviews = api_get(f"/interviews/?job_id={job['id']}") or []
        for interview in interviews:
            interview['job_title'] = job['title']
            all_interviews.append(interview)
    
    if not all_interviews:
        st.info("No interviews scheduled yet.")
        return
    
    # Filter by status
    status_filter = st.selectbox("Filter by Status", ["All", "PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"])
    
    if status_filter != "All":
        all_interviews = [i for i in all_interviews if (i['status'].upper() if isinstance(i['status'], str) else str(i['status'])) == status_filter]
    
    st.write(f"**{len(all_interviews)} interviews**")
    
    # Display interviews
    for interview in all_interviews:
        # Get candidate info
        candidate = api_get(f"/candidates/{interview['candidate_id']}")
        
        with st.expander(f"🎤 {candidate['first_name'] if candidate else 'Unknown'} - {interview['status']}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Job:** {interview['job_title']}")
                st.markdown(f"**Candidate:** {candidate['first_name']} {candidate['last_name']}" if candidate else "Unknown")
                st.markdown(f"**Status:** {interview['status']}")
                st.markdown(f"**Started:** {interview.get('started_at', 'Not started')}")
                
                interview_status_upper = interview['status'].upper() if isinstance(interview['status'], str) else str(interview['status'])
                
                if interview_status_upper == 'COMPLETED':
                    st.markdown(f"**Completed:** {interview.get('completed_at', 'N/A')}")
                    st.markdown(f"**Duration:** {interview.get('duration_seconds', 0) // 60} minutes")
                
                # Show conversation
                if interview.get('conversation_history'):
                    with st.expander("View Conversation"):
                        for msg in interview['conversation_history']:
                            role = "🤖" if msg['role'] == 'assistant' else "👤"
                            st.markdown(f"**{role}:** {msg['content']}")
            
            with col2:
                st.metric("Progress", f"{interview.get('current_question_index', 0)}/10")
                
                interview_status_upper = interview['status'].upper() if isinstance(interview['status'], str) else str(interview['status'])
                
                # Delete button
                if st.button("🗑️ Delete", key=f"delete_{interview['id']}"):
                    result = api_delete(f"/interviews/{interview['id']}")
                    if result is not None:
                        st.success("Interview deleted!")
                        st.rerun()
                    else:
                        st.error("Failed to delete interview")
                
                if interview_status_upper == 'COMPLETED':
                    # Generate Report button
                    if st.button("📊 Generate Report", key=f"btn_report_{interview['id']}"):
                        with st.spinner("Generating comprehensive report..."):
                            report = api_post(f"/interviews/{interview['id']}/report")
                            if report and isinstance(report, dict):
                                st.session_state[f"report_{interview['id']}"] = report
                                st.rerun()
                            else:
                                st.error("Failed to generate report. The interview may not have dimension scores.")
            
            # Display report outside columns for full width
            if interview_status_upper == 'COMPLETED' and f"report_{interview['id']}" in st.session_state:
                report = st.session_state[f"report_{interview['id']}"]
                if report and isinstance(report, dict):
                    st.success("✅ Report Generated")
                    
                    # Display report in full width without expander
                    st.markdown("---")
                    st.markdown("## 📄 Comprehensive Interview Report")
                    st.markdown("---")
                    
                    # Candidate Summary
                    st.markdown("### 👤 Candidate Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Name", report.get('candidate_name', 'N/A'))
                    with col2:
                        st.metric("Position", report.get('position', 'N/A'))
                    with col3:
                        interview_date = report.get('interview_date', 'N/A')
                        if interview_date != 'N/A':
                            from datetime import datetime
                            try:
                                dt = datetime.fromisoformat(interview_date.replace('Z', '+00:00'))
                                interview_date = dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                pass
                        st.metric("Interview Date", interview_date)
                    with col4:
                        duration = report.get('duration_minutes', 0)
                        st.metric("Duration", f"{duration:.1f} min" if duration else "N/A")
                    
                    st.markdown("---")
                    
                    # Overall Assessment
                    st.markdown("### 🎯 Overall Assessment")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Recommendation", report.get('recommendation', 'N/A').replace('_', ' ').title())
                    with col2:
                        st.metric("Overall Score", f"{report.get('overall_score', 0):.2f}/5.0")
                    with col3:
                        st.metric("Confidence", report.get('confidence_level', 'N/A'))
                    
                    st.markdown("---")
                    
                    # Summary
                    if report.get('summary'):
                        st.markdown("### 📝 Executive Summary")
                        st.info(report['summary'])
                        st.markdown("")
                    
                    # Dimension Scores
                    if report.get('dimension_scores'):
                        st.markdown("### 📊 Dimension Scores")
                        st.markdown("")
                        for dim in report['dimension_scores']:
                            with st.container():
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"**{dim['dimension_name']}** - *{dim['level']}*")
                                with col2:
                                    st.markdown(f"**{dim['score']:.2f}/5.0** ({dim['percentage']:.0f}%)")
                                st.caption(dim.get('reasoning', 'No reasoning provided'))
                                if dim.get('evidence'):
                                    with st.expander("📌 View Evidence"):
                                        for evidence in dim['evidence']:
                                            st.markdown(f"- *\"{evidence}\"*")
                                st.markdown("")
                        st.markdown("---")
                    
                    # Key Strengths
                    if report.get('key_strengths'):
                        st.markdown("### ✅ Key Strengths")
                        st.markdown("")
                        for strength in report['key_strengths']:
                            if isinstance(strength, dict):
                                st.markdown(f"**{strength.get('title', 'Strength')}**")
                                st.write(strength.get('description', ''))
                                if strength.get('evidence'):
                                    with st.expander("📌 Supporting Evidence"):
                                        for evidence in strength['evidence']:
                                            st.markdown(f"- *\"{evidence}\"*")
                            else:
                                st.markdown(f"- {strength}")
                            st.markdown("")
                        st.markdown("---")
                    
                    # Areas of Concern
                    if report.get('areas_of_concern'):
                        st.markdown("### ⚠️ Areas of Concern")
                        st.markdown("")
                        for concern in report['areas_of_concern']:
                            if isinstance(concern, dict):
                                severity = concern.get('severity', 'moderate')
                                emoji = "🔴" if severity == "major" else "🟡" if severity == "moderate" else "🟢"
                                st.markdown(f"{emoji} **{concern.get('title', 'Concern')}** *({severity})*")
                                st.write(concern.get('description', ''))
                                if concern.get('evidence'):
                                    with st.expander("📌 Supporting Evidence"):
                                        for evidence in concern['evidence']:
                                            st.markdown(f"- *\"{evidence}\"*")
                            else:
                                st.markdown(f"- {concern}")
                            st.markdown("")
                        st.markdown("---")
                    
                    # Notable Quotes
                    if report.get('notable_quotes'):
                        st.markdown("### 💬 Notable Quotes")
                        st.markdown("")
                        for quote in report['notable_quotes']:
                            if isinstance(quote, dict):
                                st.markdown(f"> *\"{quote.get('quote', '')}\"*")
                                st.caption(f"**Context:** {quote.get('context', '')}")
                                if quote.get('dimension'):
                                    st.caption(f"**Related to:** {quote['dimension']}")
                            else:
                                st.markdown(f"> *\"{quote}\"*")
                            st.markdown("")
                        st.markdown("---")
                    
                    # Follow-up Questions
                    if report.get('suggested_follow_ups'):
                        st.markdown("### ❓ Suggested Follow-up Questions")
                        st.markdown("")
                        for i, followup in enumerate(report['suggested_follow_ups'], 1):
                            if isinstance(followup, dict):
                                st.markdown(f"**{i}. {followup.get('question', '')}**")
                                st.caption(f"💡 *Reason:* {followup.get('reason', '')}")
                                st.caption(f"📊 *Dimension:* {followup.get('dimension', '')}")
                            else:
                                st.markdown(f"**{i}.** {followup}")
                            st.markdown("")
                        st.markdown("---")
                    
                    # Transcript
                    if report.get('full_transcript'):
                        st.markdown("### 📜 Full Transcript")
                        with st.expander("Click to view full conversation", expanded=False):
                            st.text_area("Conversation", report['full_transcript'], height=400, label_visibility="collapsed")

# Main navigation
def main():
    st.sidebar.title("⚙️ Admin Portal")
    
    page = st.sidebar.radio(
        "Navigation",
        ['dashboard', 'jobs', 'candidates', 'interviews'],
        format_func=lambda x: {
            'dashboard': '📊 Dashboard',
            'jobs': '💼 Jobs',
            'candidates': '👥 Candidates',
            'interviews': '🎤 Interviews'
        }[x]
    )
    
    if page == 'dashboard':
        dashboard_page()
    elif page == 'jobs':
        jobs_management_page()
    elif page == 'candidates':
        candidates_review_page()
    elif page == 'interviews':
        interviews_monitor_page()

if __name__ == "__main__":
    main()
