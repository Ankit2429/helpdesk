# RAG Retrieval & Benchmark Evaluation Report

- **Timestamp**: `2026-07-29T10:48:23Z`
- **Total Queries Evaluated**: `1014`
- **Retrieval Cut-off (K)**: `5`
- **Overall Pass Rate**: `0.30%`

## Executive Summary Metrics

| Metric | Score | Description |
| :--- | :---: | :--- |
| **Precision@5** | `0.0000` | Relevant documents in top-K |
| **Recall@5** | `0.0000` | Target documents retrieved |
| **MRR** | `0.0000` | Mean Reciprocal Rank |
| **Hit Rate@5** | `0.0000` | Queries with >= 1 relevant doc in top-K |
| **NDCG@5** | `0.0000` | Ranking relevance discount score |
| **Exact Match** | `0.0000` | String exact equality ratio |
| **Token F1** | `0.0909` | Token overlap harmonic mean |
| **Mean Latency** | `0.01 ms` | Average evaluation latency |

## Category Breakdown

| Category | Queries | Pass Rate | P@K | R@K | MRR | Hit Rate | NDCG@K | Token F1 | Avg Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Admission** | 5 | 0.0% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.072 | 0.0 ms |
| **Departments** | 843 | 0.4% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.089 | 0.0 ms |
| **Facilities** | 45 | 0.0% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.089 | 0.0 ms |
| **Faculty** | 76 | 0.0% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.129 | 0.0 ms |
| **Fees** | 5 | 0.0% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0 ms |
| **Misc** | 6 | 0.0% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0 ms |
| **Navigation** | 29 | 0.0% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.100 | 0.0 ms |
| **Placement** | 5 | 0.0% | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.005 | 0.0 ms |

## Detailed Item Results

| ID | Category | Question | Hit Rate | Token F1 | Status | Latency |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| 1 | Admission | How do I get admission here? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 2 | Admission | Where is the admission office? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 3 | Admission | Which documents should I bring for ad... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 4 | Admission | Can I get admission through KCET? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 5 | Admission | What is the admission process? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 1 | Departments | Where is the University Achievements ... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 2 | Departments | Does this college have a department f... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 3 | Departments | Can I meet a faculty member from Abou... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 4 | Departments | What courses are offered in Subjects ... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 5 | Departments | Where is the Industry Supported Labs ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 6 | Departments | Can I meet a faculty member from Our ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 7 | Departments | Which block is Programs Offered in? | 0.00 | 0.13 | FAILED | 0.0 ms |
| 8 | Departments | Can I meet a faculty member from Bran... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 9 | Departments | Does this college have a department f... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 10 | Departments | Where is the Branches Offered departm... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 11 | Departments | Does this college have a department f... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 12 | Departments | Which block is University Achievement... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 13 | Departments | What courses are offered in Universit... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 14 | Departments | Which block is Our leading Alumni in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 15 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 16 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 17 | Departments | Which block is Companies Provide in? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 18 | Departments | What courses are offered in Our leadi... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 19 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 20 | Departments | Which block is Unique Initiatives in? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 21 | Departments | What courses are offered in Unique In... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 22 | Departments | Does this college have a department f... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 23 | Departments | Can I meet a faculty member from Indu... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 24 | Departments | Which block is THANK YOU in? | 0.00 | 0.13 | FAILED | 0.0 ms |
| 25 | Departments | Can I meet a faculty member from Comp... | 0.00 | 0.28 | FAILED | 0.0 ms |
| 26 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 27 | Departments | What courses are offered in Industry ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 28 | Departments | Which block is SoftskillsT raining to... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 29 | Departments | Which block is Our Recruiters in? | 0.00 | 0.03 | FAILED | 0.0 ms |
| 30 | Departments | Can I meet a faculty member from Subj... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 31 | Departments | Does this college have a department f... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 32 | Departments | Where is the Certifications department? | 0.00 | 0.11 | FAILED | 0.0 ms |
| 33 | Departments | Which block is University Achievement... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 34 | Departments | Where is the Companies Provide depart... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 35 | Departments | Which block is By Air in? | 0.00 | 0.11 | FAILED | 0.0 ms |
| 36 | Departments | What courses are offered in By Air? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 37 | Departments | Does this college have a department f... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 38 | Departments | Does this college have a department f... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 39 | Departments | What courses are offered in Mission? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 40 | Departments | Which block is Mission in? | 0.00 | 0.06 | FAILED | 0.0 ms |
| 41 | Departments | Where is the By Air department? | 0.00 | 0.21 | FAILED | 0.0 ms |
| 42 | Departments | What courses are offered in Accredita... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 43 | Departments | Where is the Accreditation Status dep... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 44 | Departments | Which block is Accreditation Status in? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 45 | Departments | Can I meet a faculty member from Accr... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 46 | Departments | Does this college have a department f... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 47 | Departments | What courses are offered in Dear Stud... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 48 | Departments | Where is the Dear Students department? | 0.00 | 0.09 | FAILED | 0.0 ms |
| 49 | Departments | Which block is Dear Students in? | 0.00 | 0.17 | FAILED | 0.0 ms |
| 50 | Departments | Can I meet a faculty member from Dear... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 51 | Departments | Does this college have a department f... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 52 | Departments | Can I meet a faculty member from 13 000? | 0.00 | 0.04 | FAILED | 0.0 ms |
| 53 | Departments | Which block is 13 000 in? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 54 | Departments | Where is the 1 38 000 department? | 0.00 | 0.11 | FAILED | 0.0 ms |
| 55 | Departments | What courses are offered in 1 38 000? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 56 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 57 | Departments | What courses are offered in Inspiring... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 58 | Departments | Where is the Inspiring excellence nur... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 59 | Departments | Which block is Inspiring excellence n... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 60 | Departments | Can I meet a faculty member from Insp... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 61 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 62 | Departments | What courses are offered in Dr N H Ay... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 63 | Departments | Which block is Dr Prabhakar B Kore in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 64 | Departments | Which block is Dr Basavaraj S Anami in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 65 | Departments | Which block is Dr Prakash G Tewari in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 66 | Departments | What courses are offered in Dr Prakas... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 67 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 68 | Departments | Can I meet a faculty member from Dr P... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 69 | Departments | Where is the Dr Prabhakar B Kore depa... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 70 | Departments | Can I meet a faculty member from Dr N... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 71 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 72 | Departments | What courses are offered in Dr Prabha... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 73 | Departments | Which block is Prof B L Desai in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 74 | Departments | Which block is Dr Sudha N Murty in? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 75 | Departments | What courses are offered in Dr Basava... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 76 | Departments | Can I meet a faculty member from Dr A... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 77 | Departments | Can I meet a faculty member from Dr B... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 78 | Departments | Which block is Dr Madhusudan V Atre in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 79 | Departments | Does this college have a department f... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 80 | Departments | Where is the 2000 department? | 0.00 | 0.09 | FAILED | 0.1 ms |
| 81 | Departments | Can I meet a faculty member from KLE ... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 82 | Departments | Which block is Research and innovatio... | 0.00 | 0.27 | FAILED | 0.0 ms |
| 83 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 84 | Departments | Where is the The University is one of... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 85 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 86 | Departments | What courses are offered in Mr Muruge... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 87 | Departments | Which block is KLE Technological Univ... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 88 | Departments | Does this college have a department f... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 89 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 90 | Departments | Which block is Dr Sudha Murty in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 91 | Departments | What courses are offered in KLE Techn... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 92 | Departments | Can I meet a faculty member from Mr P... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 93 | Departments | What courses are offered in Research ... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 94 | Departments | Where is the Research Policy department? | 0.00 | 0.20 | FAILED | 0.0 ms |
| 95 | Departments | Which block is Research Policy in? | 0.00 | 0.20 | FAILED | 0.0 ms |
| 96 | Departments | Can I meet a faculty member from Rese... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 97 | Departments | Does this college have a department f... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 98 | Departments | What courses are offered in Undergrad... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 99 | Departments | Where is the Undergraduate department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 100 | Departments | Which block is Undergraduate in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 101 | Departments | Can I meet a faculty member from Unde... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 102 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 103 | Departments | What courses are offered in Research? | 0.00 | 0.13 | FAILED | 0.0 ms |
| 104 | Departments | Where is the Research department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 105 | Departments | Which block is Research in? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 106 | Departments | Can I meet a faculty member from Rese... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 107 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 108 | Departments | What courses are offered in Copy to? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 109 | Departments | Where is the KARNATAKA STATE LAW UNIV... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 110 | Departments | What courses are offered in KARNATAKA... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 111 | Departments | Where is the Copy to department? | 0.00 | 0.13 | FAILED | 0.0 ms |
| 112 | Departments | Does this college have a department f... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 113 | Departments | Can I meet a faculty member from KARN... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 114 | Departments | Which block is KARNATAKA STATE LAW UN... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 115 | Departments | What courses are offered in the depar... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 116 | Departments | Where is the the department department? | 0.00 | 0.02 | FAILED | 0.0 ms |
| 117 | Departments | Which block is the department in? | 0.00 | 0.02 | FAILED | 0.0 ms |
| 118 | Departments | Can I meet a faculty member from the ... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 119 | Departments | Does this college have a department f... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 120 | Departments | What courses are offered in Classrooms? | 0.00 | 0.06 | FAILED | 0.0 ms |
| 121 | Departments | Where is the Classrooms department? | 0.00 | 0.06 | FAILED | 0.0 ms |
| 122 | Departments | Which block is Classrooms in? | 0.00 | 0.06 | FAILED | 0.0 ms |
| 123 | Departments | Can I meet a faculty member from Clas... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 124 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 125 | Departments | What courses are offered in Testimoni... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 126 | Departments | Can I meet a faculty member from Test... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 127 | Departments | Can I meet a faculty member from Toda... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 128 | Departments | Which block is Today we are on the cu... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 129 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 130 | Departments | Which block is Fee Structure in? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 131 | Departments | Can I meet a faculty member from Fee ... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 132 | Departments | Can I meet a faculty member from Elig... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 133 | Departments | Where is the Fee Structure department? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 134 | Departments | Where is the Testimonials department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 135 | Departments | Does this college have a department f... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 136 | Departments | Which block is Engineering Biology fo... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 137 | Departments | Which block is Eligibility Criteria in? | 0.00 | 0.06 | FAILED | 0.0 ms |
| 138 | Departments | What courses are offered in Eligibili... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 139 | Departments | Can I meet a faculty member from Cour... | 0.00 | 0.01 | FAILED | 0.0 ms |
| 140 | Departments | Where is the Engineering Biology for ... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 141 | Departments | Does this college have a department f... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 142 | Departments | Can I meet a faculty member from Chem... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 143 | Departments | Which block is Powering the Digital F... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 144 | Departments | Where is the Powering the Digital Fut... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 145 | Departments | Can I meet a faculty member from From... | 0.00 | 0.34 | FAILED | 0.0 ms |
| 146 | Departments | Which block is From the billions of t... | 0.00 | 0.36 | FAILED | 0.0 ms |
| 147 | Departments | Does this college have a department f... | 0.00 | 0.34 | FAILED | 0.0 ms |
| 148 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 149 | Departments | Which block is The Bachelor of Commer... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 150 | Departments | Does this college have a department f... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 151 | Departments | Which block is SMSR has been successf... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 152 | Departments | Can I meet a faculty member from Inte... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 153 | Departments | Where is the SMSR has been successful... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 154 | Departments | Which block is The core of the bachel... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 155 | Departments | Which block is Software Engineering in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 156 | Departments | What courses are offered in Software ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 157 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 158 | Departments | Which block is Testimonials in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 159 | Departments | Where is the Software Engineering dep... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 160 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 161 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 162 | Departments | Which block is The minimum duration o... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 163 | Departments | Where is the Eligibility Criteria dep... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 164 | Departments | What courses are offered in The minim... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 165 | Departments | Where is the The minimum duration of ... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 166 | Departments | Can I meet a faculty member from This... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 167 | Departments | Which block is This program enables l... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 168 | Departments | Does this college have a department f... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 169 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 170 | Departments | Which block is The Bachelor of Busine... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 171 | Departments | Does this college have a department f... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 172 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 173 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 174 | Departments | Which block is B Sc in Hotel Manageme... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 175 | Departments | Which block is Career Scope & Opportu... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 176 | Departments | What courses are offered in Career Sc... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 177 | Departments | Can I meet a faculty member from Elig... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 178 | Departments | Where is the Eligibility & Admissions... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 179 | Departments | Can I meet a faculty member from Care... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 180 | Departments | Can I meet a faculty member from Core... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 181 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 182 | Departments | What courses are offered in Academic ... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 183 | Departments | Can I meet a faculty member from Acad... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 184 | Departments | Does this college have a department f... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 185 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 186 | Departments | Which block is MBA Fees Structure for... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 187 | Departments | What courses are offered in If you ar... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 188 | Departments | Which block is If you are an Internat... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 189 | Departments | What courses are offered in Miss? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 190 | Departments | Can I meet a faculty member from Miss? | 0.00 | 0.00 | FAILED | 0.1 ms |
| 191 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 192 | Departments | Which block is MISS in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 193 | Departments | Where is the MISS department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 194 | Departments | Which block is Admission Process For ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 195 | Departments | Which block is Syllabus in? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 196 | Departments | What courses are offered in Syllabus? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 197 | Departments | Does this college have a department f... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 198 | Departments | Can I meet a faculty member from Admi... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 199 | Departments | Where is the Admission Process For LL... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 200 | Departments | What courses are offered in Admission... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 201 | Departments | Where is the Syllabus department? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 202 | Departments | Does this college have a department f... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 203 | Departments | What courses are offered in Duration ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 204 | Departments | Which block is The main focus of the ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 205 | Departments | Which block is Student Institution an... | 0.00 | 0.38 | FAILED | 0.0 ms |
| 206 | Departments | What courses are offered in Student I... | 0.00 | 0.33 | FAILED | 0.0 ms |
| 207 | Departments | Does this college have a department f... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 208 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 209 | Departments | Does this college have a department f... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 210 | Departments | What courses are offered in The main ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 211 | Departments | Which block is Mission of the Departm... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 212 | Departments | Which block is Details of Electives o... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 213 | Departments | Can I meet a faculty member from Expe... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 214 | Departments | What courses are offered in Expectati... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 215 | Departments | Which block is Theme Visual Intellige... | 0.00 | 0.00 | FAILED | 0.1 ms |
| 216 | Departments | Which block is MS Engg by Research Pr... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 217 | Departments | What courses are offered in MS Engg b... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 218 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 219 | Departments | Can I meet a faculty member from Them... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 220 | Departments | Where is the Theme Visual Intelligenc... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 221 | Departments | Can I meet a faculty member from Expe... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 222 | Departments | Does this college have a department f... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 223 | Departments | What courses are offered in Theme Vis... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 224 | Departments | Which block is Research focus areas in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 225 | Departments | Which block is Massive Open Online Co... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 226 | Departments | Can I meet a faculty member from Cons... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 227 | Departments | Which block is CALL FOR MS Engg by Re... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 228 | Departments | What courses are offered in The Postg... | 0.00 | 0.12 | FAILED | 1.0 ms |
| 229 | Departments | What courses are offered in The Postg... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 230 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 231 | Departments | Which block is The Department of Civi... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 232 | Departments | Which block is PROFESSIONAL in? | 0.00 | 0.18 | FAILED | 0.0 ms |
| 233 | Departments | Where is the PROFESSIONAL department? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 234 | Departments | What courses are offered in Research ... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 235 | Departments | Where is the Research Programs Shapin... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 236 | Departments | Which block is Research Programs Shap... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 237 | Departments | Can I meet a faculty member from Rese... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 238 | Departments | Does this college have a department f... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 239 | Departments | What courses are offered in Departmen... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 240 | Departments | Can I meet a faculty member from Depa... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 241 | Departments | Does this college have a department f... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 242 | Departments | Can I meet a faculty member from Scho... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 243 | Departments | Which block is School of Advanced Stu... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 244 | Departments | Can I meet a faculty member from PhD ... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 245 | Departments | Does this college have a department f... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 246 | Departments | Where is the PhD Scholars Electrical ... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 247 | Departments | What courses are offered in PhD Schol... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 248 | Departments | What courses are offered in School of... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 249 | Departments | Where is the School of Advanced Studi... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 250 | Departments | What courses are offered in School of... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 251 | Departments | Can I meet a faculty member from Scho... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 252 | Departments | Does this college have a department f... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 253 | Departments | Can I meet a faculty member from Depa... | 0.00 | 0.33 | FAILED | 0.0 ms |
| 254 | Departments | Where is the Department of Mathematic... | 0.00 | 0.35 | FAILED | 0.0 ms |
| 255 | Departments | Can I meet a faculty member from Scho... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 256 | Departments | Which block is School of Advanced Stu... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 257 | Departments | Can I meet a faculty member from PhD ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 258 | Departments | Does this college have a department f... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 259 | Departments | Where is the PhD Scholars Physics dep... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 260 | Departments | What courses are offered in PhD Schol... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 261 | Departments | What courses are offered in School of... | 0.00 | 0.23 | FAILED | 0.0 ms |
| 262 | Departments | Where is the School of Advanced Studi... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 263 | Departments | Can I meet a faculty member from Scho... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 264 | Departments | Which block is School of Civil Engine... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 265 | Departments | Can I meet a faculty member from Ph D... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 266 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 267 | Departments | Where is the Ph D Scholars Civil Engi... | 0.00 | 0.11 | FAILED | 0.1 ms |
| 268 | Departments | What courses are offered in Ph D Scho... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 269 | Departments | What courses are offered in School of... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 270 | Departments | What courses are offered in School of... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 271 | Departments | Can I meet a faculty member from Scho... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 272 | Departments | Does this college have a department f... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 273 | Departments | Can I meet a faculty member from Scho... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 274 | Departments | Which block is School of Mechanical E... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 275 | Departments | Which block is Current Ph D Scholars ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 276 | Departments | Can I meet a faculty member from Curr... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 277 | Departments | Can I meet a faculty member from Mech... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 278 | Departments | Where is the Current Ph D Scholars Me... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 279 | Departments | Does this college have a department f... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 280 | Departments | What courses are offered in Browse by... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 281 | Departments | Where is the Browse by Faculties depa... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 282 | Departments | Which block is Browse by Faculties in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 283 | Departments | Can I meet a faculty member from Brow... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 284 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 285 | Departments | What courses are offered in Departmen... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 286 | Departments | Where is the Department of Fashion De... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 287 | Departments | Which block is Department of Fashion ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 288 | Departments | Can I meet a faculty member from Depa... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 289 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 290 | Departments | Does this college have a department f... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 291 | Departments | Where is the Our Recruiters department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 292 | Departments | Can I meet a faculty member from Plac... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 293 | Departments | Which block is Where Culture Meets Cr... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 294 | Departments | Can I meet a faculty member from The ... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 295 | Departments | Where is the The Future of Innovative... | 0.00 | 0.28 | FAILED | 0.0 ms |
| 296 | Departments | Does this college have a department f... | 0.00 | 0.26 | FAILED | 0.0 ms |
| 297 | Departments | Which block is Media Coverage in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 298 | Departments | Can I meet a faculty member from Medi... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 299 | Departments | Which block is The Future of Innovati... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 300 | Departments | What courses are offered in Entrepren... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 301 | Departments | Which block is Overview in? | 0.00 | 0.09 | FAILED | 0.0 ms |
| 302 | Departments | Which block is Undergraduate Seat Dis... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 303 | Departments | What courses are offered in Undergrad... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 304 | Departments | Does this college have a department f... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 305 | Departments | Can I meet a faculty member from Over... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 306 | Departments | Where is the Overview department? | 0.00 | 0.09 | FAILED | 0.0 ms |
| 307 | Departments | What courses are offered in Overview? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 308 | Departments | Where is the Undergraduate Seat Distr... | 0.00 | 0.30 | FAILED | 0.0 ms |
| 309 | Departments | Does this college have a department f... | 0.00 | 0.27 | FAILED | 0.0 ms |
| 310 | Departments | What courses are offered in Admission... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 311 | Departments | Which block is Admission Procedure M ... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 312 | Departments | What courses are offered in Admission... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 313 | Departments | Does this college have a department f... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 314 | Departments | Which block is Intake M Tech Programs... | 0.00 | 0.32 | FAILED | 0.0 ms |
| 315 | Departments | Where is the Admission Procedure M Te... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 316 | Departments | Does this college have a department f... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 317 | Departments | Does this college have a department f... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 318 | Departments | Where is the Other PG Intake department? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 319 | Departments | What courses are offered in Admission... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 320 | Departments | Which block is Bachelor of Engineerin... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 321 | Departments | What courses are offered in Bachelor ... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 322 | Departments | Which block is Admission Procedure in? | 0.00 | 0.11 | FAILED | 0.0 ms |
| 323 | Departments | Can I meet a faculty member from Docu... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 324 | Departments | Where is the Bachelor of Engineering ... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 325 | Departments | Does this college have a department f... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 326 | Departments | Where is the Documents to be submitte... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 327 | Departments | What courses are offered in UG & PG P... | 0.00 | 0.39 | FAILED | 0.0 ms |
| 328 | Departments | Where is the UG & PG Programs of High... | 0.00 | 0.35 | FAILED | 0.0 ms |
| 329 | Departments | Which block is UG & PG Programs of Hi... | 0.00 | 0.35 | FAILED | 0.0 ms |
| 330 | Departments | Can I meet a faculty member from UG &... | 0.00 | 0.37 | FAILED | 0.0 ms |
| 331 | Departments | Does this college have a department f... | 0.00 | 0.33 | FAILED | 0.0 ms |
| 332 | Departments | What courses are offered in APPENDIX I? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 333 | Departments | Which block is Academic Eligibility in? | 0.00 | 0.09 | FAILED | 0.0 ms |
| 334 | Departments | What courses are offered in Academic ... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 335 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 336 | Departments | Which block is Fee Payment & Refund R... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 337 | Departments | Which block is Reservation for Childr... | 0.00 | 0.41 | FAILED | 0.0 ms |
| 338 | Departments | Does this college have a department f... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 339 | Departments | Which block is Essential Documents in? | 0.00 | 0.09 | FAILED | 0.0 ms |
| 340 | Departments | Where is the Fee Payment & Refund Rul... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 341 | Departments | Which block is KLE Technological Univ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 342 | Departments | Can I meet a faculty member from KLE ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 343 | Departments | Where is the KLE Technological Univer... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 344 | Departments | What courses are offered in KLE Techn... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 345 | Departments | Which block is Contact Details for Ba... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 346 | Departments | What courses are offered in KLE Law C... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 347 | Departments | Which block is KLE Law Campus in? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 348 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 349 | Departments | What courses are offered in DEPARTMEN... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 350 | Departments | Can I meet a faculty member from DEPA... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 351 | Departments | Can I meet a faculty member from Copy... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 352 | Departments | Which block is Copy to in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 353 | Departments | Does this college have a department f... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 354 | Departments | Can I meet a faculty member from BACH... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 355 | Departments | Which block is Controller of Examinat... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 356 | Departments | Can I meet a faculty member from Cont... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 357 | Departments | Can I meet a faculty member from SCHO... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 358 | Departments | Which block is BACHELOR OF SCIENCE IN... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 359 | Departments | Where is the Controller of Examinatio... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 360 | Departments | Where is the the Allied Departments C... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 361 | Departments | Where is the PART A- Profile of the I... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 362 | Departments | Can I meet a faculty member from Tabl... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 363 | Departments | What courses are offered in PART C Fa... | 0.00 | 0.40 | FAILED | 0.0 ms |
| 364 | Departments | What courses are offered in Table No ... | 0.00 | 0.27 | FAILED | 0.0 ms |
| 365 | Departments | Can I meet a faculty member from B2 D... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 366 | Departments | Which block is C9 Institution Seed Mo... | 0.00 | 0.42 | FAILED | 0.0 ms |
| 367 | Departments | Which block is Table No A7 1 List of ... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 368 | Departments | Does this college have a department f... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 369 | Departments | Where is the CAYm1 department? | 0.00 | 0.09 | FAILED | 0.0 ms |
| 370 | Departments | Can I meet a faculty member from PART... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 371 | Departments | Which block is PART A- Profile of the... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 372 | Departments | Can I meet a faculty member from Tabl... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 373 | Departments | Can I meet a faculty member from Tabl... | 0.00 | 0.26 | FAILED | 0.0 ms |
| 374 | Departments | Which block is Table No B8 1 Academic... | 0.00 | 0.28 | FAILED | 0.0 ms |
| 375 | Departments | Which block is Table No D2 1 List of ... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 376 | Departments | Where is the PART D Laboratory Infras... | 0.00 | 0.33 | FAILED | 0.0 ms |
| 377 | Departments | Can I meet a faculty member from Our ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 378 | Departments | Which block is Our Research Focus Are... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 379 | Departments | Where is the Human-Robot Collaboratio... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 380 | Departments | What courses are offered in Human-Rob... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 381 | Departments | Which block is Human-Robot Collaborat... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 382 | Departments | Where is the Our Research Focus Areas... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 383 | Departments | Can I meet a faculty member from Huma... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 384 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 385 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 386 | Departments | What courses are offered in Past Events? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 387 | Departments | Where is the Past Events department? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 388 | Departments | Which block is Past Events in? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 389 | Departments | Can I meet a faculty member from Past... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 390 | Departments | Does this college have a department f... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 391 | Departments | Can I meet a faculty member from AICWiC? | 0.00 | 0.11 | FAILED | 0.0 ms |
| 392 | Departments | Which block is AICWiC in? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 393 | Departments | Where is the Relevant Events department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 394 | Departments | What courses are offered in Relevant ... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 395 | Departments | Which block is Relevant Events in? | 0.00 | 0.02 | FAILED | 0.0 ms |
| 396 | Departments | Where is the AICWiC department? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 397 | Departments | Can I meet a faculty member from Rele... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 398 | Departments | Does this college have a department f... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 399 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 400 | Departments | What courses are offered in AICWiC? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 401 | Departments | Does this college have a department f... | 0.00 | 0.01 | FAILED | 0.0 ms |
| 402 | Departments | Can I meet a faculty member from Afte... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 403 | Departments | What courses are offered in SCHOOL OF... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 404 | Departments | Where is the SCHOOL OF ELECTRONICS AN... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 405 | Departments | Can I meet a faculty member from SCHO... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 406 | Departments | Which block is SCHOOL OF COMPUTER SCI... | 0.00 | 0.03 | FAILED | 0.1 ms |
| 407 | Departments | Can I meet a faculty member from DEPA... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 408 | Departments | Can I meet a faculty member from Afte... | 0.00 | 0.15 | FAILED | 0.1 ms |
| 409 | Departments | Which block is DEPARTMENT OF ELECTRIC... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 410 | Departments | Which block is DEPARTMENT OF CHEMICAL... | 0.00 | 0.03 | FAILED | 0.1 ms |
| 411 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 412 | Departments | What courses are offered in DEPARTMEN... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 413 | Departments | Which block is SCHOOL OF ELECTRONICS ... | 0.00 | 0.05 | FAILED | 0.1 ms |
| 414 | Departments | Which block is SCHOOL OF CIVIL ENGINE... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 415 | Departments | Which block is After 2nd &amp 4th Sem... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 416 | Departments | Can I meet a faculty member from DEPA... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 417 | Departments | Does this college have a department f... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 418 | Departments | Which block is SCHOOL OF ELECTRONICS ... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 419 | Departments | What courses are offered in BACHELOR ... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 420 | Departments | Where is the DEPARTMENT OF AUTOMATION... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 421 | Departments | What courses are offered in SCHOOL OF... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 422 | Departments | Does this college have a department f... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 423 | Departments | What courses are offered in Controlle... | 0.00 | 0.23 | FAILED | 0.0 ms |
| 424 | Departments | Which block is DEPARTMENT OF AUTOMATI... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 425 | Departments | Which block is BACHELOR OF BUSINESS A... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 426 | Departments | What courses are offered in DEPARTMEN... | 0.00 | 0.00 | FAILED | 0.1 ms |
| 427 | Departments | Which block is DEPARTMENT OF BACHELOR... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 428 | Departments | Can I meet a faculty member from BACH... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 429 | Departments | Where is the SCHOOL OF CIVIL ENGINEER... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 430 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 431 | Departments | What courses are offered in DEPARTMEN... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 432 | Departments | Where is the BACHELOR OF BUSINESS ADM... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 433 | Departments | What courses are offered in BACHELOR ... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 434 | Departments | Can I meet a faculty member from BACH... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 435 | Departments | Does this college have a department f... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 436 | Departments | Can I meet a faculty member from INTE... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 437 | Departments | Which block is BACHELOR OF COMMERCE in? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 438 | Departments | Can I meet a faculty member from BACH... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 439 | Departments | Which block is Defense Club in? | 0.00 | 0.17 | FAILED | 0.1 ms |
| 440 | Departments | Can I meet a faculty member from UPSC... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 441 | Departments | Where is the UPSC Club department? | 0.00 | 0.19 | FAILED | 0.0 ms |
| 442 | Departments | Can I meet a faculty member from High... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 443 | Departments | Can I meet a faculty member from Word... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 444 | Departments | What courses are offered in Higher St... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 445 | Departments | Can I meet a faculty member from Covi... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 446 | Departments | Does this college have a department f... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 447 | Departments | Which block is 91-8555676012 in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 448 | Departments | Where is the Covid-19 Readiness depar... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 449 | Departments | What courses are offered in 91-855567... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 450 | Departments | What courses are offered in Covid-19 ... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 451 | Departments | Where is the Research centers departm... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 452 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 453 | Departments | Does this college have a department f... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 454 | Departments | What courses are offered in Total Stu... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 455 | Departments | Where is the Student Enrollment depar... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 456 | Departments | Can I meet a faculty member from Our ... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 457 | Departments | Which block is Foreword in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 458 | Departments | Can I meet a faculty member from CONT... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 459 | Departments | Where is the Summary of publications ... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 460 | Departments | Does this college have a department f... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 461 | Departments | Where is the CONTENTS department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 462 | Departments | What courses are offered in Research ... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 463 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 464 | Departments | Which block is Our Vision in? | 0.00 | 0.04 | FAILED | 0.0 ms |
| 465 | Departments | Does this college have a department f... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 466 | Departments | Which block is Research and Innovatio... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 467 | Departments | Can I meet a faculty member from Crea... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 468 | Departments | Where is the Karnataka Lingayat Educa... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 469 | Departments | What courses are offered in Academic ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 470 | Departments | Which block is Student admissions for... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 471 | Departments | Which block is Postgraduate Programs in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 472 | Departments | What courses are offered in Undergrad... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 473 | Departments | Where is the Creating Value Leveragin... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 474 | Departments | Which block is Introduction and Our O... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 475 | Departments | Can I meet a faculty member from Work... | 0.00 | 0.26 | FAILED | 0.0 ms |
| 476 | Departments | Can I meet a faculty member from Karn... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 477 | Departments | Which block is Karnataka Lingayat Edu... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 478 | Departments | Can I meet a faculty member from Intr... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 479 | Departments | What courses are offered in Postgradu... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 480 | Departments | Does this college have a department f... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 481 | Departments | Which block is Workshop on Advancing ... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 482 | Departments | Where is the Postgraduate Programs de... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 483 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 484 | Departments | Where is the Academic Quality departm... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 485 | Departments | What courses are offered in Advances ... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 486 | Departments | Which block is Student admissions for... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 487 | Departments | Where is the Our Vision department? | 0.00 | 0.04 | FAILED | 0.0 ms |
| 488 | Departments | Which block is Creating Value Leverag... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 489 | Departments | Can I meet a faculty member from Inno... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 490 | Departments | Which block is CONTENTS in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 491 | Departments | Does this college have a department f... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 492 | Departments | Which block is Innovations in teachin... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 493 | Departments | Does this college have a department f... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 494 | Departments | Where is the Advances in Curriculum d... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 495 | Departments | What courses are offered in DEPARTMEN... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 496 | Departments | What courses are offered in DEPARTMEN... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 497 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 498 | Departments | Can I meet a faculty member from SCHO... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 499 | Departments | Where is the SCHOOL OF COMPUTER SCIEN... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 500 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 501 | Departments | What courses are offered in SCHOOL OF... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 502 | Departments | Which block is Time Table for Summer ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 503 | Departments | Which block is DEPARTMENT OF BIOMEDIC... | 0.00 | 0.01 | FAILED | 0.0 ms |
| 504 | Departments | Does this college have a department f... | 0.00 | 0.01 | FAILED | 0.0 ms |
| 505 | Departments | Can I meet a faculty member from SCHO... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 506 | Departments | Where is the Time Table for Summer Ex... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 507 | Departments | Where is the DEPARTMENT OF BIOMEDICAL... | 0.00 | 0.01 | FAILED | 0.0 ms |
| 508 | Departments | Can I meet a faculty member from 12 P... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 509 | Departments | Where is the 5 Accreditation Details ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 510 | Departments | What courses are offered in Number of... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 511 | Departments | Which block is 21 Distance education ... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 512 | Departments | Which block is 20 Focus on Outcome ba... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 513 | Departments | What courses are offered in 16 Multid... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 514 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 515 | Departments | Which block is 11 Significant contrib... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 516 | Departments | Can I meet a faculty member from 1 3 ... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 517 | Departments | Can I meet a faculty member from 5 Ac... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 518 | Departments | Which block is 5 Accreditation Detail... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 519 | Departments | Can I meet a faculty member from 11 S... | 0.00 | 0.05 | FAILED | 0.1 ms |
| 520 | Departments | What courses are offered in 20 Focus ... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 521 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 522 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 523 | Departments | Can I meet a faculty member from Assi... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 524 | Departments | What courses are offered in 19 Approp... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 525 | Departments | Which block is 1 3 - Curriculum Enric... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 526 | Departments | Where is the DEPARTMENT OF ELECTRICAL... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 527 | Departments | Does this college have a department f... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 528 | Departments | Can I meet a faculty member from SCHO... | 0.00 | 0.01 | FAILED | 0.0 ms |
| 529 | Departments | Where is the BACHELOR OF COMPUTER APP... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 530 | Departments | What courses are offered in SCHOOL OF... | 0.00 | 0.01 | FAILED | 0.0 ms |
| 531 | Departments | Which block is BACHELOR OF SCIENCE IN... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 532 | Departments | Where is the BACHELOR OF COMMERCE dep... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 533 | Departments | Can I meet a faculty member from SCHO... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 534 | Departments | What courses are offered in Minutes o... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 535 | Departments | Which block is 1 NAAC peerteam visit in? | 0.00 | 0.15 | FAILED | 0.0 ms |
| 536 | Departments | What courses are offered in 1 NAAC pe... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 537 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 538 | Departments | Does this college have a department f... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 539 | Departments | Which block is 3 Re-Constitution of l... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 540 | Departments | Which block is Minutes of the meeting... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 541 | Departments | Can I meet a faculty member from Minu... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 542 | Departments | Where is the 1 NAAC peerteam visit de... | 0.00 | 0.23 | FAILED | 0.0 ms |
| 543 | Departments | Does this college have a department f... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 544 | Departments | Where is the Minutes of the meeting h... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 545 | Departments | Which block is Annual Reports 2019 - ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 546 | Departments | What courses are offered in Annual Re... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 547 | Departments | Can I meet a faculty member from Prev... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 548 | Departments | Where is the Previous Annual Reports ... | 0.00 | 0.23 | FAILED | 0.0 ms |
| 549 | Departments | Can I meet a faculty member from Annu... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 550 | Departments | What courses are offered in Previous ... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 551 | Departments | What courses are offered in Dual Degr... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 552 | Departments | Which block is 1 Guidelines on submis... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 553 | Departments | Where is the All India Council for Te... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 554 | Departments | Which block is Application Report - P... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 555 | Departments | What courses are offered in Applicati... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 556 | Departments | Does this college have a department f... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 557 | Departments | Does this college have a department f... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 558 | Departments | Which block is Regional Office codes in? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 559 | Departments | Which block is All India Council for ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 560 | Departments | Which block is Dual Degree Integrated... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 561 | Departments | What courses are offered in Programme... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 562 | Departments | Which block is Programme and Courses in? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 563 | Departments | Can I meet a faculty member from Dual... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 564 | Departments | Where is the Application Report - Par... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 565 | Departments | Does this college have a department f... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 566 | Departments | What courses are offered in All India... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 567 | Departments | Where is the Dual Degree Integrated C... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 568 | Departments | Which block is Application Report Par... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 569 | Departments | Can I meet a faculty member from Appl... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 570 | Departments | Where is the Application Report Part-... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 571 | Departments | Which block is Instructional Area in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 572 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 573 | Departments | Does this college have a department f... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 574 | Departments | Which block is Important Note for Pay... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 575 | Departments | Where is the Programme and Courses de... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 576 | Departments | Where is the Instructional Area depar... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 577 | Departments | What courses are offered in Applicati... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 578 | Departments | Can I meet a faculty member from All ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 579 | Departments | Can I meet a faculty member from Appl... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 580 | Departments | Which block is Application Report Par... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 581 | Departments | Does this college have a department f... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 582 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 583 | Departments | Can I meet a faculty member from Facu... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 584 | Departments | Does this college have a department f... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 585 | Departments | Which block is Faculty Details in? | 0.00 | 0.20 | FAILED | 0.0 ms |
| 586 | Departments | Where is the Faculty Counts department? | 0.00 | 0.13 | FAILED | 0.0 ms |
| 587 | Departments | Where is the Application Report - Par... | 0.00 | 0.02 | FAILED | 0.0 ms |
| 588 | Departments | What courses are offered in Faculty D... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 589 | Departments | Where is the DEPARTMENT OF BACHELOR O... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 590 | Departments | What courses are offered in DEPARTMEN... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 591 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 592 | Departments | Does this college have a department f... | 0.00 | 0.29 | FAILED | 0.0 ms |
| 593 | Departments | Which block is Courses Offered in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 594 | Departments | Where is the Celebrating glorious 75 ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 595 | Departments | Which block is Research & Innovation in? | 0.00 | 0.10 | FAILED | 0.0 ms |
| 596 | Departments | What courses are offered in Research ... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 597 | Departments | Does this college have a department f... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 598 | Departments | Can I meet a faculty member from Cour... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 599 | Departments | Where is the Courses Offered department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 600 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 601 | Departments | What courses are offered in Courses O... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 602 | Departments | Which block is Facilities in? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 603 | Departments | Which block is Celebrating glorious 7... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 604 | Departments | What courses are offered in Nearby Lo... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 605 | Departments | Which block is Nearby Location in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 606 | Departments | Where is the Research & Innovation de... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 607 | Departments | Does this college have a department f... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 608 | Departments | What courses are offered in Celebrati... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 609 | Departments | Which block is Marketing Club in? | 0.00 | 0.16 | FAILED | 0.0 ms |
| 610 | Departments | Which block is Objectives in? | 0.00 | 0.15 | FAILED | 0.0 ms |
| 611 | Departments | What courses are offered in Objectives? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 612 | Departments | Does this college have a department f... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 613 | Departments | Can I meet a faculty member from Mark... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 614 | Departments | Where is the Marketing Club department? | 0.00 | 0.05 | FAILED | 0.0 ms |
| 615 | Departments | What courses are offered in Marketing... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 616 | Departments | Which block is Operations Club in? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 617 | Departments | Can I meet a faculty member from Entr... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 618 | Departments | Where is the Objectives department? | 0.00 | 0.15 | FAILED | 0.0 ms |
| 619 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 620 | Departments | Where is the Entrepreneurship Club de... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 621 | Departments | What courses are offered in Human Res... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 622 | Departments | Can I meet a faculty member from AQAR... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 623 | Departments | Which block is AQAR 2022-23 in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 624 | Departments | Can I meet a faculty member from Minu... | 0.00 | 0.50 | PASSED | 0.0 ms |
| 625 | Departments | Does this college have a department f... | 0.00 | 0.50 | PASSED | 0.0 ms |
| 626 | Departments | Which block is IQAC & Composition in? | 0.00 | 0.16 | FAILED | 0.0 ms |
| 627 | Departments | Where is the Minutes of the Meeting o... | 0.00 | 0.57 | PASSED | 0.0 ms |
| 628 | Departments | What courses are offered in IQAC & Co... | 0.00 | 0.15 | FAILED | 0.1 ms |
| 629 | Departments | Can I meet a faculty member from Unde... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 630 | Departments | What courses are offered in Principle... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 631 | Departments | Which block is Introducing Engineerin... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 632 | Departments | Which block is Major Academic initiat... | 0.00 | 0.24 | FAILED | 0.1 ms |
| 633 | Departments | Where is the Undergraduate Programs d... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 634 | Departments | Which block is Admission Process in? | 0.00 | 0.09 | FAILED | 0.0 ms |
| 635 | Departments | Can I meet a faculty member from Admi... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 636 | Departments | What courses are offered in Major Aca... | 0.00 | 0.29 | FAILED | 0.0 ms |
| 637 | Departments | Does this college have a department f... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 638 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 639 | Departments | Where is the Major Academic initiativ... | 0.00 | 0.30 | FAILED | 0.0 ms |
| 640 | Departments | Does this college have a department f... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 641 | Departments | Where is the Faculty Development Prog... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 642 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 643 | Departments | Does this college have a department f... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 644 | Departments | Where is the Research Programs depart... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 645 | Departments | Can I meet a faculty member from Intr... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 646 | Departments | Where is the Research and Innovation ... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 647 | Departments | Does this college have a department f... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 648 | Departments | Does this college have a department f... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 649 | Departments | Where is the Introduction department? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 650 | Departments | What courses are offered in Placement? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 651 | Departments | Does this college have a department f... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 652 | Departments | Does this college have a department f... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 653 | Departments | Which block is Undergraduate Programs... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 654 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 655 | Departments | Which block is Placement in? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 656 | Departments | Which block is Academic Quality in? | 0.00 | 0.06 | FAILED | 0.0 ms |
| 657 | Departments | Which block is Student admissions for... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 658 | Departments | What courses are offered in Undergrad... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 659 | Departments | Does this college have a department f... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 660 | Departments | Can I meet a faculty member from Coll... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 661 | Departments | Can I meet a faculty member from Fore... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 662 | Departments | What courses are offered in Student a... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 663 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 664 | Departments | Does this college have a department f... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 665 | Departments | Which block is Collaboration with San... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 666 | Departments | Where is the Student admissions for t... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 667 | Departments | Does this college have a department f... | 0.00 | 0.34 | FAILED | 0.0 ms |
| 668 | Departments | Where is the Full Stack Development -... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 669 | Departments | Does this college have a department f... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 670 | Departments | Does this college have a department f... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 671 | Departments | Which block is Introduction in? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 672 | Departments | Where is the Blockchain Technologies ... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 673 | Departments | Where is the Foreword department? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 674 | Departments | What courses are offered in RESTful W... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 675 | Departments | Does this college have a department f... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 676 | Departments | Which block is RESTful Web Services in? | 0.00 | 0.28 | FAILED | 0.0 ms |
| 677 | Departments | Where is the Machine learning ML &amp... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 678 | Departments | Where is the Chancellor s Message dep... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 679 | Departments | Which block is Student admissions for... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 680 | Departments | Can I meet a faculty member from Co-t... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 681 | Departments | Can I meet a faculty member from Chan... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 682 | Departments | Which block is Chancellor s Message in? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 683 | Departments | What courses are offered in Student a... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 684 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 685 | Departments | Does this college have a department f... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 686 | Departments | Which block is Co-teaching by Eklaksh... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 687 | Departments | Where is the Student admissions for t... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 688 | Departments | Does this college have a department f... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 689 | Departments | Where is the Session 13 UPSC Intervie... | 0.00 | 0.26 | FAILED | 0.0 ms |
| 690 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 691 | Departments | Can I meet a faculty member from STAT... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 692 | Departments | Does this college have a department f... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 693 | Departments | What courses are offered in Session 2... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 694 | Departments | Where is the Session 1 How to Prepare... | 0.00 | 0.43 | FAILED | 0.0 ms |
| 695 | Departments | Can I meet a faculty member from Impo... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 696 | Departments | Which block is WEEKLY in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 697 | Departments | Can I meet a faculty member from DAILY? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 698 | Departments | Where is the Session 14 Stay Positive... | 0.00 | 0.31 | FAILED | 0.0 ms |
| 699 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 700 | Departments | Where is the DAILY department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 701 | Departments | What courses are offered in Session 1... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 702 | Departments | Does this college have a department f... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 703 | Departments | Does this college have a department f... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 704 | Departments | Which block is Important subjects of ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 705 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 706 | Departments | Does this college have a department f... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 707 | Departments | Which block is Session 12 Revision in? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 708 | Departments | Where is the Session 11 Important Gov... | 0.00 | 0.26 | FAILED | 0.0 ms |
| 709 | Departments | Where is the nirf-innovation-category... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 710 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 711 | Departments | Can I meet a faculty member from Subm... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 712 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 713 | Departments | What courses are offered in FDI inves... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 714 | Departments | Where is the Seed Funding department? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 715 | Departments | Can I meet a faculty member from Star... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 716 | Departments | Which block is Start up recognized by... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 717 | Departments | Can I meet a faculty member from Tota... | 0.00 | 0.00 | FAILED | 0.1 ms |
| 718 | Departments | Where is the Academic Courses in Inno... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 719 | Departments | Does this college have a department f... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 720 | Departments | Where is the Total Actual Student Str... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 721 | Departments | What courses are offered in Incubatio... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 722 | Departments | Does this college have a department f... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 723 | Departments | Does this college have a department f... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 724 | Departments | Which block is Startups which have go... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 725 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 726 | Departments | Does this college have a department f... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 727 | Departments | Which block is Incubation Activities in? | 0.00 | 0.15 | FAILED | 0.0 ms |
| 728 | Departments | Where is the Pre-incubation Activitie... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 729 | Departments | What courses are offered in Statutory... | 0.00 | 0.38 | FAILED | 0.0 ms |
| 730 | Departments | Where is the Statutory Declaration un... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 731 | Departments | What courses are offered in Statutory... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 732 | Departments | Where is the Statutory Declaration un... | 0.00 | 0.39 | FAILED | 0.0 ms |
| 733 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 734 | Departments | Can I meet a faculty member from Stat... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 735 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 736 | Departments | What courses are offered in Brief His... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 737 | Departments | Which block is Statutory Declaration ... | 0.00 | 0.39 | FAILED | 0.0 ms |
| 738 | Departments | Does this college have a department f... | 0.00 | 0.35 | FAILED | 0.0 ms |
| 739 | Departments | What courses are offered in Euro s Ra... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 740 | Departments | Where is the Euro s Racing M-Baja Ach... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 741 | Departments | Which block is Euro s Racing M-Baja A... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 742 | Departments | Can I meet a faculty member from Euro... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 743 | Departments | Does this college have a department f... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 744 | Departments | What courses are offered in Relevant ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 745 | Departments | Where is the Relevant News department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 746 | Departments | Which block is Relevant News in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 747 | Departments | Can I meet a faculty member from Rele... | 0.00 | 0.00 | FAILED | 0.1 ms |
| 748 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 749 | Departments | What courses are offered in Data Scie... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 750 | Departments | Where is the Data Science and AI in A... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 751 | Departments | Which block is Data Science and AI in... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 752 | Departments | Can I meet a faculty member from Data... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 753 | Departments | Does this college have a department f... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 754 | Departments | What courses are offered in BAJA SAE ... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 755 | Departments | Where is the BAJA SAE India 2026 comp... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 756 | Departments | Which block is BAJA SAE India 2026 co... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 757 | Departments | Can I meet a faculty member from BAJA... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 758 | Departments | Does this college have a department f... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 759 | Departments | What courses are offered in BROWSE BY? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 760 | Departments | Where is the BROWSE BY department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 761 | Departments | Which block is BROWSE BY in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 762 | Departments | Can I meet a faculty member from BROW... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 763 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 764 | Departments | Which block is December 2024 in? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 765 | Departments | Which block is February 2023 in? | 0.00 | 0.16 | FAILED | 0.0 ms |
| 766 | Departments | What courses are offered in February ... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 767 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 768 | Departments | Can I meet a faculty member from Dece... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 769 | Departments | Where is the December 2024 department? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 770 | Departments | Which block is 2023 in? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 771 | Departments | Can I meet a faculty member from 2022? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 772 | Departments | Where is the February 2023 department? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 773 | Departments | Where is the 2022 department? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 774 | Departments | Can I meet a faculty member from Apri... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 775 | Departments | Does this college have a department f... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 776 | Departments | What courses are offered in February ... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 777 | Departments | Which block is April 2022 in? | 0.00 | 0.10 | FAILED | 0.0 ms |
| 778 | Departments | Which block is August 2022 in? | 0.00 | 0.17 | FAILED | 0.0 ms |
| 779 | Departments | Where is the May 2023 department? | 0.00 | 0.17 | FAILED | 0.0 ms |
| 780 | Departments | Does this college have a department f... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 781 | Departments | Which block is June 2023 in? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 782 | Departments | Where is the April 2019 department? | 0.00 | 0.10 | FAILED | 0.0 ms |
| 783 | Departments | Where is the 2024 Batch Top Recruiter... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 784 | Departments | Does this college have a department f... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 785 | Departments | Can I meet a faculty member from KLE ... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 786 | Departments | Does this college have a department f... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 787 | Departments | What courses are offered in Industry ... | 0.00 | 0.03 | FAILED | 0.0 ms |
| 788 | Departments | Where is the Our leading Alumni depar... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 789 | Departments | Can I meet a faculty member from Othe... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 790 | Departments | Which block is Bachelor of Engineerin... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 791 | Departments | Can I meet a faculty member from KLE ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 792 | Departments | Does this college have a department f... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 793 | Departments | Where is the KLE Technological Univer... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 794 | Departments | What courses are offered in 2023 Batc... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 795 | Departments | Does this college have a department f... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 796 | Departments | Does this college have a department f... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 797 | Departments | Which block is Other courses in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 798 | Departments | Does this college have a department f... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 799 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 800 | Departments | Which block is 2023 Batch Top Recruit... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 801 | Departments | Where is the Nanomaterialsfor departm... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 802 | Departments | What courses are offered in Nanomater... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 803 | Departments | Which block is Nanomaterialsfor in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 804 | Departments | Can I meet a faculty member from Nano... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 805 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 806 | Departments | Can I meet a faculty member from CEVI... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 807 | Departments | Which block is CEVI Research Focus Ar... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 808 | Departments | Where is the Multimodal Learning depa... | 0.00 | 0.00 | FAILED | 0.1 ms |
| 809 | Departments | What courses are offered in Multimoda... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 810 | Departments | Which block is Multimodal Learning in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 811 | Departments | Where is the CEVI Research Focus Area... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 812 | Departments | Can I meet a faculty member from Mult... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 813 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 814 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 815 | Departments | Where is the Connectivity department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 816 | Departments | What courses are offered in Connectiv... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 817 | Departments | Which block is Connectivity in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 818 | Departments | Can I meet a faculty member from Conn... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 819 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 820 | Departments | What courses are offered in Our Resea... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 821 | Departments | Where is the Cloud Computing department? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 822 | Departments | What courses are offered in Cloud Com... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 823 | Departments | Which block is Cloud Computing in? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 824 | Departments | Can I meet a faculty member from Clou... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 825 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 826 | Departments | Where is the Grid Integrated Charging... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 827 | Departments | What courses are offered in Grid Inte... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 828 | Departments | Which block is Grid Integrated Chargi... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 829 | Departments | Can I meet a faculty member from Grid... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 830 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 831 | Departments | What courses are offered in KLE Tech ... | 0.00 | 0.39 | FAILED | 0.0 ms |
| 832 | Departments | Can I meet a faculty member from KLE ... | 0.00 | 0.41 | FAILED | 0.0 ms |
| 833 | Departments | Does this college have a department f... | 0.00 | 0.41 | FAILED | 0.0 ms |
| 834 | Departments | Can I meet a faculty member from Expl... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 835 | Departments | Which block is Explore our Science an... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 836 | Departments | Where is the Center for Material Scie... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 837 | Departments | What courses are offered in Center fo... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 838 | Departments | Which block is Center for Material Sc... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 839 | Departments | Where is the Explore our Science and ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 840 | Departments | Can I meet a faculty member from Cent... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 841 | Departments | Does this college have a department f... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 842 | Departments | Does this college have a department f... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 843 | Departments | What courses are offered in Explore o... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 1 | Facilities | Where is the Revised Time Table for 3... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 2 | Facilities | Is there a gym inside the campus? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 3 | Facilities | Does the college have a medical room ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 4 | Facilities | Is Wi-Fi available on campus for stud... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 5 | Facilities | Where is the library located? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 6 | Facilities | Is there a cafeteria or canteen on ca... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 7 | Facilities | Where is the Hostels? | 0.00 | 0.21 | FAILED | 0.0 ms |
| 8 | Facilities | Where is the Auditorium? | 0.00 | 0.09 | FAILED | 0.0 ms |
| 9 | Facilities | Where is the Gymnasium? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 10 | Facilities | Where is the Bank & ATM? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 11 | Facilities | Where is the Medical Health Centre? | 0.00 | 0.13 | FAILED | 0.0 ms |
| 12 | Facilities | Where is the Gym & Sports? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 13 | Facilities | Where is the Laboratories? | 0.00 | 0.06 | FAILED | 0.0 ms |
| 14 | Facilities | Where is the Latest Announcements? | 0.00 | 0.04 | FAILED | 0.0 ms |
| 15 | Facilities | Where is the E-Resources? | 0.00 | 0.04 | FAILED | 0.0 ms |
| 16 | Facilities | Where is the Library Collections? | 0.00 | 0.13 | FAILED | 0.0 ms |
| 17 | Facilities | Where is the Library Space? | 0.00 | 0.27 | FAILED | 0.0 ms |
| 18 | Facilities | Where is the Infrastructural Facilities? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 19 | Facilities | Where is the KLE University Central L... | 0.00 | 0.32 | FAILED | 0.0 ms |
| 20 | Facilities | Where is the Reference Section? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 21 | Facilities | Where is the Issue Section? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 22 | Facilities | Where is the Reading Section? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 23 | Facilities | Where is the K L E SOCIETY S LAW COLL... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 24 | Facilities | Where is the NOTICE? | 0.00 | 0.14 | FAILED | 0.0 ms |
| 25 | Facilities | Where is the GOVERNMENT OF KARNATAKA? | 0.00 | 0.18 | FAILED | 0.0 ms |
| 26 | Facilities | Where is the ORDER? | 0.00 | 0.04 | FAILED | 0.0 ms |
| 27 | Facilities | Where is the 13 Strict enforcement of... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 28 | Facilities | Where is the Time Table for 3year LL ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 29 | Facilities | Where is the 11 Significant contribut... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 30 | Facilities | Where is the 21 Distance education on... | 0.00 | 0.19 | FAILED | 0.0 ms |
| 31 | Facilities | Where is the 19 Appropriate integrati... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 32 | Facilities | Where is the 18 Skill development? | 0.00 | 0.12 | FAILED | 0.0 ms |
| 33 | Facilities | Where is the 12 Plan of action chalke... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 34 | Facilities | Where is the 1 1 2 - Number of Progra... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 35 | Facilities | Where is the 1 2 1 - Number of new co... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 36 | Facilities | Where is the 1 4 - Feedback System? | 0.00 | 0.23 | FAILED | 0.0 ms |
| 37 | Facilities | Where is the 2 3 - Teaching- Learning... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 38 | Facilities | Where is the 1 Programme? | 0.00 | 0.01 | FAILED | 0.0 ms |
| 39 | Facilities | Where is the ABC Registration Proof h... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 40 | Facilities | Where is the 2 Courses designed with ... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 41 | Facilities | Where is the YEARLY STATUS REPORT - 2... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 42 | Facilities | Where is the 3304? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 43 | Facilities | Where is the the facility? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 44 | Facilities | Where is the 2 3 2 - Teachers use ICT... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 45 | Facilities | Where is the 20 Focus on Outcome base... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 1 | Faculty | How can I meet the HOD of KLE Technol... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 2 | Faculty | Where is the faculty room? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 3 | Faculty | Can I talk to a professor? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 4 | Faculty | Where is the staff room located? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 5 | Faculty | How can I meet the HOD of Table No A7... | 0.00 | 0.16 | FAILED | 0.0 ms |
| 6 | Faculty | How can I meet the HOD of C2 Student-... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 7 | Faculty | How can I meet the HOD of C1 Faculty ... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 8 | Faculty | How can I meet the HOD of Table No B8... | 0.00 | 0.26 | FAILED | 0.0 ms |
| 9 | Faculty | How can I meet the HOD of B2 Detail o... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 10 | Faculty | How can I meet the HOD of C6 Academic... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 11 | Faculty | How can I meet the HOD of CAYm3? | 0.00 | 0.23 | FAILED | 0.0 ms |
| 12 | Faculty | How can I meet the HOD of Major Equip... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 13 | Faculty | How can I meet the HOD of Research La... | 0.00 | 0.29 | FAILED | 0.0 ms |
| 14 | Faculty | How can I meet the HOD of NATIONAL BO... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 15 | Faculty | How can I meet the HOD of C7 Sponsore... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 16 | Faculty | How can I meet the HOD of Table No A6... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 17 | Faculty | How can I meet the HOD of Pilot Scale... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 18 | Faculty | How can I meet the HOD of PART C Facu... | 0.00 | 0.30 | FAILED | 0.0 ms |
| 19 | Faculty | How can I meet the HOD of Faculty Con... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 20 | Faculty | How can I meet the HOD of B V B Colle... | 0.00 | 0.07 | FAILED | 0.1 ms |
| 21 | Faculty | How can I meet the HOD of Faculty Con... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 22 | Faculty | How can I meet the HOD of Faculty Con... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 23 | Faculty | How can I meet the HOD of Faculty Con... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 24 | Faculty | How can I meet the HOD of Faculty Con... | 0.00 | 0.06 | FAILED | 0.1 ms |
| 25 | Faculty | How can I meet the HOD of the departm... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 26 | Faculty | How can I meet the HOD of CAYm1? | 0.00 | 0.16 | FAILED | 0.0 ms |
| 27 | Faculty | How can I meet the HOD of the Allied ... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 28 | Faculty | How can I meet the HOD of PART A- Pro... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 29 | Faculty | How can I meet the HOD of Table No C2... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 30 | Faculty | How can I meet the HOD of C9 Institut... | 0.00 | 0.49 | FAILED | 0.0 ms |
| 31 | Faculty | How can I meet the HOD of KLE Technol... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 32 | Faculty | How can I meet the HOD of About KLE T... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 33 | Faculty | How can I meet the HOD of Vision of t... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 34 | Faculty | How can I meet the HOD of Overview? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 35 | Faculty | How can I meet the HOD of IQAC Long T... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 36 | Faculty | How can I meet the HOD of Aim of IQAC? | 0.00 | 0.27 | FAILED | 0.1 ms |
| 37 | Faculty | How can I meet the HOD of The objecti... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 38 | Faculty | How can I meet the HOD of Strategies ... | 0.00 | 0.11 | FAILED | 0.0 ms |
| 39 | Faculty | How can I meet the HOD of Responsibil... | 0.00 | 0.10 | FAILED | 0.0 ms |
| 40 | Faculty | How can I meet the HOD of Composition... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 41 | Faculty | How can I meet the HOD of Course Outc... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 42 | Faculty | How can I meet the HOD of Unit - III ... | 0.00 | 0.27 | FAILED | 0.0 ms |
| 43 | Faculty | How can I meet the HOD of Unit II Pat... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 44 | Faculty | How can I meet the HOD of Unit - V In... | 0.00 | 0.13 | FAILED | 0.0 ms |
| 45 | Faculty | How can I meet the HOD of SPECIALISAT... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 46 | Faculty | How can I meet the HOD of Unit - IV R... | 0.00 | 0.14 | FAILED | 0.0 ms |
| 47 | Faculty | How can I meet the HOD of Unit II Pos... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 48 | Faculty | How can I meet the HOD of Unit - II D... | 0.00 | 0.29 | FAILED | 0.0 ms |
| 49 | Faculty | How can I meet the HOD of KLE LAW COL... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 50 | Faculty | How can I meet the HOD of Prescribed ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 51 | Faculty | How can I meet the HOD of Unit I Over... | 0.00 | 0.32 | FAILED | 0.0 ms |
| 52 | Faculty | How can I meet the HOD of Unit III So... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 53 | Faculty | How can I meet the HOD of Unit- IV Tr... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 54 | Faculty | How can I meet the HOD of Unit - I In... | 0.00 | 0.12 | FAILED | 0.0 ms |
| 55 | Faculty | How can I meet the HOD of PARLIAMENTA... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 56 | Faculty | How can I meet the HOD of KARNATAKA A... | 0.00 | 0.25 | FAILED | 0.0 ms |
| 57 | Faculty | How can I meet the HOD of THE KLE TEC... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 58 | Faculty | How can I meet the HOD of PRELIMINARY? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 59 | Faculty | How can I meet the HOD of THE UNIVERS... | 0.00 | 0.24 | FAILED | 0.0 ms |
| 60 | Faculty | How can I meet the HOD of OFFICERS OF... | 0.00 | 0.38 | FAILED | 0.0 ms |
| 61 | Faculty | How can I meet the HOD of STATUTES AN... | 0.00 | 0.23 | FAILED | 0.0 ms |
| 62 | Faculty | How can I meet the HOD of CHAPTER - V... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 63 | Faculty | How can I meet the HOD of H R BHARDWA... | 0.00 | 0.34 | FAILED | 0.0 ms |
| 64 | Faculty | How can I meet the HOD of K DWARAKANA... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 65 | Faculty | How can I meet the HOD of Submitted I... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 66 | Faculty | How can I meet the HOD of Sanctioned ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 67 | Faculty | How can I meet the HOD of Total Actua... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 68 | Faculty | How can I meet the HOD of UG 4 Years ... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 69 | Faculty | How can I meet the HOD of National In... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 70 | Faculty | How can I meet the HOD of Ph D Studen... | 0.00 | 0.04 | FAILED | 0.0 ms |
| 71 | Faculty | How can I meet the HOD of Financial R... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 72 | Faculty | How can I meet the HOD of PCS Facilit... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 73 | Faculty | How can I meet the HOD of Faculty Det... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 74 | Faculty | How can I meet the HOD of Multiple En... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 75 | Faculty | How can I meet the HOD of Sustainable... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 76 | Faculty | How can I meet the HOD of Accreditation? | 0.00 | 0.10 | FAILED | 0.0 ms |
| 1 | Fees | How much is the tuition fee? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 2 | Fees | Can I pay fees online? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 3 | Fees | Are scholarships available for students? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 4 | Fees | When is the last date to pay fees? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 5 | Fees | Where do I pay the college fees? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 1 | Misc | What are the college timings? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 2 | Misc | Where should visitors enter the campus? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 3 | Misc | Can outsiders visit the campus? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 4 | Misc | Where do I collect my student ID card? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 5 | Misc | Where is the examination office? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 6 | Misc | Where can I submit my documents? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 1 | Navigation | Where is Bachelor of Commerce and Bac... | 0.00 | 0.06 | FAILED | 0.0 ms |
| 2 | Navigation | Is there parking for visitors on campus? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 3 | Navigation | Where is KLE Society s Law College Be... | 0.00 | 0.21 | FAILED | 0.0 ms |
| 4 | Navigation | How do I reach the examination section? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 5 | Navigation | How do I reach the Bachelor of Commer... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 6 | Navigation | Where is the canteen? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 7 | Navigation | How do I reach the Bachelor of Laws? | 0.00 | 0.07 | FAILED | 0.0 ms |
| 8 | Navigation | Can you guide me to the KLE Society s... | 0.00 | 0.17 | FAILED | 0.0 ms |
| 9 | Navigation | Can you guide me to the Controller of... | 0.00 | 0.22 | FAILED | 0.0 ms |
| 10 | Navigation | Where is Bachelor of Laws? | 0.00 | 0.04 | FAILED | 0.0 ms |
| 11 | Navigation | Where is Bachelor of Business Adminis... | 0.00 | 0.09 | FAILED | 0.3 ms |
| 12 | Navigation | How do I reach the KLE Society s Law ... | 0.00 | 0.18 | FAILED | 0.0 ms |
| 13 | Navigation | Where is Controller of Examinations? | 0.00 | 0.26 | FAILED | 0.0 ms |
| 14 | Navigation | Can you guide me to the Bachelor of C... | 0.00 | 0.09 | FAILED | 0.0 ms |
| 15 | Navigation | Where is the nearest washroom? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 16 | Navigation | Where is The United Nations Economic ... | 0.00 | 0.20 | FAILED | 0.0 ms |
| 17 | Navigation | Where is Newsletter? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 18 | Navigation | Where is About the KLESLCMUN 2017? | 0.00 | 0.18 | FAILED | 0.0 ms |
| 19 | Navigation | How do I reach the United Nations Sec... | 0.00 | 0.15 | FAILED | 0.0 ms |
| 20 | Navigation | Where is United Nations Office on Dru... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 21 | Navigation | Can you guide me to the Newsletter? | 0.00 | 0.08 | FAILED | 0.0 ms |
| 22 | Navigation | Can you guide me to the Table of Cont... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 23 | Navigation | Where is United Nations Security Coun... | 0.00 | 0.08 | FAILED | 0.0 ms |
| 24 | Navigation | Where is Disarmament and Internationa... | 0.00 | 0.23 | FAILED | 0.0 ms |
| 25 | Navigation | How do I reach the Newsletter? | 0.00 | 0.04 | FAILED | 0.0 ms |
| 26 | Navigation | How do I reach the United Nations Off... | 0.00 | 0.07 | FAILED | 0.0 ms |
| 27 | Navigation | Where is Table of Contents? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 28 | Navigation | Can you guide me to the The United Na... | 0.00 | 0.27 | FAILED | 0.0 ms |
| 29 | Navigation | Can you guide me to the About the KLE... | 0.00 | 0.05 | FAILED | 0.0 ms |
| 1 | Placement | Do companies visit this college for p... | 0.00 | 0.00 | FAILED | 0.0 ms |
| 2 | Placement | Which companies recruit students from... | 0.00 | 0.01 | FAILED | 0.0 ms |
| 3 | Placement | What is the placement percentage? | 0.00 | 0.00 | FAILED | 0.0 ms |
| 4 | Placement | Are internships available for students? | 0.00 | 0.01 | FAILED | 0.0 ms |
| 5 | Placement | What is the highest package offered i... | 0.00 | 0.01 | FAILED | 0.0 ms |
