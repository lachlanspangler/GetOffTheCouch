# Non-events audit (ADR-0010)

_Generated 2026-11-02 21:02 UTC by `scripts/non_events_audit.py` from `gotc.db` after a full build. Re-run after any rule change._

## Summary

- **92,706** listings published (per source membership), **705** held back by the build-time gate, **0** skipped at ingest (online-only, excluded places, campus-internal) — every one quarantined in `gated_listings` with its rule and reason, never silently dropped.
- Golden set (`tests/fixtures/listing_gate/golden.yaml`, labelled blind to the rules): **245 labelled listings · precision 0.987 · recall 0.907** `{'tn': 158, 'tp': 78, 'fn': 8, 'fp': 1}`
- The FIU withdrawal deadline that started this: see *FIU* below.

## Top rules

| Rule | Held back | Family |
|---|---|---|
| `campus_internal_audience` | 329 | internal_only |
| `appointment` | 105 | appointment |
| `closure` | 52 | closure |
| `campus_uncategorized` | 31 | no_public_signal |
| `governance_meeting` | 30 | governance_meeting |
| `campus_admissions` | 25 | internal_only |
| `campus_term_date` | 23 | academic_calendar |
| `campus_career` | 21 | internal_only |
| `internal_only` | 18 | internal_only |
| `office_hours` | 17 | office_hours |
| `campus_meeting` | 15 | internal_only |
| `campus_academic_admin` | 14 | internal_only |
| `admin_deadline` | 12 | admin_deadline |
| `academic_calendar` | 8 | academic_calendar |
| `placeholder` | 5 | placeholder |

## Top rejected patterns (matched text)

| Rule | Matched text | Count |
|---|---|---|
| `campus_internal_audience` | label 'students' | 174 |
| `campus_internal_audience` | label 'current students' | 48 |
| `campus_internal_audience` | label 'faculty & staff' | 47 |
| `appointment` | one-on-one | 46 |
| `campus_uncategorized` | category basis fallback | 31 |
| `campus_term_date` | spring: | 23 |
| `closure` | closed for veterans | 23 |
| `appointment` | one on one | 21 |
| `closure` | closed for | 18 |
| `office_hours` | office hours | 17 |
| `campus_internal_audience` | label 'staff' | 15 |
| `appointment` | 1-on-1 | 15 |
| `governance_meeting` | committee meeting | 12 |
| `admin_deadline` | applications open | 11 |
| `campus_internal_audience` | label 'graduate students' | 11 |
| `appointment` | by appointment | 11 |
| `internal_only` | private event | 10 |
| `appointment` | 1 on 1 | 9 |
| `campus_internal_audience` | label 'student organizations' | 9 |
| `campus_admissions` | info session | 8 |
| `campus_admissions` | information session | 8 |
| `campus_internal_audience` | label 'sjsu employees' | 7 |
| `campus_academic_admin` | study abroad | 5 |
| `governance_meeting` | board meeting | 5 |
| `academic_calendar` | fall b: | 5 |
| `campus_meeting` | weekly meeting | 4 |
| `campus_academic_admin` | syllabus | 4 |
| `placeholder` | test | 4 |
| `governance_meeting` | board" meeting | 4 |
| `campus_career` | career services | 4 |
| `campus_internal_audience` | label 'undergraduate students' | 4 |
| `campus_internal_audience` | label 'students - undergraduates' | 4 |
| `campus_academic_admin` | grand rounds | 3 |
| `campus_career` | internships | 3 |
| `campus_career` | internship | 3 |
| `campus_admissions` | campus visit | 3 |
| `closure` | library closed | 3 |
| `campus_internal_audience` | label 'students - graduates' | 3 |
| `governance_meeting` | committee meetings | 2 |
| `governance_meeting` | oversight committee meeting | 2 |

## Per source

Kept = published listings from this source; held = quarantined (gate + ingest). Samples are random (seeded):
read the held-back column for anything real, and the kept column for anything that isn't.

### University (35 units · 1,690 kept · 500 held back)

| Unit | Kept | Held | Share held | Top rules |
|---|---|---|---|---|
| `fiu_events@miami` | 61 | 108 | 64% | campus_internal_audience 45, campus_term_date 23, campus_career 11 |
| `utaustin_events@austin` | 237 | 102 | 30% | campus_internal_audience 46, campus_uncategorized 19, governance_meeting 13 |
| `bham_uab_events@birmingham` | 43 | 84 | 66% | campus_internal_audience 73, campus_admissions 8, campus_academic_admin 3 |
| `usc_events@los_angeles` | 98 | 61 | 38% | campus_internal_audience 60, campus_career 1 |
| `sjsu_events@san_jose` | 54 | 31 | 36% | campus_internal_audience 30, campus_academic_admin 1 |
| `stanford_events@san_jose` | 177 | 26 | 13% | campus_internal_audience 22, internal_only 2, campus_meeting 2 |
| `clt_uncc_events@charlotte` | 63 | 20 | 24% | campus_internal_audience 17, campus_career 3 |
| `ncsu_events@raleigh` | 79 | 18 | 19% | campus_internal_audience 17, campus_academic_admin 1 |
| `vanderbilt_events@nashville` | 11 | 10 | 48% | campus_internal_audience 9, campus_career 1 |
| `umkc_events@kansas_city` | 32 | 8 | 20% | campus_meeting 7, campus_admissions 1 |
| `pitt_events@pittsburgh` | 49 | 6 | 11% | campus_internal_audience 5, closure 1 |
| `cmu_events@pittsburgh` | 14 | 4 | 22% | campus_admissions 4 |
| `northeastern_events@boston` | 13 | 4 | 24% | internal_only 1, campus_admissions 1, campus_career 1 |
| `nyu_events@nyc` | 6 | 4 | 40% | campus_internal_audience 2, campus_uncategorized 1, governance_meeting 1 |
| `okc_uco_events@oklahoma_city` | 22 | 3 | 12% | campus_internal_audience 2, campus_career 1 |
| `ucf_events@orlando` | 47 | 3 | 6% | internal_only 2, campus_admissions 1 |
| `rice_events@houston` | 67 | 2 | 3% | campus_admissions 2 |
| `uw_events@seattle` | 56 | 2 | 3% | campus_uncategorized 1, campus_academic_admin 1 |
| `berkeley_events@san_francisco` | 8 | 1 | 11% | campus_career 1 |
| `uc_events@cincinnati` | 4 | 1 | 20% | campus_career 1 |
| `unf_events@jacksonville` | 50 | 1 | 2% | campus_admissions 1 |
| `up_events@portland` | 27 | 1 | 4% | campus_internal_audience 1 |
| `emory_events@atlanta` | 38 | 0 | 0% |  |
| `gsu_events@atlanta` | 16 | 0 | 0% |  |
| `gwu_events@washington_dc` | 11 | 0 | 0% |  |
| `hfd_trinity_arts_events@hartford` | 2 | 0 | 0% |  |
| `pvd_brown_events@providence` | 22 | 0 | 0% |  |
| `sacstate_events@sacramento` | 56 | 0 | 0% |  |
| `tampa_ut_events@tampa` | 6 | 0 | 0% |  |
| `towson_events@baltimore` | 33 | 0 | 0% |  |
| `ucr_events@riverside` | 165 | 0 | 0% |  |
| `ucsd_events@san_diego` | 65 | 0 | 0% |  |
| `umn_events@minneapolis` | 1 | 0 | 0% |  |
| `uta_events@dallas` | 38 | 0 | 0% |  |
| `utdallas_events@dallas` | 19 | 0 | 0% |  |

<details><summary>Samples: kept vs held back</summary>

**`fiu_events@miami`**
- ✕ Mindful Mondays - Workshop — _campus_internal_audience_
- ✕ TTR: Leadership and Personal Branding in a Tech-Saturated Era — _campus_uncategorized_
- ✕ AI for Communications Masterclass — _campus_internal_audience_
- ✕ CEC - Networking, Communication, and Soft Skills workshop — _campus_internal_audience_
- ✓ FIU Latin Jazz Concert
- ✓ The Dean’s Perspective: Understanding the Legal Market
- ✓ Understanding the Midterms: What the Results Reveal and the Road Ahead

**`utaustin_events@austin`**
- ✕ Student Affairs Meeting — _campus_meeting_
- ✕ Afternoon Yoga — _campus_internal_audience_
- ✕ Turkey Trot — _campus_internal_audience_
- ✕ Campus Open Recovery — _campus_internal_audience_
- ✓ First-Gen Celebration
- ✓ AHA BLS Provider (CPR) Certification
- ✓ 2026 Post-Election Debriefing

**`bham_uab_events@birmingham`**
- ✕ Effective Communication and Respect — _campus_internal_audience_
- ✕ Be Confident in Your Confidence — _campus_internal_audience_
- ✕ Fostering International Student Success at UAB - CTL Building Block — _campus_internal_audience_
- ✕ Healthy Relationship Workshop — _campus_internal_audience_
- ✓ ASO Masterworks: English Light
- ✓ Fall Brass Ensembles Concert
- ✓ Opera Scenes

**`usc_events@los_angeles`**
- ✕ Free Yoga Classes at the URC Fishbowl — _campus_internal_audience_
- ✕ Forbidden Pages: Past and Present — _campus_internal_audience_
- ✕ Free Yoga Classes at the URC Fishbowl — _campus_internal_audience_
- ✕ Visit the USC Sustainability booth at the Trojan Farmers Market — _campus_internal_audience_
- ✓ Which Program is Right for Me? Comparing the Educational Counseling (EC) vs. Postsecondary Administration and 
- ✓ Eco Media Film Fest x Impact Weekend
- ✓ 2026 Delta Murphy Lecture: “How Free Market Thinking Has Blocked Climate Action”

**`sjsu_events@san_jose`**
- ✕ Build Your Own Learning Community with Padlet — _campus_internal_audience_
- ✕ Crafts of Light: A Diwali, Tihar, Bandi Chhor Divas Celebration — _campus_internal_audience_
- ✕ Boldly You: Learning How to Make Connections — _campus_internal_audience_
- ✕ Writing Workshop: Emailing Netiquette: Academic and Professional Communication — _campus_internal_audience_
- ✓ Finance with AI for SMBs / Hosted by Silicon Valley SBDC x Bizzaly
- ✓ Opening Reception - Natalie and James Thompson Gallery: Common Ground
- ✓ Art of Remembrance Ofrenda Exhibit

**`stanford_events@san_jose`**
- ✕ A Rift in Time. Reinhart Koselleck and the Theory of History — _campus_internal_audience_
- ✕ Creative Teaching with AI — _campus_internal_audience_
- ✕ Big Earth Hackathon: Wildland Fire Challenge — _campus_internal_audience_
- ✕ Environmental Humanities Project: Graduate Student Work-in-progress Lab — _campus_internal_audience_
- ✓ Gallery Conversations / JANE!
- ✓ When We Bridge: Indigenous Peoples’ Guardianship, Knowledge, and Global Impact
- ✓ Electric Contrasts: the Art of the Detail

**`clt_uncc_events@charlotte`**
- ✕ Part 1: Canvas Accessibility with UDOIT — _campus_internal_audience_
- ✕ Rock Climbing Night at the SAC — _campus_internal_audience_
- ✕ Part 1: Canvas Accessibility with UDOIT — _campus_internal_audience_
- ✕ Resume Workshop with LandDesign for Civil + Environmental Engineering — _campus_career_
- ✓ Azure Workshop Week 4
- ✓ SOLD Council Workshop: Transferrable Organization Skills & Celebration
- ✓ Qualtrics 102

**`ncsu_events@raleigh`**
- ✕ Glow Up for Mental Health — _campus_internal_audience_
- ✕ LaunchPad Incubator — _campus_internal_audience_
- ✕ Teamwork in Research Groups — _campus_internal_audience_
- ✕ Study Abroad: Your Global Experience, Your Career Advantage — _campus_academic_admin_
- ✓ Fall Chamber Singers and Instrumentalists Concert
- ✓ Global Film Series: L'Histoire de Souleymane/Souleymane’s Story
- ✓ Fall Dance Concert

**`vanderbilt_events@nashville`**
- ✕ Los CorreDores Spanish Run Club — _campus_internal_audience_
- ✕ German Conversation Hour — _campus_internal_audience_
- ✕ Mindfulness for Everyday Life 4-Week Workshop — _campus_internal_audience_
- ✕ French Conversation Hour — _campus_internal_audience_
- ✓ Studio VU Visiting Artist Fritz Horstman with Artist Lecture
- ✓ Department of Physics & Astronomy: Guy & Rebecca Forman Lecture in Science Education
- ✓ CEE Frank L. Parker Distinguished Professor Lecture: J.N. Reddy, Texas A&M University*

**`umkc_events@kansas_city`**
- ✕ Concrete Canoe Weekly Meeting — _campus_meeting_
- ✕ Concrete Canoe Hull Design Meeting — _campus_meeting_
- ✕ First Gen Celebration: First Gen Study Abroad info session — _campus_admissions_
- ✕ Concrete Canoe Weekly Meeting — _campus_meeting_
- ✓ Show Me Success Workshop: Steps After Graduation
- ✓ Master Class: Steven Multer, horn
- ✓ Composers’ Guild Concert #3

**`pitt_events@pittsburgh`**
- ✕ Heinz Chapel Choir Campus Holiday Concert — _closure_
- ✕ Compromised: The Black Educator's Fight for Equity - Screening — _campus_internal_audience_
- ✕ CAAPP Presents: Facing The Wilderness w/ MaKshya Tolbert & Kira Tucker — _campus_internal_audience_
- ✕ The Commeration of the Holodomor and Other Atrocities — _campus_internal_audience_
- ✓ Pitt Public Market
- ✓ Film Screening of Malês
- ✓ Polish Film Festival: What Belongs to Others (Cudze rzeczy, 2026)

**`cmu_events@pittsburgh`**
- ✕ Campus Visit (Info Session + Campus Tour) — _campus_admissions_
- ✕ Virtual Student-Led Campus Tour — _campus_admissions_
- ✕ Campus Visit (Info Session + Campus Tour) — _campus_admissions_
- ✕ Campus Visit (Info Session + Campus Tour) — _campus_admissions_
- ✓ Tai Chi and QiGong Series
- ✓ Hands-On: Mini Painting with the RPG Collection
- ✓ Kearra Amaya Gopee: Carnegie Mellon University School of Art Visiting Artist Lecture Series

**`northeastern_events@boston`**
- ✕ 2026 AIChE Annual Conference Student Recruitment Fair — _campus_career_
- ✕ Northeastern University Graduate Fair: Unlock Your Double Husky Scholarship — _campus_admissions_
- ✕ Boston Graduate Fair - Fall 2026 — _internal_only_
- ✕ Fusion Book Club Meeting — _campus_meeting_
- ✓ Daily Yoga
- ✓ Daily Yoga
- ✓ Daily Yoga

**`nyu_events@nyc`**
- ✕ Tips & Tricks for Interviewing — _campus_internal_audience_
- ✕ Ceramics Class — _campus_internal_audience_
- ✕ NYU Strawberry Festival committee meeting — _governance_meeting_
- ✕ 2026 MFA Project Space — _campus_uncategorized_
- ✓ 2026 APHA Annual Meeting and Expo
- ✓ CANCELED: APO Eboard + Chapter + Pledge Class
- ✓ APO Eboard + Chapter + Pledge Class

**`okc_uco_events@oklahoma_city`**
- ✕ Wednesday Wellness Walk — _campus_internal_audience_
- ✕ Wednesday Wellness Walk — _campus_internal_audience_
- ✕ PGA Golf Management Career & Internship Fair — _campus_career_
- ✓ Craft N Yap
- ✓ Ceramics Workshop
- ✓ Chamber Orchestra in Concert

**`ucf_events@orlando`**
- ✕ 3D Printing Basics: From Digital to Physical — _internal_only_
- ✕ Reduce Obstacles, Increase Engagement: An Introduction to Open Education — _internal_only_
- ✕ Writing Lab: Admission Essays — _campus_admissions_
- ✓ Blues for an Alabama Sky / Theatre UCF
- ✓ Blues for an Alabama Sky / Theatre UCF
- ✓ Hybrid Futures: Image, Music and Text, a Reading with J. Mae. Barizo

**`rice_events@houston`**
- ✕ Graduate Student Ambassador Campus Tour (In-person) — _campus_admissions_
- ✕ Rice Global Paris Summer Program: Info Session and Course Fair — _campus_admissions_
- ✓ Jewish Book and Arts Festival, Community Reading
- ✓ Class of 2001’s 25th Reunion Reception
- ✓ A Human Year is Seven Earth Years

**`uw_events@seattle`**
- ✕ Laboratory Medicine Grand Rounds: Thao Truong, PhD, D(ABMM) - What's On Our Plate Today? Automating Microbiolo — _campus_academic_admin_
- ✕ UWCFD Holiday Evergreen Sale — _campus_uncategorized_
- ✓ Phèdre
- ✓ Daily 15 Minute Movement Break - Yoga and Fitness
- ✓ Class Visit - Enhancing Leadership Effectiveness

**`berkeley_events@san_francisco`**
- ✕ [BCLT] 1L Tech & IP Recruiting Fair — _campus_career_
- ✓ CJ Week: Eco-Optimism Knowledge Share and Zine Workshop
- ✓ Día de los Muertos Altar Exhibition & Reception
- ✓ Tendon thread feat. Tanya Lukin Linklater

**`uc_events@cincinnati`**
- ✕ U.S. Customs and Border Protection Virtual Career Expo – November 3rd — _campus_career_
- ✓ Commuter Student Lounge: Winter Safety & Preparedness Fair
- ✓ Día de los Muertos Celebration
- ✓ CCM Composers Concert: A View From The Edge

**`unf_events@jacksonville`**
- ✕ Illuminate Your Future: Ed.D. Info Sessions — _campus_admissions_
- ✓ Construction Quality Management for Contractors
- ✓ Día de Muertos/Day of the Dead Downtown Jacksonville
- ✓ Winter Wind Chamber Music

**`up_events@portland`**
- ✕ Dialogue Dinner: Fasting & Feasting — _campus_internal_audience_
- ✓ Macbeth by William Shakespeare
- ✓ University of Portland Men's Basketball vs East Texas A&M
- ✓ University of Portland Women's Basketball vs UC Santa Barbara

</details>

### Library (51 units · 9,405 kept · 157 held back)

| Unit | Kept | Held | Share held | Top rules |
|---|---|---|---|---|
| `sjpl_events@san_jose` | 403 | 44 | 10% | appointment 44 |
| `phoenix_public_library_events@phoenix` | 252 | 17 | 6% | closure 17 |
| `wccls_events@portland` | 209 | 14 | 6% | appointment 11, closure 3 |
| `hfd_public_library_events@hartford` | 175 | 11 | 6% | appointment 11 |
| `pvd_east_providence_library_events@providence` | 80 | 11 | 12% | appointment 11 |
| `clt_cmlibrary_events@charlotte` | 357 | 8 | 2% | appointment 8 |
| `bpl_events@boston` | 365 | 7 | 2% | appointment 7 |
| `kcls_events@seattle` | 209 | 6 | 3% | office_hours 5, appointment 1 |
| `sccl_events@san_jose` | 129 | 6 | 4% | closure 6 |
| `spl_events@seattle` | 142 | 5 | 3% | office_hours 4, closure 1 |
| `chipublib_events@chicago` | 922 | 4 | 0% | office_hours 4 |
| `mdpls_events@miami` | 446 | 4 | 1% | governance_meeting 4 |
| `jocolibrary_events@kansas_city` | 80 | 3 | 4% | appointment 2, governance_meeting 1 |
| `ocls_events@orlando` | 630 | 3 | 0% | office_hours 3 |
| `bham_hoover_library_events@birmingham` | 21 | 2 | 9% | appointment 2 |
| `norfolk_library_events@hampton_roads` | 56 | 2 | 3% | closure 2 |
| `oakland_library_events@san_francisco` | 148 | 2 | 1% | appointment 2 |
| `westerville_library_events@columbus` | 38 | 2 | 5% | closure 1, governance_meeting 1 |
| `hcpl_events@houston` | 250 | 1 | 0% | appointment 1 |
| `heights_libraries_events@cleveland` | 98 | 1 | 1% | governance_meeting 1 |
| `indypl_events@indianapolis` | 148 | 1 | 1% | appointment 1 |
| `lvccld_events@las_vegas` | 370 | 1 | 0% | appointment 1 |
| `pvd_cranston_library_events@providence` | 104 | 1 | 1% | governance_meeting 1 |
| `pvd_pawtucket_library_events@providence` | 49 | 1 | 2% | governance_meeting 1 |
| `afpl_events@atlanta` | 311 | 0 | 0% |  |
| `arapahoe_library_events@denver` | 119 | 0 | 0% |  |
| `bham_bpl_events@birmingham` | 101 | 0 | 0% |  |
| `bham_homewood_library_events@birmingham` | 25 | 0 | 0% |  |
| `ccpl_events@cleveland` | 211 | 0 | 0% |  |
| `chandler_library_events@phoenix` | 121 | 0 | 0% |  |
| `chesapeake_library_events@hampton_roads` | 41 | 0 | 0% |  |
| `chpl_events@cincinnati` | 379 | 0 | 0% |  |
| `corona_library_events@riverside` | 114 | 0 | 0% |  |
| `dcpl_events@washington_dc` | 195 | 0 | 0% |  |
| `dekalb_library_events@atlanta` | 111 | 0 | 0% |  |
| `grandview_library_events@columbus` | 7 | 0 | 0% |  |
| `grpl_events@grand_rapids` | 45 | 0 | 0% |  |
| `hclib_events@minneapolis` | 214 | 0 | 0% |  |
| `henrico_library_events@richmond` | 106 | 0 | 0% |  |
| `jax_library_events@jacksonville` | 125 | 0 | 0% |  |
| `jeffco_library_events@denver` | 140 | 0 | 0% |  |
| `kdl_events@grand_rapids` | 107 | 0 | 0% |  |
| `mpl_events@milwaukee` | 187 | 0 | 0% |  |
| `pratt_library_events@baltimore` | 144 | 0 | 0% |  |
| `rpl_events@richmond` | 32 | 0 | 0% |  |
| `sacpl_events@sacramento` | 99 | 0 | 0% |  |
| `sdcl_events@san_diego` | 223 | 0 | 0% |  |
| `slcolibrary_events@salt_lake_city` | 171 | 0 | 0% |  |
| `slcpl_events@salt_lake_city` | 89 | 0 | 0% |  |
| `slpl_events@st_louis` | 134 | 0 | 0% |  |
| `tampa_hcplc_events@tampa` | 173 | 0 | 0% |  |

<details><summary>Samples: kept vs held back</summary>

**`sjpl_events@san_jose`**
- ✕ 1-on-1 Tech Help by Appointment — _appointment_
- ✕ One-On-One Tech Help — _appointment_
- ✕ Tech Mentor: One on One Computer Help — _appointment_
- ✕ Digital Skills: One-On-One Tech Help for Seniors — _appointment_
- ✓ 大朋友(50+)社區团体活动 / Chinese Orchestra
- ✓ Indoor Family Storytime
- ✓ Saturday Fun: Arts, Crafts, and More

**`phoenix_public_library_events@phoenix`**
- ✕ Library closed for Veterans Day — _closure_
- ✕ Library closed for Veterans Day — _closure_
- ✕ Library closed for Veterans Day — _closure_
- ✕ Library closed for Veterans Day — _closure_
- ✓ Red Cross Blood Drive
- ✓ Teen Adventure Hour
- ✓ Afternoons at Ocotillo

**`wccls_events@portland`**
- ✕ Library Closed — _closure_
- ✕ Digital Navigator – One-on-One Tech Help/ Navegador Digital – Apoyo Uno a Uno — _appointment_
- ✕ Digital Navigator – One-on-One Tech Help — _appointment_
- ✕ Digital Navigator: One-on-One Tech Help — _appointment_
- ✓ Science Storytime: Rain Cycle Science
- ✓ Intercambio Language Exchange
- ✓ Read to the Dogs/Lee a los perros

**`hfd_public_library_events@hartford`**
- ✕ One-on-One Financial Coaching (By Appointment Only) — _appointment_
- ✕ 1-on-1 Business Advising with CEDF - — _appointment_
- ✕ One-on-One Financial Coaching (By Appointment Only) — _appointment_
- ✕ 1-on-1 Business Advising with WBDC — _appointment_
- ✓ Pumpkin Contest
- ✓ Self Care Sesh
- ✓ Pearson Test Center testing

**`pvd_east_providence_library_events@providence`**
- ✕ One on One Tech Help — _appointment_
- ✕ One on One Tech Help — _appointment_
- ✕ One on One Tech Help — _appointment_
- ✕ One on One Tech Help — _appointment_
- ✓ Providence Children's Film Festival's Jury Night
- ✓ Frankenbots
- ✓ Meatless Meals: Brownies

**`clt_cmlibrary_events@charlotte`**
- ✕ Library eBooks & More: 1-on-1 Support Session — _appointment_
- ✕ My Next Step for Teens: Ask A Librarian 1-on-1 — _appointment_
- ✕ 1-on-1 Small Business Resource Help — _appointment_
- ✕ BOSS+MODE: Resume & Job Help 1-on-1 for Teens — _appointment_
- ✓ Haunted Houses & Hidden Histories: Researching the Ghosts of Your Home
- ✓ Baby Storytime
- ✓ Reading Buddies

**`bpl_events@boston`**
- ✕ Tech Help by Appointment — _appointment_
- ✕ Tech Help by Appointment — _appointment_
- ✕ Tech Help by Appointment — _appointment_
- ✕ Tech Help (By Appointment) — _appointment_
- ✓ All-Ages Story Time
- ✓ Colors and the Art World with Talia Bega (Ages 5-12)
- ✓ LEGO Club

**`kcls_events@seattle`**
- ✕ King County Department of Local Services Office Hours — _office_hours_
- ✕ King County Department of Local Services Office Hours — _office_hours_
- ✕ In-person Medicare 1:1 Counseling (Appointment Only) — _appointment_
- ✕ King County Local Services: Community Vans Office Hours — _office_hours_
- ✓ Tech Help for Seniors
- ✓ English Language Learning (ELL) Classes
- ✓ STEAM Family Story Time

**`sccl_events@san_jose`**
- ✕ Saratoga Library Closed for Veterans Day — _closure_
- ✕ Los Altos Library Closed for Veterans Day — _closure_
- ✕ Cupertino Library Closed for Veterans Day — _closure_
- ✕ Campbell Library Closed for Veterans Day — _closure_
- ✓ Adult Nonfiction Book Discussion: Nothing to Envy: Ordinary Lives in North Korea
- ✓ Music & Movement Storytime
- ✓ Peter Fletcher Classical Guitar Concert

**`spl_events@seattle`**
- ✕ Office Hours with Department of Neighborhoods — _office_hours_
- ✕ Office Hours with Department of Neighborhoods / Sesiones con el Departamento de Vecindarios — _office_hours_
- ✕ Library Closed in observance of Veterans Day — _closure_
- ✕ Office Hours with Department of Neighborhoods / Sesiones con el Departamento de Vecindarios — _office_hours_
- ✓ Kaleidoscope Play & Learn / 万花筒游戏和学习 / 萬花筒遊戲和學習
- ✓ English Conversation Circle
- ✓ Virtual & In-Person Citizenship Class - English

**`chipublib_events@chicago`**
- ✕ Teen Librarian Office Hours — _office_hours_
- ✕ Teen Librarian Office Hours — _office_hours_
- ✕ Teen Librarian Office Hours — _office_hours_
- ✕ Teen Librarian Office Hours — _office_hours_
- ✓ Shrinky Dink Pokémon Keychains
- ✓ Meet Calvin B. Jones: Make a Mini-Mural
- ✓ Zumba Go Chair Fitness

**`mdpls_events@miami`**
- ✕ The "Board" Meeting — _governance_meeting_
- ✕ The "Board" Meeting — _governance_meeting_
- ✕ The "Board" Meeting — _governance_meeting_
- ✕ The "Board" Meeting — _governance_meeting_
- ✓ Storytime Fun!
- ✓ Homework Help and Tutoring
- ✓ Audio Production with Logic Pro: Level 1

**`jocolibrary_events@kansas_city`**
- ✕ One-on-One Basic Genealogy Help — _appointment_
- ✕ One-on-One Basic Genealogy Help — _appointment_
- ✕ Johnson County Library Board Meeting — _governance_meeting_
- ✓ Preschool Storytime
- ✓ Meet the Author: Jennifer Lynn Barnes and Sarah Henning
- ✓ Yoga and Mindfulness

**`ocls_events@orlando`**
- ✕ District 10 Office Hours — _office_hours_
- ✕ District 10 Office Hours — _office_hours_
- ✕ District 35 Office Hours — _office_hours_
- ✓ Baby Tales
- ✓ Sewing - Fabric Bookmarks
- ✓ Baby Tales

**`bham_hoover_library_events@birmingham`**
- ✕ One-on-One Tech Help — _appointment_
- ✕ One-on-One Tech Help — _appointment_
- ✓ Beyond Words Book Club
- ✓ My First Resume Workshop
- ✓ Sound Bath and Mini-Brain Lecture

**`norfolk_library_events@hampton_roads`**
- ✕ Holiday Closure - Election Day — _closure_
- ✕ Holiday Closure - Veterans Day — _closure_
- ✓ Graphic Novel Society
- ✓ Driving Safety Awareness
- ✓ Driving Safety Awareness

**`oakland_library_events@san_francisco`**
- ✕ Neighborhood Business Assistance (by appointment only) — _appointment_
- ✕ Neighborhood Business Assistance (by appointment only) — _appointment_
- ✓ Bilingual Storytime/Hora de Cuentos Bilingüe
- ✓ Family Resource Navigators
- ✓ Teen Dungeons & Dragons Club @ Fruitvale

**`westerville_library_events@columbus`**
- ✕ Finance & Facilities: Board Committee Meeting — _governance_meeting_
- ✕ Closed for Staff Development Day — _closure_
- ✓ Canva 101
- ✓ Book to Movie Club
- ✓ Baby Storytime

**`hcpl_events@houston`**
- ✕ Cricut 1 on 1 Orientation — _appointment_
- ✓ Basic ESL
- ✓ Intro Computer Class
- ✓ Charcoal Drawing Class

**`heights_libraries_events@cleveland`**
- ✕ Committee Meeting — _governance_meeting_
- ✓ Afternoon Snack at the Library
- ✓ Tai Chi and Qigong
- ✓ Fall Fest at Noble

**`indypl_events@indianapolis`**
- ✕ Ask a CPA: One-on-One Nonprofit Finance Appointments (Register on Eventbrite) — _appointment_
- ✓ Teen Mystery: The Pharaoh's Curse
- ✓ Storytime with Professor Watermelon
- ✓ Career Center at East 38th Street

**`lvccld_events@las_vegas`**
- ✕ Device Advice: One on One Tech Help — _appointment_
- ✓ Homework Help & Tutoring
- ✓ Come Out and Clay
- ✓ LEGO League

**`pvd_cranston_library_events@providence`**
- ✕ Cranston Public Library Board of Trustees Meeting @ Central — _governance_meeting_
- ✓ The Other Book Group @ Central
- ✓ Knit & Crochet Group @ Auburn
- ✓ Space Ship Storytime @ Oak Lawn

**`pvd_pawtucket_library_events@providence`**
- ✕ Board of Trustees — _governance_meeting_
- ✓ Pawtucket Sustainability, Parks, & Mobility
- ✓ Storied Lives Book Club
- ✓ Family Zumba

</details>

### City & Civic Calendars (101 units · 4,557 kept · 8 held back)

| Unit | Kept | Held | Share held | Top rules |
|---|---|---|---|---|
| `mprb_events@minneapolis` | 22 | 4 | 15% | governance_meeting 4 |
| `creative_alliance_events@baltimore` | 72 | 1 | 1% | office_hours 1 |
| `fairytale_town_events@sacramento` | 21 | 1 | 5% | closure 1 |
| `scottsdale_city_events@phoenix` | 8 | 1 | 11% | governance_meeting 1 |
| `seattle_city_events@seattle` | 85 | 1 | 1% | governance_meeting 1 |
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
| `chicago_park_events@chicago` | 239 | 0 | 0% |  |
| `chicago_park_permits@chicago` | 32 | 0 | 0% |  |
| `clt_cmpd_community_events@charlotte` | 140 | 0 | 0% |  |
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
| `kc_roos_athletics@kansas_city` | 22 | 0 | 0% |  |
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
| `now_playing_utah@salt_lake_city` | 278 | 0 | 0% |  |
| `nyc_parks_events@nyc` | 447 | 0 | 0% |  |
| `nyc_permitted_events@nyc` | 196 | 0 | 0% |  |
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
- ✕ Board Meeting — _governance_meeting_
- ✕ Board Meeting — _governance_meeting_
- ✕ Board Meeting — _governance_meeting_
- ✓ Peace Garden Volunteering
- ✓ Nicollet Island Fall Market
- ✓ Solomon Park Off-Leash Recreation Area Community Open House #2

**`creative_alliance_events@baltimore`**
- ✕ Baker Artist Office Hours / NOV 2026 — _office_hours_
- ✓ Belly Dance with Naimah Dances / Winter
- ✓ Jóvenes en Acción 2026
- ✓ Momentum Award Conversation: Madyha Leghari, Ghazal Mojtahedi, and Bao Nguyen

**`fairytale_town_events@sacramento`**
- ✕ Closed for Thanksgiving — _closure_
- ✓ Toddler Time!
- ✓ Toddler Time!
- ✓ Homeschool Clubhouse: Art History

**`scottsdale_city_events@phoenix`**
- ✕ Citizens' Bond Oversight Committee - Regular - 11-16-26 — _governance_meeting_
- ✓ AZ Fall League / Scottsdale Scorpions
- ✓ Arts & Crafts Fair
- ✓ AZ Fall League / Scottsdale Scorpions

**`seattle_city_events@seattle`**
- ✕ Pioneer Square Preservation Board Meeting — _governance_meeting_
- ✓ Sound Medicine for Liberation and Healing
- ✓ Sturtevant Ravine Work Party!
- ✓ Seattle Forest Week at Discovery Park

</details>

### Venues & Other (474 units · 77,054 kept · 40 held back)

| Unit | Kept | Held | Share held | Top rules |
|---|---|---|---|---|
| `mr_tipples@san_francisco` | 71 | 6 | 8% | closure 5, internal_only 1 |
| `chris_jazz_cafe@philadelphia` | 89 | 4 | 4% | closure 3, internal_only 1 |
| `ticketmaster@los_angeles` | 1678 | 3 | 0% | closure 2, placeholder 1 |
| `ticketmaster@miami` | 343 | 3 | 1% | appointment 3 |
| `ticketmaster@san_francisco` | 1076 | 3 | 0% | internal_only 3 |
| `carousel_lounge@austin` | 45 | 2 | 4% | closure 2 |
| `cliff_bells@detroit` | 49 | 2 | 4% | closure 2 |
| `helium_comedy_philly@philadelphia` | 89 | 2 | 2% | internal_only 2 |
| `ticketmaster@st_louis` | 341 | 2 | 1% | internal_only 2 |
| `dakota_jazz@minneapolis` | 99 | 1 | 1% | internal_only 1 |
| `goodnights_comedy@raleigh` | 146 | 1 | 1% | closure 1 |
| `royal_room_seattle@seattle` | 8 | 1 | 11% | closure 1 |
| `ticketmaster@atlanta` | 934 | 1 | 0% | academic_calendar 1 |
| `ticketmaster@charlotte` | 315 | 1 | 0% | internal_only 1 |
| `ticketmaster@chicago` | 1628 | 1 | 0% | closure 1 |
| `ticketmaster@cincinnati` | 420 | 1 | 0% | governance_meeting 1 |
| `ticketmaster@columbus` | 512 | 1 | 0% | placeholder 1 |
| `ticketmaster@las_vegas` | 1952 | 1 | 0% | placeholder 1 |
| `ticketmaster@philadelphia` | 809 | 1 | 0% | placeholder 1 |
| `ticketmaster@seattle` | 740 | 1 | 0% | closure 1 |
| `ticketmaster@washington_dc` | 941 | 1 | 0% | placeholder 1 |
| `zinc_bar@nyc` | 64 | 1 | 2% | closure 1 |

<details><summary>Samples: kept vs held back</summary>

**`mr_tipples@san_francisco`**
- ✕ Closed for Private Event — _closure_
- ✕ Closed for Private Event — _closure_
- ✕ Closed for a Private Event — _closure_
- ✕ Private Event — _internal_only_
- ✓ Adam Shulman Sexet
- ✓ Patrick Wolff Quartet featuring Matt Wilson
- ✓ Kurt Ribak Quartet

**`chris_jazz_cafe@philadelphia`**
- ✕ Closed for Holiday — _closure_
- ✕ Closed for Thanksgiving — _closure_
- ✕ Private Party — _internal_only_
- ✕ Closed for Holiday — _closure_
- ✓ Vocalist Anaïs Reno with The Peter Bernstein/Aidan McKeon Quartet
- ✓ Josh Lawrence Holiday Show
- ✓ HFB Ensemble

**`ticketmaster@los_angeles`**
- ✕ Closed for Thanksgiving! — _closure_
- ✕ Test — _placeholder_
- ✕ Closed for Thanksgiving! — _closure_
- ✓ The Download Comedy Show ft. Kate Lav, OJ Stellar and more TBA
- ✓ Margaret Glaspy w/ Anna Tivel
- ✓ Snakehips

**`ticketmaster@miami`**
- ✕ 2027 Unrivaled Season 1 on 1 — _appointment_
- ✕ 2027 Unrivaled Season 1 on 1 — _appointment_
- ✕ Unrivaled 2027 Season 1 on 1 — _appointment_
- ✓ Monster Jam
- ✓ Miami City Ballet Presents George Balanchine's The Nutcracker (Recommended for ages 4 and Up)
- ✓ Giggly Squad Podcast

**`ticketmaster@san_francisco`**
- ✕ Private Event — _internal_only_
- ✕ Private Event — _internal_only_
- ✕ Private Event — _internal_only_
- ✓ Greg Fitzsimmons
- ✓ Rent
- ✓ Dana Gould

**`carousel_lounge@austin`**
- ✕ CLOSED – CHRISTMAS, hope its fabulous — _closure_
- ✕ THANKSGIVING – CLOSED come back tomorrow — _closure_
- ✓ Rasa Nova 7pm, Touch of Space 8-9pm (J. Daily)
- ✓ 5 After Midnight (Jay)
- ✓ J J Brat (Zamecki)

**`cliff_bells@detroit`**
- ✕ Closed for the Holiday — _closure_
- ✕ Closed for the Holiday — _closure_
- ✓ Duke Ellington’s Nutcracker Suite
- ✓ Soulful Holidays with the Sean Dobbins Organ Trio +
- ✓ Paul King

**`helium_comedy_philly@philadelphia`**
- ✕ Private Event — _internal_only_
- ✕ Private Event — _internal_only_
- ✓ Emily Catalano
- ✓ Daniela Mora
- ✓ Ian Fidance

**`ticketmaster@st_louis`**
- ✕ Book Your Private Event Today — _internal_only_
- ✕ Book Your Private Event Today — _internal_only_
- ✓ St. Louis Billikens Mens Basketball vs. Florida A&M Rattlers Mens Basketball
- ✓ Jodeci- 35th Anniversary Tour of Forever My Lady
- ✓ ALMOST MAINE By John Cariani, Directed by Doug Finlayson

**`dakota_jazz@minneapolis`**
- ✕ Private Event — _internal_only_
- ✓ Leo Kottke: Live at The Ordway
- ✓ The Peterson Family: ‘Twas the Jam Before Christmas
- ✓ The Cookers: 20th Anniversary Tour

**`goodnights_comedy@raleigh`**
- ✕ Closed for Private Event — _closure_
- ✓ Room 861 at Goodnights: Clint Coley
- ✓ Room 861 at Goodnights: Nicky Paris
- ✓ Special Event: Adam Conover

**`royal_room_seattle@seattle`**
- ✕ CLOSED FOR MAINTENANCE — _closure_
- ✓ We Are Stardust – A Jazz Tribute to Joni Mitchell
- ✓ MOXIE
- ✓ Prismia Presents “Midnight Girl” Music Video Release Show

**`ticketmaster@atlanta`**
- ✕ Cam Kirk Studios: Night School Final Exam — _academic_calendar_
- ✓ Grateful Shred
- ✓ Jungle Bells
- ✓ Broadway Rave / 18+

**`ticketmaster@charlotte`**
- ✕ OneWorld Health - Private Event — _internal_only_
- ✓ Mountain Grass Unit - Appalachian Smoke Tour
- ✓ Charlotte Hornets vs. Memphis Grizzlies
- ✓ MICO - IN:BETWEEN TOUR

**`ticketmaster@chicago`**
- ✕ Closed for Thanksgiving Holiday — _closure_
- ✓ Pearlsnap
- ✓ BEARS (vs Buccaneers) GAME on THE PATIO & IN SIDEBAR!
- ✓ Baz Luhrmanns Romeo & Juliet (NZL)

**`ticketmaster@cincinnati`**
- ✕ Koffin Kats/ Voodoo Glow Skulls w/ U.S. Daggers, Alex Kasznel & the Board of Directors — _governance_meeting_
- ✓ Cincinnati Bearcats Mens Basketball vs. TCU Horned Frogs Mens Basketball
- ✓ Cyclones v. Fuel / $2 Beer - Ugly Christmas Sweater Night
- ✓ The Menzingers: Everything I Ever Saw North American Tour

**`ticketmaster@columbus`**
- ✕ TBA — _placeholder_
- ✓ Maybe Happy Ending (Touring)
- ✓ Black Stone Cherry (All ages with adult)
- ✓ The Brokes at Woodlands Tavern

**`ticketmaster@las_vegas`**
- ✕ Test — _placeholder_
- ✓ Lauryn Hill w/ Wyclef Jean
- ✓ UNLV Rebels Football vs. Nevada Wolfpack Football
- ✓ Michael Yo Clean Not Spotless Comedy at Jimmy Kimmel's Comedy Club

**`ticketmaster@philadelphia`**
- ✕ Test — _placeholder_
- ✓ Comedy Allstars
- ✓ Hell's Kitchen (Touring)
- ✓ Liana Flores

**`ticketmaster@seattle`**
- ✕ Closed for Thanksgiving — _closure_
- ✓ 6:30pm Preshow Talkback Upgrade
- ✓ All Access Pass – Climate Pledge Arena Tours
- ✓ Seattle Kraken vs. Washington Capitals

**`ticketmaster@washington_dc`**
- ✕ Test — _placeholder_
- ✓ Washington Capitals VIP Tickets: 11/19/26
- ✓ Ruben Studdard
- ✓ MARVIN - The Marvin Gaye Musical

**`zinc_bar@nyc`**
- ✕ Club Closed for the Holiday — _closure_
- ✓ Axel Tosca’s Cuban Jam
- ✓ Paul Nedzela
- ✓ Open for Cocktails

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
- **Campus audience tags.** A campus listing tagged only for students/faculty/staff (no public tag) is held back unless it's a performance, exhibition, game, lecture, seminar or reading: those are usually open.
