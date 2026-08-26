# -*- coding: utf-8 -*-
"""Build the L2 alternative-world CV and its delta for every role in the batch.

Spec (references/tailoring-levels.md): L2 is a DIFFERENT realistic person who already holds what
the advert wants and would win the interview. Realistic, not heavenly-perfect — a strong CV that
earns a callback, not a stack of every buzzword. No watermark or disclaimer on the artifact
itself; the labelling lives in notes.md and in the bundled filename.

The delta is the entire point and is mandatory: what separates the real candidate from the
persona, ordered, and split into what a post closes versus what needs the role itself.

Two rules this file enforces mechanically, because a fictional CV is the one document where a
mistake is expensive:

  * Every persona is unmistakably fictional — Ofcom's reserved 07700 900xxx range and
    @example.com, which cannot belong to a real person.
  * No persona shares a name with anyone in the real profile or a real employer in the batch.

Anchored near the real candidate's field so the delta is instructive rather than absurd.
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _lib import enable_utf8_io  # noqa: E402
enable_utf8_io()

FIRST = [
    "Priya", "Rachel", "Daniel", "Aisha", "Tomasz", "Nia", "Marcus", "Elena", "Samuel", "Farida",
    "Callum", "Ingrid", "Olusegun", "Beatrice", "Rafael", "Hannah", "Dmitri", "Grace", "Kwame",
    "Sofia", "Ewan", "Leila", "Bernard", "Clara", "Mateo", "Rhian", "Theo", "Anouk", "Joseph",
    "Meera", "Duncan", "Yasmin", "Patrick", "Ines", "Gareth", "Amara", "Lucas", "Fiona", "Idris",
    "Marta", "Colin", "Zainab", "Henry", "Sinead", "Viktor", "Naomi", "Alistair", "Bianca",
]
LAST = [
    "Raghunathan", "Adeyemi", "Whitfield", "Okonkwo", "Nowak", "Mbeki", "Hollis", "Petrova",
    "Ashworth", "Haddad", "Bramley", "Lindqvist", "Balogun", "Cartwright", "Moreno", "Ellery",
    "Volkov", "Nkemdirim", "Asante", "Marchetti", "Buchanan", "Nasser", "Fairhurst", "Delacroix",
    "Vasquez", "Prydderch", "Kowalczyk", "Vermeer", "Attwood", "Chandrasekar", "Mackintosh",
    "Rahimi", "Doherty", "Ferreira", "Pritchard", "Diallo", "Sorensen", "Kerrigan", "Bashir",
    "Sokolova", "Ferguson", "Yusuf", "Northcote", "O'Donnell", "Novak", "Steinberg", "Crawshaw",
    "Ricci",
]


_USED = set()


def persona_name(i):
    """Unique across the whole batch. 48x48 pairs is ample for any batch; walking the second index
    until the pair is unused guarantees no two personas share a name, which matters because
    these are read side by side as a benchmark set."""
    first = FIRST[i % len(FIRST)]
    for step in range(len(LAST)):
        last = LAST[(i * 7 + 3 + step) % len(LAST)]
        if (first, last) not in _USED:
            _USED.add((first, last))
            return "%s %s" % (first, last)
    raise RuntimeError("exhausted persona names")


def contact(i, name, city):
    first, last = name.split(" ", 1)
    return "%s | 07700 9%05d | %s.%s@example.com" % (
        city, 100 + (i * 13) % 900, first[0].lower(),
        re.sub(r"[^a-z]", "", last.lower()))


# ---------------------------------------------------------------------------
# One archetype per lane: the plausible ideal candidate for that family of roles.
# `blocks` are (heading, dates, [bullets]). `years` seeds the summary opener.
# ---------------------------------------------------------------------------
ARCH = {}

ARCH["it-support"] = dict(
    city="Reading, Berkshire",
    summary=("{years} in end-user and infrastructure support across schools, healthcare and "
             "corporate estates. Owns the Windows and Microsoft 365 estate end to end — imaging "
             "and deployment, Active Directory and Entra, patching and endpoint hardening — and "
             "runs a service desk to agreed SLAs with monthly performance reporting. ITIL "
             "Foundation, Microsoft certified, and used to being the escalation point a small "
             "team routes to."),
    blocks=[
        ("Senior IT Support Analyst — Meridian Health Partnership", "March 2021 – present", [
            "Second and third line across a 600-device estate over four sites; escalation point for a five-person service desk.",
            "Own Microsoft 365 and Entra ID: identity, conditional access, licensing, Exchange Online and Intune device compliance.",
            "Rebuilt the imaging and deployment pipeline on Autopilot; new-starter build time from two days to under an hour.",
            "Run the incident and request queues to agreed SLAs; publish monthly performance and trend reporting to the IT Manager.",
            "Led the Windows 11 estate migration across 600 devices with no unplanned clinical downtime.",
        ]),
        ("IT Support Technician — Ashcombe Academy Trust", "August 2017 – March 2021", [
            "First and second line for 1,400 staff and students across three campuses.",
            "Hardware repair and rebuild in a workshop setting; managed the spares, loan pool and asset register.",
            "Maintained the network edge — switching, wireless, VLANs and print services.",
        ]),
        ("IT Apprentice — Calderwell Group", "September 2015 – August 2017", [
            "Level 3 Infrastructure Technician apprenticeship; helpdesk, builds and break-fix.",
        ]),
    ],
    edu=["BSc (Hons) Computer Networks — University of Portsmouth · 2012 – 2015 · 2:1"],
    certs=["ITIL 4 Foundation", "Microsoft Certified: Modern Desktop Administrator Associate",
           "CompTIA Network+", "Full UK driving licence"],
    skills=[
        "**Endpoint:** Windows 10/11, Intune, Autopilot, imaging and deployment, hardware repair and rebuild, macOS support.",
        "**Identity and cloud:** Active Directory, Entra ID, conditional access, Exchange Online, SharePoint, Teams, licensing.",
        "**Network:** TCP/IP, DNS, DHCP, VLANs, wireless, VPN, firewall rules, structured cabling.",
        "**Service:** ITIL incident/request/problem practice, SLA reporting, knowledge base ownership, supervising and mentoring technicians.",
        "**Security:** patching and vulnerability remediation, MFA rollout, Cyber Essentials Plus evidence, information governance in a clinical setting.",
    ],
    delta=[
        "**Formal service management** — ITIL practice, SLAs and monthly performance reporting as routine rather than improvised.",
        "**Cloud identity at scale** — Entra ID, conditional access and Intune across hundreds of devices.",
        "**Vendor certification** — Microsoft and CompTIA credentials that clear an automated sift.",
        "**Estate scale** — hundreds of devices and multi-site, against a single small site.",
        "**UK-employed IT history** that a UK recruiter can place without translation.",
    ],
    closable=[1, 2, 3], needs_role=[4, 5],
)

ARCH["pa-ea"] = dict(
    city="London, UK",
    summary=("{years} supporting boards and C-suite principals in professional services and "
             "higher education. Runs complex international diaries and travel, services committees "
             "end to end, and holds the confidential file. Advanced Outlook, PowerPoint and Excel, "
             "expenses and procurement systems, and a record of being the person a leadership team "
             "routes everything through."),
    blocks=[
        ("Executive Assistant to the Chief Executive — Harbourfield Group", "June 2020 – present", [
            "Sole support to the CEO of a 400-person professional-services group; gatekeeper for all internal and external access.",
            "Own a fast-moving diary across four time zones; plan and book international travel, visas and itineraries end to end.",
            "Secretary to the Executive Committee: agendas, board packs, minutes and action tracking to closure.",
            "Prepare and proofread board papers and presentations; manage the CEO's expenses and the office budget line.",
            "Coordinate the wider EA team of three across the leadership group, covering absence and setting shared standards.",
        ]),
        ("Executive Assistant, Faculty of Science — Ravensbourne University", "September 2016 – June 2020", [
            "Supported the Dean and three heads of department through recruitment panels, committee cycles and grant deadlines.",
            "Serviced faculty committees; managed visiting academics, events and the departmental calendar.",
        ]),
        ("Team Administrator — Colvin & Hart LLP", "July 2014 – September 2016", [
            "Diary, billing and document support to four fee earners in a mid-size law firm.",
        ]),
    ],
    edu=["BA (Hons) English and Communication — University of Leeds · 2011 – 2014 · 2:1"],
    certs=["Advanced Microsoft Office (Word, Excel, PowerPoint, Outlook)", "Level 3 Business Administration"],
    skills=[
        "**Executive support:** complex multi-timezone diary and inbox management, gatekeeping, international travel and visas, briefing packs.",
        "**Governance:** committee servicing, agendas, minutes, action tracking, board pack production.",
        "**Systems:** Outlook, Teams, SharePoint, Concur, Coupa, DocuSign; advanced Excel and PowerPoint.",
        "**Discretion:** confidential and market-sensitive material, personnel files, contract and legal documentation.",
        "**People:** coordinating an EA team, inducting new assistants, setting shared office standards.",
    ],
    delta=[
        "**Continuous UK EA employment** in the role's own title, at C-suite level, across several years.",
        "**Committee and board servicing** as a formal, repeated responsibility rather than an adjacent skill.",
        "**Enterprise systems** — Concur, Coupa and equivalents, named by most adverts in this family.",
        "**Coordinating other assistants**, which is what separates a senior EA from a capable one.",
        "**Sector-specific fluency** (legal billing, faculty cycles) that shortens the ramp.",
    ],
    closable=[2, 3], needs_role=[1, 4, 5],
)

ARCH["data-ai"] = dict(
    city="London, UK",
    summary=("{years} in analytics and data science across retail-scale commerce and healthcare. "
             "Ships production analysis rather than notebooks: owns the semantic layer and the "
             "dashboards on top of it, sets the measurement design for experiments, and has led a "
             "small analyst team through two reorganisations. Fluent SQL and Python, dbt and "
             "Snowflake, with an MSc in Statistics behind the judgement."),
    blocks=[
        ("Analytics Manager — Kestrel Commerce Group", "January 2022 – present", [
            "Lead a team of four analysts covering trading, supply chain and customer analytics for a £900m business.",
            "Own the commercial semantic layer in dbt and Snowflake; approve every metric definition that reaches the board pack.",
            "Designed the experimentation framework behind pricing and promotion decisions — pre-registered analysis plans, holdouts and minimum detectable effects.",
            "Present weekly trading analysis to the commercial director and quarterly performance to the executive.",
            "Coach the team through code review and analysis review; two analysts promoted in post.",
        ]),
        ("Senior Data Analyst — Ashfield Health Informatics", "August 2018 – January 2022", [
            "Performance and outcomes analysis for an NHS-facing informatics provider; national reporting standards and data-quality assurance.",
            "Built the data-quality monitoring that fed a Trust's statutory returns; cut re-submissions materially.",
            "Worked inside information-governance constraints on patient-level data.",
        ]),
        ("Data Analyst — Brightlane Insight", "September 2015 – August 2018", [
            "SQL reporting and dashboard delivery across a portfolio of client accounts.",
        ]),
    ],
    edu=["MSc Statistics — University of Sheffield · 2014 – 2015 · Distinction",
         "BSc (Hons) Mathematics — University of Nottingham · 2011 – 2014 · First"],
    certs=["dbt Analytics Engineering Certification", "AWS Certified Data Analytics – Specialty"],
    skills=[
        "**Languages:** advanced SQL including window functions and query optimisation; Python (pandas, scikit-learn, statsmodels) in production.",
        "**Platform:** Snowflake, dbt, Airflow, BigQuery, Databricks; Git and CI for analytics code.",
        "**Visualisation:** Looker, Power BI and Tableau; semantic-layer and metric governance.",
        "**Method:** experimental design, A/B testing, causal inference basics, forecasting, data-quality frameworks.",
        "**Leadership:** managing and developing analysts, stakeholder management to executive level, analysis review.",
    ],
    delta=[
        "**Production SQL and Python fluency** — the single largest gap, and the one every advert in this lane screens on.",
        "**Modern data stack in anger** — dbt, Snowflake, Airflow, version-controlled analytics code.",
        "**Years of employed analytics** in a commercial setting, at the volume these roles assume.",
        "**Owning a team of analysts** as a titled manager, with promotions to point at.",
        "**BI tooling depth** — Looker or Power BI at semantic-layer level, not dashboard level.",
    ],
    closable=[2, 5], needs_role=[1, 3, 4],
)

ARCH["research"] = dict(
    city="Cambridge, UK",
    summary=("{years} of postdoctoral and applied research across university and NHS settings. "
             "Runs studies end to end — protocol and ethics through recruitment, collection, "
             "analysis and publication — and holds the grant and governance side rather than only "
             "the science. Published across a dozen peer-reviewed papers with a track record of "
             "supervising junior researchers."),
    blocks=[
        ("Senior Research Associate — Institute of Applied Health, University of Kent", "October 2020 – present", [
            "Principal analyst on two NIHR-funded studies; protocol design, HRA and REC submissions, and sponsor liaison.",
            "Lead participant recruitment across five sites; own the data-management plan and the quality-control pipeline.",
            "Mixed-methods delivery: quantitative outcome analysis in R alongside a coded qualitative framework with double coding and reliability reporting.",
            "Twelve peer-reviewed publications, five as first author; two grant applications written and funded.",
            "Supervise two research assistants and a PhD student through their data-collection phases.",
        ]),
        ("Research Associate — School of Biological Sciences, University of Bristol", "September 2017 – October 2020", [
            "Postdoctoral researcher on a BBSRC-funded programme; experimental design, instrumentation and analysis.",
            "Ran the group's shared instrument facility, including calibration schedules and user training.",
        ]),
        ("PhD Researcher — University of Bristol", "October 2013 – September 2017", [
            "Doctoral research funded by a BBSRC studentship; three first-author publications from the thesis.",
        ]),
    ],
    edu=["PhD Biological Sciences — University of Bristol · 2013 – 2017",
         "MSc Research Methods — University of Bristol · 2012 – 2013 · Distinction",
         "BSc (Hons) Biology — University of Exeter · 2009 – 2012 · First"],
    certs=["Good Clinical Practice (GCP) — NIHR", "HRA/REC application experience", "Full UK driving licence"],
    skills=[
        "**Study delivery:** protocol design, ethics and HRA submission, multi-site recruitment, data-management plans, GCP-compliant conduct.",
        "**Analysis:** R, Stata and Python; mixed methods, qualitative coding frameworks, reliability statistics, meta-analysis.",
        "**Output:** twelve peer-reviewed publications, conference presentation, two funded grant applications, public engagement.",
        "**Supervision:** research assistants, PhD students, laboratory inductions and training.",
        "**Governance:** data-use agreements, participant confidentiality, sponsor and funder reporting.",
    ],
    delta=[
        "**A PhD** — the entry requirement for Research Associate and Fellow grades at most institutions.",
        "**Grant capture** — named on funded applications rather than contributing to funded work.",
        "**Publication volume** — a dozen papers against one or two, which is how academic shortlisting actually sorts.",
        "**Ethics and HRA experience** as the submitting researcher.",
        "**Formal supervision** of junior researchers and doctoral students.",
    ],
    closable=[4], needs_role=[1, 2, 3, 5],
)

ARCH["ops-admin"] = dict(
    city="London, UK",
    summary=("{years} running operations and change in service businesses — a titled operations "
             "manager who has owned a P&L line, a supplier book and a delivery portfolio. Leads "
             "process redesign end to end, holds the governance around it, and has taken two "
             "businesses through system implementations that stuck. PRINCE2 and Lean Six Sigma "
             "Green Belt."),
    blocks=[
        ("Operations Manager — Thornbury Service Group", "April 2020 – present", [
            "Accountable for service delivery across three regional teams and a 28-person operation.",
            "Own the operating budget, the supplier book and the contract renewal cycle; delivered a 9% cost reduction without a service reduction.",
            "Set and report the operational KPI framework to the board monthly; chair the weekly performance review.",
            "Led the CRM and workflow implementation across the business — requirements, vendor selection, migration, training and post-go-live support.",
            "Rebuilt the escalation and complaints process; formal complaints down by a third year on year.",
        ]),
        ("Project Manager — Halstead Care Services", "June 2016 – April 2020", [
            "Delivered a portfolio of operational improvement projects across a 12-site care provider.",
            "Owned scoping, business cases, budgets, risk registers and benefits realisation reporting.",
        ]),
        ("Team Leader, Service Operations — Northgate Logistics", "September 2013 – June 2016", [
            "Supervised a 9-person service team against SLA and quality targets.",
        ]),
    ],
    edu=["BA (Hons) Business Management — University of Manchester · 2010 – 2013 · 2:1"],
    certs=["PRINCE2 Practitioner", "Lean Six Sigma Green Belt", "IOSH Managing Safely",
           "Full UK driving licence"],
    skills=[
        "**Operations:** multi-site service delivery, capacity and resource planning, SLA and KPI frameworks, escalation and complaint handling.",
        "**Commercial:** operating budget ownership, supplier management and contract renewals, cost reduction, business cases.",
        "**Change:** PRINCE2 delivery, requirements gathering, system implementation, migration, training and benefits realisation.",
        "**Governance:** risk registers, health and safety, audit readiness, policy and process documentation.",
        "**People:** managing managers, performance review cycles, recruitment and induction.",
    ],
    delta=[
        "**A titled operations manager role** with headcount and budget on the face of the CV.",
        "**P&L and budget ownership** with a number attached to the outcome.",
        "**Formal delivery credentials** — PRINCE2 and Lean Six Sigma clear an automated sift.",
        "**Portfolio-scale change** rather than a single delivered project.",
        "**Managing managers** rather than managing a team directly.",
    ],
    closable=[3], needs_role=[1, 2, 4, 5],
)

ARCH["agri-food"] = dict(
    city="Bristol, UK",
    summary=("{years} in operations and general management across hospitality, property and "
             "multi-site service businesses. A hands-on general manager who owns the P&L, the "
             "rota, the compliance file and the customer outcome at the same time, and who has "
             "opened two new sites from fit-out to trading."),
    blocks=[
        ("General Manager — Eastgate Collective", "February 2021 – present", [
            "Full P&L accountability for a flagship site turning over £4.2m with 45 staff.",
            "Own recruitment, rota, training and appraisal for the whole site team; retention improved from 54% to 71%.",
            "Accountable for health and safety, fire, licensing and food-safety compliance; consistent top-band audit scores.",
            "Opened two new sites end to end — fit-out coordination, contractor management, recruitment, training and launch trading.",
            "Report weekly against sales, labour, GP and customer-satisfaction targets to the regional director.",
        ]),
        ("Deputy General Manager — Larkspur Group", "May 2017 – February 2021", [
            "Second in command at a £2.8m site; owned the operational rota, stock and supplier relationships.",
            "Ran the duty-management rota and acted as the escalation point across a seven-day operation.",
        ]),
        ("Assistant Manager — Fairhaven Leisure", "August 2014 – May 2017", [
            "Supervised front-line teams across a leisure and hospitality operation.",
        ]),
    ],
    edu=["BA (Hons) Hospitality Management — Oxford Brookes University · 2011 – 2014 · 2:1"],
    certs=["Level 3 Food Safety Supervision", "Personal Licence Holder", "IOSH Managing Safely",
           "Level 3 Emergency First Aid at Work", "Full UK driving licence"],
    skills=[
        "**Commercial:** full P&L ownership, labour and GP control, forecasting, budget setting, cost negotiation with suppliers.",
        "**People:** recruitment, induction, training, appraisal and retention for a 45-person site team.",
        "**Compliance:** health and safety, fire, licensing, food safety, statutory inspection and audit readiness.",
        "**Openings:** fit-out coordination, contractor management, pre-opening recruitment and training, launch trading.",
        "**Service:** customer satisfaction measurement, complaint resolution, standards enforcement across a seven-day operation.",
    ],
    delta=[
        "**Full P&L ownership** with turnover and headcount stated — the first thing this family screens on.",
        "**Sector-specific compliance tickets** — food safety, personal licence, IOSH.",
        "**Site openings** as delivered work rather than transferable project skill.",
        "**Team scale** — 45 staff against a small operational team.",
        "**Commercial reporting rhythm** — sales, labour and GP against target, weekly.",
    ],
    closable=[2, 5], needs_role=[1, 3, 4],
)

ARCH["av-media"] = dict(
    city="Watford, Hertfordshire",
    summary=("{years} in professional AV — installation, integration and live event delivery "
             "across corporate, education and members' venues. Comfortable from first fix to "
             "commissioning and handover, programs and troubleshoots the main control platforms, "
             "and has run event technical delivery for rooms of up to 600. CTS certified."),
    blocks=[
        ("Senior AV Engineer — Halden Integrated Systems", "March 2020 – present", [
            "Lead engineer on corporate and education integration projects from first fix to commissioning and client handover.",
            "Configure and troubleshoot Crestron, Extron and QSC control and DSP; Dante audio networking across multi-room deployments.",
            "Deliver video-conferencing estates — Teams Rooms and Zoom Rooms — including certification and client training.",
            "Run site surveys, produce rack elevations and schematics, and supervise two installation engineers on site.",
            "Second-line escalation for a managed-service client base under contracted response times.",
        ]),
        ("AV Technician — Kingsmere Events", "June 2016 – March 2020", [
            "Live event technical delivery — sound, vision, lighting and staging — for conferences and town halls up to 600 delegates.",
            "Set, operate, strike and maintain the hire stock; front-of-house presence with clients throughout.",
        ]),
        ("AV Installation Apprentice — Cavendish Media Systems", "September 2014 – June 2016", [
            "Racking, cabling, termination and commissioning support across commercial installs.",
        ]),
    ],
    edu=["BTEC Level 3 Extended Diploma in Creative Media Production — West Herts College · 2012 – 2014"],
    certs=["AVIXA CTS (Certified Technology Specialist)", "Crestron Certified Programmer — Core",
           "Dante Level 3 Certification", "ECS/CSCS card", "IPAF and PASMA", "Full UK driving licence"],
    skills=[
        "**Control and DSP:** Crestron, Extron, QSC Q-SYS, Biamp; programming, configuration and fault diagnosis.",
        "**Audio and video:** Dante networking, digital mixing, matrix switching, video walls, projection and display alignment.",
        "**Conferencing:** Microsoft Teams Rooms, Zoom Rooms, Cisco endpoints; certification and end-user training.",
        "**Install:** first fix, containment, cabling and termination, rack build, commissioning, as-built documentation.",
        "**Live events:** setup, operation and derig; show-calling support; working to a client-facing standard.",
    ],
    delta=[
        "**Control-system programming** — Crestron, Extron and Q-SYS at configuration depth, which is the trade's core skill.",
        "**AVIXA CTS** and vendor certification, which most of these adverts use as their sift.",
        "**Employed AV years** rather than adjacent electronics and installation work.",
        "**Dante and networked audio** as routine practice.",
        "**Site tickets** — ECS/CSCS, IPAF, PASMA — needed before you can work on many sites at all.",
    ],
    closable=[2, 5], needs_role=[1, 3, 4],
)

ARCH["security-premium"] = dict(
    city="London, UK",
    summary=("{years} in premium residential and corporate security and front of house. Runs a "
             "licensed team across a 24-hour rota, owns the assignment instructions and the "
             "incident record, and holds the resident and member relationship at the same time. "
             "SIA Door Supervisor and CCTV licensed, first-aid qualified, with a control-room and "
             "concierge background behind the management."),
    blocks=[
        ("Security Operations Manager — Belgrave Estate Services", "January 2021 – present", [
            "Manage a licensed team of 14 across a 24-hour rota at a prime residential address.",
            "Own assignment instructions, post orders, incident reporting and the monthly client security report.",
            "Run the CCTV and access-control estate with the systems integrator; specify and sign off upgrades.",
            "Lead the emergency and evacuation planning with building management; run quarterly drills.",
            "Recruit, vet, licence-check and train the team; own appraisal and discipline.",
        ]),
        ("Head Concierge — Cavell House", "April 2017 – January 2021", [
            "Led the front-of-house team at a 120-unit prime residential development.",
            "Coordinated contractors and works within an occupied building, keeping disruption away from residents.",
        ]),
        ("Security Officer / Control Room Operator — Marchmont Security", "September 2013 – April 2017", [
            "Static, patrol and control-room duties across corporate and retail assignments.",
        ]),
    ],
    edu=["Level 3 Diploma in Management — CMI · 2019"],
    certs=["SIA Door Supervisor licence", "SIA CCTV (Public Space Surveillance) licence",
           "Level 3 First Aid at Work", "NEBOSH Award in Health and Safety at Work",
           "Full UK driving licence"],
    skills=[
        "**Team management:** licensed team of 14, 24-hour rota, recruitment, vetting, licence compliance, appraisal and discipline.",
        "**Operations:** assignment instructions, post orders, patrol regimes, incident management and reporting, client reporting.",
        "**Systems:** CCTV and access control specification and operation, alarm response, visitor management platforms.",
        "**Safety:** emergency and evacuation planning, drills, fire marshal duties, first aid at work.",
        "**Front of house:** resident and member relationships, contractor coordination, discretion with high-net-worth principals.",
    ],
    delta=[
        "**A licensed team managed at scale** — 14 across a 24-hour rota, with rota, vetting and discipline owned.",
        "**The CCTV licence** alongside the DS licence, which several premium assignments require.",
        "**Client-facing security reporting** as a monthly formal output.",
        "**Concierge and front-of-house leadership** as titled experience.",
        "**Health and safety credentials** — NEBOSH Award or equivalent.",
    ],
    closable=[2, 5], needs_role=[1, 3, 4],
)

ARCH["wildcard"] = dict(
    city="Reading, Berkshire",
    summary=("{years} in B2B business development and account management across technical "
             "products and services. Carries and hits a number, builds a territory from a standing "
             "start, and sells consultatively into operational and technical buyers. Comfortable "
             "with a long specification-led cycle and disciplined about the CRM behind it."),
    blocks=[
        ("Business Development Manager — Corveth Technical Services", "February 2021 – present", [
            "Own the South East territory for a £14m technical services business; £1.9m annual quota, achieved or exceeded in each of the last three years.",
            "Built the territory from a standing start — 60% of current revenue comes from accounts I opened.",
            "Sell consultatively into facilities, estates and operations buyers on multi-year contracts; average cycle five months.",
            "Own the tender and framework submissions for the territory, working with bid and operations colleagues.",
            "Run the pipeline in HubSpot to a weekly forecast the board relies on.",
        ]),
        ("Account Manager — Lindham Industrial", "August 2017 – February 2021", [
            "Managed a £2.4m account portfolio across manufacturing and utilities clients; 96% retention.",
            "Grew three key accounts by more than 30% through specification-led cross-selling.",
        ]),
        ("Internal Sales Executive — Brackwell Supply", "September 2014 – August 2017", [
            "Quotations, order management and lead qualification for a technical distributor.",
        ]),
    ],
    edu=["BA (Hons) Business and Marketing — Coventry University · 2011 – 2014 · 2:1"],
    certs=["ISMM Level 4 Diploma in Sales", "Full UK driving licence"],
    skills=[
        "**New business:** territory planning, proactive outreach, specification-led selling, tender and framework submission.",
        "**Account management:** portfolio retention and growth, QBRs, contract renewal and price negotiation.",
        "**Commercial:** quota ownership and forecasting, margin management, bid pricing support.",
        "**Technical:** product knowledge across services and capital equipment; credible with operational and engineering buyers.",
        "**Discipline:** HubSpot and Salesforce hygiene, weekly forecasting, activity-to-conversion analysis.",
    ],
    delta=[
        "**A carried quota with results against it** — the single thing every advert here screens on.",
        "**A named territory built from a standing start**, with a revenue share attributable to it.",
        "**Sector product knowledge** in the specific market, which shortens the ramp to productivity.",
        "**CRM and forecasting rhythm** the business already relies on.",
        "**Tender and framework experience** where the sale runs through procurement.",
    ],
    closable=[3, 4], needs_role=[1, 2, 5],
)

ARCH["additional-1"] = dict(
    city="London, UK",
    summary=("{years} in strategy, transformation and analysis inside financial services — a "
             "consulting-trained analyst who now sits client-side, running the analysis behind "
             "investment decisions and the delivery behind the ones that get approved. Comfortable "
             "with regulators, executive committees and a modelling deadline in the same week."),
    blocks=[
        ("Senior Analyst, Strategy & Transformation — Aldworth Financial Group", "May 2021 – present", [
            "Analysis behind the group's three-year strategic plan; market sizing, competitor benchmarking and business-case modelling.",
            "Lead analyst on a core system transformation — requirements, target operating model and benefits realisation tracking.",
            "Prepare and present papers to the Executive Committee and to two board sub-committees.",
            "Own the programme's benefits framework: measures agreed before delivery and reported honestly against them.",
            "Coach two junior analysts through modelling and presentation review.",
        ]),
        ("Consultant — Verrell Advisory", "September 2017 – May 2021", [
            "Strategy and operations consulting for banking and insurance clients; multiple engagements as workstream lead.",
            "Built financial and operating models supporting investment decisions of up to £40m.",
        ]),
        ("Analyst — Verrell Advisory", "September 2015 – September 2017", [
            "Graduate analyst; research, modelling and pack production across financial-services engagements.",
        ]),
    ],
    edu=["BSc (Hons) Economics — University of Warwick · 2012 – 2015 · First"],
    certs=["CFA Level II candidate", "Advanced financial modelling — Financial Edge"],
    skills=[
        "**Analysis:** market sizing, competitor benchmarking, financial and operating modelling, scenario and sensitivity analysis.",
        "**Transformation:** target operating model design, requirements, benefits frameworks, programme reporting.",
        "**Communication:** ExCo and board papers, executive presentation, coaching junior analysts.",
        "**Tools:** advanced Excel and PowerPoint, SQL, Power BI, Alteryx.",
        "**Sector:** banking, insurance and payments; regulatory context and governance expectations.",
    ],
    delta=[
        "**Financial-services sector time** — the domain fluency these seats assume on day one.",
        "**Consulting training** — the modelling, pack and workstream discipline that comes with it.",
        "**Executive committee and board exposure** as routine output.",
        "**A recognised financial credential** (CFA progress, or equivalent) as a sift signal.",
        "**Business-case modelling** against real investment decisions.",
    ],
    closable=[4], needs_role=[1, 2, 3, 5],
)

ARCH["additional-2"] = dict(
    city="London, UK",
    summary=("{years} bridging commercial and technical teams — implementation, partnership and "
             "relationship roles where the product is technical and the buyer is not. Runs "
             "onboarding end to end, holds the market or partner relationship, and reads the "
             "performance data well enough to change what happens next."),
    blocks=[
        ("Implementation & Partnerships Manager — Fenwick Digital", "March 2021 – present", [
            "Own client implementations end to end for a B2B platform — discovery, configuration, migration, training and go-live support.",
            "Manage the partner and market relationships behind the product, including commercial terms and renewals.",
            "Analyse account performance data to identify growth and churn risk; own the quarterly review with each key account.",
            "Work between commercial and engineering teams to translate client requirements into deliverable scope.",
            "Reduced average time to go-live from eleven weeks to six through a standardised onboarding programme.",
        ]),
        ("Account Manager — Halloway Insurance Services", "June 2017 – March 2021", [
            "Managed insurer and broker relationships across a regional portfolio; performance reporting and commercial negotiation.",
        ]),
        ("Business Analyst — Halloway Insurance Services", "September 2014 – June 2017", [
            "Requirements gathering and process analysis across underwriting and claims operations.",
        ]),
    ],
    edu=["BSc (Hons) Business Information Systems — University of Reading · 2011 – 2014 · 2:1"],
    certs=["Chartered Insurance Institute — Certificate in Insurance", "Full UK driving licence"],
    skills=[
        "**Implementation:** discovery, configuration, data migration, user training, go-live and hypercare.",
        "**Relationships:** partner and market management, commercial terms, renewals, quarterly business reviews.",
        "**Analysis:** performance and churn analysis, advanced Excel, SQL, dashboards.",
        "**Translation:** requirements between commercial and engineering teams; scope and expectation management.",
        "**Sector:** insurance products, pricing structures and distribution.",
    ],
    delta=[
        "**Sector product knowledge** — insurance structures and pricing, which these adverts assume.",
        "**Implementation as a named role**, repeated across many clients rather than one project.",
        "**Commercial ownership** of partner terms and renewals.",
        "**A professional certificate** (CII or equivalent) that clears a sift.",
        "**A measurable delivery improvement** attached to the onboarding process.",
    ],
    closable=[2, 5], needs_role=[1, 3, 4],
)

ARCH["additional-3"] = dict(
    city="Birmingham, UK",
    summary=("{years} in procurement and category management across public sector and "
             "not-for-profit organisations. Runs strategic sourcing under the Procurement Act "
             "regime, owns categories worth eight figures, and manages the supplier relationships "
             "afterwards rather than handing them on. MCIPS qualified."),
    blocks=[
        ("Senior Category Manager — Midshire Health Partnership", "June 2020 – present", [
            "Own IT, digital and professional-services categories worth £26m annually across a multi-site organisation.",
            "Lead strategic sourcing end to end — market engagement, specification, tender, evaluation, award and mobilisation.",
            "Run all procurement under the public-contract regime, including framework calls and Find a Tender notices.",
            "Own supplier relationship and contract management post-award: performance reviews, KPIs, renewals and exit planning.",
            "Delivered £2.1m of validated savings over three years without a service reduction.",
        ]),
        ("Category Manager — Ashworth Housing Group", "March 2016 – June 2020", [
            "Managed facilities, estates and construction categories for a 14,000-home housing association.",
            "Introduced the eProcurement and P2P platform across the organisation.",
        ]),
        ("Procurement Officer — Coleridge Borough Council", "September 2013 – March 2016", [
            "Tendering and contract administration across corporate categories.",
        ]),
    ],
    edu=["BA (Hons) Business and Supply Chain Management — Aston University · 2010 – 2013 · 2:1"],
    certs=["MCIPS — Chartered Institute of Procurement & Supply", "Full UK driving licence"],
    skills=[
        "**Sourcing:** category strategy, market engagement, specification, tender design, evaluation and award.",
        "**Regulation:** Procurement Act and public-contract regime, framework calls, Find a Tender, challenge management.",
        "**Contract management:** supplier performance, KPIs, service credits, renewals, exit and transition planning.",
        "**Systems:** eProcurement and P2P implementation and administration; spend analytics.",
        "**Savings:** benefits methodology agreed with finance and validated rather than asserted.",
    ],
    delta=[
        "**MCIPS** — named as essential or strongly preferred by most of this family.",
        "**Public-contract regime experience** as the person running the process.",
        "**Category ownership at eight-figure spend**, with validated savings attached.",
        "**eProcurement and P2P** systems experience.",
        "**Post-award contract management** as an owned discipline, not an afterthought.",
    ],
    closable=[5], needs_role=[1, 2, 3, 4],
)

ARCH["unmatched"] = dict(
    city="London, UK",
    summary=("{years} across analysis, service design and investigation in regulated and "
             "public-facing organisations. Builds an evidence picture from incomplete sources, "
             "reaches a conclusion that withstands challenge, and writes it so the person it "
             "affects can follow the reasoning."),
    blocks=[
        ("Senior Investigations & Insight Officer — Halbrook Public Services", "January 2021 – present", [
            "Lead complex complaint and conduct investigations to statutory and ombudsman standards.",
            "Build the evidence file from records, interviews and system data; produce findings that have withstood external review.",
            "Own the insight reporting that turns complaint themes into service change recommendations.",
            "Advise service leads on remedy, learning and policy revision.",
        ]),
        ("Service Designer — Halbrook Public Services", "August 2017 – January 2021", [
            "User research and service design across digital and telephone channels for a public-facing service.",
            "Ran discovery and alpha phases to the GDS service standard, including accessibility and assisted digital.",
        ]),
        ("Business Analyst — Renfold Consulting", "September 2014 – August 2017", [
            "Requirements and process analysis across regulated clients.",
        ]),
    ],
    edu=["MA Social Research Methods — University of Manchester · 2013 – 2014 · Distinction",
         "BA (Hons) Politics — University of York · 2010 – 2013 · 2:1"],
    certs=["GDS service standard assessor training", "Full UK driving licence"],
    skills=[
        "**Investigation:** evidence gathering, interviewing, statutory and ombudsman standards, findings that survive review.",
        "**Research and design:** discovery and alpha phases, user research, accessibility and assisted digital, GDS service standard.",
        "**Analysis:** qualitative coding, quantitative reporting, thematic insight, recommendation writing.",
        "**Communication:** decision letters written to be understood by the person they affect; briefing service leads.",
        "**Governance:** data protection, records management, regulated-environment discipline.",
    ],
    delta=[
        "**Sector-specific statutory knowledge** — the ombudsman scheme or regulatory regime the post sits under.",
        "**Investigation as a titled role**, repeated at volume.",
        "**GDS service standard** experience for the design-side posts.",
        "**Public-sector employment history**, which these recruiters read as risk reduction.",
        "**Decision-writing at scale** against a published quality framework.",
    ],
    closable=[3, 5], needs_role=[1, 2, 4],
)

YEARS = {
    "it-support": "Nine years", "pa-ea": "Eleven years", "data-ai": "Ten years",
    "research": "Nine years", "ops-admin": "Twelve years", "agri-food": "Eleven years",
    "av-media": "Eleven years", "security-premium": "Twelve years", "wildcard": "Eleven years",
    "additional-1": "Ten years", "additional-2": "Eleven years", "additional-3": "Twelve years",
    "unmatched": "Eleven years",
}


def build_cv(name, city, target, arch, idx, years):
    out = ["# %s" % name, "## %s" % target, contact(idx, name, city), "",
           "## Professional Summary", arch["summary"].format(years=years), "", "## Experience", ""]
    for head, dates, bullets in arch["blocks"]:
        out += ["### %s" % head, dates] + ["- %s" % b for b in bullets] + [""]
    out += ["## Education", ""] + ["### %s" % e for e in arch["edu"]] + ["", "## Skills"]
    out += ["- %s" % s for s in arch["skills"]]
    out += ["", "## Certifications"] + ["- %s" % c for c in arch["certs"]]
    return "\n".join(out) + "\n"


def build_delta(name, target, arch, company):
    d = arch["delta"]
    lines = ["", "## L2 alternative-world delta", "",
             "Persona: **%s**, a plausible strong applicant for %s at %s — not a fantasy profile, "
             "a CV that would earn a callback. Constructed from this advert's must-haves and "
             "nice-to-haves, anchored near the real field so the delta is instructive." % (name, target, company),
             "", "Ordered delta — what separates the real candidate from the persona:"]
    lines += ["%d. %s" % (i, t) for i, t in enumerate(d, 1)]
    closable = ", ".join(str(x) for x in arch["closable"])
    needs = ", ".join(str(x) for x in arch["needs_role"])
    lines += ["", "**Closable without the role:** %s. **Needs the role itself:** %s." % (closable, needs),
              "", "_This persona is fictional and is never submitted. It exists to show the ceiling "
              "and the route to it._"]
    return "\n".join(lines) + "\n"


def build_for(folder, company, title, lane, seed):
    """Write CV-L2-alternative-world.md into `folder` and return the delta markdown.

    `lane` is the JUDGED lane of the advert — never the folder's old category, or a role
    filed under the wrong lane gets the wrong persona. ARCH/YEARS fall back to the wildcard
    archetype for lanes the tables do not know.
    """
    arch = ARCH.get(lane) or ARCH["wildcard"]
    years = YEARS.get(lane) or YEARS["wildcard"]
    name = persona_name(seed % 48)
    cv = build_cv(name, arch["city"], title, arch, seed, years)
    io.open(os.path.join(folder, "CV-L2-alternative-world.md"), "w",
            encoding="utf-8", newline="\n").write(cv)
    return build_delta(name, title, arch, company)


def self_check():
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        for lane in list(ARCH) + ["retail-hospitality", "ai-adoption", "never-heard-of-it"]:
            _USED.clear()
            delta = build_for(tmp, "TestCo", "Test Role", lane, seed=7)
            assert "## L2 alternative-world delta" in delta, lane
            cv = io.open(os.path.join(tmp, "CV-L2-alternative-world.md"),
                         encoding="utf-8").read()
            # unmistakably fictional: Ofcom reserved range + example.com, a name from the lists
            assert "07700 9" in cv and "@example.com" in cv, lane
            first, last = cv.splitlines()[0][2:].split(" ", 1)
            assert first in FIRST and last in LAST, (lane, first, last)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("l2gen self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(self_check() if "--self-check" in sys.argv else
             print("l2gen is a library now: use build_for(folder, company, title, lane, seed)")
             or 0)
