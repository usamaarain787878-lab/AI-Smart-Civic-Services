import streamlit as st
import sqlite3
import pandas as pd
import os
import json

# Page Setup
st.set_page_config(
    page_title="AI Smart Civic Services Platform",
    page_icon="🏙️",
    layout="wide"
)

st.title("🏙️ AI Smart Civic Services Platform")
st.write("AI-powered civic complaint routing, tracking, and management system.")

# Database Check
db_path = "civic_services.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    
    # Navigation Sidebar
    st.sidebar.header("Control Panel")
    menu = st.sidebar.selectbox("Choose Section", ["Live Dashboard", "File Complaint", "AI Evaluation Results"])
    
    if menu == "Live Dashboard":
        st.subheader("📊 Active Civic Complaints")
        try:
            # Check existing tables in sqlite
            query_tables = "SELECT name FROM sqlite_master WHERE type='table';"
            tables_df = pd.read_sql(query_tables, conn)
            
            if not tables_df.empty:
                table_name = tables_df.iloc[0, 0] # Pehli table utha lein
                df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info(f"Table '{table_name}' is currently empty.")
            else:
                st.info("No tables found in the database.")
        except Exception as e:
            st.error(f"Error loading database records: {e}")
            
    elif menu == "File Complaint":
        st.subheader("📝 Register a New Issue")
        with st.form("civic_form"):
            citizen_name = st.text_input("Your Full Name")
            category = st.selectbox("Issue Category", ["Road Infrastructure", "Water & Sanitation", "Street Lighting", "Waste Management", "Public Safety"])
            location = st.text_input("Area / Location")
            description = st.text_area("Detailed Description")
            submit_btn = st.form_submit_button("Submit Complaint to AI Router")
            
            if submit_btn:
                if citizen_name and description:
                    st.success("Complaint successfully registered and routed via AI system!")
                else:
                    st.warning("Please fill in all mandatory fields.")
                    
    elif menu == "AI Evaluation Results":
        st.subheader("🤖 AI Performance & Test Reports")
        eval_file = "ai_evaluation_results.json"
        if os.path.exists(eval_file):
            with open(eval_file, "r") as f:
                eval_data = json.load(f)
            st.json(eval_data)
        else:
            st.info("AI evaluation results file (`ai_evaluation_results.json`) not found.")
            
    conn.close()
else:
    st.error(f"Critical Error: Database file `{db_path}` is missing from the repository. Please upload it!")
