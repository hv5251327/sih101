import os
import sqlite3
import urllib.parse
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "igot_mospi.db")

# Full official course syllabus mapped to specific designation groups across 4 pillars
ALL_COURSES = [
    # --- ISS: DG & ADG ---
    {"id": "iss-apex-stat-1", "target_group": "DG_ADG", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "System of National Accounts (SNA 2025 Updates & Macroeconomic Aggregates)", "provider": "NSSTA / MoSPI", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-apex-stat-2", "target_group": "DG_ADG", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "System of Environmental-Economic Accounting (SEEA)", "provider": "UN / NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-apex-tech-1", "target_group": "DG_ADG", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Executive Overview of Data Analytics & AI in Governance", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-apex-tech-2", "target_group": "DG_ADG", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Big Data Ecosystems for Official Statistics & Decision Support", "provider": "NSSTA / iGOT", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-apex-gov-1", "target_group": "DG_ADG", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Digital Personal Data Protection (DPDP) Act 2023 & Apex Compliance", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-apex-gov-2", "target_group": "DG_ADG", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "National Data Governance and Access Policy (NDGAP)", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-apex-beh-1", "target_group": "DG_ADG", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Apex Public Leadership & Strategic Policy Formulation", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-apex-beh-2", "target_group": "DG_ADG", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Inter-Ministerial Stakeholder Negotiation & Consensus Building", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- ISS: DDG & Director / Joint Director ---
    {"id": "iss-dir-stat-1", "target_group": "DDG_DIR", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Multivariate Analysis & Advanced Econometric Modelling", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dir-stat-2", "target_group": "DDG_DIR", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "SDG Indicator Frameworks & Global Monitoring Guidelines", "provider": "NSSTA / iGOT", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dir-tech-1", "target_group": "DDG_DIR", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Data Science with R and Python for Official Imputation", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dir-tech-2", "target_group": "DDG_DIR", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "GIS-Based Spatial Data Analysis in Official Sampling", "provider": "NSSTA / iGOT", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dir-gov-1", "target_group": "DDG_DIR", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Cyber Security Practices for Senior Government Officials", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dir-gov-2", "target_group": "DDG_DIR", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Data Quality Assurance & Metadata Standards (SDMX)", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dir-beh-1", "target_group": "DDG_DIR", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Conflict Resolution & Team Coaching for Division Heads", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dir-beh-2", "target_group": "DDG_DIR", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Public Procurement (GeM & GFR 2017 Rules)", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- ISS: Deputy Director & Assistant Director ---
    {"id": "iss-dd-stat-1", "target_group": "DD_AD", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Index Numbers Compilation: CPI, IIP & WPI Frameworks", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dd-stat-2", "target_group": "DD_AD", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Time Series Forecasting & Seasonal Adjustments (X-13ARIMA-SEATS)", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dd-tech-1", "target_group": "DD_AD", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Advanced SQL & Relational Database Management for Survey Tabulation", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dd-tech-2", "target_group": "DD_AD", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Python for Statistical Automation & Web Scraping", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dd-gov-1", "target_group": "DD_AD", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Data Ethics & Information Security Fundamentals", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dd-gov-2", "target_group": "DD_AD", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "E-Office 7.0 Process Automation", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dd-beh-1", "target_group": "DD_AD", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Time Management & Project Supervision", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-dd-beh-2", "target_group": "DD_AD", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Effective Technical Report Writing and Briefing Notes", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- ISS: Probationer / Officer Trainee ---
    {"id": "iss-ot-stat-1", "target_group": "ISS_OT", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Official Statistical System in India: Mandate, Structure & History", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-ot-stat-2", "target_group": "ISS_OT", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Sampling Theory, Survey Sampling & Estimation Procedures", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-ot-tech-1", "target_group": "ISS_OT", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Statistical Computing with R (Basics to Intermediate)", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-ot-tech-2", "target_group": "ISS_OT", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Excel for Statistical Analysis & Visualization", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-ot-gov-1", "target_group": "ISS_OT", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Code of Conduct & Civil Services Conduct Rules", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-ot-gov-2", "target_group": "ISS_OT", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Foundational Information Security Awareness", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-ot-beh-1", "target_group": "ISS_OT", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Foundations of Professional Communication", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "iss-ot-beh-2", "target_group": "ISS_OT", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Ethical Governance & Public Value", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- SSS: Senior Statistical Officer (SSO) ---
    {"id": "sss-sso-stat-1", "target_group": "SSO", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Periodic Labour Force Survey (PLFS) Schedule Scrutiny & Validation", "provider": "NSSTA / FOD", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sso-stat-2", "target_group": "SSO", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Annual Survey of Unincorporated Sector Enterprises (ASUSE) Verification", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sso-tech-1", "target_group": "SSO", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "CAPI (Computer-Assisted Personal Interviewing) Portal Validation Protocols", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sso-tech-2", "target_group": "SSO", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Advanced Data Cleaning & Outlier Treatment using R/Python", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sso-gov-1", "target_group": "SSO", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Field Respondent Confidentiality & Data Protection Guidelines", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sso-gov-2", "target_group": "SSO", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Office Procedure & Drafting for Gazetted Officers", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sso-beh-1", "target_group": "SSO", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Field Inspection, Quality Audits & Enumerator Mentorship", "provider": "NSSTA / iGOT", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sso-beh-2", "target_group": "SSO", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Workplace Problem-Solving & Stress Management", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- SSS: Junior Statistical Officer (JSO) ---
    {"id": "sss-jso-stat-1", "target_group": "JSO", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Primary Survey Schedules: Concepts, Definitions & Operational Guidelines", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-jso-stat-2", "target_group": "JSO", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Consumer Price Index (CPI) Rural/Urban Market Price Collection", "provider": "NSSTA / FOD", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-jso-tech-1", "target_group": "JSO", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "CAPI Handheld Tablet Operation & Real-Time Sync", "provider": "NSSTA / FOD", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-jso-tech-2", "target_group": "JSO", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Bhuvan App Integration for Urban Frame Survey (UFS) Mapping", "provider": "ISRO / NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-jso-gov-1", "target_group": "JSO", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Ethics in Primary Data Collection & Information Security", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-jso-gov-2", "target_group": "JSO", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Basics of Government Record Management", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-jso-beh-1", "target_group": "JSO", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Public Interviewing & Effective Communication Techniques", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-jso-beh-2", "target_group": "JSO", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Team Building & Field Coordination Skills", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- SSS: Statistical Assistant / Senior Field Investigator ---
    {"id": "sss-sa-stat-1", "target_group": "SA_SFI", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Field Enumeration Procedures & Schedule Canvassing Guidelines", "provider": "NSSTA / FOD", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sa-stat-2", "target_group": "SA_SFI", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Data Entry Validation & Consistency Rules", "provider": "DPD / NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sa-tech-1", "target_group": "SA_SFI", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Digital Mobile Applications for Official Sample Surveys", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sa-tech-2", "target_group": "SA_SFI", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Basic Computer Operations & MS Excel Basics", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sa-gov-1", "target_group": "SA_SFI", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Safe Data Handling & Device Security in Field Operations", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sa-beh-1", "target_group": "SA_SFI", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Interpersonal Skills & Handling Difficult Respondents", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "sss-sa-beh-2", "target_group": "SA_SFI", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Work Ethics & Professional Integrity", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- DES: State Director & Joint / Deputy Director (State DES) ---
    {"id": "des-dir-stat-1", "target_group": "DES_DIR", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Gross State Domestic Product (GSDP) & District Domestic Product (DDP) Compilation", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dir-stat-2", "target_group": "DES_DIR", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "State Sustainable Development Goals (SDG) Vision Frameworks", "provider": "NITI Aayog / iGOT", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dir-tech-1", "target_group": "DES_DIR", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "State Statistical Open Data Portals Architecture", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dir-tech-2", "target_group": "DES_DIR", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Spatial Decision Support Systems (SDSS) for State Planning", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dir-gov-1", "target_group": "DES_DIR", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Inter-Departmental Data Sharing & State Data Protocols", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dir-gov-2", "target_group": "DES_DIR", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Digital Governance Implementation for State Administration", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dir-beh-1", "target_group": "DES_DIR", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Inter-Ministerial Strategic Coordination & District Review Management", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dir-beh-2", "target_group": "DES_DIR", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Executive Administrative Decision Making", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- DES: District Statistical Officer (DSO) ---
    {"id": "des-dso-stat-1", "target_group": "DSO", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Local Level Planning & District Statistical Handbooks Formulation", "provider": "NSSTA / State DES", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dso-stat-2", "target_group": "DSO", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Crop Estimation Surveys (EARAS / GCES) & Agricultural Statistics", "provider": "DES / MoA&FW", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dso-tech-1", "target_group": "DSO", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "District Open Data Systems & Dashboard Management", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dso-tech-2", "target_group": "DSO", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "GIS Tools for Village & Block Level Spatial Tagging", "provider": "NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dso-gov-1", "target_group": "DSO", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Civil Registration System (CRS) & Vital Statistics Record Maintenance", "provider": "ORGI / NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dso-beh-1", "target_group": "DSO", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "District Administration Liaison & Collectorate Coordination", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-dso-beh-2", "target_group": "DSO", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Supervision of Field Investigators & Resource Allocation", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- DES: Assistant Statistical Officer (ASO) & Statistical Inspector ---
    {"id": "des-aso-stat-1", "target_group": "ASO_INSP", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Price Collection for State Wholesale & Retail Indices", "provider": "State DES", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-aso-stat-2", "target_group": "ASO_INSP", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Municipal & Industrial Statistics Scrutiny", "provider": "State DES / NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-aso-tech-1", "target_group": "ASO_INSP", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "State Web Portals: Data Entry & Real-Time Scrutiny Modules", "provider": "State DES", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-aso-tech-2", "target_group": "ASO_INSP", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Intermediate Excel & Tabulation Techniques", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-aso-gov-1", "target_group": "ASO_INSP", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Information Security Basics for State Employees", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-aso-beh-1", "target_group": "ASO_INSP", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Effective Coordination with District Line Departments", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-aso-beh-2", "target_group": "ASO_INSP", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Field Supervision & Verification Best Practices", "provider": "NSSTA / DES", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},

    # --- DES: Primary Field Investigator / Enumerator ---
    {"id": "des-enum-stat-1", "target_group": "ENUM", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Basic Field Data Collection Principles & Schedule Navigation", "provider": "State DES", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-enum-stat-2", "target_group": "ENUM", "pillar": "statistical", "pillarTitle": "Statistical Frameworks",
     "title": "Agricultural Crop Cutting Experiments (CCE) Measurement Rules", "provider": "State DES", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-enum-tech-1", "target_group": "ENUM", "pillar": "technical", "pillarTitle": "Technical Tools & AI/GIS",
     "title": "Mobile App Navigation & GPS Point Capture for Field Surveys", "provider": "State DES / NSSTA", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-enum-gov-1", "target_group": "ENUM", "pillar": "governance", "pillarTitle": "Digital Governance & Privacy",
     "title": "Civic Responsibility & Respondent Privacy Protocols", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"},
    {"id": "des-enum-beh-1", "target_group": "ENUM", "pillar": "behavioural", "pillarTitle": "Managerial & Behavioural",
     "title": "Citizen Communication & Field Courtesy", "provider": "iGOT Karmayogi", "embedUrl": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"}
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS training_modules (
        module_id VARCHAR(50) PRIMARY KEY,
        target_group VARCHAR(50) NOT NULL,
        pillar VARCHAR(50) NOT NULL,
        pillar_title VARCHAR(100) NOT NULL,
        title VARCHAR(250) NOT NULL,
        provider VARCHAR(100) NOT NULL,
        embed_url TEXT NOT NULL
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(100) NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        designation VARCHAR(150),
        department VARCHAR(150),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS officer_profiles (
        officer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(100) UNIQUE NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        department VARCHAR(150) NOT NULL,
        designation_name VARCHAR(150),
        current_statistical INTEGER DEFAULT 0,
        current_technical INTEGER DEFAULT 0,
        current_governance INTEGER DEFAULT 0,
        current_behavioural INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS officer_recommendations (
        rec_id INTEGER PRIMARY KEY AUTOINCREMENT,
        officer_email VARCHAR(100) NOT NULL,
        designation_name VARCHAR(150) NOT NULL,
        module_id VARCHAR(50) NOT NULL,
        module_title VARCHAR(250) NOT NULL,
        pillar VARCHAR(50) NOT NULL,
        embed_url TEXT NOT NULL,
        is_completed INTEGER DEFAULT 0,
        recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(officer_email, module_id)
    );''')

    for m in ALL_COURSES:
        c.execute("""
            INSERT OR REPLACE INTO training_modules (module_id, target_group, pillar, pillar_title, title, provider, embed_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (m["id"], m["target_group"], m["pillar"], m["pillarTitle"], m["title"], m["provider"], m["embedUrl"]))

    conn.commit()
    conn.close()

init_db()

# Fine-grained designation to target group mapping
def resolve_target_group(desig):
    d = desig.lower()
    if "director general" in d or "apex" in d or "additional director general" in d or "hag" in d:
        return "DG_ADG"
    elif "deputy director general" in d or "sag" in d or "joint director" in d or "jag" in d or ("director" in d and "iss" in d and "deputy" not in d and "assistant" not in d):
        return "DDG_DIR"
    elif "deputy director" in d or "sts" in d or "assistant director" in d or "jts" in d:
        return "DD_AD"
    elif "probationer" in d or "trainee" in d:
        return "ISS_OT"
    elif "senior statistical officer" in d or "sso" in d:
        return "SSO"
    elif "junior statistical officer" in d or "jso" in d:
        return "JSO"
    elif "statistical assistant" in d or "investigator" in d and "primary" not in d:
        return "SA_SFI"
    elif "director of economics" in d or "state head" in d or ("state des" in d and "director" in d):
        return "DES_DIR"
    elif "district statistical officer" in d or "dso" in d:
        return "DSO"
    elif "assistant statistical officer" in d or "statistical inspector" in d:
        return "ASO_INSP"
    elif "primary field investigator" in d or "enumerator" in d:
        return "ENUM"
    return "JSO"

@app.route("/api/officer/recommendations", methods=["POST"])
def get_recommendations():
    data = request.json or {}
    email = data.get("email", "officer@gov.in")
    designation = data.get("designation", "Junior Statistical Officer (JSO)")
    search_topic = data.get("search_topic", "").strip().lower()

    target_group = resolve_target_group(designation)
    conn = get_db()
    c = conn.cursor()

    if search_topic:
        c.execute("""
            SELECT module_id, target_group, pillar, pillar_title, title, provider, embed_url 
            FROM training_modules 
            WHERE LOWER(title) LIKE ? OR LOWER(pillar_title) LIKE ? OR LOWER(provider) LIKE ?
        """, (f"%{search_topic}%", f"%{search_topic}%", f"%{search_topic}%"))
    else:
        c.execute("""
            SELECT module_id, target_group, pillar, pillar_title, title, provider, embed_url 
            FROM training_modules 
            WHERE target_group = ?
        """, (target_group,))

    rows = c.fetchall()

    for r in rows:
        c.execute("""
            INSERT OR IGNORE INTO officer_recommendations 
            (officer_email, designation_name, module_id, module_title, pillar, embed_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, designation, r["module_id"], r["title"], r["pillar"], r["embed_url"]))
    conn.commit()

    c.execute("SELECT module_id, is_completed FROM officer_recommendations WHERE officer_email = ?", (email,))
    done_map = {row[0]: bool(row[1]) for row in c.fetchall()}
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r["module_id"],
            "target_group": r["target_group"],
            "pillar": r["pillar"],
            "pillarTitle": r["pillar_title"],
            "title": r["title"],
            "provider": r["provider"],
            "embedUrl": r["embed_url"],
            "is_completed": done_map.get(r["module_id"], False)
        })

    return jsonify({"target_group": target_group, "modules": result})

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    dept = data.get("department", "National Accounts Division").strip()
    desig = data.get("designation", "Junior Statistical Officer (JSO)").strip()

    if not email or not name or not password:
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE LOWER(email) = ?", (email,))
    if c.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Email is already registered!"}), 409

    c.execute("INSERT INTO users (email, password, full_name, designation, department) VALUES (?, ?, ?, ?, ?)",
              (email, password, name, desig, dept))

    c.execute("""
        INSERT INTO officer_profiles (email, full_name, department, designation_name, current_statistical, current_technical, current_governance, current_behavioural)
        VALUES (?, ?, ?, ?, 0, 0, 0, 0)
        ON CONFLICT(email) DO UPDATE SET
            full_name = excluded.full_name,
            department = excluded.department,
            designation_name = excluded.designation_name
    """, (email, name, dept, desig))

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Registered successfully"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, email, password, full_name, designation, department FROM users WHERE LOWER(email) = ?", (email,))
    user = c.fetchone()
    conn.close()

    if not user:
        return jsonify({"status": "error", "message": "No account found. Please register."}), 404

    if user["password"] != password:
        return jsonify({"status": "error", "message": "Incorrect password."}), 401

    return jsonify({
        "status": "success",
        "user": {
            "name": user["full_name"],
            "email": user["email"],
            "department": user["department"] or "MoSPI General Division",
            "designation": user["designation"] or "Junior Statistical Officer (JSO)"
        }
    })

if __name__ == "__main__":
    app.run(port=5000, debug=False)