# Non-events audit (ADR-0010)

_Generated 2026-11-02 21:34 UTC by `scripts/non_events_audit.py` from `gotc.db` after a full build. Re-run after any rule change._

## Summary

- **92,733** listings published (per source membership), **588** held back by the build-time gate, **0** skipped at ingest (online-only, excluded places, campus-internal) — every one quarantined in `gated_listings` with its rule and reason, never silently dropped.
- Golden set (`tests/fixtures/listing_gate/golden.yaml`, labelled blind to the rules): **287 labelled listings · precision 0.988 · recall 0.888** `{'tn': 197, 'tp': 79, 'fn': 10, 'fp': 1}`. **Caveat:** 245 listings under-sample the campus audience-tag rule, so the per-rule false-positive rates the cold data review measured (below) matter more than this headline number.
- Ingest-stage counts appear after each source's next fetch. A DB built only from older records shows build-stage rows only.
- The FIU withdrawal deadline that started this: see *FIU* below.

## Top rules

| Rule | Held back (rows) | Distinct titles | Family |
|---|---|---|---|
| `campus_internal_audience` | 129 | 99 | internal_only |
| `appointment` | 124 | 51 | appointment |
| `closure` | 53 | 28 | closure |
| `campus_support_group` | 37 | 15 | internal_only |
| `placeholder_matchup` | 33 | 33 | placeholder |
| `proctored_testing` | 27 | 10 | appointment |
| `governance_meeting` | 26 | 18 | governance_meeting |
| `campus_admissions` | 25 | 17 | internal_only |
| `campus_term_date` | 23 | 2 | academic_calendar |
| `campus_meeting` | 21 | 14 | internal_only |
| `campus_career` | 20 | 17 | internal_only |
| `office_hours` | 17 | 9 | office_hours |
| `campus_academic_admin` | 14 | 12 | internal_only |
| `admin_deadline` | 12 | 2 | admin_deadline |
| `internal_only` | 12 | 9 | internal_only |
| `placeholder` | 8 | 3 | placeholder |
| `academic_calendar` | 7 | 4 | academic_calendar |

## Top rejected patterns (matched text)

| Rule | Matched text | Count |
|---|---|---|
| `appointment` | one-on-one | 46 |
| `campus_internal_audience` | label 'current students' | 38 |
| `campus_support_group` | share community meeting | 35 |
| `campus_internal_audience` | label 'faculty & staff' | 34 |
| `placeholder_matchup` | tbd at | 33 |
| `campus_term_date` | spring: | 23 |
| `closure` | closed for veterans | 23 |
| `appointment` | 1:1 | 22 |
| `appointment` | one on one | 21 |
| `office_hours` | office hours | 17 |
| `appointment` | 1-on-1 | 15 |
| `closure` | closed for | 14 |
| `governance_meeting` | committee meeting | 12 |
| `admin_deadline` | applications open | 11 |
| `appointment` | by appointment | 11 |
| `campus_internal_audience` | label 'graduate students' | 10 |
| `proctored_testing` | pre-testing | 10 |
| `campus_internal_audience` | label 'students - undergraduates' | 9 |
| `campus_admissions` | info session | 8 |
| `campus_admissions` | information session | 8 |
| `campus_internal_audience` | label 'faculty/staff' | 8 |
| `proctored_testing` | test center | 7 |
| `campus_internal_audience` | label 'student organizations' | 7 |
| `appointment` | 1 on 1 | 6 |
| `campus_internal_audience` | label 'postdocs' | 6 |
| `campus_internal_audience` | label 'sjsu employees' | 6 |
| `proctored_testing` | ged testing | 5 |
| `campus_internal_audience` | label 'staff' | 5 |
| `campus_academic_admin` | study abroad | 5 |
| `governance_meeting` | board meeting | 5 |
| `academic_calendar` | fall b: | 5 |
| `campus_meeting` | weekly meeting | 4 |
| `campus_academic_admin` | syllabus | 4 |
| `proctored_testing` | pre-test session | 4 |
| `placeholder` | test | 4 |
| `campus_career` | career services | 4 |
| `internal_only` | private event | 4 |
| `campus_meeting` | faculty and staff network | 3 |
| `campus_academic_admin` | grand rounds | 3 |
| `campus_career` | internships | 3 |

## Per source

Kept = published listings from this source; held = quarantined (gate + ingest). Samples are random (seeded):
read the held-back column for anything real, and the kept column for anything that isn't.

### University (35 units · 1,838 kept · 310 held back)

| Unit | Kept | Held | Share held | Top rules |
|---|---|---|---|---|
| `utaustin_events@austin` | 244 | 81 | 25% | campus_support_group 35, governance_meeting 13, admin_deadline 11 |
| `fiu_events@miami` | 100 | 66 | 40% | campus_term_date 23, campus_internal_audience 12, campus_career 11 |
| `bham_uab_events@birmingham` | 70 | 55 | 44% | campus_internal_audience 44, campus_admissions 8, campus_academic_admin 3 |
| `clt_uncc_events@charlotte` | 64 | 19 | 23% | campus_internal_audience 16, campus_career 3 |
| `sjsu_events@san_jose` | 69 | 16 | 19% | campus_internal_audience 15, campus_academic_admin 1 |
| `stanford_events@san_jose` | 187 | 16 | 8% | campus_internal_audience 11, internal_only 2, campus_meeting 2 |
| `ncsu_events@raleigh` | 88 | 9 | 9% | campus_internal_audience 8, campus_academic_admin 1 |
| `usc_events@los_angeles` | 129 | 9 | 7% | campus_internal_audience 8, campus_career 1 |
| `umkc_events@kansas_city` | 32 | 8 | 20% | campus_meeting 7, campus_admissions 1 |
| `vanderbilt_events@nashville` | 13 | 7 | 35% | campus_internal_audience 7 |
| `cmu_events@pittsburgh` | 14 | 4 | 22% | campus_admissions 4 |
| `northeastern_events@boston` | 13 | 4 | 24% | internal_only 1, campus_admissions 1, campus_career 1 |
| `nyu_events@nyc` | 5 | 4 | 44% | campus_meeting 2, campus_internal_audience 1, governance_meeting 1 |
| `okc_uco_events@oklahoma_city` | 22 | 3 | 12% | campus_internal_audience 2, campus_career 1 |
| `ucf_events@orlando` | 47 | 3 | 6% | internal_only 2, campus_admissions 1 |
| `rice_events@houston` | 67 | 2 | 3% | campus_admissions 2 |
| `berkeley_events@san_francisco` | 8 | 1 | 11% | campus_career 1 |
| `uc_events@cincinnati` | 4 | 1 | 20% | campus_career 1 |
| `unf_events@jacksonville` | 50 | 1 | 2% | campus_admissions 1 |
| `uw_events@seattle` | 57 | 1 | 2% | campus_academic_admin 1 |
| `emory_events@atlanta` | 38 | 0 | 0% |  |
| `gsu_events@atlanta` | 16 | 0 | 0% |  |
| `gwu_events@washington_dc` | 11 | 0 | 0% |  |
| `hfd_trinity_arts_events@hartford` | 2 | 0 | 0% |  |
| `pitt_events@pittsburgh` | 55 | 0 | 0% |  |
| `pvd_brown_events@providence` | 22 | 0 | 0% |  |
| `sacstate_events@sacramento` | 56 | 0 | 0% |  |
| `tampa_ut_events@tampa` | 6 | 0 | 0% |  |
| `towson_events@baltimore` | 33 | 0 | 0% |  |
| `ucr_events@riverside` | 165 | 0 | 0% |  |
| `ucsd_events@san_diego` | 65 | 0 | 0% |  |
| `umn_events@minneapolis` | 1 | 0 | 0% |  |
| `up_events@portland` | 28 | 0 | 0% |  |
| `uta_events@dallas` | 38 | 0 | 0% |  |
| `utdallas_events@dallas` | 19 | 0 | 0% |  |

<details><summary>Samples: kept vs held back</summary>

**`utaustin_events@austin`**
- ✕ UT Staff Toastmasters Club - Open House — _campus_meeting_
- ✕ "Escaping the Parent Trap: Reflecting on Family Relationships Through Film" SHARE Community Meeting ×2 — _campus_support_group_
- ✕ Financial Affairs Committee Meeting — _governance_meeting_
- ✕ "New Roots: Cultivating Black Mental Wellness" SHARE Community Meeting ×3 — _campus_support_group_
- ✓ Cannabis Recovery ×2
- ✓ Live and Learn in Europe this Summer!
- ✓ AHA BLS Provider (CPR) Certification Renewal

**`fiu_events@miami`**
- ✕ Spring: Official registration for degree-seeking students by assigned registration time and day ×22 — _campus_term_date_
- ✕ Teaching in the Age of AI: Fundamentals - Workshop ×2 — _campus_internal_audience_
- ✕ RPPTL Real Estate Meeting — _campus_meeting_
- ✕ FBA Firm Visit: Career & Internship Insights at Kozyak Tropin & Throckmorton — _campus_career_
- ✓ Join Us! 2026 FIU Festival of The Trees
- ✓ Paul O'Dette Lute Concert
- ✓ The Economic Effects of Party Power Centralization within China’s State-Owned Enterprises

**`bham_uab_events@birmingham`**
- ✕ QPR Gatekeeper Training for Suicide Prevention — _campus_internal_audience_
- ✕ Effective Communication and Respect — _campus_internal_audience_
- ✕ UAB Ophthalmology: Grand Rounds Lecture — _campus_academic_admin_
- ✕ Dissemination, Implementation, and Improvement Science Core (DIISC) Drop in Clinic — _campus_internal_audience_
- ✓ Nursing PhD Virtual Open House
- ✓ Holiday Happy Hour: Cocktails for Every Celebration
- ✓ Department of Biology: Fall Seminar Series ×3

**`clt_uncc_events@charlotte`**
- ✕ Writing Effective Prompts Gemini & Copilot for a Smarter To-Do List Workflow — _campus_internal_audience_
- ✕ Rock Climbing Night at the SAC ×5 — _campus_internal_audience_
- ✕ Youth Job Fair — _campus_career_
- ✕ Part 4: Creating Accessible Instructional Materials with AI ×2 — _campus_internal_audience_
- ✓ Yoga Under the Stars
- ✓ Every Thing That Grows ×2
- ✓ The Vagina Dialogues- Body Image Edition

**`sjsu_events@san_jose`**
- ✕ Adobe Portfolio - Create a professional multi-page website to showcase your digital skills and career ready sk — _campus_internal_audience_
- ✕ Searching for Research Articles & Utilizing SJSU Library Resources — _campus_internal_audience_
- ✕ Writing Workshop: Writing Concisely — _campus_internal_audience_
- ✕ Writing Workshop: Deconstructing the Prompt — _campus_internal_audience_
- ✓ Faculty Design Thinking Workshop
- ✓ Tech Movie Night: I, Robot
- ✓ Third Annual Running in Prayer Run & Prayer Circle

**`stanford_events@san_jose`**
- ✕ Anxiety Toolbox ×2 — _campus_internal_audience_
- ✕ Using AI to Find Sources — _campus_internal_audience_
- ✕ STVP Studio: Deconstruct → Reconstruct Featuring MILL — _internal_only_
- ✕ Introduction to Enverus — _internal_only_
- ✓ War, Sanctions and the Intimacy of Everyday Life
- ✓ Tracing What Remains: Memory, Place, and Chinese American Histories
- ✓ Branner Library Book & Map Exhibit - Water in the West ×3

**`ncsu_events@raleigh`**
- ✕ User-Friendly Communication ×2 — _campus_internal_audience_
- ✕ Writing a Teaching Philosophy In-Person Workshop — _campus_internal_audience_
- ✕ Study Abroad: Your Global Experience, Your Career Advantage — _campus_academic_admin_
- ✕ INFUSE'd Research Storytelling — _campus_internal_audience_
- ✓ Fall Chamber Singers and Instrumentalists Concert
- ✓ Intercultural Insights: Comparing the U.S., Spain & Latin America
- ✓ You Are Here Exhibition ×8

**`usc_events@los_angeles`**
- ✕ Trojan Talk with FIRY — _campus_career_
- ✕ AI & The University — _campus_internal_audience_
- ✕ Free Yoga Classes at the URC Fishbowl ×5 — _campus_internal_audience_
- ✕ Mindful Tree Tour — _campus_internal_audience_
- ✓ Data Are Made, Not Found: A Story of Politics, Power, and the Civil Servants Who Saved the US Census
- ✓ In Conversation with Danny Widener & Natalia Molina: Third Worlds Within: Multiethnic Movements and Transnatio
- ✓ “Is Nonfiction Dead?”: Answers to Burning Questions from the Publishing Post-Apocalypse

**`umkc_events@kansas_city`**
- ✕ Concrete Canoe Hull Design Meeting ×2 — _campus_meeting_
- ✕ Concrete Canoe Weekly Meeting ×3 — _campus_meeting_
- ✕ First Gen Celebration: First Gen Study Abroad info session — _campus_admissions_
- ✕ Concrete Canoe Aesthetics Meeting ×2 — _campus_meeting_
- ✓ Tau Beta Play
- ✓ Composers’ Guild Concert #3
- ✓ How to Not Drown / Book Club Meetup

**`vanderbilt_events@nashville`**
- ✕ WSTS Core Studio Workshop: Entering a Scholarly Conversation — _campus_internal_audience_
- ✕ French Conversation Hour — _campus_internal_audience_
- ✕ Mindfulness for Everyday Life 4-Week Workshop — _campus_internal_audience_
- ✕ German Conversation Hour — _campus_internal_audience_
- ✓ Studio VU Visiting Artist Fritz Horstman with Artist Lecture
- ✓ Vanderbilt Institute for Population and Public Health 20th Anniversary Celebration
- ✓ Native American and Indigenous Heritage Month Reception

**`cmu_events@pittsburgh`**
- ✕ Virtual Student-Led Campus Tour — _campus_admissions_
- ✕ Campus Visit (Info Session + Campus Tour) ×3 — _campus_admissions_
- ✓ Dismantling Internalized Ableism & The Art of Strategic Disclosure
- ✓ Music Theater/Acting Virtual Q&A
- ✓ Democracy Day Celebration

**`northeastern_events@boston`**
- ✕ Boston Graduate Fair - Fall 2026 — _internal_only_
- ✕ Northeastern University Graduate Fair: Unlock Your Double Husky Scholarship — _campus_admissions_
- ✕ Fusion Book Club Meeting — _campus_meeting_
- ✕ 2026 AIChE Annual Conference Student Recruitment Fair — _campus_career_
- ✓ The Center on Crime, Race, and Justice Presents: The David B. Schulman Distinguished Lecture Series – Navigati
- ✓ Daily Yoga ×8
- ✓ Yoga Nidra with Aromatherapy & Type a message •0. DIY Essential Oils

**`nyu_events@nyc`**
- ✕ NYU Strawberry Festival committee meeting — _governance_meeting_
- ✕ APO Eboard + Chapter + Pledge Class — _campus_meeting_
- ✕ Tips & Tricks for Interviewing — _campus_internal_audience_
- ✕ CANCELED: APO Eboard + Chapter + Pledge Class — _campus_meeting_
- ✓ 2026 MFA Project Space
- ✓ BMI Sisters Book Club
- ✓ Mentorship Oud Making

**`okc_uco_events@oklahoma_city`**
- ✕ Wednesday Wellness Walk ×2 — _campus_internal_audience_
- ✕ PGA Golf Management Career & Internship Fair — _campus_career_
- ✓ Chamber Orchestra in Concert
- ✓ “Virginia Sitzes: Electric Networks” Exhibition Reception
- ✓ Ceramics Workshop

**`ucf_events@orlando`**
- ✕ Writing Lab: Admission Essays — _campus_admissions_
- ✕ 3D Printing Basics: From Digital to Physical — _internal_only_
- ✕ Reduce Obstacles, Increase Engagement: An Introduction to Open Education — _internal_only_
- ✓ Book Nook at Art Knight!
- ✓ Fall 2026 Urban and Regional Planning Distinguished Lecture Series: Paving the Way for the Next Bell: The Coll
- ✓ University Orchestra Concert

**`rice_events@houston`**
- ✕ Graduate Student Ambassador Campus Tour (In-person) — _campus_admissions_
- ✕ Rice Global Paris Summer Program: Info Session and Course Fair — _campus_admissions_
- ✓ Rice University Football vs Tulane - Homecoming & Alumni Weekend
- ✓ Jewish Book and Arts Festival, Community Reading
- ✓ Holistic Garden Tour

**`berkeley_events@san_francisco`**
- ✕ [BCLT] 1L Tech & IP Recruiting Fair — _campus_career_
- ✓ Day of the Dead Celebration (Dia de los Muertos) ×2
- ✓ Tendon thread feat. Tanya Lukin Linklater
- ✓ CJ Week: Eco-Optimism Knowledge Share and Zine Workshop

**`uc_events@cincinnati`**
- ✕ U.S. Customs and Border Protection Virtual Career Expo – November 3rd — _campus_career_
- ✓ Día de los Muertos Celebration
- ✓ Commuter Student Lounge: Winter Safety & Preparedness Fair ×2
- ✓ CCM Composers Concert: A View From The Edge

**`unf_events@jacksonville`**
- ✕ Illuminate Your Future: Ed.D. Info Sessions — _campus_admissions_
- ✓ Winter Wind Chamber Music
- ✓ String Chamber Music Recital
- ✓ Mud in Motion: Wheel Thrown Pottery for Beginners at MOCA ×2

**`uw_events@seattle`**
- ✕ Laboratory Medicine Grand Rounds: Thao Truong, PhD, D(ABMM) - What's On Our Plate Today? Automating Microbiolo — _campus_academic_admin_
- ✓ UWCFD Lunch & Learn: The Great Outdoors
- ✓ Scan Design Distinguished Visiting Professor Lecture: UNLOVED BUILDINGS Transformation and reuse as the next s
- ✓ UW Traumatic Brain Injury - Behavioral Health ECHO

**`emory_events@atlanta`**
- ✓ Bate-Papo ×2
- ✓ Why Anthropology Matters speaker series - for Global Health
- ✓ RISE (Resilience, Illness, Stories, Empathy) Bookclub
- ✓ Emory Emergency Notification System Test
- ✓ Interpretation and Engagement: Narrative Wisdom and African Arts

**`gsu_events@atlanta`**
- ✓ The Democracy Fest: Leading With Ethical Decisions
- ✓ Backpack to Belonging – One Step at a Time
- ✓ Shaping AI for the Public Good: Lecture by David A. Patterson
- ✓ Library Game Day
- ✓ 29th Annual Juried Student Exhibition Opening Reception

**`gwu_events@washington_dc`**
- ✓ National Symphony Orchestra: The Nutcracker & Cinderella ×2
- ✓ Beyond Discovery: Archaeology, Heritage and Partnership in the Galilee
- ✓ Art Capital: Museum Politics and the Making of the Louvre Abu Dhabi
- ✓ National Symphony Orchestra: Serenades & Simple Songs ×2
- ✓ Film Screening & Panel: The President and the Dragon

**`hfd_trinity_arts_events@hartford`**
- ✓ Sanjuro (Samurai Sundays: Remembering Tatsuya Nakadai)
- ✓ Met Opera Live in HD:Samson et Dalila

**`pitt_events@pittsburgh`**
- ✓ Heinz Chapel Choir Holiday Concert #2
- ✓ Senhora Liberdade: 19th-Century Afro-Brazilians Defy Slavery
- ✓ Suppression and Expression: A Concert Exploring Art, Mental Health, and Intergenerational Trauma
- ✓ Class Piano Fall 2026 Recital
- ✓ 56th Jazz Seminar Kickoff Performance

**`pvd_brown_events@providence`**
- ✓ Art at Watson Presents — Diagnósticos: technology, information and self ×2
- ✓ Using A.I. as an on-ramp to computer programming
- ✓ Words as Weapons: How Wikipedia Became a Battlefield for Cultural Heritage
- ✓ Practical AI: Using Gemini’s “Deep Research” to Contextualize your Research Project
- ✓ PPE Workshop: Nico Voigtlaender, De-Polarizing Politics: Jesuit-Educated MPs in the French Third Republic

**`sacstate_events@sacramento`**
- ✓ "Conversations From the Rack"
- ✓ Sacramento State Volleyball vs UC Irvine - Club Sports Night
- ✓ Football Watch Party - Hornets vs. Central Michigan
- ✓ Student Recital: Chet Chwalik, jazz piano
- ✓ Friends of the University Library Book Bin ×2

**`tampa_ut_events@tampa`**
- ✓ Tampa Animation Festival
- ✓ Railroad to River: University of Tampa in Hidden View
- ✓ Men's Basketball vs Beacon
- ✓ Kaledioscope: The Spirit within the Geometry of Wind and Water
- ✓ Women's Basketball vs Ave Maria

**`towson_events@baltimore`**
- ✓ STEM for ALL Lecture Series: The Long-Gone Ocean Beneath Baltimore: The Story of the Lapetus and the Appalachi
- ✓ Entrepreneurship Bootcamp: AI for Founders
- ✓ Exhibition: Encounter 해후(邂逅) ×8
- ✓ Planetarium Event: The Secret Lives of Stars
- ✓ BTU Partnership Awards

**`ucr_events@riverside`**
- ✓ UC Riverside Women's Basketball vs Idaho State
- ✓ SCUBA Open Water Certification ×5
- ✓ Student Performance and Composition (Florence Bayz Music Series)
- ✓ UCR Orchestra and Wind Ensemble
- ✓ Ian Dicke & Matt McBane: Patterns and Drones

**`ucsd_events@san_diego`**
- ✓ Library Milestones / Exhibit ×8
- ✓ Writing for TV and Theatre: Alumnae on Writing Your Way In
- ✓ United States Poets Laureate / Exhibit ×8
- ✓ The Human Condition: An Exploration of Art & Literature / Exhibit ×8
- ✓ Triton Alumni and Welcome Center Tours ×2

**`umn_events@minneapolis`**
- ✓ Through the Looking Lens / Coffman Art Gallery / Coffman Memorial Union

**`up_events@portland`**
- ✓ University of Portland Women's Basketball vs South Carolina State
- ✓ UP Orchestra Concert
- ✓ University of Portland Men's Basketball vs Lamar
- ✓ University of Portland Men's Basketball vs East Texas A&M
- ✓ University of Portland Women's Basketball vs Stanford

**`uta_events@dallas`**
- ✓ UTA Annual Fall Piano Contest & Honors Recital
- ✓ Abigail Jennings Viola Recital
- ✓ Frozen Frontiers: 500 Years of Mapping Antarctica Exhibit ×8
- ✓ Clavier Recital
- ✓ The Mystery Continues: Amelia Earhart in UTA Special Collections Mini-Exhibit

**`utdallas_events@dallas`**
- ✓ MEMBER EVENT: Twisted, Plaited, Sculpted: Collection of the Carl & Marilynn Thoma Foundation - Member Receptio
- ✓ LOLUTD x UTD Esports League of Legends Worlds Finals Watch Party
- ✓ Thanks Day Celebration 2026
- ✓ How Blood Can Now Tell Us About Brain Health: Integration and Implementation of Blood Biomarkers for Alzheimer
- ✓ Nebula Gallery Presents: Dangerous Beauty ×8

</details>

### Library (51 units · 9,321 kept · 206 held back)

| Unit | Kept | Held | Share held | Top rules |
|---|---|---|---|---|
| `sjpl_events@san_jose` | 391 | 56 | 13% | appointment 56 |
| `wccls_events@portland` | 200 | 20 | 9% | appointment 17, closure 3 |
| `hfd_public_library_events@hartford` | 167 | 19 | 10% | appointment 11, proctored_testing 8 |
| `phoenix_public_library_events@phoenix` | 252 | 17 | 6% | closure 17 |
| `lvccld_events@las_vegas` | 355 | 15 | 4% | proctored_testing 14, appointment 1 |
| `clt_cmlibrary_events@charlotte` | 352 | 12 | 3% | appointment 12 |
| `pvd_east_providence_library_events@providence` | 80 | 11 | 12% | appointment 11 |
| `bpl_events@boston` | 363 | 7 | 2% | appointment 7 |
| `kcls_events@seattle` | 208 | 6 | 3% | office_hours 5, appointment 1 |
| `sccl_events@san_jose` | 128 | 6 | 4% | closure 6 |
| `afpl_events@atlanta` | 305 | 5 | 2% | proctored_testing 5 |
| `spl_events@seattle` | 141 | 5 | 3% | office_hours 4, closure 1 |
| `chipublib_events@chicago` | 920 | 4 | 0% | office_hours 4 |
| `corona_library_events@riverside` | 111 | 3 | 3% | closure 3 |
| `jocolibrary_events@kansas_city` | 80 | 3 | 4% | appointment 2, governance_meeting 1 |
| `ocls_events@orlando` | 629 | 3 | 0% | office_hours 3 |
| `bham_hoover_library_events@birmingham` | 21 | 2 | 9% | appointment 2 |
| `norfolk_library_events@hampton_roads` | 56 | 2 | 3% | closure 2 |
| `oakland_library_events@san_francisco` | 148 | 2 | 1% | appointment 2 |
| `westerville_library_events@columbus` | 38 | 2 | 5% | closure 1, governance_meeting 1 |
| `hcpl_events@houston` | 250 | 1 | 0% | appointment 1 |
| `heights_libraries_events@cleveland` | 97 | 1 | 1% | governance_meeting 1 |
| `indypl_events@indianapolis` | 148 | 1 | 1% | appointment 1 |
| `pvd_cranston_library_events@providence` | 104 | 1 | 1% | governance_meeting 1 |
| `pvd_pawtucket_library_events@providence` | 49 | 1 | 2% | governance_meeting 1 |
| `slpl_events@st_louis` | 132 | 1 | 1% | closure 1 |
| `arapahoe_library_events@denver` | 119 | 0 | 0% |  |
| `bham_bpl_events@birmingham` | 100 | 0 | 0% |  |
| `bham_homewood_library_events@birmingham` | 25 | 0 | 0% |  |
| `ccpl_events@cleveland` | 211 | 0 | 0% |  |
| `chandler_library_events@phoenix` | 120 | 0 | 0% |  |
| `chesapeake_library_events@hampton_roads` | 40 | 0 | 0% |  |
| `chpl_events@cincinnati` | 377 | 0 | 0% |  |
| `dcpl_events@washington_dc` | 195 | 0 | 0% |  |
| `dekalb_library_events@atlanta` | 109 | 0 | 0% |  |
| `grandview_library_events@columbus` | 7 | 0 | 0% |  |
| `grpl_events@grand_rapids` | 45 | 0 | 0% |  |
| `hclib_events@minneapolis` | 213 | 0 | 0% |  |
| `henrico_library_events@richmond` | 106 | 0 | 0% |  |
| `jax_library_events@jacksonville` | 125 | 0 | 0% |  |
| `jeffco_library_events@denver` | 140 | 0 | 0% |  |
| `kdl_events@grand_rapids` | 106 | 0 | 0% |  |
| `mdpls_events@miami` | 448 | 0 | 0% |  |
| `mpl_events@milwaukee` | 187 | 0 | 0% |  |
| `pratt_library_events@baltimore` | 144 | 0 | 0% |  |
| `rpl_events@richmond` | 31 | 0 | 0% |  |
| `sacpl_events@sacramento` | 99 | 0 | 0% |  |
| `sdcl_events@san_diego` | 220 | 0 | 0% |  |
| `slcolibrary_events@salt_lake_city` | 167 | 0 | 0% |  |
| `slcpl_events@salt_lake_city` | 89 | 0 | 0% |  |
| `tampa_hcplc_events@tampa` | 173 | 0 | 0% |  |

<details><summary>Samples: kept vs held back</summary>

**`sjpl_events@san_jose`**
- ✕ 1-on-1 Tech Help by Appointment — _appointment_
- ✕ 1 on 1 Tech Assistance (In-Person) — _appointment_
- ✕ Computer Assembly Workshop [by Appointment] ×4 — _appointment_
- ✕ One-on-One Computer Help with our Tech Mentor ×2 — _appointment_
- ✓ OneInMath: Math Program for K-3rd at Evergreen Library
- ✓ Basic English 2 Class
- ✓ Origami for Kids

**`wccls_events@portland`**
- ✕ Digital Navigator – One-on-One Tech Help/ Navegador Digital – Apoyo Uno a Uno ×4 — _appointment_
- ✕ Digital Navigator – One-on-One Tech Help ×4 — _appointment_
- ✕ Digital Navigator: One-on-One Tech Help ×3 — _appointment_
- ✕ Early Closure - Veterans Day — _closure_
- ✓ Music & Movement in Mandarin / 儿童中文音乐律动课
- ✓ Tiny Tots ×2
- ✓ Library Book Group

**`hfd_public_library_events@hartford`**
- ✕ 1-on-1 Business Advising with CEDF - ×2 — _appointment_
- ✕ Placement and Progress Testing for Library Programs — _proctored_testing_
- ✕ Pearson Test Center testing ×3 — _proctored_testing_
- ✕ One-on-One Financial Coaching (By Appointment Only) ×8 — _appointment_
- ✓ English for All ×2
- ✓ Support Group for Foster Care & Abandonment
- ✓ English Learners Success ×3

**`phoenix_public_library_events@phoenix`**
- ✕ Library closed for Veterans Day ×17 — _closure_
- ✓ Mahjong Meet Up ×2
- ✓ Teen Tuesday
- ✓ Play SPOT

**`lvccld_events@las_vegas`**
- ✕ ESL Pre-test Session ×4 — _proctored_testing_
- ✕ Pre-Testing For Spring Valley ESL Classes ×3 — _proctored_testing_
- ✕ Pre-Testing For Sahara West ESL Classes ×3 — _proctored_testing_
- ✕ Device Advice: One on One Tech Help — _appointment_
- ✓ Community Care Pop-Up
- ✓ Homework Help
- ✓ Fine Arts Friday

**`clt_cmlibrary_events@charlotte`**
- ✕ My Next Step for Teens: Ask A Librarian 1-on-1 — _appointment_
- ✕ Tutores de Tecnología: Sesión de apoyo 1 a 1 — _appointment_
- ✕ Arabic Tutoring 1-on-1 — _appointment_
- ✕ Resume Help Desk 1:1 — _appointment_
- ✓ Spawn Point! Video Game Club ×2
- ✓ Story Explorers
- ✓ Teen Crafternoon: Hunger Games Themed Jewelry Making

**`pvd_east_providence_library_events@providence`**
- ✕ One on One Tech Help ×11 — _appointment_
- ✓ Teen Kinusaiga
- ✓ Teen Zen Sesh
- ✓ Kanopy Documentary Screening - Your Attention Please

**`bpl_events@boston`**
- ✕ Tech Help (By Appointment) ×2 — _appointment_
- ✕ Tech Help by Appointment ×5 — _appointment_
- ✓ Storytelling: "On the Corner" ×2
- ✓ The Art of Everyday Things: Age Strong Painting Workshop
- ✓ Car Care Basics with Sally Dawson

**`kcls_events@seattle`**
- ✕ King County Parks and Recreation Office Hours — _office_hours_
- ✕ King County Local Services: Community Vans Office Hours — _office_hours_
- ✕ In-person Medicare 1:1 Counseling (Appointment Only) — _appointment_
- ✕ King County Department of Local Services Office Hours ×3 — _office_hours_
- ✓ English Language Learners (ELL) Class ×2
- ✓ Fiber Arts Meetup
- ✓ Beginning Crochet for Teens and Adults

**`sccl_events@san_jose`**
- ✕ Milpitas Library Closed for Veterans Day — _closure_
- ✕ Saratoga Library Closed for Veterans Day — _closure_
- ✕ Los Altos Library Closed for Veterans Day — _closure_
- ✕ Campbell Library Closed for Veterans Day — _closure_
- ✓ Adult Nonfiction Book Discussion: Nothing to Envy: Ordinary Lives in North Korea
- ✓ Knitting Club for Kids
- ✓ 中/英文雙語說故事時間 Mandarin/English Bilingual Family Storytime

**`afpl_events@atlanta`**
- ✕ GED Testing - Southeast Library ×3 — _proctored_testing_
- ✕ GED Testing - Central Library ×2 — _proctored_testing_
- ✓ Metro Kids' Club ×2
- ✓ Friday Fun Storytime
- ✓ Game Day for Tweens and Teens.

**`spl_events@seattle`**
- ✕ Office Hours with Department of Neighborhoods / Sesiones con el Departamento de Vecindarios ×2 — _office_hours_
- ✕ Library Closed in observance of Veterans Day — _closure_
- ✕ Office Hours with Department of Neighborhoods ×2 — _office_hours_
- ✓ Garden Hotline Presents: Growing Oyster Mushrooms
- ✓ Toddler Play Group ×4
- ✓ Connect & Assist with Seattle Public Utilities

**`chipublib_events@chicago`**
- ✕ Teen Librarian Office Hours ×4 — _office_hours_
- ✓ Teen Film Series- The Hunger Games: Mockingjay Part 1 (2014)
- ✓ Mather's Grow-It-Together Garden Club In-Person Viewing
- ✓ Weekend LEGO® Club

**`corona_library_events@riverside`**
- ✕ Closed in Observance of Veterans Day — _closure_
- ✕ Closed in Observance of Thanksgiving Holiday ×2 — _closure_
- ✓ Adaptive Story Hour ×2
- ✓ ESL Speaking & Listening Skills ×5
- ✓ Mystery Book Club ×2

**`jocolibrary_events@kansas_city`**
- ✕ One-on-One Basic Genealogy Help ×2 — _appointment_
- ✕ Johnson County Library Board Meeting — _governance_meeting_
- ✓ Gather at the Table
- ✓ Baby Storytime ×8
- ✓ Mystery Novel Escape Room for Teens ×3

**`ocls_events@orlando`**
- ✕ District 10 Office Hours ×2 — _office_hours_
- ✕ District 35 Office Hours — _office_hours_
- ✓ Salem, 1692
- ✓ Traditional Mahjong Club
- ✓ Video: Shooting Video with DSLR Camera

**`bham_hoover_library_events@birmingham`**
- ✕ One-on-One Tech Help ×2 — _appointment_
- ✓ Kids D&D
- ✓ Libby Meet & Greet
- ✓ Teen D&D

**`norfolk_library_events@hampton_roads`**
- ✕ Holiday Closure - Election Day — _closure_
- ✕ Holiday Closure - Veterans Day — _closure_
- ✓ Upcycle Fest with Keep Norfolk Beautiful
- ✓ Game Night @ Lafayette ×2
- ✓ Graphic Novel Society

**`oakland_library_events@san_francisco`**
- ✕ Neighborhood Business Assistance (by appointment only) ×2 — _appointment_
- ✓ Drop-In Computer Literacy and Adult Literacy Support
- ✓ TEENS & TWEENS! Pokemon: Trading Card Game Club ×2
- ✓ Eastside Teen Radio

**`westerville_library_events@columbus`**
- ✕ Closed for Staff Development Day — _closure_
- ✕ Finance & Facilities: Board Committee Meeting — _governance_meeting_
- ✓ Homework Help ×2
- ✓ Read Between the Wines: Group 5
- ✓ Baby Storytime ×3

**`hcpl_events@houston`**
- ✕ Cricut 1 on 1 Orientation — _appointment_
- ✓ Blueprint Series for Medicare, Medicaid and Social Security Part 3
- ✓ ESL Level 1/ Clase de Ingles Nivel 1
- ✓ Pre-K+ Storytime (for Walkers & Talkers) ×2

**`heights_libraries_events@cleveland`**
- ✕ Committee Meeting — _governance_meeting_
- ✓ ASPIRE ESOL Classes (Noble) ×2
- ✓ Coventry Branch Centennial Celebration
- ✓ Afternoon Snack at the Library ×7

**`indypl_events@indianapolis`**
- ✕ Ask a CPA: One-on-One Nonprofit Finance Appointments (Register on Eventbrite) — _appointment_
- ✓ Haitian Creole Conversation Circle
- ✓ Tot Art at Southport
- ✓ Chess for Beginners

**`pvd_cranston_library_events@providence`**
- ✕ Cranston Public Library Board of Trustees Meeting @ Central — _governance_meeting_
- ✓ Friendship Bracelets @ William Hall
- ✓ Hidden in the Stacks Book Group @ Central
- ✓ Chair Yoga @ Auburn ×2

**`pvd_pawtucket_library_events@providence`**
- ✕ Board of Trustees — _governance_meeting_
- ✓ Storied Lives Book Club
- ✓ Spanish Conversation Class
- ✓ Women's Conversation Circle

**`slpl_events@st_louis`**
- ✕ SLPL Closed — _closure_
- ✓ UNO & Card Games
- ✓ Balance and Revitalize
- ✓ Central Library Architectural Tours ×6

**`arapahoe_library_events@denver`**
- ✓ Explore and Connect with Your Library Card
- ✓ May Movie Night
- ✓ Southglenn Teen Café
- ✓ Clases de Computación para Adultos en Eloise May ×2
- ✓ Literacy Spot with and Early Literacy Specialist ×8

**`bham_bpl_events@birmingham`**
- ✓ Chair Aerobics with Myra Tarver
- ✓ The Morning Lineup ×2
- ✓ Stitch & Chat ×2
- ✓ Community Resource Day
- ✓ Bards and Brews

**`bham_homewood_library_events@birmingham`**
- ✓ Homeschool Hour: S.T.E.A.M. Powered!
- ✓ Google Slides
- ✓ Storypalooza
- ✓ Pretend Play Stations
- ✓ Stay and Play

**`ccpl_events@cleveland`**
- ✓ Google Docs Basics ★
- ✓ Bookmarks & Body Bags
- ✓ Cooking with Kids
- ✓ Career Planning for College
- ✓ Family Storytime ×8

**`chandler_library_events@phoenix`**
- ✓ Teen Scene
- ✓ Intro to American Sign Language ×3
- ✓ Peer Tutoring ×3
- ✓ Preschool Time ×2
- ✓ Teeny, Tiny, Polymer Clay Figurines for Teens

**`chesapeake_library_events@hampton_roads`**
- ✓ Tech for Beginners
- ✓ Medicare 101
- ✓ Dungeons & Dragons
- ✓ Move and Groove ×2
- ✓ BINGO for a Cause

**`chpl_events@cincinnati`**
- ✓ Ready, Set, Race: Hot Wheels!
- ✓ Resource Connect: Workforce Development
- ✓ Tween Hangout: Switch Games!
- ✓ After School Gaming
- ✓ ESL Reading Discussion Group

**`dcpl_events@washington_dc`**
- ✓ Game ON: Adults & Seniors
- ✓ Gentle Yoga with Beth Lawrence
- ✓ Black Studies Book Club
- ✓ Tech Help Tuesdays
- ✓ Historic Easements: What Homeowners Need to Know

**`dekalb_library_events@atlanta`**
- ✓ Mind Bubble Homework Help: Grades K-5th ×2
- ✓ Notary Service
- ✓ Tech Help for Beginners
- ✓ Mind Bubble Homework Help: Grades 6th-8th ×2
- ✓ Kids Sewing

**`grandview_library_events@columbus`**
- ✓ Story Times: Music & Movement
- ✓ Family Story Time - Evening Edition
- ✓ Grandview Library Writers Group
- ✓ Story Time: Tales for Toddlers
- ✓ CANCELLED: Armstrong & Flight

**`grpl_events@grand_rapids`**
- ✓ Mystery Book Club / Van Belkum
- ✓ Crafternoons / Madison Square
- ✓ Indigenous Fashion Presentation with Bead and Powwow Supply
- ✓ Encore!
- ✓ Medicare 101 / Seymour

**`hclib_events@minneapolis`**
- ✓ Brookdale Library Chess Club ×2
- ✓ A Novel in November ×2
- ✓ Stitched Loon Ornament ×3
- ✓ Seed Circles
- ✓ Give a Hoot

**`henrico_library_events@richmond`**
- ✓ Historically Speaking: George C. Marshall, a Life of Service
- ✓ READ Out Loud Book Group ×2
- ✓ Microsoft PowerPoint
- ✓ Virtual Author Event: Reclaiming Your Inner Wisdom: Sacred Indigenous Teachings with Asha Frost
- ✓ Understanding Canine Body Language with the Richmond SPCA

**`jax_library_events@jacksonville`**
- ✓ Decide and Conquer
- ✓ Lego Freestyle
- ✓ Games & Fandoms ×6
- ✓ Smart Spending
- ✓ Ex Libris Zine Collab

**`jeffco_library_events@denver`**
- ✓ Library for All: Interactive Program for Adults with Disabilities ×2
- ✓ Kids Club ×2
- ✓ Create Space Tours: Diwali
- ✓ Writing the Novel: From Seed to Story
- ✓ Hard Times Writing Workshop

**`kdl_events@grand_rapids`**
- ✓ Bookmobile Visit / Bright Beginnings Playgroup at Kelloggsville ECC
- ✓ Alpine Ave. Book Discussion
- ✓ My Life in the FBI
- ✓ Bookmobile Visit / Kingsbury Apartments
- ✓ Fall Craft Party

**`mdpls_events@miami`**
- ✓ Crochet and Connections
- ✓ Everglades Exploration 101
- ✓ Take and Make Craft Kits
- ✓ Friday Unplugged: Teen Spot
- ✓ Learn to Speak Haitian Creole

**`mpl_events@milwaukee`**
- ✓ Pop-Art Paint & Sip
- ✓ Ready Readers Book Club
- ✓ Mini Makers ×2
- ✓ Mind your Mending: Clothes Repair
- ✓ Mom 2 Mom Support Group

**`pratt_library_events@baltimore`**
- ✓ Manga Drawing Lessons
- ✓ Watercolor Pencil Art
- ✓ Turkey Tales and Crafts
- ✓ Shut Up & Read at Ovenbird Highlandtown
- ✓ Teen Board & Card Game Night

**`rpl_events@richmond`**
- ✓ Future Ready: Social Capital Maxxing
- ✓ Preschool Storytime ×2
- ✓ Art Club
- ✓ Can You Beat A Librarian Trivia: At Sine Irish Pub **UPDATED TIME**
- ✓ Teen Anime Manga Association (TAMA): Origami Maple Leaves

**`sacpl_events@sacramento`**
- ✓ Hora de Cuentos Bilingüe - Bilingual Storytime
- ✓ Melissa King: Enters the Chat
- ✓ STEAM: Build with LEGO Bricks
- ✓ Vote Center ×8
- ✓ Adult Space: Games

**`sdcl_events@san_diego`**
- ✓ ESL English Language Class: Beginning ×3
- ✓ Chess Club ×2
- ✓ Pre-K Play
- ✓ Sewing Group
- ✓ Drop-In Tech Help ×3

**`slcolibrary_events@salt_lake_city`**
- ✓ Teen Time
- ✓ Stories and Play
- ✓ Music and Movement
- ✓ Dia de los Muertos Storytime
- ✓ Open Art Hour

**`slcpl_events@salt_lake_city`**
- ✓ College Application Clinics ×2
- ✓ Poetry Writing Group ×2
- ✓ Alphabet Soup ×2
- ✓ Tween Coding for Gamers ×2
- ✓ Candlelit Yoga

**`tampa_hcplc_events@tampa`**
- ✓ SMART Journaling
- ✓ History of Decoupage with a Confetti Coaster
- ✓ Joyful Jewelry Making
- ✓ Library Resources for Your Job Search for Teens
- ✓ Conversation Corner

</details>

### City & Civic Calendars (101 units · 4,547 kept · 10 held back)

| Unit | Kept | Held | Share held | Top rules |
|---|---|---|---|---|
| `mprb_events@minneapolis` | 22 | 4 | 15% | governance_meeting 4 |
| `seattle_city_events@seattle` | 84 | 2 | 2% | governance_meeting 2 |
| `creative_alliance_events@baltimore` | 72 | 1 | 1% | office_hours 1 |
| `fairytale_town_events@sacramento` | 21 | 1 | 5% | closure 1 |
| `nyc_permitted_events@nyc` | 195 | 1 | 1% | closure 1 |
| `scottsdale_city_events@phoenix` | 8 | 1 | 11% | governance_meeting 1 |
| `alamodome@san_antonio` | 11 | 0 | 0% |  |
| `atlanta_botanical_garden@atlanta` | 28 | 0 | 0% |  |
| `austin_parks_foundation_events@austin` | 18 | 0 | 0% |  |
| `balboa_park_events@san_diego` | 47 | 0 | 0% |  |
| `baltimore_county_volunteer@baltimore` | 16 | 0 | 0% |  |
| `bartrams_garden_events@philadelphia` | 14 | 0 | 0% |  |
| `bayfront_park_miami@miami` | 3 | 0 | 0% |  |
| `bc_athletics@boston` | 21 | 0 | 0% |  |
| `brackenridge_park_events@san_antonio` | 18 | 0 | 0% |  |
| `bu_athletics@boston` | 33 | 0 | 0% |  |
| `buffalo_bayou_events@houston` | 27 | 0 | 0% |  |
| `cap_city_comedy@austin` | 101 | 0 | 0% |  |
| `carnegie_museums_events@pittsburgh` | 21 | 0 | 0% |  |
| `carver_cultural_center@san_antonio` | 15 | 0 | 0% |  |
| `cbu_athletics@riverside` | 19 | 0 | 0% |  |
| `cedar_cultural_center@minneapolis` | 41 | 0 | 0% |  |
| `challenge_trivia_kansas_city@kansas_city` | 18 | 0 | 0% |  |
| `challenge_trivia_okc@oklahoma_city` | 39 | 0 | 0% |  |
| `chicago_park_adult_classes@chicago` | 62 | 0 | 0% |  |
| `chicago_park_adult_leagues@chicago` | 4 | 0 | 0% |  |
| `chicago_park_events@chicago` | 236 | 0 | 0% |  |
| `chicago_park_permits@chicago` | 32 | 0 | 0% |  |
| `clt_cmpd_community_events@charlotte` | 139 | 0 | 0% |  |
| `columbus_commons@columbus` | 14 | 0 | 0% |  |
| `dallas_arboretum@dallas` | 10 | 0 | 0% |  |
| `dallas_parks_events@dallas` | 33 | 0 | 0% |  |
| `desert_botanical_garden_events@phoenix` | 59 | 0 | 0% |  |
| `downtown_baltimore_events@baltimore` | 33 | 0 | 0% |  |
| `downtown_boston_events@boston` | 73 | 0 | 0% |  |
| `downtown_dallas_events@dallas` | 103 | 0 | 0% |  |
| `downtown_seattle_events@seattle` | 9 | 0 | 0% |  |
| `earshot_jazz@seattle` | 256 | 0 | 0% |  |
| `folly_theater@kansas_city` | 45 | 0 | 0% |  |
| `ford_field@detroit` | 16 | 0 | 0% |  |
| `gcu_athletics@phoenix` | 28 | 0 | 0% |  |
| `gggp_events@san_francisco` | 21 | 0 | 0% |  |
| `heb_center@austin` | 51 | 0 | 0% |  |
| `hfd_ct_museum_history@hartford` | 30 | 0 | 0% |  |
| `hfd_hartford_hawks@hartford` | 14 | 0 | 0% |  |
| `hfd_mark_twain_house@hartford` | 8 | 0 | 0% |  |
| `hfd_trinity_bantams@hartford` | 36 | 0 | 0% |  |
| `houston_arboretum_events@houston` | 38 | 0 | 0% |  |
| `ju_athletics@jacksonville` | 23 | 0 | 0% |  |
| `kc_roos_athletics@kansas_city` | 21 | 0 | 0% |  |
| `lan_su_garden@portland` | 39 | 0 | 0% |  |
| `levy_park_events@houston` | 56 | 0 | 0% |  |
| `lewis_ginter_events@richmond` | 38 | 0 | 0% |  |
| `luma_the_made@san_francisco` | 17 | 0 | 0% |  |
| `luma_zoma_house@minneapolis` | 3 | 0 | 0% |  |
| `marcus_center@milwaukee` | 28 | 0 | 0% |  |
| `memorial_park_events@houston` | 21 | 0 | 0% |  |
| `memphis_meddlesome@memphis` | 28 | 0 | 0% |  |
| `memphis_overton_park_shell@memphis` | 7 | 0 | 0% |  |
| `memphis_river_parks@memphis` | 9 | 0 | 0% |  |
| `memphis_wiseacre@memphis` | 26 | 0 | 0% |  |
| `mesa_arts_center@phoenix` | 62 | 0 | 0% |  |
| `mo_new_liquor_licenses_kc@kansas_city` | 14 | 0 | 0% |  |
| `montalvo_arts@san_jose` | 4 | 0 | 0% |  |
| `montgomery_volunteer@washington_dc` | 35 | 0 | 0% |  |
| `mount_vernon_triangle_events@washington_dc` | 11 | 0 | 0% |  |
| `mpls_downtown_events@minneapolis` | 76 | 0 | 0% |  |
| `ncmns_events@raleigh` | 60 | 0 | 0% |  |
| `notoriety_live@las_vegas` | 5 | 0 | 0% |  |
| `now_playing_utah@salt_lake_city` | 275 | 0 | 0% |  |
| `nyc_parks_events@nyc` | 447 | 0 | 0% |  |
| `okc_cowboy_museum@oklahoma_city` | 10 | 0 | 0% |  |
| `okc_ocu_athletics@oklahoma_city` | 15 | 0 | 0% |  |
| `okc_science_museum@oklahoma_city` | 5 | 0 | 0% |  |
| `orlando_museum_of_art@orlando` | 30 | 0 | 0% |  |
| `orlando_restaurant_openings@orlando` | 7 | 0 | 0% |  |
| `pearl_events@san_antonio` | 22 | 0 | 0% |  |
| `piedmont_park_events@atlanta` | 22 | 0 | 0% |  |
| `pittsburgh_parks_events@pittsburgh` | 9 | 0 | 0% |  |
| `portland_art_museum@portland` | 59 | 0 | 0% |  |
| `portland_farmers_market@portland` | 18 | 0 | 0% |  |
| `pvd_friars_athletics@providence` | 30 | 0 | 0% |  |
| `pvd_ppac@providence` | 24 | 0 | 0% |  |
| `raleigh_special_events@raleigh` | 16 | 0 | 0% |  |
| `redlands_athletics@riverside` | 15 | 0 | 0% |  |
| `rice_athletics@houston` | 22 | 0 | 0% |  |
| `rivers_of_steel_events@pittsburgh` | 3 | 0 | 0% |  |
| `sacramento_business_openings@sacramento` | 23 | 0 | 0% |  |
| `schottenstein_center@columbus` | 59 | 0 | 0% |  |
| `seven_venues_norfolk@hampton_roads` | 65 | 0 | 0% |  |
| `sf_recpark_events@san_francisco` | 9 | 0 | 0% |  |
| `slu_athletics@st_louis` | 13 | 0 | 0% |  |
| `smithsonian_events@washington_dc` | 205 | 0 | 0% |  |
| `songbyrd_dc@washington_dc` | 39 | 0 | 0% |  |
| `tampa_downtown_events@tampa` | 24 | 0 | 0% |  |
| `td_garden@boston` | 95 | 0 | 0% |  |
| `uwkc_volunteer@seattle` | 14 | 0 | 0% |  |
| `uwsa_volunteer@san_antonio` | 25 | 0 | 0% |  |
| `virginia_zoo_events@hampton_roads` | 35 | 0 | 0% |  |
| `visit_ballard_events@seattle` | 81 | 0 | 0% |  |
| `witte_museum_events@san_antonio` | 6 | 0 | 0% |  |

<details><summary>Samples: kept vs held back</summary>

**`mprb_events@minneapolis`**
- ✕ North Mississippi Regional Park Plan Community Advisory Committee Meeting — _governance_meeting_
- ✕ Board Meeting ×3 — _governance_meeting_
- ✓ Solomon Park Off-Leash Recreation Area Community Open House #1
- ✓ Solomon Park Off-Leash Recreation Area Community Open House #2
- ✓ North Loop Service Saturdays

**`seattle_city_events@seattle`**
- ✕ Community Surveillance Working Group Meeting — _governance_meeting_
- ✕ Pioneer Square Preservation Board Meeting — _governance_meeting_
- ✓ Daybreak Community & Land Tending ×4
- ✓ Seattle Forest Week and Green Lake!
- ✓ Open Adoption Hours ×8

**`creative_alliance_events@baltimore`**
- ✕ Baker Artist Office Hours / NOV 2026 — _office_hours_
- ✓ Lunasa
- ✓ Traditional Italian Christmas Cookies
- ✓ Jóvenes en Acción 2026 ×8

**`fairytale_town_events@sacramento`**
- ✕ Closed for Thanksgiving — _closure_
- ✓ Winter Wonderland ×5
- ✓ Story Time with the Maidu Museum
- ✓ Scholastic Book Fair!

**`nyc_permitted_events@nyc`**
- ✕ Nassau Summer/Fall Street Closures — _closure_
- ✓ Dieux - Parasol - Dieux Pop-up ×5
- ✓ Jackson Heights Greenmarket Sunday ×4
- ✓ HHFM East Harlem Market ×3

**`scottsdale_city_events@phoenix`**
- ✕ Citizens' Bond Oversight Committee - Regular - 11-16-26 — _governance_meeting_
- ✓ Scottsdale Heritage Connection Saturdays
- ✓ Arts & Crafts Fair
- ✓ Fall Book Sale

**`alamodome@san_antonio`**
- ✓ UTSA Roadrunners v North Texas
- ✓ Monster Jam
- ✓ UIL STATE MARCHING BAND CONTEST
- ✓ Navy All-American Bowl
- ✓ Bands Of America: San Antonio Super Regional Championship Prelims

**`atlanta_botanical_garden@atlanta`**
- ✓ Drawing the Fall Harvest
- ✓ Garden Lights, Holiday Nights Volunteer Training
- ✓ SOLD OUT: Young Sprouts ×4
- ✓ Smartphone Flower Photography
- ✓ Garden Lights, Holiday Nights Member Premiere

**`austin_parks_foundation_events@austin`**
- ✓ 11/4 Playdate in the Park: Parque Zaragoza Neighborhood Park
- ✓ It’s My Park Day: 11/9 Tool & Supply Bag Drop Off
- ✓ 11/14 Art in the Park: Colony Park District Park
- ✓ Restoration Reset: Park Stewardship at Kendra Page Neighborhood Park ×2
- ✓ It’s My Park Day: 11/5 Tool & Supply Bag Pickup

**`balboa_park_events@san_diego`**
- ✓ House of USA Lawn Program – Veterans Day Celebration
- ✓ Fleet Accessibility Mornings
- ✓ Chanoyu Tea Ceremony Demonstrations
- ✓ Spinning Resistance: Women, Cloth, and the Long Memory of 1776
- ✓ Coffee and Conversations

**`baltimore_county_volunteer@baltimore`**
- ✓ Event Volunteer
- ✓ Volunteer Potluck Dinner (November)
- ✓ Le Diner Bleu Gala
- ✓ Chesapeake Patriot 5K Run and 1K Walk 2026
- ✓ Caregiver Support Program Volunteer

**`bartrams_garden_events@philadelphia`**
- ✓ SWWAG Workshop: Putting the Farm to Bed to Prepare Your Winter Garden
- ✓ Little Explorers: Colorful Leaves
- ✓ Open Mic & Gallery
- ✓ Sankofa Community Farm Volunteer Day
- ✓ Showing of ‘Nuevo Mundo’

**`bayfront_park_miami@miami`**
- ✓ Race for Champions 2026
- ✓ Family Style Festival
- ✓ GIVE MIAMI 5K + FESTIVAL

**`bc_athletics@boston`**
- ✓ Boston College Women's Basketball vs UMass Lowell - Military Appreciation Game / Kids 12 & Under Free
- ✓ Boston College Swimming vs University of Connecticut (Women Only)
- ✓ Boston College Women's Hockey at Boston University
- ✓ Boston College Women's Basketball vs UMass - Kids 12 & Under Receive Free Admission
- ✓ Boston College Women's Hockey at Northeastern

**`brackenridge_park_events@san_antonio`**
- ✓ 3rd Annual Brack Bash
- ✓ Community Sound Bath
- ✓ Community Sound Baths at Joske Pavilion
- ✓ The Gentle Art of Jiu Jitsu
- ✓ Tai Chi in the Park ×2

**`bu_athletics@boston`**
- ✓ Boston University Men's Ice Hockey vs Northeastern - BU Hockey Soccer Scarf Giveaway
- ✓ Boston University Men's Ice Hockey vs Quinnipiac - Dog Pound Wall Flag Giveaway
- ✓ Boston University Men's Ice Hockey vs Denver - Winter Surge Rally Towel Giveaway
- ✓ Boston College Swimming at Terrier Invite ×3
- ✓ Boston University Women's Basketball vs Northeastern

**`buffalo_bayou_events@houston`**
- ✓ Sound Healing Meditation ×8
- ✓ Buffalo Bayou Cruise ×7
- ✓ Tinsel Trek ×2
- ✓ Buffalo Bayou Park Wellness Walk ×5
- ✓ Monthly Volunteer Workday

**`cap_city_comedy@austin`**
- ✓ Alfred Robles ×5
- ✓ Philip Lindsay
- ✓ Dale Elliott Jr
- ✓ Christian Johnson ×2
- ✓ Pinky Patel

**`carnegie_museums_events@pittsburgh`**
- ✓ Sound Series: An Evening with Nellie McKay
- ✓ R.W. Moriarty Science Seminar: What Migrating Birds Risk and Need
- ✓ The Future of Art History: Carnegie Internationals in Context
- ✓ Storytime at the Museum ×8
- ✓ Café Sci: Lights, Camera, Action; How the 2026 Nobel Prize is Changing our Understanding of the Brain and Beha

**`carver_cultural_center@san_antonio`**
- ✓ A-wreath-a Making Class
- ✓ It's a San Antonio Christmas
- ✓ Kings Return
- ✓ The Quilt: Live in Concert – Russell Hill Rogers Musical Evenings
- ✓ 35th Annual ATAC Globe Awards

**`cbu_athletics@riverside`**
- ✓ California Baptist University Men's Basketball at UC Riverside - Crosstown Showdown
- ✓ Pepperdine Waves at California Baptist Lancers Womens Basketball
- ✓ California Baptist University Men's Basketball vs University of Arkansas - Pine Bluff
- ✓ California Baptist University Men's Water Polo vs UC San Diego
- ✓ Pacific Tigers at California Baptist Lancers Womens Basketball

**`cedar_cultural_center@minneapolis`**
- ✓ Gill Weather and Eldest Daughter with Meghan Kreidler (of Kiss the Tiger)
- ✓ An Evening with Duo Andalus
- ✓ Teddy Thompson w/ Jenna Nicholls
- ✓ Manu Delago & Max ZT
- ✓ Alela Diane with Shannon Lay

**`challenge_trivia_kansas_city@kansas_city`**
- ✓ Live Trivia at Tanners Bar and Grill - Lenexa, KS ×4
- ✓ Live Trivia at Konrad’s Kitchen and Tap House - Lee's Summit ×4
- ✓ Singo at Patrick's Bar and No Grill - Kansas City, MO
- ✓ Live Trivia (non-NTL) at Patrick's Bar and No Grill - Kansas City, MO
- ✓ Live Trivia at Twin City Tavern - Kansas City (Westport) ×4

**`challenge_trivia_okc@oklahoma_city`**
- ✓ Music Match at Logie's on the Corner - Norman ×4
- ✓ Singo at Chicken N Pickle - OKC - Oklahoma City ×4
- ✓ Live Trivia at Chicken N Pickle - OKC - Oklahoma City ×4
- ✓ Live Trivia at Logie's on the Corner - Norman ×4
- ✓ Live Trivia at Hey Day Entertainment - Norman ×4

**`chicago_park_adult_classes@chicago`**
- ✓ Tennis Lessons: NTRP 1.0-1.5, Level 1 at McFetridge ×4
- ✓ Boxing for Adults (ASMG) at Gately ×2
- ✓ Tennis Lessons: NTRP 3.0 - 3.5, Level 3 at McFetridge ×4
- ✓ Bowling (Blind VI-Deaf & HOH) at Horner
- ✓ Pickleball - Drills and Skills - Tactical at McFetridge

**`chicago_park_adult_leagues@chicago`**
- ✓ Basketball League at Russell Square
- ✓ Womens Volleyball League at Wentworth
- ✓ Volleyball League at Davis Square
- ✓ Mens Basketball League at Mt. Greenwood

**`chicago_park_events@chicago`**
- ✓ Think Outside the Block at Ogden
- ✓ Hot Chocolate with Santa at Bell
- ✓ Thanksgiving Throw Down at Scottsdale
- ✓ Winter Art Workshop - Art at Morgan Park SC ×2
- ✓ Drop and Shop at Indian Road ×2

**`chicago_park_permits@chicago`**
- ✓ LifeTime Chicago Turkey Trot 8K and 5K ×2
- ✓ PSG-2026-Fall Holiday Tournament
- ✓ Chicago Jingle Bell Run
- ✓ Fit 4 Me Health Fitness Festival Kosciuszko
- ✓ CSSC-2026- Turkey Bowl (Non-exclusive Use)

**`clt_cmpd_community_events@charlotte`**
- ✓ Jh Gunn Community Meeting (CMPD Hickory Grove Division)
- ✓ Coffee With A Cop/Community Roll Call - Starbucks (CMPD University City Division)
- ✓ Wilson Heights (CMPD Metro Division) ×2
- ✓ Bradfield Farms Neighborhood Watch Meeting (CMPD Hickory Grove Division) ×13
- ✓ Washington Heights (CMPD Metro Division) ×5

**`columbus_commons@columbus`**
- ✓ FREE Wanderlights ×8
- ✓ FREE Wander Nights at Wanderlights ×6

**`dallas_arboretum@dallas`**
- ✓ Holiday at the Arboretum
- ✓ ​​Floral Candles Workshop
- ✓ The Art of Holiday Wreath Design​
- ✓ Holiday ​Gingerbread House
- ✓ Visits with Santa

**`dallas_parks_events@dallas`**
- ✓ Paws on Patrol at Northbark Dog Park
- ✓ District 8 Wellness Block Party at Janie C Turner Rec
- ✓ Take a Photo Thursday! (December)
- ✓ Super Saturdays! (November)
- ✓ Bushmills Neighborhood Green Ribbon Cutting

**`desert_botanical_garden_events@phoenix`**
- ✓ Fall Garden After Dark ×8
- ✓ Chiles & Chocolate Festival ×3
- ✓ Super Bloom Art Exhibit ×8
- ✓ Wednesday Dog Nights ×2
- ✓ Saturday Dog Days ×2

**`downtown_baltimore_events@baltimore`**
- ✓ “An Evening of Soul” A Tribute to Gladys Knight & Patti Labelle
- ✓ NUTCRACKER! Magical Christmas Ballet
- ✓ 2026 ABCT 60th Annual Convention
- ✓ Maryland Gymnastics Christmas on the Chesapeake 2026
- ✓ Carl Filipiak Jazz Quartet @ Keystone Korner

**`downtown_boston_events@boston`**
- ✓ Jeremy Jordan
- ✓ Camp Harbor View 5k Road Race
- ✓ November Hands-On History Day
- ✓ Experience The Ruckus! ×8
- ✓ Rocky In Concert

**`downtown_dallas_events@dallas`**
- ✓ Mystic Pizza - The Musical - Dallas ×4
- ✓ The Music of Hey Arnold! Live - Dallas
- ✓ CultureMap City Rink / Main Street Garden ×8
- ✓ Wild Salsa Taco Tuesday ×5
- ✓ Bravo! – AT&T Performing Arts Center

**`downtown_seattle_events@seattle`**
- ✓ DSA Access
- ✓ Occidental Square Holiday Bazaar
- ✓ Holiday Ice Skating Rink in Occidental Square
- ✓ Pines on Pike Christmas Tree Lot
- ✓ Sunset Art Walk Markets

**`earshot_jazz@seattle`**
- ✓ The Four Tops ×6
- ✓ Patrick Rifflin ×3
- ✓ Brazz – Brazilian Jazz
- ✓ What’s Going On: Night One: Conduction Workshop and Art of the Trio
- ✓ Michael Owcharuk Trio // Jacob Zimmerman 3 (alternating Sundays) ×3

**`folly_theater@kansas_city`**
- ✓ Julian Lage
- ✓ Preservation Hall Jazz Band
- ✓ Art of the Piano: Sir Stephen Hough
- ✓ Bernadette Peters
- ✓ The Nutcracker

**`ford_field@detroit`**
- ✓ Detroit Lions vs. Tennessee Titans
- ✓ Detroit Lions vs. Chicago Bears
- ✓ Detroit Lions vs. New York Giants
- ✓ Detroit Lions vs. Tampa Bay Buccaneers
- ✓ Motor City MACtion

**`gcu_athletics@phoenix`**
- ✓ Grand Canyon University Beach Volleyball vs GCU Fall Tournament
- ✓ Grand Canyon University Women's Swimming and Diving vs Air Force
- ✓ Grand Canyon University Volleyball vs San José State - Dig Together, Senior Day
- ✓ Georgia State Panthers at Grand Canyon Lopes Womens Basketball
- ✓ Grand Canyon University Men's Basketball vs Incarnate Word - Community Impact Night

**`gggp_events@san_francisco`**
- ✓ November Forest Bathing
- ✓ Ask A Master Gardener ×3
- ✓ Knitting in Nature ×2
- ✓ Birding in the Garden with Golden Gate Bird Alliance
- ✓ Midday Yoga in the Garden ×2

**`heb_center@austin`**
- ✓ Cristian Castro
- ✓ Grand Rapids Griffins vs Texas Stars ×4
- ✓ Cirque Musica Holiday Wonderland
- ✓ Chicago Wolves vs Texas Stars ×4
- ✓ Coachella Valley Firebirds vs Texas Stars ×2

**`hfd_ct_museum_history@hartford`**
- ✓ Behind-the-Scenes Tour: Remembering G. Fox & Co. ×4
- ✓ Made to Last: Mohegan Basket Traditions with Sharon Maynard and Cass Meehan
- ✓ Family Activity Kits – New Theme!
- ✓ Member Event! Holiday Brunch: A Year in Review through our Collections
- ✓ The Legacy: Building with my Great-grandfather’s Tools

**`hfd_hartford_hawks@hartford`**
- ✓ University of Hartford Women's Basketball vs Russell Sage College
- ✓ University of Hartford Women's Basketball vs Wentworth Institute of Technology
- ✓ University of Hartford Men's Basketball vs Endicott College
- ✓ University of Hartford Men's Basketball vs Wentworth Institute of Technology
- ✓ University of Hartford Women's Basketball vs United States Coast Guard Academy

**`hfd_mark_twain_house@hartford`**
- ✓ The Mark Twain Award Weekend
- ✓ Creative Writing in the Age of AI Symposium
- ✓ An Evening with Illeana Douglas
- ✓ Mark Twain American Voice in Literature Award 2026 Celebration
- ✓ Ghost Tours of The Mark Twain House

**`hfd_trinity_bantams@hartford`**
- ✓ Trinity College Women's Squash vs Bates College
- ✓ Trinity College Women's Ice Hockey vs Bowdoin College ×2
- ✓ Trinity College Men's Squash vs Colby College
- ✓ Trinity College Men's Basketball vs Yeshiva University
- ✓ Trinity College Women's Basketball vs Babson College

**`houston_arboretum_events@houston`**
- ✓ Guided Nature Hikes ×4
- ✓ Sip & Stroll
- ✓ Tree Planting Workshop
- ✓ Winter Walk
- ✓ Tyke Hikes en español ×2

**`ju_athletics@jacksonville`**
- ✓ Jacksonville University Men's Basketball vs Trinity College of Jacksonville - YOUTH SPORTS DAY
- ✓ Jacksonville University Women's Volleyball at North Florida
- ✓ Jacksonville University Ice Hockey Florida State
- ✓ Jacksonville University Men's Basketball vs Central Arkansas - HOOP ROOM
- ✓ Jacksonville University Men's Basketball vs Little Rock - HOOPS FOR HUNGER / HOOP ROOM

**`kc_roos_athletics@kansas_city`**
- ✓ Kansas City Women's Basketball vs SEMO
- ✓ Kansas City Women's Basketball vs Lindenwood
- ✓ Kansas City Volleyball vs South Dakota State
- ✓ Kansas City Women's Basketball vs Park
- ✓ Kansas City Volleyball vs South Dakota

**`lan_su_garden@portland`**
- ✓ Make Your Own Chrysanthemum Wind Chime ×3
- ✓ Holiday Dried Flower Wreath Workshop with Walking Whale Flower Farm ×2
- ✓ Monthly Member Hour ×2
- ✓ Tour + Pour (Ticketed Experience) ×3
- ✓ Taste of Home, Where the Heart Belongs — Chinese Homestyle Cooking Demonstration

**`levy_park_events@houston`**
- ✓ Restorative Yoga with Stephanie McCarrey ×2
- ✓ Argentine Tango Series ×4
- ✓ Slow Flow with Stephanie McCarrey ×7
- ✓ Houston Museum of Natural Science
- ✓ Blue Dragon Tai Chi ×8

**`lewis_ginter_events@richmond`**
- ✓ Holiday Wreath Workshop, Dec afternoon
- ✓ SEASONAL SPLENDOR TOUR: NOVEMBER 5
- ✓ Botanical Illustration Studio: Exploring Appropriate Backgrounds for Botanical Art
- ✓ WORLDS UNDER GLASS: DESERT TO RAINFOREST TOUR: NOVEMBER 10
- ✓ Orchids 101

**`luma_the_made@san_francisco`**
- ✓ 💻 interactive fiction meetup 💻 ×2
- ✓ ✩˚₊‧ live music + visuals jam ‧₊˚✩
- ✓ fight nights @ the MADE ×4
- ✓ ₊˚⊹♡ game dev showcase ♡⊹˚₊ ×2
- ✓ Experimental Play Nights Presents: The Hexidecipadathon

**`luma_zoma_house@minneapolis`**
- ✓ Late Night Open Mic 003: Writers Room Edition
- ✓ Sis-Giving
- ✓ BIPOC Improv Jam

**`marcus_center@milwaukee`**
- ✓ Girls Night: The Musical
- ✓ Waitress
- ✓ Hold On To Your Butts
- ✓ Buena Vista Social Club (Touring)
- ✓ The Sound of Music (Touring)

**`memorial_park_events@houston`**
- ✓ Yoga on the Lawn ×2
- ✓ Star Parties with Houston Astronomical Society
- ✓ Bird Survey at Memorial Park
- ✓ Wellness Walks at Memorial Park ×8
- ✓ Volunteer with Memorial Park Conservancy ×6

**`memphis_meddlesome@memphis`**
- ✓ 9th Annual Meddlesome Meandering 0.5K
- ✓ Happy Hour! ×5
- ✓ Mie And Grady Productions presents: THE 11:29 REUNION!
- ✓ Trivia Night ×5
- ✓ Thirsty Thursday! ×5

**`memphis_overton_park_shell@memphis`**
- ✓ Shell on Wheels: MOSH Laser Live ft. Unapologetic.
- ✓ Shell on Wheels: ARTSmemphis Green House Party
- ✓ Baptist Health & Wellness Series: Zumba ×2
- ✓ Baptist Health & Wellness Series: Twilight Yoga and Pilates
- ✓ Baptist Health & Wellness Series: Breath work and Meditation

**`memphis_river_parks@memphis`**
- ✓ Hustle & Flow HIIT — MEMPHIS RIVER PARKS
- ✓ Stargazing — MEMPHIS RIVER PARKS
- ✓ River Walkers — MEMPHIS RIVER PARKS ×3
- ✓ Fire Pit Friday — MEMPHIS RIVER PARKS ×4

**`memphis_wiseacre@memphis`**
- ✓ RENAISSANCE FAIRE AT WISEACRE
- ✓ OG Trivia Night ×5
- ✓ Trivia Night ×5
- ✓ Medal Mondays $4 Pints ×6
- ✓ Free Workout Series ×4

**`mesa_arts_center@phoenix`**
- ✓ Youth Symphony of the Southwest Concerts YSOTS
- ✓ EVCT Chicken Little and the Legend of El Pollo Diablo East Valley Children's Theatre
- ✓ Dan and Phil: Hard Launch World Tour
- ✓ Southwest Shakespeare Company SSC Tartuffe
- ✓ Jesse Cook

**`mo_new_liquor_licenses_kc@kansas_city`**
- ✓ Worlds Of Fun — new liquor license
- ✓ Carmen's Cafe — new liquor license
- ✓ Rendezvous Lounge — new liquor license
- ✓ Pizza 51 — new liquor license
- ✓ Louies Reserve — new liquor license

**`montalvo_arts@san_jose`**
- ✓ Marc Broussard
- ✓ The Smithereens
- ✓ Mosaic America (Grade K-8)
- ✓ SOLAS

**`montgomery_volunteer@washington_dc`**
- ✓ Help us unload our Christmas Tree truck! READ DESCRIPTION CAREFULLY
- ✓ 1st Annual Dog Costume Contest
- ✓ Professional Volunteer Event Photographer
- ✓ Event Support at the 2026 Montgomery Serves Awards!
- ✓ Professional Volunteer Event Videographer

**`mount_vernon_triangle_events@washington_dc`**
- ✓ FRESHFARM MVT Market ×6
- ✓ VIDA Fitness Open House ×2
- ✓ Writers of Washington Presents: Common Sense Take 2
- ✓ Free Public Art Tours at Walter E. Washington Convention Center
- ✓ Center Stage Presents: The Serpent Queen

**`mpls_downtown_events@minneapolis`**
- ✓ Neil deGrasse Tyson: Science as a Way of Knowing
- ✓ Derrick Stroup: Running Hot Tour
- ✓ Service Tuesdays
- ✓ Work Wednesday: Job Training and Resources
- ✓ The Glenn Miller Orchestra

**`ncmns_events@raleigh`**
- ✓ Project RESTORE Educator Trek: Waterdog Warriors
- ✓ Science Detectives: Coastal Critters
- ✓ Science Café: Decoding the Lives of Sri Lanka’s Elephants
- ✓ Roots of Discovery: Festival of Lights
- ✓ The ICONS Tour ×5

**`notoriety_live@las_vegas`**
- ✓ Jazz Vegas Orchestra Live
- ✓ Notoriety Comedy Club
- ✓ Vinnie Favorito Unfiltered
- ✓ Spirit of the King: The Ultimate ELVIS Show
- ✓ Chase Brown’s Vegas Country

**`now_playing_utah@salt_lake_city`**
- ✓ Cyanotype Photograms: Light, Chemistry, Water, Image
- ✓ Laughing Stock Improv Comedy
- ✓ Community Cinema Film Series
- ✓ ALIX PEREZ: NORTH AMERICAN TOUR
- ✓ Everclear live at The Complex!

**`nyc_parks_events@nyc`**
- ✓ NYRR Open Run: Highland Park ×2
- ✓ NYRR Open Run: Baisley Pond Park ×2
- ✓ NYRR Open Run: Shore Road Park ×2
- ✓ Total Body Reset ×2
- ✓ Artist Talk with Cecile Chong and Alexander Zev

**`okc_cowboy_museum@oklahoma_city`**
- ✓ Deck the Hall
- ✓ Brushes & Bubbly
- ✓ Annie Oakley Society Luncheon
- ✓ Small Works, Great Wonders Art Sale
- ✓ Military Appreciation Day

**`okc_ocu_athletics@oklahoma_city`**
- ✓ Oklahoma City University #11 Women's Wrestling vs Rose State College
- ✓ Oklahoma City University #6 Men's Wrestling vs Drury University
- ✓ Oklahoma City University Men's Basketball vs Langston
- ✓ Oklahoma City University Men's Basketball vs Southwestern Christian University
- ✓ Oklahoma City University Women's Basketball vs Texas Wesleyan University

**`okc_science_museum@oklahoma_city`**
- ✓ Member Shopping Night
- ✓ Women in STEAM Conference 2026
- ✓ Teen Science Café: Ecosystem Under Our Feet
- ✓ Teen Science Café: Music as Medicine
- ✓ Teacher Professional Development Workshop

**`orlando_museum_of_art@orlando`**
- ✓ Gallery Talks
- ✓ Art Night Out: December
- ✓ Highlights Tour ×6
- ✓ Art Night Out: Red, White & Gobble: The Turkey That Almost Was
- ✓ OMA Book Club ×2

**`orlando_restaurant_openings@orlando`**
- ✓ Jd Dumpling King — new restaurant license
- ✓ Sweeties Ice Cream — new restaurant license
- ✓ Coincidence Cafe Llc — new restaurant license
- ✓ Station 441 A Paradise Inc — new restaurant license
- ✓ Udon Fifty Llc — new restaurant license

**`pearl_events@san_antonio`**
- ✓ Grateful Shred
- ✓ Farmers Market ×2
- ✓ Latin Dance Night at Stable Hall ×2
- ✓ FIT4MOM First Friday
- ✓ Night Market ×2

**`piedmont_park_events@atlanta`**
- ✓ Silk Scarf Painting
- ✓ Connect and Learn: Meteorites!
- ✓ Figure Drawing
- ✓ Community Game Night
- ✓ Light Up the Season Lantern Parade & Lighting Celebration

**`pittsburgh_parks_events@pittsburgh`**
- ✓ Discovery Time: Fun with Senses – Frick Environmental Center
- ✓ Birding Pittsburgh’s Parks – August Wilson Park
- ✓ Restorative Yoga with Mindful Self-Care – Frick Environmental Center
- ✓ Sunday Songwriters Series at Schenley Park Visitor Center
- ✓ Galleria Botanica Holiday Centerpiece Workshop

**`portland_art_museum@portland`**
- ✓ A Queer Guide to Saving American Democracy: Book Release + Queen of New York w/ Marti Cummings
- ✓ Plus Plus Bizarre Bazaar
- ✓ Amélie (2001)
- ✓ Curtis Cook Stand Up
- ✓ Shu Lea Cheang Shorts & Fresh Kill x Lesbian Cinema Club

**`portland_farmers_market@portland`**
- ✓ Neighbors in the Market: Jenny Tseng
- ✓ Lents International Farmers Market ×3
- ✓ Ian Joe Bailey
- ✓ PSU Farmers Market ×6
- ✓ School of Rock Portland

**`pvd_friars_athletics@providence`**
- ✓ Providence College Women's Basketball vs Bryant University - Military Appreciation Night
- ✓ Providence College Men's Ice Hockey vs New Hampshire
- ✓ Providence College Men's Basketball vs Stonehill - Paint It Black
- ✓ Brown University Women's Volleyball vs Penn
- ✓ Providence College Men's Basketball vs Butler

**`pvd_ppac@providence`**
- ✓ Hell's Kitchen - Providence
- ✓ Brit Floyd: Animals 50
- ✓ The Rock Orchestra by Candlelight
- ✓ Eric Andre: Subtle
- ✓ Death Becomes Her - Providence

**`raleigh_special_events@raleigh`**
- ✓ Raleigh Turkey Trot
- ✓ Morning Times First Friday Market
- ✓ Lewispalooza
- ✓ AIDS Walk
- ✓ Every Breath Forward - Lung Cancer Awareness Flags

**`redlands_athletics@riverside`**
- ✓ University of Redlands Women's Basketball vs Azusa Pacific University
- ✓ University of Redlands Women's Basketball vs Whittier College
- ✓ University of Redlands Men's Basketball vs University of California, Santa Cruz ×2
- ✓ University of Redlands Men's Water Polo vs University of La Verne
- ✓ University of Redlands Women's Basketball vs Sewanee

**`rice_athletics@houston`**
- ✓ Rice University Swimming & Diving vs Tulane - Senior Day
- ✓ Rice University Men's Basketball vs Texas A&M - Corpus Christi
- ✓ Houston Christian Huskies at Rice Owls Womens Basketball
- ✓ Rice University Men's Basketball vs Nicholls
- ✓ Rice University Men's Basketball vs East Texas A&M

**`rivers_of_steel_events@pittsburgh`**
- ✓ Blacksmithing: Holiday Ornaments
- ✓ The Doodle Bowl Experience
- ✓ All levels Blacksmithing: Bladesmithing 1

**`sacramento_business_openings@sacramento`**
- ✓ Hstreetsweets Llc — new business registration
- ✓ Hot Bunz Sac Inc. — new business registration
- ✓ Sabr Hd Inc Dba Matari Coffee Co — new business registration
- ✓ Cinnapop Cafe — new business registration
- ✓ Angry Chickz — new business registration

**`schottenstein_center@columbus`**
- ✓ Ohio State Buckeyes Womens Basketball vs. Washington Huskies Women's Basketball
- ✓ Nickelback: Everything Under The Sun Tour
- ✓ Ohio State Buckeyes Womens Basketball vs. Akron Zips Womens Basketball
- ✓ Winter Jam
- ✓ Ohio State Buckeyes Womens Basketball vs. Univ of Maryland Terrapins Womens Basketball

**`seven_venues_norfolk@hampton_roads`**
- ✓ Pagliacci
- ✓ Virginia Arts Festival - Gabriela Allemana
- ✓ Jason Palmer
- ✓ Dr. Jekyll & Mr. Hyde
- ✓ Edmonia

**`sf_recpark_events@san_francisco`**
- ✓ Zumba and Shake The Fog ×2
- ✓ Sunset Dunes Community Cleanup ×2
- ✓ 2nd Sunday Serenades ×2
- ✓ EcoCenter Volunteer Workparty ×2
- ✓ Chair Yoga

**`slu_athletics@st_louis`**
- ✓ Saint Louis University Women's Basketball vs SEMO - Holiday Food Drive
- ✓ Saint Louis University Women's Basketball vs Illinois State - Pass Back
- ✓ Saint Louis University Volleyball vs Davidson ×2
- ✓ Saint Louis University Women's Basketball vs Missouri State - Toy Drive
- ✓ Saint Louis University Women's Basketball vs Ohio - Teddy Bear Toss

**`smithsonian_events@washington_dc`**
- ✓ Forward Religions Conference 2026: Welcome Home
- ✓ Día de los Muertos Celebration
- ✓ The Surprising Males of the Orangutan World
- ✓ Meditation Mondays
- ✓ Play Date at NMNH: Animal Spotlight - Bison!

**`songbyrd_dc@washington_dc`**
- ✓ DEVON GABRIELLA
- ✓ AFRODESI DC FT. MR SAJ & FRIENDS
- ✓ Natanya
- ✓ JEFF THE BROTHERHOOD
- ✓ Josie Edwards

**`tampa_downtown_events@tampa`**
- ✓ Zumba in the Park
- ✓ Tampa Bay History Center Annual Gala
- ✓ Railroad to River: University of Tampa in Hidden View
- ✓ HIIT in the Park
- ✓ Thursday Ceramics

**`td_garden@boston`**
- ✓ Boston Bruins vs. Buffalo Sabres
- ✓ Celtics vs. Grizzlies
- ✓ Boston Celtics vs. Minnesota Timberwolves (Jayson Tatum Bobblehead)
- ✓ Celtics vs. Bucks
- ✓ Boston Celtics vs. Washington Wizards ×2

**`uwkc_volunteer@seattle`**
- ✓ 2026 Seattle Arbor Day
- ✓ Advocacy in Action: Support United Way at Seattle City Hall
- ✓ Thanksgiving Day
- ✓ Jingle Bell Run Event Volunteers
- ✓ Greeting Card & Supply Sorting for Seniors (Beacon Hill)

**`uwsa_volunteer@san_antonio`**
- ✓ Virtual Opportunity: Boost Your Community's Volunteer Engagement!
- ✓ Thanksgiving Day Dining Room
- ✓ Thanksgiving Day Kitchen ×3
- ✓ Future Travel Leaders Network Youth Volunteer
- ✓ Coordinate a book drive for Little Free Libraries near you

**`virginia_zoo_events@hampton_roads`**
- ✓ Poppy Storytime
- ✓ *NEW* Community Days ×6
- ✓ Holidays in the Wild: Holiday Market
- ✓ Member Perk: Wild Wednesday ×5
- ✓ Wild Wheels ×2

**`visit_ballard_events@seattle`**
- ✓ Photo & film meetup: Ballard Film Club with Artemis Coffee & Ballard Film & Foto
- ✓ Intro to Machine Knitting
- ✓ Bingo Monday ×4
- ✓ Craft Party: Sprinkle Embroidery
- ✓ Book Club – Emotional Damage

**`witte_museum_events@san_antonio`**
- ✓ STEAM Sunday: Candy Cane Constructors
- ✓ Conference on Texas: Our Culinary Roots
- ✓ Daily Special with Gardopia ×2
- ✓ Cocktails & Culture: Witte Watercolors
- ✓ Our Culinary Roots: La Tamalada

</details>

### Venues & Other (474 units · 77,027 kept · 62 held back)

| Unit | Kept | Held | Share held | Top rules |
|---|---|---|---|---|
| `mr_tipples@san_francisco` | 71 | 6 | 8% | closure 5, internal_only 1 |
| `chris_jazz_cafe@philadelphia` | 89 | 4 | 4% | closure 3, internal_only 1 |
| `seatgeek@los_angeles` | 1283 | 4 | 0% | placeholder_matchup 4 |
| `ticketmaster@san_francisco` | 1076 | 3 | 0% | placeholder 3 |
| `carousel_lounge@austin` | 45 | 2 | 4% | closure 2 |
| `cliff_bells@detroit` | 49 | 2 | 4% | closure 2 |
| `helium_comedy_philly@philadelphia` | 89 | 2 | 2% | internal_only 2 |
| `seatgeek@atlanta` | 857 | 2 | 0% | placeholder_matchup 2 |
| `seatgeek@washington_dc` | 1005 | 2 | 0% | placeholder_matchup 2 |
| `dakota_jazz@minneapolis` | 99 | 1 | 1% | internal_only 1 |
| `goodnights_comedy@raleigh` | 146 | 1 | 1% | closure 1 |
| `madrone_art_bar@san_francisco` | 83 | 1 | 1% | closure 1 |
| `royal_room_seattle@seattle` | 8 | 1 | 11% | closure 1 |
| `seatgeek@boston` | 1052 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@charlotte` | 488 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@chicago` | 1179 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@dallas` | 839 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@denver` | 765 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@detroit` | 578 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@fresno` | 123 | 1 | 1% | placeholder_matchup 1 |
| `seatgeek@hampton_roads` | 326 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@houston` | 802 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@indianapolis` | 569 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@memphis` | 186 | 1 | 1% | placeholder_matchup 1 |
| `seatgeek@miami` | 368 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@milwaukee` | 462 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@minneapolis` | 694 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@nyc` | 1466 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@oklahoma_city` | 220 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@orlando` | 460 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@philadelphia` | 921 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@phoenix` | 1137 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@portland` | 596 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@sacramento` | 451 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@salt_lake_city` | 412 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@san_antonio` | 364 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@san_diego` | 564 | 1 | 0% | placeholder_matchup 1 |
| `seatgeek@san_francisco` | 1093 | 1 | 0% | placeholder_matchup 1 |
| `ticketmaster@columbus` | 512 | 1 | 0% | placeholder 1 |
| `ticketmaster@las_vegas` | 1954 | 1 | 0% | placeholder 1 |
| `ticketmaster@los_angeles` | 1680 | 1 | 0% | placeholder 1 |
| `ticketmaster@philadelphia` | 809 | 1 | 0% | placeholder 1 |
| `ticketmaster@washington_dc` | 941 | 1 | 0% | placeholder 1 |
| `zinc_bar@nyc` | 64 | 1 | 2% | closure 1 |

<details><summary>Samples: kept vs held back</summary>

**`mr_tipples@san_francisco`**
- ✕ Closed for a Private Event — _closure_
- ✕ Closed for the Holiday ×2 — _closure_
- ✕ Closed for Private Event ×2 — _closure_
- ✕ Private Event — _internal_only_
- ✓ Kurt Ribak Quartet ×2
- ✓ The Kuehn Tumalan Latin 5tet ×2
- ✓ Philippe Vieux Quartet ×2

**`chris_jazz_cafe@philadelphia`**
- ✕ Closed for Holiday ×2 — _closure_
- ✕ Closed for Thanksgiving — _closure_
- ✕ Private Party — _internal_only_
- ✓ Gabriel Meyer & His Band
- ✓ Gardyn Jazz Orchestra ×2
- ✓ Laura Orzehoski & Her Quintet's Holiday Show ×2

**`seatgeek@los_angeles`**
- ✕ TBD at Los Angeles Clippers — _placeholder_matchup_
- ✕ TBD at Angel City FC - NWSL Semifinals — _placeholder_matchup_
- ✕ TBD at Los Angeles Lakers — _placeholder_matchup_
- ✕ TBD at UCLA Bruins Mens Basketball — _placeholder_matchup_
- ✓ LA Clippers vs Orlando Magic
- ✓ Afrojack
- ✓ June McDoom with Eliana Glass

**`ticketmaster@san_francisco`**
- ✕ Private Event ×3 — _placeholder_
- ✓ SF Gay Men's Chorus Holiday Spectacular: Home for the Holidays - 8pm
- ✓ Ibeyi
- ✓ Y&T

**`carousel_lounge@austin`**
- ✕ CLOSED – CHRISTMAS, hope its fabulous — _closure_
- ✕ THANKSGIVING – CLOSED come back tomorrow — _closure_
- ✓ Movement Disorder
- ✓ J J Brat (Zamecki)
- ✓ Ancient Forward ×2

**`cliff_bells@detroit`**
- ✕ Closed for the Holiday ×2 — _closure_
- ✓ Monique Ella Rose
- ✓ Christopher L. Wilson Trio
- ✓ Anthony Stanco Quartet ×2

**`helium_comedy_philly@philadelphia`**
- ✕ Private Event ×2 — _internal_only_
- ✓ Open Mic Night ×2
- ✓ Special Event: Kev Adams
- ✓ Special Event: Just Nesh

**`seatgeek@atlanta`**
- ✕ TBD at Georgia State Panthers Womens Basketball — _placeholder_matchup_
- ✕ TBD at Atlanta Hawks — _placeholder_matchup_
- ✓ Josie Edwards
- ✓ Bach + Brahms ×2
- ✓ The Wallflowers with Yola

**`seatgeek@washington_dc`**
- ✕ TBD at Washington Wizards — _placeholder_matchup_
- ✕ TBD at Washington Spirit - NWSL Semifinals — _placeholder_matchup_
- ✓ Vancouver Canucks at Washington Capitals
- ✓ Georgetown Hoyas Men's Basketball v Rider
- ✓ Freak Slug

**`dakota_jazz@minneapolis`**
- ✕ Private Event — _internal_only_
- ✓ Rachael & Vilray ×6
- ✓ The Beautiful Day: Kurt Elling Sings Christmas ×2
- ✓ VIP EVENT: Boney James Live

**`goodnights_comedy@raleigh`**
- ✕ Closed for Private Event — _closure_
- ✓ Special Event: Shafi Hossain
- ✓ Room 861 at Goodnights: Nick Deez
- ✓ Room 861 at Goodnights: Splou

**`madrone_art_bar@san_francisco`**
- ✕ Bar is Closed — _closure_
- ✓ STRAIGHTEN IT OUT ×2
- ✓ Monthly Trivia Night ×2
- ✓ SUNDAY B3 SESSIONS ×6

**`royal_room_seattle@seattle`**
- ✕ CLOSED FOR MAINTENANCE — _closure_
- ✓ What’s Going On: New Music Mondays
- ✓ MOXIE
- ✓ Prismia Presents “Midnight Girl” Music Video Release Show

**`seatgeek@boston`**
- ✕ TBD at Boston Celtics — _placeholder_matchup_
- ✓ Josie Edwards
- ✓ A Conversation with Trisha Paytas
- ✓ UMass Minutewomen at Harvard Crimson Womens Basketball

**`seatgeek@charlotte`**
- ✕ TBD at Charlotte Hornets — _placeholder_matchup_
- ✓ BEAT: Belew/Vai/Levin/Bozzio Performing the Music of KING CRIMSON
- ✓ Bellarmine Knights at Queens Royals Womens Basketball
- ✓ DALVIN LA MELODIA - USA TOUR 2026

**`seatgeek@chicago`**
- ✕ TBD at Chicago Bulls — _placeholder_matchup_
- ✓ Northwestern Wildcats Men's Basketball vs. DePaul Blue Demons Men's Basketball
- ✓ Joffrey Ballet - Notes On Love ×8
- ✓ Saint Louis Billikens at Loyola Chicago Ramblers Womens Basketball

**`seatgeek@dallas`**
- ✕ TBD at Dallas Mavericks — _placeholder_matchup_
- ✓ Doughboys Live With Nick Wiger & Mike Mitchell
- ✓ SMU Mustangs Mens Basketball vs. Georgia Tech Yellow Jackets Mens Basketball
- ✓ Virginia Cavaliers at SMU Mustangs Womens Basketball

**`seatgeek@denver`**
- ✕ TBD at Denver Nuggets — _placeholder_matchup_
- ✓ Scott Bradlee's Postmodern Jukebox - The Future Is Vintage World Tour
- ✓ Jesse Cook: Forever Live Tour
- ✓ Peter Antoniou: Brain Teaser

**`seatgeek@detroit`**
- ✕ TBD at Detroit Pistons — _placeholder_matchup_
- ✓ Sueco with Jeris Johnson
- ✓ Kim Mitchell with David Wilcox
- ✓ Contre Jour: Lee Ranaldo + Leah Singer

**`seatgeek@fresno`**
- ✕ TBD at Fresno State Bulldogs Football — _placeholder_matchup_
- ✓ Shakedown Citi
- ✓ Oceanside Shock at Fresno Falcons ×2
- ✓ Miss May I and Born of Osiris with Convictions and Downswing

**`seatgeek@hampton_roads`**
- ✕ TBD at Old Dominion Monarchs Womens Basketball — _placeholder_matchup_
- ✓ Duke Blue Devils at Norfolk State Spartanettes Womens Basketball
- ✓ Fox N' Vead
- ✓ Old Dominion Monarchs Womens Basketball vs. Virginia Cavaliers Womens Basketball

**`seatgeek@houston`**
- ✕ TBD at Houston Rockets — _placeholder_matchup_
- ✓ Gerardo Coronel y Pancho Uresti
- ✓ Crankdat (18 and Over)
- ✓ Inna

**`seatgeek@indianapolis`**
- ✕ TBD at Indiana Pacers — _placeholder_matchup_
- ✓ Indiana Pacers vs. Los Angeles Lakers
- ✓ Butler Bulldogs Men's Basketball vs. Bellarmine University Knights Mens Basketball
- ✓ Butler Bulldogs Men's Basketball vs. Providence College Men's Basketball

**`seatgeek@memphis`**
- ✕ TBD at Memphis Grizzlies — _placeholder_matchup_
- ✓ North Texas Mean Green at Memphis Tigers Womens Basketball
- ✓ Memphis Grizzlies vs. LA Clippers ×2
- ✓ Memphis Grizzlies vs. Phoenix Suns

**`seatgeek@miami`**
- ✕ TBD at Miami Heat — _placeholder_matchup_
- ✓ Inna
- ✓ The Tenors
- ✓ Kid Fury

**`seatgeek@milwaukee`**
- ✕ TBD at Milwaukee Bucks — _placeholder_matchup_
- ✓ The High Kings - The Power Of The People
- ✓ Brian Cox
- ✓ Andrew Bird w/ Milwaukee Symphony Orchestra

**`seatgeek@minneapolis`**
- ✕ TBD at Minnesota Timberwolves — _placeholder_matchup_
- ✓ Rutgers Scarlet Knights at Minnesota Golden Gophers Wrestling
- ✓ Saosin with Silent Planet, Like Moths To Flames and SAVE US
- ✓ KATSEYE: THE WILDWORLD TOUR

**`seatgeek@nyc`**
- ✕ TBD at Gotham FC - NWSL Semifinals — _placeholder_matchup_
- ✓ Lenny Pearce
- ✓ The Play That Goes Wrong - New York ×8
- ✓ Donny Benet (18 and Over)

**`seatgeek@oklahoma_city`**
- ✕ TBD at Oklahoma City Thunder — _placeholder_matchup_
- ✓ Deorro
- ✓ Oklahoma City Philharmonic - Fate, Fire & Fantasy
- ✓ Stockton Kings at Oklahoma City Blue

**`seatgeek@orlando`**
- ✕ TBD at Orlando Magic — _placeholder_matchup_
- ✓ Chris Fleming
- ✓ David Bisbal - Tour Eternos 2026
- ✓ UCF Knights Womens Basketball vs. Austin Peay Governors Womens Basketball

**`seatgeek@philadelphia`**
- ✕ TBD at Philadelphia 76ers — _placeholder_matchup_
- ✓ SeJoe
- ✓ Fordham Rams at Saint Joseph's Hawks Womens Basketball
- ✓ Dartmouth Big Green at Temple Owls Mens Basketball

**`seatgeek@phoenix`**
- ✕ TBD at Phoenix Suns — _placeholder_matchup_
- ✓ Paige Fish - The Midnight Crisis Tour
- ✓ Mojo Brookzz with Nate Jackson (18+)
- ✓ Hawaii at Grand Canyon Lopes Womens Basketball

**`seatgeek@portland`**
- ✕ TBD at Portland Trail Blazers — _placeholder_matchup_
- ✓ Ron Funches ×2
- ✓ Fred Armisen: Comedy For Musicians But Everyone Is Welcome ×2
- ✓ Karen Rontowski

**`seatgeek@sacramento`**
- ✕ TBD at Sacramento Kings — _placeholder_matchup_
- ✓ Welcome To The West
- ✓ By All Means Comedy Competition ×2
- ✓ Jeff Dye ×3

**`seatgeek@salt_lake_city`**
- ✕ TBD at Utah Jazz — _placeholder_matchup_
- ✓ Derrick Stroup
- ✓ Layton Giordani (19+)
- ✓ Beartooth with Don Broco, Magnolia Park and Windwaker

**`seatgeek@san_antonio`**
- ✕ TBD at San Antonio Spurs — _placeholder_matchup_
- ✓ Hell's Kitchen - San Antonio ×8
- ✓ San Antonio Spurs vs. Detroit Pistons
- ✓ Tony Rock ×5

**`seatgeek@san_diego`**
- ✕ TBD at San Diego Wave FC - NWSL Semifinals — _placeholder_matchup_
- ✓ Testify - Rage Against the Machine Tribute
- ✓ The Sheepdogs
- ✓ Proper NYE/NYD - Thursday (21+)

**`seatgeek@san_francisco`**
- ✕ TBD at Golden State Warriors — _placeholder_matchup_
- ✓ California Golden Bears Mens Basketball vs. Syracuse University Mens Basketball
- ✓ Portland Pilots at San Francisco Dons Womens Basketball
- ✓ Frequency 8

**`ticketmaster@columbus`**
- ✕ TBA — _placeholder_
- ✓ Micky Dolenz
- ✓ 2026 82MAJOR [82CLUB : out of control] TOUR in Columbus
- ✓ The Casualties

**`ticketmaster@las_vegas`**
- ✕ Test — _placeholder_
- ✓ UNLV Rebels Mens Basketball vs. Wyoming Cowboys Mens Basketball
- ✓ Aussie Heat / Las Vegas' Most Hands-On Male Revue ×8
- ✓ The Conjurors at The Magicians Room ×8

**`ticketmaster@los_angeles`**
- ✕ Test — _placeholder_
- ✓ Los Angeles Kings vs. Detroit Red Wings
- ✓ Collect-A-Con (Los Angeles 2, CA)
- ✓ SVDDEN DEATH

**`ticketmaster@philadelphia`**
- ✕ Test — _placeholder_
- ✓ Hans Williams
- ✓ VOILA
- ✓ Cristina Mariani

**`ticketmaster@washington_dc`**
- ✕ Test — _placeholder_
- ✓ Capitals vs Islanders (Margaritaville)
- ✓ Alter Bridge - What Lies Within Tour
- ✓ Wizards VIP Packages: 1/7/2027

**`zinc_bar@nyc`**
- ✕ Club Closed for the Holiday — _closure_
- ✓ Valtinho Anastácio ×8
- ✓ Sarah Hanahan Quartet
- ✓ Chris Beck Quartet

</details>

## FIU

Published Miami listings mentioning "withdraw": **0**. Held back:

- Fall B: Last day to withdraw from the University with a WI grade — `academic_calendar`: an academic-calendar date (withdraw, drop/add, refunds, grades, finals, term start/end), not an event

## Known gaps and judgment calls

- **Golden-set disagreements I left as labelled.** Labels are the blind labeller's; where I disagree I say so here instead of editing the label. See `pytest tests/unit/test_listing_gate_golden.py -s` for the current misses.
- **Placeholder opponents** ("Cavaliers vs. TBD") are kept: the game happens. The labeller called one a non-event (unsure).
- **Cancelled listings** stay in the export marked cancelled (the city page hides them; a saved event still says it was cancelled), so the gate doesn't hold them back.
- **License-signal openings** ("— new business registration") are a separate kind (`opening`), shown as openings, not events; the gate doesn't apply to them.
- **Public board/commission meetings** are held back as administration (soft rule): a newcomer rarely wants a zoning board's business meeting. Community and neighborhood meetings, public input sessions, town halls and candidate forums are kept.
- **Campus audience tags.** A campus listing tagged only for current students / faculty / staff (no public tag) is held back unless its title or description says it's a performance, exhibition, game, talk, screening, celebration or fair. A bare "Students" tag doesn't count: campuses put it on public events too.
- **Uncategorized campus listings are published** (as uncategorized, with no estimates). A rule that held them back was retired after the cold data review found about 55% of them were real talks and exhibitions.
- **Same title, different verdicts.** A campus can tag occurrences of one program differently, so one date may be held and another published. The audit shows both.
- **Away games** ("Football at Missouri") on campus athletics feeds aren't gated by title: many "X at Y" games are crosstown. That needs a venue-distance check (idea ledger).
