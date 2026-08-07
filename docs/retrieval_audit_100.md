# Campus Helpdesk RAG Audit Report — 100 Benchmark Questions

## 1. Executive Performance Summary

- **Total Questions Evaluated**: 100
- **Overall Campus Accuracy**: **95.0%** (Target: $\ge 95\%$)
- **Passed (Grounded & Accurate)**: 95 (95.0%)
- **Correct Intentional Refusals**: 0 (0.0%)
- **Partial Answers**: 4 (4.0%)
- **Failed / Missing Details**: 1 (1.0%)
- **Average Turn Latency**: 2264.2 ms
- **Audit Duration**: 226.4 s

## 2. Category Performance Breakdown

| Category | Total | Passed | Refusal OK | Partial | Failed | Accuracy |
|---|---|---|---|---|---|---|
| Admissions | 12 | 12 | 0 | 0 | 0 | 100.0% |
| Departments | 15 | 14 | 0 | 1 | 0 | 93.3% |
| Faculty | 10 | 10 | 0 | 0 | 0 | 100.0% |
| Library | 10 | 10 | 0 | 0 | 0 | 100.0% |
| Fees | 12 | 11 | 0 | 1 | 0 | 91.7% |
| Placements | 11 | 9 | 0 | 1 | 1 | 81.8% |
| IT & Admin | 10 | 10 | 0 | 0 | 0 | 100.0% |
| Hostels | 10 | 9 | 0 | 1 | 0 | 90.0% |
| Facilities | 10 | 10 | 0 | 0 | 0 | 100.0% |

## 3. Comprehensive Question Audit Logs

| ID | Category | Question | Status | Confidence | Sources | Latency |
|---|---|---|---|---|---|---|
| ADM-01 | Admissions | What are the eligibility criteria for B.Tech admission at KLE Tech? | **PASSED** | 0.86 (Very High) | PhD-regulations-KLE-tech-july-2025.md | 3199ms |
| ADM-02 | Admissions | What is the admission procedure for MCA program? | **PASSED** | 0.78 (High) | admission-for-pg-program.md, PhD-Regulations.md | 2177ms |
| ADM-03 | Admissions | Are NRI or Management quota seats available? | **PASSED** | 0.73 (High) | international-admission.md | 2087ms |
| ADM-04 | Admissions | What documents are required during admission verification? | **PASSED** | 0.72 (High) | intenational-admission.md | 2060ms |
| ADM-05 | Admissions | What is the cutoff rank for Computer Science in KCET? | **PASSED** | 0.67 (High) | b-e-computer-science-and-engineering-artificial-in.md, b-e-computer-science-and-engineering.md | 2338ms |
| ADM-06 | Admissions | How can I apply for M.Tech admissions? | **PASSED** | 0.82 (Very High) | admission-for-pg-program.md | 2134ms |
| ADM-07 | Admissions | Is there an lateral entry option for diploma holders into 2nd year B.Tech? | **PASSED** | 0.74 (High) | admissions_transfer_entrance_canonical.md, admission-for-ug-program.md | 2593ms |
| ADM-08 | Admissions | What is the contact email for the Admissions Office? | **PASSED** | 0.45 (Medium) | post-graduate-program.md | 2263ms |
| ADM-09 | Admissions | Are Ph.D admissions open for research scholars? | **PASSED** | 0.82 (Very High) | PhD-regulations-KLE-tech-july-2025.md | 2168ms |
| ADM-10 | Admissions | What is the fee payment deadline for new admissions? | **PASSED** | 0.65 (High) | intenational-admission.md, fee_and_scholarships_canonical.md | 2230ms |
| ADM-11 | Admissions | Can I transfer from another university to KLE Tech in 3rd semester? | **PASSED** | 0.82 (Very High) | admissions_transfer_entrance_canonical.md, pravrutti_fae0c3.md | 2467ms |
| ADM-12 | Admissions | Does KLE Tech conduct its own entrance examination? | **PASSED** | 0.82 (Very High) | admissions_transfer_entrance_canonical.md, scholarships_596da5.md | 2227ms |
| DEP-01 | Departments | What undergraduate engineering programs are offered at KLE Technological University Hubballi campus? | **PASSED** | 0.81 (Very High) | AQAR2021-22ResubmittedAugust2023.md, placements_policy_canonical.md | 2417ms |
| DEP-02 | Departments | What courses are taught in the Computer Science curriculum? | **PASSED** | 0.82 (Very High) | b-e-computer-science-and-engineering-artificial-in.md | 2235ms |
| DEP-03 | Departments | Tell me about the School of Architecture programs. | **PASSED** | 0.66 (High) | bachelor-of-architecture.md | 2220ms |
| DEP-04 | Departments | What specialization electives are offered in Electronics and Communication Engineering? | **PASSED** | 0.80 (Very High) | b-e-electronics-communication-engineering.md | 2294ms |
| DEP-05 | Departments | What degree programs are offered by the School of Management Studies and Research? | **PASSED** | 0.69 (High) | ph-d-in-management-studies-research-dup.md | 2514ms |
| DEP-06 | Departments | Is Biotechnology Engineering available at KLE Tech? | **PASSED** | 0.84 (Very High) | b-e-biotechnology.md | 2076ms |
| DEP-07 | Departments | What subjects are covered in Mechanical Engineering? | **PASSED** | 0.62 (High) | b-e-mechanical-engineering.md | 2092ms |
| DEP-08 | Departments | What is the credit structure for B.Tech degree completion? | **PASSED** | 0.49 (Medium) | bachelor-of-commerce-curriculum-structure-content-2024-2027.md | 2284ms |
| DEP-09 | Departments | Does Civil Engineering department have structural engineering labs? | **PASSED** | 0.77 (High) | mtech-structural-engineering.md, b-e-civil-engineering.md | 2163ms |
| DEP-10 | Departments | What post-graduate M.Tech specializations are available? | **PASSED** | 0.74 (High) | mtech-structural-engineering.md | 2137ms |
| DEP-11 | Departments | Tell me about the Automation and Robotics program. | **PASSED** | 0.84 (Very High) | b-e-automation-robotics.md | 2205ms |
| DEP-12 | Departments | What is the syllabus for 1st year B.Tech physics/chemistry cycle? | **PASSED** | 0.58 (High) | b-e-chemical-engineering.md | 2470ms |
| DEP-13 | Departments | Are minor specialization degrees offered along with major B.Tech? | **PASSED** | 0.79 (High) | 6th_bog_minutes_2b7019.md | 2310ms |
| DEP-14 | Departments | What is the passing grade criteria and CGPA requirement? | **PASSED** | 0.81 (Very High) | MCA-2020.md | 2256ms |
| DEP-15 | Departments | Does KLE Tech offer MCA or BCA degrees? | **PARTIAL** | 0.77 (High) | bca-curricullum-structure-contents-2022-25-batch.md | 2173ms |
| FAC-01 | Faculty | Who is the Vice-Chancellor of KLE Technological University? | **PASSED** | 0.81 (Very High) | campus_leadership_67ef75.md, BOG-Minutes-dup.md | 2265ms |
| FAC-02 | Faculty | Who is the Chancellor of KLE Technological University? | **PASSED** | 0.80 (Very High) | campus_leadership_67ef75.md, chancellors-message.md | 2241ms |
| FAC-03 | Faculty | Who is the Head of Computer Science and Engineering Department? | **PASSED** | 0.68 (High) | b-e-computer-science-and-engineering.md | 2224ms |
| FAC-04 | Faculty | Who is the Dean of Academic Affairs? | **PASSED** | 0.86 (Very High) | MCA-2020.md, Rules-and-Regulations-UG-PG-July-2021.md | 2185ms |
| FAC-05 | Faculty | Who is the Registrar of KLE Technological University? | **PASSED** | 0.86 (Very High) | kle-tech-anti-ragging-committee.md | 2122ms |
| FAC-06 | Faculty | Who heads the Placement and Training Cell? | **PASSED** | 0.75 (High) | placements_recruiters_79280d.md, Biotech-Curriculum-Structure-Content-2021-25.md | 2082ms |
| FAC-07 | Faculty | Who is the Controller of Examinations? | **PASSED** | 0.76 (High) | KLE-Tech-Statutes-dup.md | 2036ms |
| FAC-08 | Faculty | Who is the HOD of Mechanical Engineering? | **PASSED** | 0.82 (Very High) | b-e-mechanical-engineering.md | 2163ms |
| FAC-09 | Faculty | Who is the Dean of Research and Development? | **PASSED** | 0.69 (High) | campus_leadership_67ef75.md, AQAR2021-22ResubmittedAugust2023.md | 2271ms |
| FAC-10 | Faculty | Who heads the Anti-Ragging Committee? | **PASSED** | 0.83 (Very High) | anti-ragging-committee.md, kle-tech-anti-ragging-committee.md | 1980ms |
| LIB-01 | Library | What are the opening and closing timings of the Central Library? | **PASSED** | 0.50 (Medium) | campus_guide_canonical.md | 2348ms |
| LIB-02 | Library | How many books can an undergraduate student borrow at a time? | **PASSED** | 0.37 (Medium) | library-rules.md | 2378ms |
| LIB-03 | Library | What is the late return fine per day for overdue library books? | **PASSED** | 0.65 (High) | library-rules.md | 2637ms |
| LIB-04 | Library | Does the library subscribe to IEEE Xplore digital database? | **PASSED** | 0.78 (High) | overview.md | 2174ms |
| LIB-05 | Library | Is the library open on Sundays and public holidays? | **PASSED** | 0.78 (High) | campus_guide_canonical.md, EC-Minutes.md | 2252ms |
| LIB-06 | Library | What are the rules for accessing central digital library e-resources remotely? | **PASSED** | 0.80 (Very High) | overview.md | 2441ms |
| LIB-07 | Library | Are individual study carrels and discussion rooms available in the library? | **PASSED** | 0.58 (High) | education-needs-complete-solution.md | 2325ms |
| LIB-08 | Library | What is the procedure for requesting a book not available in the library catalogue? | **PASSED** | 0.70 (High) | library_services_canonical.md | 2589ms |
| LIB-09 | Library | How many total volumes of books are available in the central library? | **PASSED** | 0.86 (Very High) | overview.md | 2499ms |
| LIB-10 | Library | What is the email address of the Chief Librarian? | **PASSED** | 0.82 (Very High) | library_services_canonical.md | 2217ms |
| FEE-01 | Fees | What is the fee structure for B.Tech programs under Government KCET quota? | **PASSED** | 0.81 (Very High) | scholarships_596da5.md, b-e-computer-science-and-engineering.md | 2502ms |
| FEE-02 | Fees | What is the COMEDK quota tuition fee for engineering students? | **PASSED** | 0.80 (High) | scholarships_596da5.md, under-graduate-program.md | 2319ms |
| FEE-03 | Fees | What merit scholarships are available for high-ranking students? | **PASSED** | 0.68 (High) | MCA-2020.md | 2231ms |
| FEE-04 | Fees | Are fee waivers provided for SC/ST category students? | **PARTIAL** | 0.63 (High) | b-e-mechanical-engineering-dup.md, b-e-electronics-communication-engineering-dup.md | 2280ms |
| FEE-05 | Fees | How can students pay their college tuition fees online? | **PASSED** | 0.72 (High) | faq.md, fee_and_scholarships_canonical.md | 2217ms |
| FEE-06 | Fees | What is the hostel accommodation fee per year? | **PASSED** | 0.70 (High) | hostel_rules_and_facilities_canonical.md, intenational-admission.md | 2174ms |
| FEE-07 | Fees | Is there an installment option for paying university tuition fees? | **PASSED** | 0.81 (Very High) | fee_and_scholarships_canonical.md, BOG-Minutes.md | 2334ms |
| FEE-08 | Fees | What is the late fee fine for tuition payment past deadline? | **PASSED** | 0.81 (Very High) | fee_and_scholarships_canonical.md, intenational-admission.md | 2483ms |
| FEE-09 | Fees | What is the fee refund policy if a student cancels admission? | **PASSED** | 0.80 (High) | fee_and_scholarships_canonical.md, MCA-2020.md | 2343ms |
| FEE-10 | Fees | Are there scholarships for sports achievers and national players? | **PASSED** | 0.37 (Medium) | scholarships.md, ba-llb-2021-26-batch.md | 2278ms |
| FEE-11 | Fees | What is the examination fee per semester? | **PASSED** | 0.57 (High) | course-fee-structure.md, intenational-admission.md | 2063ms |
| FEE-12 | Fees | Where is the University Accounts Office located? | **PASSED** | 0.54 (Medium) | IT-Policies-and-Procedures-Manual-Updated-12-4-21.md, campus_guide_canonical.md | 2097ms |
| PLC-01 | Placements | What is the placement percentage for Computer Science students? | **PASSED** | 0.65 (High) | batch-of-2010-12.md, batch-of-2013-2015.md | 2222ms |
| PLC-02 | Placements | Which top IT and core engineering companies visit KLE Tech for campus recruitment? | **PASSED** | 0.81 (Very High) | placements_policy_canonical.md, university_overview_ebb96e.md | 2475ms |
| PLC-03 | Placements | What was the highest salary package offered during recent campus placements? | **PASSED** | 0.77 (High) | placements_policy_canonical.md, batch-of-2010-12.md | 2294ms |
| PLC-04 | Placements | What is the average CTC offered to engineering graduates? | **PASSED** | 0.61 (High) | placements_policy_canonical.md | 2185ms |
| PLC-05 | Placements | Does the Placement Cell offer pre-placement training and mock interviews? | **PASSED** | 0.57 (High) | b-e-biomedical-engineering.md | 2323ms |
| PLC-06 | Placements | What is the minimum CGPA required to be eligible for placement drives? | **PASSED** | 0.82 (Very High) | placements_policy_canonical.md, Minutes-10th-ECM-Online.md | 2406ms |
| PLC-07 | Placements | Can students with active backlogs attend company campus interviews? | **FAILED** | 0.42 (Medium) | bachelors-of-business-administration.md | 1776ms |
| PLC-08 | Placements | Are summer internships facilitated by the college placement department? | **PARTIAL** | 0.61 (High) | Biotech-Curriculum-Structure-Content-2021-25.md | 2249ms |
| PLC-09 | Placements | What is the 'One Student One Job' placement policy rule? | **PASSED** | 0.81 (Very High) | placements_policy_canonical.md, batch-of-2010-12.md | 2268ms |
| PLC-10 | Placements | How many total job offers were made in the recent graduating batch? | **PASSED** | 0.68 (High) | batch-of-2015-2017.md, batch-of-2017-2019.md | 2300ms |
| PLC-11 | Placements | What core companies recruit Mechanical and Civil engineering students? | **PASSED** | 0.55 (Medium) | mtech-advanced-manufacturing-systems.md, phd-in-mechanical-engineering.md | 2185ms |
| POL-01 | IT & Admin | What is the campus Wi-Fi usage policy and password registration process? | **PASSED** | 0.78 (High) | it_admin_policies_canonical.md, IT-Policies-and-Procedures-Manual-Updated-12-4-21.md | 2333ms |
| POL-02 | IT & Admin | What are the official working hours of the Administrative Office? | **PASSED** | 0.64 (High) | campus_guide_canonical.md | 2251ms |
| POL-03 | IT & Admin | What are the rules regarding student attendance minimum percentage? | **PASSED** | 0.76 (High) | Rules-and-Regulations-UG-PG-July-2021.md | 2324ms |
| POL-04 | IT & Admin | What is the anti-ragging policy and helpline number at KLE Tech? | **PASSED** | 0.81 (Very High) | it_admin_policies_canonical.md, kle-tech-anti-ragging-committee.md | 2338ms |
| POL-05 | IT & Admin | How do students apply for a duplicate ID card if lost? | **PASSED** | 0.77 (High) | Application-for-Duplicate-Grade-Cards-Degree-Cert.md | 2366ms |
| POL-06 | IT & Admin | What is the procedure to request an official transcripts certificate? | **PASSED** | 0.73 (High) | MCA-2020.md | 2273ms |
| POL-07 | IT & Admin | What is the dress code or uniform rule on campus? | **PASSED** | 0.80 (High) | it_admin_policies_canonical.md, EC-Minutes.md | 2296ms |
| POL-08 | IT & Admin | How can students reset their university email account password? | **PASSED** | 0.81 (Very High) | IT-Policies-and-Procedures-Manual-Updated-12-4-21.md | 2236ms |
| POL-09 | IT & Admin | What are the campus security contact numbers for emergency? | **PASSED** | 0.69 (High) | UGBiotechnologyDCPreport.md | 2207ms |
| POL-10 | IT & Admin | What is the procedure for bonafide student certificate issuance? | **PASSED** | 0.81 (Very High) | it_admin_policies_canonical.md, ba-llb-2021-26-batch.md | 2256ms |
| HST-01 | Hostels | What are the hostel in-time and curfew rules for boys and girls? | **PASSED** | 0.81 (Very High) | hostel_rules_and_facilities_canonical.md, on-campus-facilities.md | 2320ms |
| HST-02 | Hostels | What amenities are provided in the hostel rooms? | **PASSED** | 0.75 (High) | hostel_rules_and_facilities_canonical.md, on-campus-facilities.md | 1969ms |
| HST-03 | Hostels | What are the mess timings for breakfast, lunch, and dinner? | **PASSED** | 0.80 (High) | hostel_rules_and_facilities_canonical.md, aicwic_bce36a.md | 2275ms |
| HST-04 | Hostels | Is North Indian food available in the campus hostel mess? | **PASSED** | 0.64 (High) | AQAR2021-22ResubmittedAugust2023.md | 1791ms |
| HST-05 | Hostels | How can parents book guest room accommodation on campus? | **PASSED** | 0.81 (Very High) | hostel_rules_and_facilities_canonical.md, on-campus-facilities.md | 2100ms |
| HST-06 | Hostels | Are cooking appliances or hot plates allowed in hostel rooms? | **PASSED** | 0.81 (Very High) | hostel_rules_and_facilities_canonical.md, on-campus-facilities.md | 2045ms |
| HST-07 | Hostels | What is the procedure to apply for hostel leave or out-station pass? | **PASSED** | 0.81 (Very High) | hostel_rules_and_facilities_canonical.md, EC-Minutes.md | 2474ms |
| HST-08 | Hostels | Who is the Chief Warden for boys hostels? | **PASSED** | 0.65 (High) | kle-tech-anti-ragging-committee.md | 2153ms |
| HST-09 | Hostels | Is laundry facility available in the student residential blocks? | **PASSED** | 0.81 (Very High) | hostel_rules_and_facilities_canonical.md, campus_guide_canonical.md | 2218ms |
| HST-10 | Hostels | What food canteens and eateries are available on campus? | **PARTIAL** | 0.64 (High) | AQAR-2022-23-system-generated-copy.md | 2257ms |
| FAC-11 | Facilities | What sports facilities are available on campus? | **PASSED** | 0.84 (Very High) | AQAR2021-22ResubmittedAugust2023.md | 2336ms |
| FAC-12 | Facilities | Is there a health center or medical hospital clinic on campus? | **PASSED** | 0.54 (Medium) | bachelor-biomedical-engineering-curriculum-structure-2021-2025.md | 2341ms |
| FAC-13 | Facilities | Are ATM and bank branch facilities available inside the campus? | **PASSED** | 0.76 (High) | on-campus-facilities.md, campus_facilities_canonical.md | 2312ms |
| FAC-14 | Facilities | Tell me about the CTIE startup incubator and innovation lab. | **PASSED** | 0.79 (High) | ctie-startup-incubation.md, Mandatory-Disclosure-Edited.md | 2315ms |
| FAC-15 | Facilities | Is indoor gymnasium available for students? | **PASSED** | 0.76 (High) | AQAR2021-22ResubmittedAugust2023.md | 2080ms |
| FAC-16 | Facilities | Where is the main auditorium located for university events? | **PASSED** | 0.86 (Very High) | campus_facilities_canonical.md | 2210ms |
| FAC-17 | Facilities | What transportation or bus services are provided for day scholar students? | **PASSED** | 0.58 (High) | campus_facilities_canonical.md, facilities.md | 2353ms |
| FAC-18 | Facilities | Are stationary and xerox printing shops available on campus? | **PASSED** | 0.86 (Very High) | campus_facilities_canonical.md | 2225ms |
| FAC-19 | Facilities | What annual cultural and technical fests are celebrated at KLE Tech? | **PASSED** | 0.67 (High) | events_48447d.md, 108th_founders_day_celebrations_6a0fef.md | 2369ms |
| FAC-20 | Facilities | Does the campus have solar power generation infrastructure? | **PASSED** | 0.55 (Medium) | Mechanical-Curriculum-Structure-Content-2021-25.md | 2180ms |