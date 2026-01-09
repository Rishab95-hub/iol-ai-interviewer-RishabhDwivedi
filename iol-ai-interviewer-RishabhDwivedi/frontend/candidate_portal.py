"""
Candidate Portal - Streamlit UI for Phase 2
Browse jobs, apply with resume, take AI interviews
"""
import streamlit as st
import requests
from datetime import datetime
from pathlib import Path
import time

# Configuration
API_BASE_URL = "http://localhost:8001/api"
CANDIDATE_ID_KEY = "candidate_id"
SESSION_ID_KEY = "interview_session_id"

st.set_page_config(
    page_title="Candidate Portal - AI Interviewer",
    page_icon="👤",
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

def api_post(endpoint: str, data: dict = None, files: dict = None):
    """Make POST request to API"""
    try:
        if files:
            response = requests.post(
                f"{API_BASE_URL}{endpoint}",
                data=data,
                files=files
            )
        else:
            response = requests.post(
                f"{API_BASE_URL}{endpoint}",
                json=data
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def browse_jobs_page():
    """Job browsing and application page"""
    st.title("🔍 Browse Open Positions")
    
    # Fetch active jobs
    jobs = api_get("/jobs/public")
    
    if not jobs:
        st.info("No open positions at the moment. Check back soon!")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        departments = ["All"] + list(set(j.get("department", "N/A") for j in jobs))
        dept_filter = st.selectbox("Department", departments)
    with col2:
        locations = ["All"] + list(set(j.get("location", "N/A") for j in jobs))
        loc_filter = st.selectbox("Location", locations)
    with col3:
        exp_levels = ["All"] + list(set(j.get("experience_level", "N/A") for j in jobs))
        exp_filter = st.selectbox("Experience Level", exp_levels)
    
    # Filter jobs
    filtered_jobs = jobs
    if dept_filter != "All":
        filtered_jobs = [j for j in filtered_jobs if j.get("department") == dept_filter]
    if loc_filter != "All":
        filtered_jobs = [j for j in filtered_jobs if j.get("location") == loc_filter]
    if exp_filter != "All":
        filtered_jobs = [j for j in filtered_jobs if j.get("experience_level") == exp_filter]
    
    st.write(f"Found **{len(filtered_jobs)}** positions")
    
    # Display jobs
    for job in filtered_jobs:
        with st.expander(f"📄 {job['title']} - {job.get('department', 'N/A')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Location:** {job.get('location', 'N/A')}")
                st.markdown(f"**Type:** {job.get('job_type', 'N/A')}")
                st.markdown(f"**Experience:** {job.get('experience_level', 'N/A')}")
                posted_date = job.get('posted_at') or 'N/A'
                st.markdown(f"**Posted:** {posted_date[:10] if posted_date != 'N/A' else 'N/A'}")
                
                st.markdown("### Description")
                st.write(job.get('description', 'No description available'))
                
                if job.get('requirements'):
                    st.markdown("### Requirements")
                    for req in job['requirements']:
                        st.markdown(f"- {req}")
                
                if job.get('nice_to_have'):
                    st.markdown("### Nice to Have")
                    for nice in job['nice_to_have']:
                        st.markdown(f"- {nice}")
            
            with col2:
                if st.button(f"Apply Now", key=f"apply_{job['id']}"):
                    st.session_state.applying_to_job = job
                    st.rerun()

def application_form_page():
    """Job application form with resume upload"""
    job = st.session_state.get('applying_to_job')
    
    if not job:
        st.error("No job selected")
        return
    
    st.title(f"📝 Apply for {job['title']}")
    
    with st.form("application_form"):
        st.markdown("### Personal Information")
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name*", key="first_name")
            last_name = st.text_input("Last Name*", key="last_name")
            email = st.text_input("Email*", key="email")
        
        with col2:
            phone = st.text_input("Phone", key="phone")
            linkedin = st.text_input("LinkedIn URL", key="linkedin")
        
        st.markdown("### Resume Upload")
        resume_file = st.file_uploader(
            "Upload your resume (PDF, DOCX, TXT)*",
            type=['pdf', 'docx', 'txt'],
            help="Maximum 5MB"
        )
        
        st.markdown("### Cover Letter (Optional)")
        cover_letter = st.text_area(
            "Why are you interested in this position?",
            height=150
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Submit Application", type="primary")
        with col2:
            if st.form_submit_button("Cancel"):
                del st.session_state.applying_to_job
                st.rerun()
        
        if submitted:
            if not all([first_name, last_name, email, resume_file]):
                st.error("Please fill in all required fields (*)")
            else:
                # Submit application
                with st.spinner("Submitting your application..."):
                    files = {
                        'resume': (resume_file.name, resume_file.getvalue(), resume_file.type)
                    }
                    data = {
                        'job_id': job['id'],
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'phone': phone or '',
                        'linkedin_url': linkedin or '',
                        'cover_letter': cover_letter or ''
                    }
                    
                    result = api_post("/candidates/", data=data, files=files)
                    
                    if result:
                        st.success("✅ Application submitted successfully!")
                        st.session_state[CANDIDATE_ID_KEY] = result['id']
                        st.balloons()
                        time.sleep(2)
                        del st.session_state.applying_to_job
                        st.session_state.page = 'my_applications'
                        st.rerun()

def my_applications_page():
    """View candidate's applications and interviews"""
    st.title("📋 My Applications")
    
    candidate_id = st.session_state.get(CANDIDATE_ID_KEY)
    
    # If no candidate_id, prompt for email lookup
    if not candidate_id:
        st.info("📧 Enter your email to view your applications")
        
        with st.form("email_lookup"):
            email = st.text_input("Email Address", placeholder="your.email@example.com")
            submitted = st.form_submit_button("View My Applications")
            
            if submitted and email:
                # Look up candidate by email
                candidates = api_get(f"/candidates/")
                if candidates:
                    matching = [c for c in candidates if c['email'].lower() == email.lower()]
                    if matching:
                        st.session_state[CANDIDATE_ID_KEY] = matching[0]['id']
                        st.rerun()
                    else:
                        st.error("No applications found for this email address.")
        return
    
    # Fetch candidate info
    candidate = api_get(f"/candidates/{candidate_id}")
    
    if not candidate:
        st.error("Unable to load your application.")
        return
    
    st.markdown(f"### Welcome, {candidate['first_name']} {candidate['last_name']}!")
    st.markdown(f"**Email:** {candidate['email']}")
    st.markdown(f"**Status:** {candidate['status']}")
    
    # Get job details
    job = api_get(f"/jobs/{candidate['job_id']}")
    
    if job:
        st.markdown(f"**Applied for:** {job['title']}")
        st.markdown(f"**Applied on:** {candidate['applied_at'][:10]}")
    
    # Check for interviews
    st.markdown("---")
    st.markdown("### 🎤 Interviews")
    
    interviews = api_get(f"/interviews/?candidate_id={candidate_id}")
    
    if interviews:
        for interview in interviews:
            with st.expander(f"Interview - {interview['status']}"):
                st.write(f"**Started:** {interview.get('started_at', 'Not started')}")
                st.write(f"**Status:** {interview['status']}")
                
                interview_status_upper = interview['status'].upper() if isinstance(interview['status'], str) else str(interview['status'])
                
                if interview_status_upper == 'PENDING':
                    if st.button("Start Interview", key=f"start_{interview['id']}"):
                        # Open live interview page in new tab
                        st.markdown(f"[🎤 Start Interview →](http://localhost:8504/voice_interview.html?interview_id={interview['id']})", unsafe_allow_html=True)
                        st.info("Click the link above to start your voice interview, or use the text-based interface:")
                        if st.button("Start Text Interview", key=f"start_text_{interview['id']}"):
                            st.session_state['interview_id'] = interview['id']
                            st.session_state['page'] = 'live_interview'
                            st.rerun()
                elif interview_status_upper == 'IN_PROGRESS':
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Resume Text Interview", key=f"resume_text_{interview['id']}"):
                            st.session_state['interview_id'] = interview['id']
                            st.session_state['page'] = 'live_interview'
                            st.rerun()
                    with col2:
                        st.markdown(f"[🎤 Voice Interview →](http://localhost:8504/voice_interview.html?interview_id={interview['id']})", unsafe_allow_html=True)
                elif interview_status_upper == 'COMPLETED':
                    st.success("✅ Interview completed!")
    else:
        st.info("No interviews scheduled yet. The hiring team will schedule your interview soon.")

def interview_page():
    """Conduct the AI interview"""
    session_id = st.session_state.get(SESSION_ID_KEY)
    
    if not session_id:
        st.error("No active interview session")
        return
    
    # Fetch interview
    interview = api_get(f"/interviews/session/{session_id}")
    
    if not interview:
        st.error("Interview not found")
        return
    
    st.title("🎤 AI Interview in Progress")
    
    interview_status_upper = interview['status'].upper() if isinstance(interview['status'], str) else str(interview['status'])
    
    # Start interview if pending
    if interview_status_upper == 'PENDING':
        if st.button("Begin Interview", type="primary"):
            api_post(f"/interviews/{interview['id']}/start")
            st.rerun()
        return
    
    # Display conversation history
    conversation = interview.get('conversation_history', [])
    
    st.markdown("### Conversation")
    
    for i, msg in enumerate(conversation):
        if msg['role'] == 'assistant':
            st.markdown(f"**🤖 Interviewer:** {msg['content']}")
        else:
            st.markdown(f"**👤 You:** {msg['content']}")
    
    # Get next question
    interview_status_upper = interview['status'].upper() if isinstance(interview['status'], str) else str(interview['status'])
    
    if interview_status_upper == 'IN_PROGRESS':
        question_index = interview.get('current_question_index', 0)
        total_questions = 10  # From template
        
        st.progress((question_index) / total_questions)
        st.write(f"Question {question_index + 1} of {total_questions}")
        
        # Get current question
        result = api_post(f"/interviews/{interview['id']}/next-question")
        
        if result and result.get('question'):
            st.markdown(f"**🤖 Interviewer:** {result['question']}")
            
            # Answer input
            with st.form("answer_form"):
                answer = st.text_area(
                    "Your Answer:",
                    height=150,
                    placeholder="Take your time to provide a detailed answer..."
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Submit Answer", type="primary")
                with col2:
                    if st.form_submit_button("End Interview"):
                        api_post(f"/interviews/{interview['id']}/complete")
                        st.success("Interview ended. Thank you!")
                        del st.session_state[SESSION_ID_KEY]
                        st.session_state.page = 'my_applications'
                        time.sleep(2)
                        st.rerun()
                
                if submitted:
                    if answer.strip():
                        # Submit answer
                        api_post(
                            f"/interviews/{interview['id']}/submit-answer",
                            data={'answer': answer}
                        )
                        st.rerun()
                    else:
                        st.error("Please provide an answer")
        else:
            # Interview complete
            st.success("🎉 Interview completed! Thank you for your time.")
            if st.button("Back to Applications"):
                del st.session_state[SESSION_ID_KEY]
                st.session_state.page = 'my_applications'
                st.rerun()
    else:
        st.info(f"Interview status: {interview['status']}")

# Main navigation
def main():
    st.sidebar.title("Candidate Portal")
    
    # Navigation
    if 'page' not in st.session_state:
        st.session_state.page = 'browse'
    
    # Handle application form
    if st.session_state.get('applying_to_job'):
        application_form_page()
        return
    
    # Handle interview
    if st.session_state.get(SESSION_ID_KEY):
        interview_page()
        return
    
    # Handle live interview page
    if st.session_state.get('page') == 'live_interview':
        interview_id = st.session_state.get('interview_id')
        if interview_id:
            # Import and run live interview page
            import sys
            import importlib.util
            spec = importlib.util.spec_from_file_location("live_interview", "pages/live_interview.py")
            live_interview = importlib.util.module_from_spec(spec)
            sys.modules["live_interview"] = live_interview
            spec.loader.exec_module(live_interview)
            return
        else:
            st.error("No interview ID found")
            st.session_state['page'] = 'my_applications'
            st.rerun()
    
    # Regular navigation
    page = st.sidebar.radio(
        "Navigation",
        ['browse', 'my_applications'],
        format_func=lambda x: {
            'browse': '🔍 Browse Jobs',
            'my_applications': '📋 My Applications'
        }[x],
        key='nav_radio'
    )
    
    st.session_state.page = page
    
    if page == 'browse':
        browse_jobs_page()
    elif page == 'my_applications':
        my_applications_page()

if __name__ == "__main__":
    main()
