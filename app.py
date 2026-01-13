import streamlit as st
import pandas as pd
import utils
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- Page Configuration ---
st.set_page_config(
    page_title="EmailHunter & Drafter",
    page_icon="📧",
    layout="wide"
)

# --- Sidebar ---
st.sidebar.title("Navigation")
app_mode = st.sidebar.radio("Go to", ["Email Permutator & Verifier", "Cold Email Drafter"])

st.sidebar.divider()
st.sidebar.subheader("LLM Configuration")
llm_provider = st.sidebar.selectbox("Select LLM Provider", ["OpenAI", "Groq"])

selected_model = ""
api_key = None

if llm_provider == "OpenAI":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")
    selected_model = st.sidebar.selectbox("Select Model", [
        "gpt-4o", 
        "gpt-4-turbo", 
        "gpt-3.5-turbo"
    ])

elif llm_provider == "Groq":
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        api_key = st.sidebar.text_input("Enter Groq API Key", type="password")
    selected_model = st.sidebar.selectbox("Select Model", [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile", 
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ])

# --- APP 1: Email Permutation & Verification ---
if app_mode == "Email Permutator & Verifier":
    st.title("📧 EmailHunter: Permutation & Verification")
    st.markdown("""
    Upload a CSV file with columns: `First Name`, `Last Name`, `Company Domain`.
    The tool will generate permutations and verify them via SMTP.
    """)

    # Create tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["📂 Bulk Upload", "👤 Direct Input", "✅ Email Checker"])

    # --- TAB 1: Bulk Upload ---
    with tab1:
        st.markdown("Upload a CSV file with columns: `First Name`, `Last Name`, `Company Domain`.")
        uploaded_file = st.file_uploader("Upload CSV/YAML", type=['csv', 'yaml'])

        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    st.error("YAML support is limited. Please use CSV for best results.")
                    df = pd.DataFrame()

                # Normalize columns
                df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
                required_cols = {'first_name', 'last_name', 'company_domain'}
                
                if not required_cols.issubset(set(df.columns)):
                    st.error(f"Missing required columns. Found: {list(df.columns)}. Expected: First Name, Last Name, Company Domain")
                else:
                    st.success("File verified successfully!")

                    if st.button("Generate & Verify Emails (Bulk)"):
                        results = []
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        total_rows = len(df)
                        
                        for index, row in df.iterrows():
                            progress = (index + 1) / total_rows
                            progress_bar.progress(progress)
                            status_text.text(f"Processing {row['first_name']} {row['last_name']}...")

                            permutations = utils.generate_permutations(
                                row['first_name'], 
                                row['last_name'], 
                                row['company_domain']
                            )
                            
                            for email in permutations:
                                verification_result = utils.verify_email_smtp(email)
                                results.append({
                                    "First Name": row['first_name'],
                                    "Last Name": row['last_name'],
                                    "Email": email,
                                    "Status": verification_result["status"]
                                })
                                
                        progress_bar.empty()
                        status_text.text("Processing Complete!")
                        
                        results_df = pd.DataFrame(results)
                        
                        st.subheader("Results")
                        def color_status(val):
                            if val == 'Valid': return 'background-color: #90ee90' # Light green
                            elif 'Risky' in val: return 'background-color: #ffd700' # Gold
                            elif 'Invalid': return 'background-color: #ffcccb' # Light red
                            return ''

                        st.dataframe(results_df.style.applymap(color_status, subset=['Status']))
                        
                        csv = results_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Results as CSV",
                            data=csv,
                            file_name='email_hunter_results.csv',
                            mime='text/csv',
                        )

            except Exception as e:
                st.error(f"An error occurred: {e}")

    # --- TAB 2: Direct Input ---
    with tab2:
        st.markdown("Enter company details and list of employees.")
        
        # 1. Company Domain
        d_domain = st.text_input("Company Domain", placeholder="example.com")
        
        # 2. People Input (Data Editor)
        st.markdown("Add People:")
        people_data = pd.DataFrame(columns=["First Name", "Last Name"])
        # Pre-fill with one empty row for better UX
        people_data = pd.DataFrame([{"First Name": "", "Last Name": ""}])
        
        edited_df = st.data_editor(people_data, num_rows="dynamic", use_container_width=True)

        if st.button("Find Emails"):
            if not d_domain:
                st.error("Please enter a Company Domain.")
            else:
                # Filter out empty rows
                valid_people = edited_df[
                    (edited_df["First Name"].str.strip() != "") & 
                    (edited_df["Last Name"].str.strip() != "")
                ]
                
                if valid_people.empty:
                    st.error("Please add at least one person with both First and Last names.")
                else:
                    with st.spinner(f"Processing {len(valid_people)} people for {d_domain}..."):
                        results = []
                        progress_bar = st.progress(0)
                        total = len(valid_people)
                        
                        for i, (index, row) in enumerate(valid_people.iterrows()):
                            fn = row['First Name']
                            ln = row['Last Name']
                            
                            permutations = utils.generate_permutations(fn, ln, d_domain)
                            
                            # Verify each
                            for email in permutations:
                                verification_result = utils.verify_email_smtp(email)
                                results.append({
                                    "First Name": fn,
                                    "Last Name": ln,
                                    "Email": email,
                                    "Status": verification_result["status"]
                                })
                            
                            progress_bar.progress((i + 1) / total)
                        
                        progress_bar.empty()
                        results_df = pd.DataFrame(results)
                        
                        st.subheader("Results")
                        def color_status(val):
                            if val == 'Valid': return 'background-color: #90ee90'
                            elif 'Risky' in val: return 'background-color: #ffd700'
                            elif 'Invalid': return 'background-color: #ffcccb'
                            return ''
                        
                        st.dataframe(results_df.style.applymap(color_status, subset=['Status']))
                        
                        # Download Button for Direct Input results
                        csv_direct = results_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Results as CSV",
                            data=csv_direct,
                            file_name='email_hunter_direct_results.csv',
                            mime='text/csv',
                        )

    # --- TAB 3: Email Checker ---
    with tab3:
        st.markdown("Check a single email address for validity.")
        check_email = st.text_input("Enter Email Address")

        if st.button("Verify Email"):
            if not check_email:
                st.error("Please enter an email address.")
            elif "@" not in check_email or "." not in check_email.split("@")[-1]:
                st.error("Invalid email format.")
            else:
                with st.spinner("Verifying..."):
                    details = utils.verify_email_smtp(check_email)
                    status = details["status"]
                    
                    st.subheader("Verification Status")
                    
                    # Main Metric
                    st.metric("Status", status, delta="Deliverable" if status=="Valid" else None)
                    
                    st.divider()
                    
                    # Detailed Grid
                    st.markdown("### 🔍 Technical Details")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"**MX Record**\n\n{details['mx_record']}")
                        st.info(f"**SPF Record**\n\n{'✅ Pass' if details['has_spf'] else '❌ Fail/Missing'}")
                    with col2:
                        st.info(f"**DMARC Record**\n\n{'✅ Pass' if details['has_dmarc'] else '❌ Fail/Missing'}")
                        st.info(f"**Role Account**\n\n{'⚠️ Yes' if details['is_role_account'] else 'No'}")
                    with col3:
                        st.info(f"**Free Provider**\n\n{'ℹ️ Yes' if details['is_free_provider'] else 'No'}")
                        st.info(f"**SMTP Banner**\n\n`{str(details['smtp_banner'])[:50]}...`" if details['smtp_banner'] else "No Banner")

                    st.markdown(f"**Reason:** {details['reason']}")
                    
                    if status == "Valid":
                        st.success(f"✅ The email `{check_email}` exists and is deliverable.")
                    elif "Risky" in status:
                        st.warning(f"⚠️ The domain `{check_email.split('@')[1]}` accepts all emails (Catch-All).")
                    elif status == "Invalid":
                        st.error(f"❌ The email `{check_email}` does not exist.")

# --- APP 2: Resume Parser & AI Email Generator ---
elif app_mode == "Cold Email Drafter":
    st.title("✍️ AI Cold Email Drafter")
    st.markdown("Upload your Resume and provide a Company/Job context to generate a tailored cold email.")

    if not api_key:
        st.warning(f"⚠️ Please provide a {llm_provider} API Key in the sidebar to use the AI features.")
        st.stop()

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Your Info")
        resume_pdf = st.file_uploader("Upload Resume (PDF)", type=['pdf'])
        
    with col2:
        st.subheader("2. Target Context")
        company_context = st.text_area(
            "Company Description or Job Post",
            height=200,
            placeholder="Paste the job description or 'About Us' page content here..."
        )

    if st.button("Generate Cold Email"):
        if not resume_pdf or not company_context:
            st.error("Please upload a resume and provide company context.")
        else:
            with st.spinner("Analyzing resume and drafting email..."):
                try:
                    # 1. Parse Resume
                    resume_text = utils.extract_text_from_pdf(resume_pdf)
                    st.write(resume_text)
                    if not resume_text:
                        st.error("Could not extract text from PDF. Is it a scanned image?")
                        st.stop()
                    
                    # 2. Setup LangChain
                    if llm_provider == "OpenAI":
                        llm = ChatOpenAI(
                            temperature=0.7,
                            model_name=selected_model,
                            openai_api_key=api_key
                        )
                    elif llm_provider == "Groq":
                        from langchain_groq import ChatGroq
                        llm = ChatGroq(
                            temperature=0.7,
                            model_name=selected_model, 
                            groq_api_key=api_key
                        )
                    
                    prompt = PromptTemplate.from_template(
                        """
                        You are a world-class cold outreach expert and copywriter.
                        
                        GOAL: Write a high-converting, personalized cold email to a recruiter or hiring manager at the target company.
                        
                        CONTEXT:
                        My Resume:
                        {resume_text}
                        
                        Target Company/Job Context:
                        {company_context}
                        
                        INSTRUCTIONS:
                        1. Analyze the resume to find the most relevant skills/experience for this specific company context.
                        2. Keep the email concise (under 200 words).
                        3. Use a professional but engaging tone.
                        4. Focus on value proposition: matches between my skills and their needs.
                        5. Include a strong Call to Action (CTA).
                        6. Output ONLY the email body (and subject line).
                        """
                    )
                    
                    chain = prompt | llm | StrOutputParser()
                    
                    response = chain.invoke({
                        "resume_text": resume_text[:4000], # Truncate to avoid context limits if huge
                        "company_context": company_context
                    })
                    
                    st.subheader("Drafted Email")
                    st.text_area("Copy your email:", value=response, height=400)
                    
                except Exception as e:
                    st.error(f"Error generating email: {e}")

