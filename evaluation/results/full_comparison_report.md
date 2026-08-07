# Full Side-by-Side Quality & Retrieval Comparison Report

**Total Benchmark Questions Evaluated**: 35

## High-Level Comparison Metrics

| Metric | Baseline Configuration | Optimized Configuration | Delta / Impact |
|---|---|---|---|
| **Average Latency** | 6.05s | **4.87s** | **19.6% Faster** |
| **Answer Correctness Rate** | 23/35 (65.7%) | 18/35 (51.4%) | -5 Questions |
| **Hallucination Rate** | 11/35 (31.4%) | 15/35 (42.9%) | Increased |
| **Questions Changed** | - | 30/35 | Identified Below |
| **Regressions Detected** | - | 5/35 | Identified Below |

---
## Per-Question Detailed Side-by-Side Comparison

### Question [LIB001] (Library): "Where is the Central Library located?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 4.86s | **4.015s** |
| **Top Retrieved Docs** | `facilities/campus_guide_canonical.md, 07-news-media/overview.md, 02-academics/academic-facilities.md` | `facilities/campus_guide_canonical.md` |
| **Confidence Score / Level** | 0.865 (Very High) | 0.8516 (Very High) |
| **Keyword Coverage** | 67% (`Administrative Block, Ground Floor`) | 67% (`Administrative Block, Ground Floor`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The Central Library is located in the Administrative Block, Ground Floor (Block C, 2nd Floor).

**Optimized Answer**:
> Central Library Location: Located in the Administrative Block, Ground Floor (Block C, 2nd Floor).

---
### Question [LIB002] (Library): "What is the carpet area and seating capacity of the Central Library?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 7.194s | **5.121s** |
| **Top Retrieved Docs** | `07-news-media/AQAR2021-22ResubmittedAugust2023.md, 07-news-media/AQAR-2022-23-system-generated-copy.md, 02-academics/academic-facilities.md` | `07-news-media/AQAR2021-22ResubmittedAugust2023.md` |
| **Confidence Score / Level** | 0.7885 (High) | 0.802 (Very High) |
| **Keyword Coverage** | 100% (`3000, 600`) | 100% (`3000, 600`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The carpet area of the Central Library at KLE Technological University, Hubballi is 3000 square meters. The seating capacity is 600.

**Optimized Answer**:
> The Central Library at KLE Technological University, Hubballi has a carpet area of 3000 square meters and a seating capacity of 600.

---
### Question [LIB003] (Library): "How many digital ebooks are available in the library collection?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.313s | **5.273s** |
| **Top Retrieved Docs** | `07-news-media/overview.md, 02-academics/academic-facilities.md` | `07-news-media/overview.md` |
| **Confidence Score / Level** | 0.7745 (High) | 0.8165 (Very High) |
| **Keyword Coverage** | 100% (`EBSCO, 188905`) | 100% (`EBSCO, 188905`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The Central Library has subscribed to 188905 ebooks from EBSCO Academic Collection with EBSCO Business Elite sources. Additionally, they collect ebooks from various publishers including IEEE MIT Press, IEEE Wiley, McGraw-Hill Access Engineering, Pearson Education, PHI India, New Age International, McGraw-Hill Express, Elsevier Publishers, CBS, and VIDEEYA ebooks perpetual access.

**Optimized Answer**:
> The Central Library subscribes to 188905 ebooks from EBSCO Academic Collection with EBSCO Business Elite sources. Additionally, they collect ebooks from various publishers including IEEE MIT Press, IEEE Wiley, McGraw-Hill Access Engineering, Pearson Education, PHI India, New Age International, McGraw-Hill Express, Elsevier publishers, CBS, and VIDEEYA ebooks perpetual access.

---
### Question [LIB004] (Library): "What online database subscriptions are provided by the library?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 7.178s | **5.377s** |
| **Top Retrieved Docs** | `07-news-media/overview.md, 07-news-media/AQAR-2022-23-system-generated-copy.md` | `07-news-media/overview.md` |
| **Confidence Score / Level** | 0.7248 (High) | 0.7775 (High) |
| **Keyword Coverage** | 67% (`IEEE, ASCE`) | 67% (`IEEE, ASCE`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The Central Library provides subscription to e-books and e-journals. Specifically, it subscribes to:  - 188905 ebooks from EBSCO Academic Collection with EBSCO Business Elite sources. - Ebooks from IEEE MIT Press, IEEE Wiley, McGraw-Hill Access Engineering, Pearson Education, PHI India, New Age International, McGraw-Hill Express, Elsevier publishers, CBS, and VIDEEYA.  Additionally, the library subscribes to 24637 full-text e-journals from IEEE, ASME, ASCE, EBSCO Management, EBSCO Art and Architecture, and Automotive Abstract.

**Optimized Answer**:
> The Central Library provides online database subscriptions from EBSCO Academic Collection, including EBSCO Business Elite sources. Additionally, they subscribe to IEEE, ASME, ASCE, EBSCO Management, EBSCO Art and Architecture, and Automotive Abstract full-text E-journals.

---
### Question [ADM001] (Admissions): "What entrance exams are accepted for B.E. undergraduate admissions?" — ✅ UNCHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 4.417s | **5.658s** |
| **Top Retrieved Docs** | `03-admissions-fees/post-graduate-program.md, 03-admissions-fees/admission-notification.md` | `03-admissions-fees/post-graduate-program.md, 03-admissions-fees/admission-notification.md` |
| **Confidence Score / Level** | 0.5171 (Medium) | 0.5171 (Medium) |
| **Keyword Coverage** | 0% (`None`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> I couldn't find verified information about that in my knowledge base.

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [ADM002] (Admissions): "What is the official Karnataka CET portal website for engineering admissions?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 6.249s | **5.348s** |
| **Top Retrieved Docs** | `03-admissions-fees/under-graduate-program.md, 03-admissions-fees/post-graduate-program.md, 03-admissions-fees/admission-for-ug-program.md` | `03-admissions-fees/under-graduate-program.md` |
| **Confidence Score / Level** | 0.8477 (Very High) | 0.8314 (Very High) |
| **Keyword Coverage** | 33% (`Admission`) | 33% (`Admission`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> The official Karnataka CET (Common Entrance Test) portal for engineering admissions can be found at:  

**Optimized Answer**:
> The official Karnataka CET (Common Entrance Test) Portal website for engineering admissions is:    For detailed information related to the application, examination, allotment of seats/counselling, payment, and admission process, candidates are requested to visit this website.

---
### Question [ADM003] (Admissions): "What is the minimum eligibility percentage for general category admissions in 10+2?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 7.313s | **4.594s** |
| **Top Retrieved Docs** | `02-academics/master-of-business-administration.md, 02-academics/b-e-computer-science-and-engineering.md, 02-academics/b-e-electronics-communication-engineering.md` | `02-academics/master-of-business-administration.md` |
| **Confidence Score / Level** | 0.6281 (High) | 0.6413 (High) |
| **Keyword Coverage** | 0% (`None`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> The minimum eligibility percentage for general category admissions in a bachelor's degree (10+2) at KLE Technological University (BVB Engineering College), Hubballi is 50%. This information can be found under the "Eligibility Criteria" section of the Master of Business Administration program details provided in the context.

**Optimized Answer**:
> The minimum eligibility percentage for general category admissions in a bachelor's degree (10+2+3) at KLE Technological University, BVB Engineering College, Hubballi is 50%.

---
### Question [ADM004] (Admissions): "How do candidates apply under the Management Quota?" — ⚠️ REGRESSION

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 9.236s | **3.993s** |
| **Top Retrieved Docs** | `01-governance-policy/EC-Minutes.md, 07-news-media/MCA-2020.md, 07-news-media/MBA-2020.md` | `01-governance-policy/EC-Minutes.md, 07-news-media/MCA-2020.md` |
| **Confidence Score / Level** | 0.8735 (Very High) | 0.8379 (Very High) |
| **Keyword Coverage** | 67% (`Management Quota, University`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | Yes |
| **Answer Correctness** | PASS | FAIL |

**Baseline Answer**:
> Candidates seeking admission under the Management Quota (Government or University) follow the procedures of the Post Graduate Common Entrance Examination as notified by the Government of Karnataka from time to time. For both Government and University quotas, they must appear for the entrance test conducted by the University or by recognized Entrance Examination authorities such as KEA/CMAT/MAT/CAT.  The University may conduct Counseling based on the rankings in the entrance test (if conducted) or directly admit candidates allotted by the central counseling conducted by the Examination Authorities: such as KEA/CMAT/MAT/CAT as per norms or any other as permitted from time to time. Candidates who have passed a qualifying examination not conducted by the Government of Karnataka or University shall submit the eligibility and migration certificate in original for admission to a programme of study.  Candidates who have passed the qualifying examination through correspondence course are not eligible for admission to the University. NRI/PIO/FN seeking admission to a programme must apply separately with equivalency/eligibility/migration certificates along with passport/visa/clearance/NOC from concerned bodies to the Admissions Committee. Admission is subject to the candidate being certified medically fit by a registered medical practitioner recognized by the University for the purpose.  Each applicant shall be required to submit a Character Certificate from the

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [DEP001] (Departments): "What specialization streams are offered under B.E. Computer Science and Engineering?" — ✅ UNCHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 4.185s | **4.512s** |
| **Top Retrieved Docs** | `02-academics/b-e-computer-science-and-engineering-artificial-in.md` | `02-academics/b-e-computer-science-and-engineering-artificial-in.md` |
| **Confidence Score / Level** | 0.7729 (High) | 0.7729 (High) |
| **Keyword Coverage** | 100% (`Computer Science, Engineering`) | 100% (`Computer Science, Engineering`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> The context provided does not contain information about specialization streams offered under B.E. Computer Science and Engineering at K.L.E.S College of Engineering, Hubballi.   I couldn't find verified information about that in my knowledge base.  Please refer to the official academic pages or contact the Student Affairs Office for detailed information on specialization streams.

**Optimized Answer**:
> The context provided does not contain information about specialization streams offered under B.E. Computer Science and Engineering at K.L.E.S College of Engineering, Hubballi.   I couldn't find verified information about that in my knowledge base.  Please refer to the official academic pages or contact the Student Affairs Office for detailed information on specialization streams.

---
### Question [DEP002] (Departments): "What degree programs are offered by the School of Architecture?" — ⚠️ REGRESSION

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 3.943s | **4.04s** |
| **Top Retrieved Docs** | `02-academics/programs.md, 01-governance-policy/4th_bog_minutes_97c73f.md, 07-news-media/schools_departments_9a4a9b.md` | `02-academics/programs.md` |
| **Confidence Score / Level** | 0.6 (High) | 0.5833 (High) |
| **Keyword Coverage** | 50% (`Architecture`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | Yes |
| **Answer Correctness** | PASS | FAIL |

**Baseline Answer**:
> The School of Architecture at KLE Technological University (BVB Engineering College, Hubballi) offers a Bachelor of Architecture program.

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [DEP003] (Departments): "Which department manages research inVLSI, power grids, and embedded systems?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 9.54s | **5.194s** |
| **Top Retrieved Docs** | `01-governance-policy/5th_bog_minutes_e084a8.md` | `01-governance-policy/5th_bog_minutes_e084a8.md` |
| **Confidence Score / Level** | 0.5732 (High) | 0.5732 (High) |
| **Keyword Coverage** | 0% (`None`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> Based on the information provided in Annexure - 2, there is no specific mention of any department managing research into "involsi", "power grids," or "embedded systems." The annexure lists various departments offering different programs but does not provide details about which departments manage specific areas of research.  For example: - Civil and Environmental Engineering (CV) - Electrics Engineering (EE) - Mechanical Engineering (ME) - Computer Science & Engineering (CS) - Biotechnology (BT) - Management Studies and Research (MS) - Center for Social Sciences (CSS) - Centre for Engineering Education Research (CEER) - Applied Sciences (AS) - Physics (PHY), Chemistry (CHEM), Mathematics (MATHS)  If you are looking for information on which departments handle research in these specific areas, you would need to refer to the university's official research guidelines or contact the respective department directly.

**Optimized Answer**:
> Based on the information provided in the context, there is no specific mention of any department managing research programs related to "VLSI Design & Embedded Systems." The data given focuses on admissions for various courses across different departments but does not include details about which departments manage specific research programs. Therefore, I couldn't find verified information about this in my knowledge base.  I couldn't find verified information about that in my knowledge base.

---
### Question [DEP004] (Departments): "What specialized postgraduate law program is offered in Intellectual Property Rights?" — ⚠️ REGRESSION

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.068s | **4.142s** |
| **Top Retrieved Docs** | `02-academics/llb.md, 02-academics/ba-llb.md, 07-news-media/pg-llm-ip-it-law-2024-26.md` | `02-academics/llb.md` |
| **Confidence Score / Level** | 0.5618 (High) | 0.5833 (High) |
| **Keyword Coverage** | 100% (`LLM, IPR, Intellectual Property`) | 33% (`Intellectual Property`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | FAIL |

**Baseline Answer**:
> The specialized postgraduate law program that offers a course on Intellectual Property Rights-I (IPR-I) is the **Pg-Llm-Ip-It-Law-2024-26** program. This program includes a specialization course titled "Specialisation Course - 8: Information Technology and Intellectual Property Law" in Semester IV, which covers topics related to intellectual property law.

**Optimized Answer**:
> The LL.B (Bachelor of Laws) program at KLE Technological University, Hubballi offers a specialization in Intellectual Property Rights-I as an optional course during the third year.

---
### Question [PLC001] (Placements): "What resources and assistance are provided by the Placement Cell?" — ⚠️ REGRESSION

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 8.264s | **3.505s** |
| **Top Retrieved Docs** | `07-news-media/sedg-cell.md, 07-news-media/Mandatory-Disclosure-Edited.md, 04-research-centers/placements_recruiters_79280d.md` | `07-news-media/sedg-cell.md` |
| **Confidence Score / Level** | 0.8087 (Very High) | 0.7946 (High) |
| **Keyword Coverage** | 100% (`Placement, Training, Recruiters`) | 0% (`None`) |
| **Citation Correctness** | Invalid | Valid |
| **Hallucination Flag** | No | Yes |
| **Answer Correctness** | PASS | FAIL |

**Baseline Answer**:
> The Placement Cell at KLE Technological University provides several resources and assistance to students for their career development and placements. Some of these include:  - **Soft skills training "VIKAS":** A 64-hour program over four semesters, offered by a reputed Bengaluru organization, covering modules such as Analytical Thinking, Mathematical Thinking, Creative + Lateral Thinking, Technical Thinking, Corporate Behavior, Written English, Spoken English.    - **Campus incubation:** Around 38 companies (many start-ups) operate from the campus, offering internships and real-world problem statements for student projects.  For more detailed information, you can refer to the source: [Placements and Leading Recruiters > Training and Placement Cell]().

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [PLC002] (Placements): "Which global education partner collaborates for the B.Com ACCA integrated program?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 4.589s | **4.346s** |
| **Top Retrieved Docs** | `02-academics/bachelor-of-commerce-integrated-with-acca.md, 02-academics/bachelor-of-commerce-curriculum-structure-content-2024-2027.md` | `02-academics/bachelor-of-commerce-integrated-with-acca.md` |
| **Confidence Score / Level** | 0.7926 (High) | 0.8482 (Very High) |
| **Keyword Coverage** | 50% (`ISDC`) | 50% (`ISDC`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The global education partner that collaborates with SMSR for the B.Com Hons (International Accounting & Finance) program is **ISDC** (International Skill Development Corporation).

**Optimized Answer**:
> ISDC (International Skill Development Corporation) collaborates for the B.Com Hons (International Accounting & Finance) program.

---
### Question [PLC003] (Placements): "What companies and industries hire graduates from the Biotechnology department?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.029s | **3.909s** |
| **Top Retrieved Docs** | `02-academics/b-e-biotechnology.md, 02-academics/bachelor-biotechnology-curriculum-2022-2026.md` | `02-academics/b-e-biotechnology.md` |
| **Confidence Score / Level** | 0.5705 (High) | 0.6292 (High) |
| **Keyword Coverage** | 25% (`Biotechnology`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> I couldn't find verified information about that in my knowledge base. The provided curriculum details do not include specific company names or industries that hire graduates from the B.E. Biotechnology program at KLE Technological University (BVB Engineering College), Hubballi.

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [PLC004] (Placements): "How are placement records and brochures made available to students?" — ✅ UNCHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 10.978s | **7.82s** |
| **Top Retrieved Docs** | `04-research-centers/placements_recruiters_79280d.md` | `04-research-centers/placements_recruiters_79280d.md` |
| **Confidence Score / Level** | 0.7616 (High) | 0.7616 (High) |
| **Keyword Coverage** | 100% (`Placement Brochure, Placement Records`) | 100% (`Placement Brochure, Placement Records`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The placement records and brochures at KLE Technological University, Hubballi are published in the university's own placement brochures. These brochures contain batch-wise top-recruiter tables for semiconductors/VLSI, automotive, software services, and consulting recruiters from 2022 through 2026 (ongoing).

**Optimized Answer**:
> The placement records and brochures at KLE Technological University, Hubballi are published in the university's own placement brochures. These brochures contain batch-wise top-recruiter tables for semiconductors/VLSI, automotive, software services, and consulting recruiters from 2022 through 2026 (ongoing).

---
### Question [HST001] (Hostel): "What residential facilities and accommodation options exist for on-campus students?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 7.912s | **5.228s** |
| **Top Retrieved Docs** | `07-news-media/on-campus-facilities.md, 07-news-media/AQAR-2022-23-system-generated-copy.md` | `07-news-media/on-campus-facilities.md` |
| **Confidence Score / Level** | 0.745 (High) | 0.796 (High) |
| **Keyword Coverage** | 100% (`hostel, boys, girls, dining`) | 100% (`hostel, boys, girls, dining`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> KLE Technological University provides residential facilities for on-campus students. These include separate hostels for boys and girls, equipped with amenities such as aesthetically built furniture, a dedicated cupboard, study table, attached bathrooms, and wholesome and hygienic food served in the dining hall. The hostel is supervised by full-time, dedicated hostel wardens who enforce set rules, norms, and schedules.

**Optimized Answer**:
> KLE Technological University (BVB Engineering College), Hubballi provides hostel facility for both boys and girls. The hostels are equipped with amenities such as aesthetically built and installed furniture, a dedicated cupboard, a study table, attached bathrooms, and serve wholesome and hygienic food in the dining hall. The facilities are supervised by full-time, dedicated hostel wardens who ensure adherence to set rules, norms, and schedules.

---
### Question [HST002] (Hostel): "What sports and fitness amenities are located near the student residences?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.468s | **5.384s** |
| **Top Retrieved Docs** | `07-news-media/AQAR2021-22ResubmittedAugust2023.md, 07-news-media/AQAR-2022-23-system-generated-copy.md` | `07-news-media/AQAR2021-22ResubmittedAugust2023.md` |
| **Confidence Score / Level** | 0.7345 (High) | 0.708 (High) |
| **Keyword Coverage** | 25% (`sports`) | 75% (`sports, indoor, outdoor`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> Based on the information provided in the context, there are no specific details about sports and fitness amenities that are located near the student residences. The context discusses general campus facilities but does not mention any proximity to student hostels. Therefore, I couldn't find verified information about this in my knowledge base.  I couldn't find verified information about that in my knowledge base.

**Optimized Answer**:
> The document does not provide specific information about sports and fitness amenities located near the student residences. It only mentions that the University has state-of-the-art indoor and outdoor facilities on campus to encourage students' participation in sports and cultural activities, but it does not specify their proximity to the student residences.   I couldn't find verified information about that in my knowledge base.

---
### Question [HST003] (Hostel): "What medical and health emergency services are available on campus?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 6.052s | **5.687s** |
| **Top Retrieved Docs** | `07-news-media/on-campus-facilities.md, 07-news-media/AQAR2021-22ResubmittedAugust2023.md` | `07-news-media/on-campus-facilities.md` |
| **Confidence Score / Level** | 0.6746 (High) | 0.7259 (High) |
| **Keyword Coverage** | 100% (`medical, health, center`) | 67% (`medical, health`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The Medical Health Center at KLE Technological University, Hubballi provides round-the-clock availability for healthcare services. It includes a team of qualified and experienced doctors to ensure the best on-campus healthcare. For any eventuality, the center has primary healthcare infrastructure such as stretchers, wheelchairs, and other critical equipment. Additionally, there is a provision for an ambulance in case of emergencies. The university also has signed MOUs with reputed medical establishments to facilitate healthcare facilities to students and others with equal gravity and concern.

**Optimized Answer**:
> The Medical Health Centre at KLE Tech University provides round-the-clock availability of qualified and experienced doctors within the campus. For any eventuality, the centre has primary healthcare infrastructure including stretchers, wheelchairs, and other critical equipment. In case of an emergency, there is also a provision for an ambulance to be available.

---
### Question [HST004] (Hostel): "What food and dining options exist in campus cafeterias?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.353s | **3.973s** |
| **Top Retrieved Docs** | `07-news-media/on-campus-facilities.md, 07-news-media/AQAR2021-22ResubmittedAugust2023.md` | `07-news-media/on-campus-facilities.md` |
| **Confidence Score / Level** | 0.5256 (Medium) | 0.5762 (High) |
| **Keyword Coverage** | 75% (`Food, Cafeteria, canteen`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> The context provided does not specify detailed information about the food and dining options in campus cafeterias. Based on the available information, there are two canteens on campus that offer a wide range of food choices for students and staff.  I couldn't find verified information about that in my knowledge base.

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [ACA001] (Academics): "What research facilities and specialized labs are established across disciplines?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.759s | **5.653s** |
| **Top Retrieved Docs** | `02-academics/academic-facilities.md, 07-news-media/AQAR-2022-23-system-generated-copy.md, 07-news-media/on-campus-facilities-dup.md` | `02-academics/academic-facilities.md` |
| **Confidence Score / Level** | 0.8129 (Very High) | 0.8323 (Very High) |
| **Keyword Coverage** | 100% (`computation, testing, materials`) | 100% (`computation, testing, materials`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> KLE Technological University (BVB Engineering College), Hubballi, has established various research laboratories to support high-quality research across different streams and disciplines. Some of these top research facilities include:  - Advanced computation - Advanced project development - Modern labs for fire testing - Composite testing - Advanced construction materials  These specialized labs are designed to provide students with opportunities to apply their knowledge in specific fields of study.

**Optimized Answer**:
> KLE Tech University has established various research laboratories to produce high-quality research across different streams and disciplines. Some of the top research facilities include:  - Advanced computation - Advanced project development - Modern labs for fire testing - Composite testing - Advanced construction materials  These specialized labs are designed to support students in their academic pursuits by providing them with opportunities to apply theoretical knowledge through practical sessions.

---
### Question [ACA002] (Academics): "What is the duration and structure of the Ph.D. doctoral program regulations?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 9.168s | **8.183s** |
| **Top Retrieved Docs** | `02-academics/PhD-regulations-KLE-tech-july-2025.md, 02-academics/PhD-Regulations.md, 07-news-media/MCA-2020.md` | `02-academics/PhD-regulations-KLE-tech-july-2025.md` |
| **Confidence Score / Level** | 0.7175 (High) | 0.7379 (High) |
| **Keyword Coverage** | 100% (`Ph.D, regulations`) | 100% (`Ph.D, regulations`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The Ph.D. doctoral program at KLE Technological University (BVB Engineering College), Hubballi, has specific regulations regarding its duration and structure as outlined in the PhD Regulations document.  ### Duration: - **Full-Time Program**: The full-time Ph.D. Programme shall be for a minimum duration of three (3) years, including course work, with a maximum duration of six (6) years from the date of registration to the Ph.D. programme.   - Additionally, up to two (2) extra years can be given, but the total period should not exceed eight (8) years from the date of admission in the Ph.D. programme. - **Part-Time Program**: The part-time Ph.D. Programme shall be for a minimum duration of four (4) years, including course work, with a maximum duration of seven (7) years from the date of registration to the Ph.D. programme.   - Additionally, up to two (2) extra years can be given, but the total period should not exceed nine (9) years from the date of admission in the Ph.D. programme.  ### Structure: - **Full-Time Program**: The structure includes different semesters and a fast track (Summer) semester within each academic year.   - Each

**Optimized Answer**:
> The PhD Programme at KLE Technological University, Hubballi, has different structures for Full Time and Part Time students as per the PhD Regulations effective July 2025:  **Full Time Structure:** - Minimum Duration: 3 years (including course work) - Maximum Duration: 6 years from the date of registration to the Ph.D. programme. - Additional Extension: Up to an additional 2 years are allowed, but the total duration should not exceed 8 years from the date of admission.  **Part Time Structure:** - Minimum Duration: 4 years (including course work) - Maximum Duration: 7 years from the date of registration to the Ph.D. programme. - Additional Extension: Up to an additional 2 years are allowed, but the total duration should not exceed 9 years from the date of admission.  Additionally, female PhD scholars and Persons with Disabilities (having more than 40% disability) may be provided with further extensions as specified in the regulations.

---
### Question [ACA003] (Academics): "How are continuous internal evaluations (CIE) conducted for undergraduate courses?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 9.112s | **6.522s** |
| **Top Retrieved Docs** | `02-academics/Computer-Science-Curriculum-Structure-Content-2021-25.md, 07-news-media/AQAR-2022-23-system-generated-copy.md` | `02-academics/Computer-Science-Curriculum-Structure-Content-2021-25.md` |
| **Confidence Score / Level** | 0.5585 (High) | 0.6155 (High) |
| **Keyword Coverage** | 50% (`evaluations`) | 50% (`evaluations`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> Continuous Internal Evaluations (CIE) for undergraduate courses at KLE Technological University, Hubballi, involve the following steps based on the provided curriculum structure:  1. **Literature Survey, Problem Analysis and Problem Formulation**: This review assesses students' understanding of literature related to their project topic, their ability to analyze problems, and their formulation of objectives.  2. **Requirements, Design, design principles adopted in modules/components and Algorithms**: In this review, the focus is on how well students have understood system requirements, designed components/modules, and applied relevant design principles and algorithms.  3. **Implementation and Testing**: This final review evaluates the implementation of the project and its testing phase to ensure it meets all specified criteria and functions as intended.  Each of these reviews contributes marks towards the overall assessment for the course CIPE (Course Title: Computer Science Engineering).

**Optimized Answer**:
> The Continuous Internal Evaluations (CIE) for the undergraduate course CIPE (Course Code: 15EHSA401) involve three reviews:  - **Review-1**: Literature Survey, Problem Analysis and Problem Formulation. - **Review-2**: Requirements, Design, design principles adopted in modules/components and Algorithms. - **Review-3**: Implementation and Testing.  Each review is conducted internally within the course structure.

---
### Question [ACA004] (Academics): "What undergraduate degree is offered in Hotel Management and Catering Technology?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.035s | **6.614s** |
| **Top Retrieved Docs** | `02-academics/bsc-in-hotel-management-and-catering-technology-bs.md, 02-academics/programs.md` | `02-academics/bsc-in-hotel-management-and-catering-technology-bs.md` |
| **Confidence Score / Level** | 0.8153 (Very High) | 0.8674 (Very High) |
| **Keyword Coverage** | 100% (`Hotel Management, B.Sc`) | 100% (`Hotel Management, B.Sc`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The undergraduate degree offered in Hotel Management and Catering Technology (B.Sc. HMCT) at KLE Technological University, BVB Engineering College, Hubballi is a Bachelor of Science (B.Sc.).

**Optimized Answer**:
> B.Sc. in Hotel Management and Catering Technology (B.Sc. HMCT) is an undergraduate degree offered at KLE Technological University, BVB Engineering College, Hubballi.

---
### Question [ACA005] (Academics): "What undergraduate program is offered in Computer Applications?" — ✅ UNCHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 4.471s | **4.661s** |
| **Top Retrieved Docs** | `07-news-media/computer_application_ae534b.md, 02-academics/programs.md` | `07-news-media/computer_application_ae534b.md, 02-academics/programs.md` |
| **Confidence Score / Level** | 0.7062 (High) | 0.7062 (High) |
| **Keyword Coverage** | 100% (`BCA, Computer Applications`) | 100% (`BCA, Computer Applications`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> Undergraduate Program of Computer Applications (Bachelor of Computer Applications, BCA) is offered at KLE Technological University (BVB Engineering College), Hubballi.

**Optimized Answer**:
> Undergraduate Program of Computer Applications (Bachelor of Computer Applications, BCA) is offered at KLE Technological University (BVB Engineering College), Hubballi.

---
### Question [REG001] (Library): "Where is the library located in campus?" — ⚠️ REGRESSION

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.136s | **5.058s** |
| **Top Retrieved Docs** | `07-news-media/overview.md, facilities/campus_guide_canonical.md, 07-news-media/AQAR-2022-23-system-generated-copy.md` | `07-news-media/overview.md` |
| **Confidence Score / Level** | 0.758 (High) | 0.7806 (High) |
| **Keyword Coverage** | 100% (`Administrative Block, Ground Floor`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | Yes |
| **Answer Correctness** | PASS | FAIL |

**Baseline Answer**:
> The Central Library is located in the Administrative Block, Ground Floor (Block C, 2nd Floor).

**Optimized Answer**:
> The Central Library is located within the Campus. However, specific building details are not provided in the given context.

---
### Question [REG002] (Library): "When is the library open?" — ✅ UNCHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 4.836s | **4.262s** |
| **Top Retrieved Docs** | `facilities/campus_guide_canonical.md` | `facilities/campus_guide_canonical.md` |
| **Confidence Score / Level** | 0.777 (High) | 0.777 (High) |
| **Keyword Coverage** | 100% (`8:00 AM, 8:00 PM`) | 100% (`8:00 AM, 8:00 PM`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The Central Library is open Monday through Saturday from 8:00 AM to 8:00 PM. It is closed on Sundays and public holidays.

**Optimized Answer**:
> The Central Library is open Monday through Saturday from 8:00 AM to 8:00 PM. It is closed on Sundays and public holidays.

---
### Question [REG003] (Library): "What are the library hours on weekends?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 9.021s | **7.042s** |
| **Top Retrieved Docs** | `facilities/campus_guide_canonical.md, 07-news-media/6Sem-BE-B.Arch-BBA2-4-Sem--BCA2sem-June-2023.md, 07-news-media/overview.md` | `facilities/campus_guide_canonical.md, 07-news-media/6Sem-BE-B.Arch-BBA2-4-Sem--BCA2sem-June-2023.md` |
| **Confidence Score / Level** | 0.7745 (High) | 0.7388 (High) |
| **Keyword Coverage** | 50% (`Saturday`) | 100% (`Saturday, 8:00 AM`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> Based on the information provided in the overview document for KLE Technological University's Central Library, there is no specific mention of library hours during weekends. The document focuses mainly on the types of resources available (books, e-books, journals), subscriptions to databases and journals, digital infrastructure, and services offered.  For precise weekend opening hours, you would need to refer directly to the current library schedule or contact the library administration for updated information. Libraries often have different operating hours during weekends compared to weekdays, especially if they are closed on Saturdays and Sundays.

**Optimized Answer**:
> The Central Library is open Monday through Saturday, from 8:00 AM to 8:00 PM. It is closed on Sundays and public holidays. Therefore, the library does not have specific weekend hours as it operates during weekdays only according to the provided information.

---
### Question [REG004] (Library): "What is the email address for the library?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 5.223s | **3.815s** |
| **Top Retrieved Docs** | `facilities/campus_guide_canonical.md, 07-news-media/overview.md, 07-news-media/facilities.md` | `facilities/campus_guide_canonical.md` |
| **Confidence Score / Level** | 0.5791 (High) | 0.6018 (High) |
| **Keyword Coverage** | 33% (`couldn't find`) | 33% (`couldn't find`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> I couldn't find verified information about that in my knowledge base.

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [REG005] (Library): "What is the library phone number?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 4.48s | **3.248s** |
| **Top Retrieved Docs** | `facilities/campus_guide_canonical.md, 07-news-media/Mandatory-Disclosure-Edited.md` | `facilities/campus_guide_canonical.md` |
| **Confidence Score / Level** | 0.6338 (High) | 0.6917 (High) |
| **Keyword Coverage** | 0% (`None`) | 33% (`couldn't find`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> The library phone number is +91-836-2378105 / 2378106.

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [REG006] (Admissions): "Where is the admissions office located?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 3.402s | **2.961s** |
| **Top Retrieved Docs** | `facilities/campus_guide_canonical.md, 03-admissions-fees/admission-for-ug-program.md, 03-admissions-fees/admission-for-pg-program.md` | `facilities/campus_guide_canonical.md, 03-admissions-fees/admission-for-ug-program.md` |
| **Confidence Score / Level** | 0.7944 (High) | 0.7589 (High) |
| **Keyword Coverage** | 100% (`Administrative Block, A-101`) | 100% (`Administrative Block, A-101`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> The Admissions Office is located in the Administrative Block, Room A-101.

**Optimized Answer**:
> The Student Admissions & Registration Office is located in the Administrative Block, Room A-101.

---
### Question [REG007] (Admissions): "What are the admissions office hours?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 2.842s | **3.12s** |
| **Top Retrieved Docs** | `03-admissions-fees/post-graduate-program.md, 03-admissions-fees/under-graduate-program.md, 03-admissions-fees/admission-for-ug-program.md` | `03-admissions-fees/post-graduate-program.md` |
| **Confidence Score / Level** | 0.5511 (High) | 0.555 (High) |
| **Keyword Coverage** | 0% (`None`) | 0% (`None`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> I couldn't find verified information about that in my knowledge base.

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---
### Question [REG008] (Admissions): "What is the admissions office phone number?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 3.494s | **4.286s** |
| **Top Retrieved Docs** | `07-news-media/contact.md, 03-admissions-fees/under-graduate-program.md, 03-admissions-fees/post-graduate-program.md` | `07-news-media/contact.md` |
| **Confidence Score / Level** | 0.6063 (High) | 0.6264 (High) |
| **Keyword Coverage** | 33% (`2378103`) | 33% (`2378103`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | Yes | Yes |
| **Answer Correctness** | FAIL | FAIL |

**Baseline Answer**:
> The admissions office phone number is +91-836-2378103.

**Optimized Answer**:
> The admissions office phone numbers for KLE Technological University, B. V. Bhoomaraddi Campus are +91-836-2378103 /105 /106, operating from 11:00 am to 5:30 pm.

---
### Question [REG009] (Admissions): "How can I get admitted?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 8.145s | **4.744s** |
| **Top Retrieved Docs** | `07-news-media/MBA-2020.md, 03-admissions-fees/intenational-admission-dup.md, 03-admissions-fees/post-graduate-program.md` | `07-news-media/MBA-2020.md` |
| **Confidence Score / Level** | 0.5507 (High) | 0.5712 (High) |
| **Keyword Coverage** | 67% (`Entrance, KEA`) | 67% (`Entrance, KEA`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> To get admitted to the Post Graduate programs at KLE Technological University (BVB Engineering College), Hubballi, you need to follow these steps based on your quota:  ### Government Quota: - Follow the procedures of the Post Graduate Common Entrance Examination as notified by the Government of Karnataka from time to time.  ### University Quota: - Candidates seeking admission under this quota should appear for the entrance test conducted by the University or recognized authorities such as KEA/CMAT/MAT/CAT. - The University may conduct Counseling based on the rankings in the entrance test (if conducted) or directly admit candidates allotted by the central counseling conducted by the Examination Authorities: such as KEA/CMAT/MAT/CAT, as per norms or any other as permitted from time to date.  ### Additional Requirements: 1. **Eligibility and Migration Certificate**: If you have passed a qualifying examination not conducted by the Government of Karnataka or University, submit this certificate in original for admission. 2. **NRI/PIO/FN Eligibility**: NRI/PIO/FN candidates seeking admission should apply separately with eligibility/migration certificates along with passport/visa/clearance/NOC from concerned bodies to the Admissions Committee.  ### Medical Fitness: - Each applicant must be certified medically

**Optimized Answer**:
> To get admitted under the University Quota at Mba-2020, a candidate must appear for the entrance test conducted by the University or recognized authorities such as KEA (Karnataka Examination Authority), CMAT (Common Management Admission Test), MAT (Management Aptitude Test), or CAT (Catapult). The University may conduct counseling based on the rankings in these entrance tests or directly admit candidates allotted by the central counseling conducted by these authorities, following any norms or permissions permitted from time to time.

---
### Question [REG010] (Hostel): "What is the cafeteria's phone number?" — 🔄 CHANGED

| Dimension | Baseline (`top_k=50`, `window=25`, `tokens=512`) | Optimized (`top_k=5`, `window=10`, `tokens=256`) |
|---|---|---|
| **Latency** | 3.564s | **3.08s** |
| **Top Retrieved Docs** | `07-news-media/AQAR-2022-23-system-generated-copy.md, 07-news-media/contact.md` | `07-news-media/AQAR-2022-23-system-generated-copy.md` |
| **Confidence Score / Level** | 0.4936 (Medium) | 0.5519 (High) |
| **Keyword Coverage** | 33% (`couldn't find`) | 33% (`couldn't find`) |
| **Citation Correctness** | Valid | Valid |
| **Hallucination Flag** | No | No |
| **Answer Correctness** | PASS | PASS |

**Baseline Answer**:
> I couldn't find verified information about that in my knowledge base.

**Optimized Answer**:
> I couldn't find verified information about that in my knowledge base.

---