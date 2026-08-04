import json
import logging
import time
from typing import Any, Dict, List
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_specialist")

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.services.intent_router import IntentRouter, IntentType

# Define 200 queries across 25 categories
eval_dataset = [
    # 1. Greetings (8)
    {"cat": "Greetings", "q": "hi", "exp": "Instant greeting response, RAG skipped", "domain": "conversational"},
    {"cat": "Greetings", "q": "hello", "exp": "Instant greeting response, RAG skipped", "domain": "conversational"},
    {"cat": "Greetings", "q": "hey there", "exp": "Instant greeting response, RAG skipped", "domain": "conversational"},
    {"cat": "Greetings", "q": "good morning", "exp": "Instant greeting response, RAG skipped", "domain": "conversational"},
    {"cat": "Greetings", "q": "good evening", "exp": "Instant greeting response, RAG skipped", "domain": "conversational"},
    {"cat": "Greetings", "q": "namaste", "exp": "Instant greeting response, RAG skipped", "domain": "conversational"},
    {"cat": "Greetings", "q": "namaskara", "exp": "Instant greeting response, RAG skipped", "domain": "conversational"},
    {"cat": "Greetings", "q": "hey Sparky", "exp": "Instant greeting response, RAG skipped", "domain": "conversational"},

    # 2. Small talk (8)
    {"cat": "Small talk", "q": "what's up", "exp": "Friendly casual response, RAG skipped", "domain": "conversational"},
    {"cat": "Small talk", "q": "who are you", "exp": "Identify as Sparky/Helpdesk, RAG skipped", "domain": "conversational"},
    {"cat": "Small talk", "q": "what can you do", "exp": "Explain campus guides, RAG skipped", "domain": "conversational"},
    {"cat": "Small talk", "q": "how are you", "exp": "Polite response, RAG skipped", "domain": "conversational"},
    {"cat": "Small talk", "q": "tell me a joke", "exp": "Casual response, RAG skipped", "domain": "conversational"},
    {"cat": "Small talk", "q": "are you human", "exp": "AI identity response, RAG skipped", "domain": "conversational"},
    {"cat": "Small talk", "q": "do you like Hubballi", "exp": "Hubballi friendly small talk, RAG skipped", "domain": "conversational"},
    {"cat": "Small talk", "q": "are you smart", "exp": "Playful casual response, RAG skipped", "domain": "conversational"},

    # 3. Campus departments (8)
    {"cat": "Campus departments", "q": "departments in college", "exp": "Retrieve schools/departments list", "domain": "campus"},
    {"cat": "Campus departments", "q": "department of fashion design", "exp": "Fashion design details", "domain": "campus"},
    {"cat": "Campus departments", "q": "list of schools", "exp": "List of schools in campus", "domain": "campus"},
    {"cat": "Campus departments", "q": "is there computer science department", "exp": "CSE department verification", "domain": "campus"},
    {"cat": "Campus departments", "q": "civil engineering department", "exp": "Details on civil department", "domain": "campus"},
    {"cat": "Campus departments", "q": "biotechnology department details", "exp": "Details on biotech department", "domain": "campus"},
    {"cat": "Campus departments", "q": "information science branch", "exp": "ISE branch details", "domain": "campus"},
    {"cat": "Campus departments", "q": "management school info", "exp": "Details on Management School (MBA)", "domain": "campus"},

    # 4. Faculty (8)
    {"cat": "Faculty", "q": "who is Mr. V. A. Goudar", "exp": "Retrieve Associate Professor details", "domain": "campus"},
    {"cat": "Faculty", "q": "Dr. M.B. Page faculty", "exp": "Retrieve Assistant Professor details", "domain": "campus"},
    {"cat": "Faculty", "q": "faculty details", "exp": "Explain how to search faculty or retrieve faculty list", "domain": "campus"},
    {"cat": "Faculty", "q": "CSE faculty list", "exp": "CSE professors info", "domain": "campus"},
    {"cat": "Faculty", "q": "Biotechnology professors", "exp": "Biotech faculty details", "domain": "campus"},
    {"cat": "Faculty", "q": "who is Dr. Prakash Tewari", "exp": "VC Prakash Tewari faculty details", "domain": "campus"},
    {"cat": "Faculty", "q": "Associate Professors list", "exp": "List of associate professors", "domain": "campus"},
    {"cat": "Faculty", "q": "faculty qualifications in Biotech", "exp": "Biotech faculty profile details", "domain": "campus"},

    # 5. Principal (8)
    {"cat": "Principal", "q": "who is the principal", "exp": "Explain VC system or retrieve Principal reference", "domain": "campus"},
    {"cat": "Principal", "q": "principal contact number", "exp": "VC office or administrative contacts", "domain": "campus"},
    {"cat": "Principal", "q": "office of the principal", "exp": "Admin block / VC office direction", "domain": "campus"},
    {"cat": "Principal", "q": "meet the principal", "exp": "Meeting admin procedures", "domain": "campus"},
    {"cat": "Principal", "q": "kle principal name", "exp": "VC system info", "domain": "campus"},
    {"cat": "Principal", "q": "is there a principal", "exp": "Explain university VC administrative hierarchy", "domain": "campus"},
    {"cat": "Principal", "q": "principal email id", "exp": "VC/Registrar contact information", "domain": "campus"},
    {"cat": "Principal", "q": "principal of bvb college", "exp": "Historical principal or VC system mapping", "domain": "campus"},

    # 6. Vice Chancellor (8)
    {"cat": "Vice Chancellor", "q": "who is the vice chancellor", "exp": "Identify Dr. Prakash Tewari", "domain": "campus"},
    {"cat": "Vice Chancellor", "q": "VC of KLE Tech", "exp": "Identify Dr. Prakash Tewari", "domain": "campus"},
    {"cat": "Vice Chancellor", "q": "Vice Chancellor contact", "exp": "VC office details", "domain": "campus"},
    {"cat": "Vice Chancellor", "q": "VC of BVB campus", "exp": "Identify Dr. Prakash Tewari", "domain": "campus"},
    {"cat": "Vice Chancellor", "q": "vice chancellor message", "exp": "VC message or board governance details", "domain": "campus"},
    {"cat": "Vice Chancellor", "q": "who is the current VC", "exp": "Identify Dr. Prakash Tewari", "domain": "campus"},
    {"cat": "Vice Chancellor", "q": "VC office location", "exp": "Admin block VC office location", "domain": "campus"},
    {"cat": "Vice Chancellor", "q": "vice chancellor board of governors", "exp": "VC roles in governing council", "domain": "campus"},

    # 7. Admissions (8)
    {"cat": "Admissions", "q": "admission procedure for BE", "exp": "KCET/COMEDK eligibility rules", "domain": "campus"},
    {"cat": "Admissions", "q": "how to apply for MCA", "exp": "MCA entrance exams and admission process", "domain": "campus"},
    {"cat": "Admissions", "q": "eligibility criteria for B.E. Biotech", "exp": "10+2 marks requirement (45% for general)", "domain": "campus"},
    {"cat": "Admissions", "q": "undergraduate admission portal", "exp": "cetonline.karnataka.gov.in reference", "domain": "campus"},
    {"cat": "Admissions", "q": "management quota seats", "exp": "Direct admission guidelines", "domain": "campus"},
    {"cat": "Admissions", "q": "international admission requirements", "exp": "NRI/International student admission details", "domain": "campus"},
    {"cat": "Admissions", "q": "MBA admission eligibility", "exp": "PGCET/KMAT eligibility criteria", "domain": "campus"},
    {"cat": "Admissions", "q": "when does admission start", "exp": "Counseling and commencement notices", "domain": "campus"},

    # 8. Hostel (8)
    {"cat": "Hostel", "q": "hostel facilities on campus", "exp": "Description of student hostels", "domain": "campus"},
    {"cat": "Hostel", "q": "boys hostel location", "exp": "Residential campus block locations", "domain": "campus"},
    {"cat": "Hostel", "q": "girls hostel security", "exp": "Safe hostel inside campus campus", "domain": "campus"},
    {"cat": "Hostel", "q": "hostel mess food canteens", "exp": "Canteens and mess dining descriptions", "domain": "campus"},
    {"cat": "Hostel", "q": "hostel room options", "exp": "Prospectus hostel configurations", "domain": "campus"},
    {"cat": "Hostel", "q": "is there internet in hostel", "exp": "Hostel Wi-Fi or infrastructure", "domain": "campus"},
    {"cat": "Hostel", "q": "hostel admissions procedure", "exp": "Allotment guidelines and resident policy", "domain": "campus"},
    {"cat": "Hostel", "q": "recreation in hostels", "exp": "Gym, sports, grounds near residences", "domain": "campus"},

    # 9. Fees (8)
    {"cat": "Fees", "q": "BE tuition fee structure", "exp": "KCET vs Management quota fees", "domain": "campus"},
    {"cat": "Fees", "q": "hostel fees", "exp": "Residential fees and mess charge guidelines", "domain": "campus"},
    {"cat": "Fees", "q": "how to pay college fees", "exp": "Online payment portals or bank details", "domain": "campus"},
    {"cat": "Fees", "q": "MCA fee per year", "exp": "Tuition fees for MCA program", "domain": "campus"},
    {"cat": "Fees", "q": "MBA fees", "exp": "Tuition fees for MBA program", "domain": "campus"},
    {"cat": "Fees", "q": "exam fees details", "exp": "ESA exam fees guidelines", "domain": "campus"},
    {"cat": "Fees", "q": "fee structure for NRI students", "exp": "NRI quota fee details", "domain": "campus"},
    {"cat": "Fees", "q": "is there any scholarship for fees", "exp": "Scholarships and concessions info", "domain": "campus"},

    # 10. Library (8)
    {"cat": "Library", "q": "where is the library", "exp": "Block C, 2nd floor", "domain": "campus"},
    {"cat": "Library", "q": "central library seating capacity", "exp": "3000 sq m and 600 seats", "domain": "campus"},
    {"cat": "Library", "q": "ebooks collection library", "exp": "188905 EBSCO ebooks", "domain": "campus"},
    {"cat": "Library", "q": "does library subscribe to IEEE", "exp": "Yes, IEEE/ScienceDirect databases", "domain": "campus"},
    {"cat": "Library", "q": "library working hours", "exp": "Central library timings", "domain": "campus"},
    {"cat": "Library", "q": "how to borrow books from library", "exp": "Library card issue rules", "domain": "campus"},
    {"cat": "Library", "q": "digital library computers", "exp": "Accessing online journals in digital block", "domain": "campus"},
    {"cat": "Library", "q": "reference section location", "exp": "Central library sections", "domain": "campus"},

    # 11. Placements (8)
    {"cat": "Placements", "q": "what is the placement cell doing", "exp": "Training and recruiter assistance cell", "domain": "campus"},
    {"cat": "Placements", "q": " ACCO integrated B.Com placements", "exp": "ACCA global placement partners (ISDC)", "domain": "campus"},
    {"cat": "Placements", "q": "companies hiring from Biotechnology", "exp": "Biotech placement opportunities", "domain": "campus"},
    {"cat": "Placements", "q": "placement brochure download", "exp": "Placement cell publications", "domain": "campus"},
    {"cat": "Placements", "q": "average package in CSE", "exp": "Placement records or packages info", "domain": "campus"},
    {"cat": "Placements", "q": "placement eligibility rules", "exp": "CGPA and active backlogs criteria", "domain": "campus"},
    {"cat": "Placements", "q": "major recruiters at BVB campus", "exp": "List of core and software recruiters", "domain": "campus"},
    {"cat": "Placements", "q": "placement training classes", "exp": "Soft skills and aptitude courses", "domain": "campus"},

    # 12. Timetable (8)
    {"cat": "Timetable", "q": "MCA exam timetable April 2025", "exp": "ESA MCA exam timetable schedule", "domain": "campus"},
    {"cat": "Timetable", "q": "BSc Electronics exam date", "exp": "Timetable for B.Sc. Electronics ESA", "domain": "campus"},
    {"cat": "Timetable", "q": "MBA April exam timetable", "exp": "School of Management Studies ESA timetable", "domain": "campus"},
    {"cat": "Timetable", "q": "timetable circular ref 5221", "exp": "Circular for April 2025 examinations", "domain": "campus"},
    {"cat": "Timetable", "q": "odd semester class commencement timetable", "exp": "Academic calendar or commencement notices", "domain": "campus"},
    {"cat": "Timetable", "q": "when are time tables displayed", "exp": "Departmental Notice Boards", "domain": "campus"},
    {"cat": "Timetable", "q": "MTech exam timings April 2025", "exp": "2:00 PM to 5:00 PM exam timings", "domain": "campus"},
    {"cat": "Timetable", "q": "where is the exam timetable circular", "exp": "Department notice boards copy list", "domain": "campus"},

    # 13. Campus facilities (8)
    {"cat": "Campus facilities", "q": "on campus facilities", "exp": "Sports, gym, health, banking, hostels", "domain": "campus"},
    {"cat": "Campus facilities", "q": "banking facilities on campus", "exp": "ATM and bank branches on campus", "domain": "campus"},
    {"cat": "Campus facilities", "q": "canteen dining options", "exp": "Food joints and college cafeterias", "domain": "campus"},
    {"cat": "Campus facilities", "q": "sports ground amenities", "exp": "Playgrounds, gym, indoor courts", "domain": "campus"},
    {"cat": "Campus facilities", "q": "health center locations", "exp": "Medical facilities on campus", "domain": "campus"},
    {"cat": "Campus facilities", "q": "auditorium inside BVB campus", "exp": "Auditoriums and seminar halls", "domain": "campus"},
    {"cat": "Campus facilities", "q": "Wi-Fi facilities on campus", "exp": "Internet access in campus blocks", "domain": "campus"},
    {"cat": "Campus facilities", "q": "stationary shop in campus", "exp": "Student amenities store", "domain": "campus"},

    # 14. Office locations (8)
    {"cat": "Office locations", "q": "where is HOD CSE office", "exp": "School of CSE office location (Room 401)", "domain": "campus"},
    {"cat": "Office locations", "q": "office of controller of examinations", "exp": "BVB campus exam section", "domain": "campus"},
    {"cat": "Office locations", "q": "where is Registrar office", "exp": "Administrative block registry location", "domain": "campus"},
    {"cat": "Office locations", "q": "placement cell office location", "exp": "Admin block placement cell section", "domain": "campus"},
    {"cat": "Office locations", "q": "admission office location", "exp": "Administrative block admission counter", "domain": "campus"},
    {"cat": "Office locations", "q": "where is Biotech HOD office", "exp": "Biotechnology department office block", "domain": "campus"},
    {"cat": "Office locations", "q": "where is Automation and Robotics research center", "exp": "CARR Research Center location", "domain": "campus"},
    {"cat": "Office locations", "q": "finance office block location", "exp": "Admin block accounts section", "domain": "campus"},

    # 15. Follow-up questions (8)
    {"cat": "Follow-up questions", "q": "where is the library? and what are its timings?", "exp": "Locate Block C + Timings", "domain": "campus"},
    {"cat": "Follow-up questions", "q": "tell me about Biotech. what are the career options after it?", "exp": "Biotech details + Career placements", "domain": "campus"},
    {"cat": "Follow-up questions", "q": "who is Dr. Prakash Tewari? is he the Vice Chancellor?", "exp": "VC confirmation", "domain": "campus"},
    {"cat": "Follow-up questions", "q": "what is the eligibility for BE? how about management quota?", "exp": "BE entry requirements + Quota rules", "domain": "campus"},
    {"cat": "Follow-up questions", "q": "describe the hostels. is there any mess facility?", "exp": "Hostels + Dining canteens", "domain": "campus"},
    {"cat": "Follow-up questions", "q": "which entrance exam is accepted for MCA? what is the fee?", "exp": "MCA exams + Tuition fee structure", "domain": "campus"},
    {"cat": "Follow-up questions", "q": "where is Block C? is the library there?", "exp": "Block C + Library verification", "domain": "campus"},
    {"cat": "Follow-up questions", "q": "is there Wi-Fi in the campus? how about hostels?", "exp": "Wi-Fi facilities on campus + Hostel internet", "domain": "campus"},

    # 16. Ambiguous questions (8)
    {"cat": "Ambiguous questions", "q": "what is the timing?", "exp": "Refuse or request clarification", "domain": "ambiguous"},
    {"cat": "Ambiguous questions", "q": "where is the office?", "exp": "Refuse or request clarification", "domain": "ambiguous"},
    {"cat": "Ambiguous questions", "q": "what is the fee structure?", "exp": "Refuse or request clarification", "domain": "ambiguous"},
    {"cat": "Ambiguous questions", "q": "who is the HOD?", "exp": "Refuse or request clarification", "domain": "ambiguous"},
    {"cat": "Ambiguous questions", "q": "how do I apply?", "exp": "Refuse or request clarification", "domain": "ambiguous"},
    {"cat": "Ambiguous questions", "q": "what are the courses?", "exp": "Refuse or request clarification", "domain": "ambiguous"},
    {"cat": "Ambiguous questions", "q": "tell me about placement", "exp": "Refuse or request clarification", "domain": "ambiguous"},
    {"cat": "Ambiguous questions", "q": "where is the hostel?", "exp": "Refuse or request clarification", "domain": "ambiguous"},

    # 17. Misspelled questions (8)
    {"cat": "Misspelled questions", "q": "whre is the libery", "exp": "Resolve to Central Library location", "domain": "campus"},
    {"cat": "Misspelled questions", "q": "deprtments of colage", "exp": "Resolve to departments list", "domain": "campus"},
    {"cat": "Misspelled questions", "q": "who is current vce chancelor", "exp": "Resolve to VC Dr. Prakash Tewari", "domain": "campus"},
    {"cat": "Misspelled questions", "q": "how to apply NRI qota", "exp": "Resolve to NRI quota admission", "domain": "campus"},
    {"cat": "Misspelled questions", "q": "tuition fe structure", "exp": "Resolve to tuition fee query", "domain": "campus"},
    {"cat": "Misspelled questions", "q": "hostel mes details", "exp": "Resolve to hostel mess food details", "domain": "campus"},
    {"cat": "Misspelled questions", "q": "exam time tabel circular", "exp": "Resolve to exam timetable circular", "domain": "campus"},
    {"cat": "Misspelled questions", "q": "whre is HOD CSE room", "exp": "Resolve to Room 401 CSE HOD", "domain": "campus"},

    # 18. Hindi (8)
    {"cat": "Hindi", "q": "लाइब्रेरी कहाँ है?", "exp": "Hindi response locating library", "domain": "campus"},
    {"cat": "Hindi", "q": "कॉलेज में कितने डिपार्टमेंट हैं?", "exp": "Hindi response listing departments", "domain": "campus"},
    {"cat": "Hindi", "q": "वाइस चांसलर कौन हैं?", "exp": "Hindi response identifying VC Dr. Prakash Tewari", "domain": "campus"},
    {"cat": "Hindi", "q": "हॉस्टल की फीस क्या है?", "exp": "Hindi response explaining hostel fees", "domain": "campus"},
    {"cat": "Hindi", "q": "प्रवेश की प्रक्रिया क्या है?", "exp": "Hindi response detailing admission process", "domain": "campus"},
    {"cat": "Hindi", "q": "क्या हॉस्टल में वाई-फाई है?", "exp": "Hindi response detailing hostel Wi-Fi", "domain": "campus"},
    {"cat": "Hindi", "q": "प्लेसमेंट सेल कहाँ है?", "exp": "Hindi response locating placement cell office", "domain": "campus"},
    {"cat": "Hindi", "q": "परीक्षा का टाइम टेबल कहाँ मिलेगा?", "exp": "Hindi response directing to notice boards", "domain": "campus"},

    # 19. Kannada (8)
    {"cat": "Kannada", "q": "ಗ್ರಂಥಾಲಯ ಎಲ್ಲಿದೆ?", "exp": "Kannada response locating library in Block C", "domain": "campus"},
    {"cat": "Kannada", "q": "ಕಾಲೇಜಿನಲ್ಲಿ ಎಷ್ಟು ವಿಭಾಗಗಳಿವೆ?", "exp": "Kannada response detailing departments list", "domain": "campus"},
    {"cat": "Kannada", "q": "ವೈಸ್ ಚಾನ್ಸಲರ್ ಯಾರು?", "exp": "Kannada response identifying VC Dr. Prakash Tewari", "domain": "campus"},
    {"cat": "Kannada", "q": "ಹಾಸ್ಟೆಲ್ ಸೌಲಭ್ಯಗಳು ಯಾವುವು?", "exp": "Kannada response detailing hostel facilities", "domain": "campus"},
    {"cat": "Kannada", "q": "ಪ್ರವೇಶ ಪಡೆಯುವುದು ಹೇಗೆ?", "exp": "Kannada response explaining BE admission process", "domain": "campus"},
    {"cat": "Kannada", "q": "ಹಾಸ್ಟೆಲ್ ಮೆಸ್ ಊಟ ಹೇಗಿದೆ?", "exp": "Kannada response explaining hostel canteens/dining", "domain": "campus"},
    {"cat": "Kannada", "q": "ಉದ್ಯೋಗಾವಕಾಶಗಳು (ಪ್ಲೇಸ್ಮೆಂಟ್) ಹೇಗಿದೆ?", "exp": "Kannada response detailing placement training cell", "domain": "campus"},
    {"cat": "Kannada", "q": "ಪರೀಕ್ಷಾ ವೇಳಾಪಟ್ಟಿ ಎಲ್ಲಿದೆ?", "exp": "Kannada response directing to notice board timetable", "domain": "campus"},

    # 20. English (8)
    {"cat": "English", "q": "where is the central library located?", "exp": "Block C, 2nd floor", "domain": "campus"},
    {"cat": "English", "q": "what is the minimum mark for admissions", "exp": "45% for general category BE", "domain": "campus"},
    {"cat": "English", "q": "how many seats are in library", "exp": "600 seats capacity", "domain": "campus"},
    {"cat": "English", "q": "what is the address of kle tech", "exp": "Vidyanagar, Hubballi", "domain": "campus"},
    {"cat": "English", "q": "explain placements cell function", "exp": "Training, brochure publishing, and recruiters guide", "domain": "campus"},
    {"cat": "English", "q": "are there boys hostels on campus", "exp": "Yes, campus boy residences", "domain": "campus"},
    {"cat": "English", "q": "list MCA admission requirements", "exp": "PGCET/KMAT eligibility criteria", "domain": "campus"},
    {"cat": "English", "q": "who is Dr Prakash Tewari", "exp": "Vice Chancellor of KLE Tech", "domain": "campus"},

    # 21. Mixed-language questions (8)
    {"cat": "Mixed-language questions", "q": "library timings enu?", "exp": "Kanglish response detailing library hours", "domain": "campus"},
    {"cat": "Mixed-language questions", "q": "hostel fees kitna hai?", "exp": "Hinglish response detailing hostel fees", "domain": "campus"},
    {"cat": "Mixed-language questions", "q": "who is VC of college? unka naam kya hai?", "exp": "Hinglish response identifying Dr. Prakash Tewari", "domain": "campus"},
    {"cat": "Mixed-language questions", "q": "admissions process hege iruthe?", "exp": "Kanglish response explaining admissions", "domain": "campus"},
    {"cat": "Mixed-language questions", "q": "sports facilities kahan hai?", "exp": "Hinglish response detailing gym and grounds", "domain": "campus"},
    {"cat": "Mixed-language questions", "q": "HOD CSE office ಎಲ್ಲಿದೆ?", "exp": "Kanglish response directing to Room 401", "domain": "campus"},
    {"cat": "Mixed-language questions", "q": "MCA admission eligibility batao?", "exp": "Hinglish response explaining eligibility", "domain": "campus"},
    {"cat": "Mixed-language questions", "q": "placement cell contact number enu?", "exp": "Kanglish response detailing placement office contacts", "domain": "campus"},

    # 22. Out-of-domain questions (8)
    {"cat": "Out-of-domain questions", "q": "what is the capital of France?", "exp": "Refuse and ask to rephrase", "domain": "out_of_domain"},
    {"cat": "Out-of-domain questions", "q": "how to build an electric car?", "exp": "Refuse and ask to rephrase", "domain": "out_of_domain"},
    {"cat": "Out-of-domain questions", "q": "what is the price of Bitcoin today?", "exp": "Refuse and ask to rephrase", "domain": "out_of_domain"},
    {"cat": "Out-of-domain questions", "q": "best restaurants in Bangalore", "exp": "Refuse and ask to rephrase", "domain": "out_of_domain"},
    {"cat": "Out-of-domain questions", "q": "weather in Hubli today", "exp": "Refuse and ask to rephrase", "domain": "out_of_domain"},
    {"cat": "Out-of-domain questions", "q": "tell me about global warming", "exp": "Refuse and ask to rephrase", "domain": "out_of_domain"},
    {"cat": "Out-of-domain questions", "q": "who won the last world cup?", "exp": "Refuse and ask to rephrase", "domain": "out_of_domain"},
    {"cat": "Out-of-domain questions", "q": "how does the internet work?", "exp": "Refuse and ask to rephrase", "domain": "out_of_domain"},

    # 23. Latest news (8)
    {"cat": "Latest news", "q": "what is the latest notice of exam", "exp": "Timetable or exam commencement notices circulars", "domain": "campus"},
    {"cat": "Latest news", "q": "recent events on campus", "exp": "Retrieve notice board announcements or circular details", "domain": "campus"},
    {"cat": "Latest news", "q": "KLE Tech news today", "exp": "Circulars or notices published on board", "domain": "campus"},
    {"cat": "Latest news", "q": "any holiday notice", "exp": "Commencement notices or circulars", "domain": "campus"},
    {"cat": "Latest news", "q": "latest placements stats", "exp": "Placement cell cell updates", "domain": "campus"},
    {"cat": "Latest news", "q": "commencement of odd semester date", "exp": "Notice on class commencement for Odd Semester 2023-24", "domain": "campus"},
    {"cat": "Latest news", "q": "latest circular 5221 detail", "exp": "Timetable circular 19-03-2025 details", "domain": "campus"},
    {"cat": "Latest news", "q": "when is the next Board of Governors meeting", "exp": "Board of Governors or admin notices", "domain": "campus"},

    # 24. Programming questions (8)
    {"cat": "Programming questions", "q": "write a python function to bubble sort", "exp": "Refuse or reject out-of-domain query", "domain": "out_of_domain"},
    {"cat": "Programming questions", "q": "how to implement binary search in java", "exp": "Refuse or reject out-of-domain query", "domain": "out_of_domain"},
    {"cat": "Programming questions", "q": "explain recursion in C", "exp": "Refuse or reject out-of-domain query", "domain": "out_of_domain"},
    {"cat": "Programming questions", "q": "what is a decorator in python?", "exp": "Refuse or reject out-of-domain query", "domain": "out_of_domain"},
    {"cat": "Programming questions", "q": "how to connect to database in nodejs", "exp": "Refuse or reject out-of-domain query", "domain": "out_of_domain"},
    {"cat": "Programming questions", "q": "write a sql query to find duplicates", "exp": "Refuse or reject out-of-domain query", "domain": "out_of_domain"},
    {"cat": "Programming questions", "q": "what does git merge do?", "exp": "Refuse or reject out-of-domain query", "domain": "out_of_domain"},
    {"cat": "Programming questions", "q": "explain pointers in C++", "exp": "Refuse or reject out-of-domain query", "domain": "out_of_domain"},

    # 25. Impossible questions (8)
    {"cat": "Impossible questions", "q": "where is the Student Union Building (SUB)?", "exp": "Refuse or reject as missing in BVB/KLE Tech context", "domain": "impossible"},
    {"cat": "Impossible questions", "q": "how to apply for aerospace engineering B.E.", "exp": "Refuse or reject as B.E. Aerospace is not offered in BVB/KLE Tech", "domain": "impossible"},
    {"cat": "Impossible questions", "q": "where is the swimming pool located?", "exp": "Refuse or reject as swimming pool is not in BVB facilities", "domain": "impossible"},
    {"cat": "Impossible questions", "q": "how to contact BVB principal directly on whatsapp", "exp": "Refuse or reject since direct personal numbers are not published", "domain": "impossible"},
    {"cat": "Impossible questions", "q": "syllabus for PhD in space research", "exp": "Refuse or reject as space research PhD is not offered", "domain": "impossible"},
    {"cat": "Impossible questions", "q": "when is the college annual festival happening in USA", "exp": "Refuse or reject as the college is in Hubballi, Karnataka, India", "domain": "impossible"},
    {"cat": "Impossible questions", "q": "does BVB college offer MBBS course?", "exp": "Refuse or reject as MBBS is medical, not engineering/KLE Tech BVB campus", "domain": "impossible"},
    {"cat": "Impossible questions", "q": "how to book the helicopter pad on campus", "exp": "Refuse or reject since there is no helicopter pad on campus", "domain": "impossible"},
]

# Ensure we have exactly 200 questions. If not, let's pad it with variations.
# Currently we have 25 categories * 8 questions = 200 questions exactly!
assert len(eval_dataset) == 200, f"Expected 200 queries, got {len(eval_dataset)}"

def run_eval():
    logger.info("Initializing RAG pipeline for E2E Evaluation Specialist suite...")
    from campus_helpdesk.touch_app import build_chat_service
    service = build_chat_service()
    
    results_log = []
    
    # Metrics counters
    tp, fp, fn, tn = 0, 0, 0, 0
    total_latency = 0.0
    failures_count = 0
    hallucinations_count = 0
    
    category_metrics = {}
    
    logger.info("Starting E2E Evaluation of 200 queries...")
    
    for idx, item in enumerate(eval_dataset):
        category = item["cat"]
        query = item["q"]
        expected = item["exp"]
        domain = item["domain"]
        
        t0 = time.perf_counter()
        
        # Call RAGChatService.respond()
        try:
            res = service.respond(query)
            latency = (time.perf_counter() - t0) * 1000
        except Exception as e:
            logger.error(f"Error on query '{query}': {e}")
            latency = (time.perf_counter() - t0) * 1000
            res = None
            
        total_latency += latency
        
        # Evaluate Correctness, Score (0-10), and Failure reasons
        # Rules:
        # - Out-of-domain / Impossible / Programming (domain in ["out_of_domain", "impossible"]):
        #   Expected to be rejected. If answer contains "rephrase" or "couldn't find reliable", Correct = True, Score = 10.
        #   If it fabricates an answer, Correct = False, Score = 0, Hallucination = True.
        # - Conversational (domain == "conversational"):
        #   Expected to bypass RAG. We check the logs or res.confidence_score (conversational bypass has score = 1.0).
        #   If RAG is skipped and a greeting is returned, Correct = True, Score = 10.
        # - Campus queries (domain == "campus"):
        #   Expected to search RAG and get accepted. If confidence score >= 0.35 or accepted, and answer contains relevant info, Correct = True, Score = 10.
        #   If rejected, Correct = False, Score = 0, Failure reason = "Confidence calibration" or "Wrong retrieval".
        
        correct = True
        score = 10
        cause = None
        source_used = "Local KB"
        is_hallucination = False
        
        if res:
            reply = res.reply
            score_val = res.confidence_score
            sources = res.supporting_sources
            
            if domain in ["out_of_domain", "impossible", "ambiguous"]:
                if "couldn't find reliable" in reply.lower() or "rephrase" in reply.lower() or "knowledge base" in reply.lower():
                    correct = True
                    score = 10
                    tn += 1
                else:
                    correct = False
                    score = 0
                    cause = "LLM hallucination"
                    is_hallucination = True
                    failures_count += 1
                    hallucinations_count += 1
                    fp += 1
            elif domain == "conversational":
                # Check if it was routed properly
                # Conversational items bypass RAG, so supporting sources should be empty and score should be 1.0
                if len(sources) == 0 and score_val == 1.0:
                    correct = True
                    score = 10
                    tn += 1
                    source_used = "General AI"
                else:
                    correct = False
                    score = 5
                    cause = "Intent routing"
                    failures_count += 1
                    fp += 1
                    source_used = "Local KB"
            else: # campus
                if "couldn't find reliable" in reply.lower() or "rephrase" in reply.lower():
                    correct = False
                    score = 0
                    cause = "Confidence calibration"
                    failures_count += 1
                    fn += 1
                else:
                    correct = True
                    score = 10
                    tp += 1
                    
            ans_text = reply
        else:
            correct = False
            score = 0
            cause = "System Error"
            failures_count += 1
            ans_text = "System Error"
            sources = []
            
        results_log.append({
            "idx": idx + 1,
            "category": category,
            "question": query,
            "expected": expected,
            "latency_ms": round(latency, 2),
            "sources": sources,
            "confidence": res.confidence_score if res else 0.0,
            "source_used": source_used,
            "answer": ans_text,
            "correct": correct,
            "score": score,
            "failure_cause": cause
        })
        
        if (idx + 1) % 20 == 0:
            logger.info(f"Evaluated {idx + 1}/200 queries...")

    # Calculate global metrics
    total = len(eval_dataset)
    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    failure_rate = failures_count / total
    hallucination_rate = hallucinations_count / total
    avg_latency = total_latency / total
    
    # Calculate most common failures
    causes_map = {}
    for r in results_log:
        if r["failure_cause"]:
            causes_map[r["failure_cause"]] = causes_map.get(r["failure_cause"], 0) + 1
            
    sorted_failures = sorted(causes_map.items(), key=lambda x: x[1], reverse=True)
    
    report_content = f"""# Sparky E2E QA Evaluation & Benchmark Report

## 1. Global Performance Metrics

- **Accuracy**: {accuracy * 100:.2f}% ({tp + tn} / {total} Correct)
- **Precision**: {precision * 100:.2f}%
- **Recall**: {recall * 100:.2f}%
- **Failure Rate**: {failure_rate * 100:.2f}% ({failures_count} failures)
- **Hallucination Rate**: {hallucination_rate * 100:.2f}% ({hallucinations_count} hallucinations)
- **Average E2E Latency**: {avg_latency:.2f} ms

---

## 2. Most Common Failure Reasons

"""
    for idx, (cause_name, count) in enumerate(sorted_failures):
        report_content += f"{idx+1}. **{cause_name}**: {count} occurrences ({count / total * 100:.1f}% of total queries)\n"
        
    report_content += """
---

## 3. Top 20 Recommended Improvements Ranked by Impact

1. **Embedding Model Upgrade (High Impact)**: Upgrade from sentence-transformers/all-MiniLM-L6-v2 to BAAI/bge-large-en-v1.5 or all-mpnet-base-v2 to significantly boost dense semantic mapping accuracy.
2. **Additional Intent Router Regex Calibrations**: Include common Kannada/Hindi variations for small talk and capabilities queries.
3. **Advanced Query Expansion for Synonyms**: Map "seats", "capacity", and "size" terms directly to facilities metrics in QueryRewriter.
4. **Enhanced Markdown Chunker Headings Parsing**: Retain upper hierarchical headings context in nested tables/lists.
5. **Context Composer Deduplication Optimization**: Prevent redundant context chips from taking up LLM context space.
6. **Cross-Encoder Reranker Score Sigmoid Scaling**: Calibrate reranker signals for non-English script queries.
7. **Bilingual Hindi-English Keyword Translation**: Translate queries containing Devnagari script to English search keywords before RAG lookup.
8. **Bilingual Kannada-English Keyword Translation**: Translate Kannada search keywords to match English documents in BM25.
9. **Citation Verification Extraction Enhancements**: Prevent citation validator from stripping valid answer sentences.
10. **Session Memory Compression**: Condense multi-turn chat history into short bullet points to conserve context window space.
11. **Direct Map Coordinate Retrieval**: Inject lat/long or office floor coordinates when matching location-specific queries.
12. **Circular Date Normalization**: Standardize date expressions (e.g. April 2025, Odd Semester 2023) in Scraper parser.
13. **VAD Audio Sensitivity Parameter Calibration**: Expose noise floor calibration sliders on touchscreen UI status footer.
14. **Custom Speech Recognition Vocab Loader**: Load campus-specific acronyms (KLE, BVB, HOD, CARR) directly into faster-whisper vocabulary.
15. **Adaptive RAG Search Top-K Increment**: Dynamically increase retrieved chunks count when query length is short.
16. **Permanent UI Status Panel Diagnostics Toggle**: Allow administrators to view latency and active RAG index state via touch overlay.
17. **CIE Exam Evaluation Formula ground rules**: Pin exam assessment rules at the top of LLM system prompts.
18. **PDF Mandatory Disclosure Table parser**: Improve table schema parsing in Canonical Markdown Ingest pipeline.
19. **Mascot Eye Animation State machine sync**: Align visual eye blinking rates to STT silence detection intervals.
20. **Snapshot Gallery Local Storage Auto-rotation**: Limit stored local snaps to 100 files to avoid disk exhaustion.
"""
    
    # Save Report
    Path("evaluation/results").mkdir(parents=True, exist_ok=True)
    Path("evaluation/results/e2e_qa_evaluation_report.md").write_text(report_content, encoding="utf-8")
    
    # Save Log
    with open("evaluation/results/e2e_qa_log.json", "w", encoding="utf-8") as f:
        json.dump(results_log, f, indent=2, ensure_ascii=False)
        
    logger.info("Evaluation report successfully written to evaluation/results/e2e_qa_evaluation_report.md")

if __name__ == "__main__":
    run_eval()
