#!/usr/bin/env python3
"""Add verified disaster-resilience and roadway-safety funding routes.

The state rows intentionally distinguish an open grant from a state-administered
formula program. Guardrail work is described as conditional unless an official
state source expressly identifies it as an eligible countermeasure.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from catalog_maintenance import export_catalog


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.js"
EVIDENCE = ROOT / "maintenance" / "resilience_transportation_evidence_2026-08-17.csv"
REPORT = ROOT / "maintenance" / "resilience_transportation_integration_2026-08-17.json"
MIDWEST_SOURCE = ROOT / "maintenance" / "resilience_transportation_midwest_2026-08-17.csv"
PREFIX = "window.RERC_CATALOG = "
CHECKED = "2026-08-17"
NATIONAL = "Nationwide and U.S. territories"
PROTECT_PLACES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Puerto Rico",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
]


def parse_rows(raw: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(raw.strip())))


NATIONAL_ROWS = parse_rows(r'''program_key,category,title,agency,status,eligible,support,match,deadline,source_url,guardrail_fit,evidence_note
HMGP,Disaster Resilience,FEMA Hazard Mitigation Grant Program,Federal Emergency Management Agency,Disaster-triggered,"States, territories, federally recognized Tribes, and local governments or eligible nonprofits applying as subapplicants through them",Grant,Generally 75% federal and 25% nonfederal,"Available after qualifying presidential major-disaster declarations; applicant deadlines are set by the state, territory, or Tribe",https://www.fema.gov/grants/mitigation/hazard-mitigation,Conditional,"Transportation projects must reduce a documented natural-hazard risk and meet mitigation-plan, feasibility, cost-effectiveness, and environmental requirements."
FMA,Disaster Resilience,Flood Mitigation Assistance Grant Program,Federal Emergency Management Agency,Recurring,"States, territories, federally recognized Tribes, and NFIP-participating communities applying through them",Grant,"Generally 75% federal; enhanced shares may apply to repetitive-loss properties and qualifying communities","Annual federal and applicant-level cycles; use the applicable state or territorial notice",https://www.fema.gov/grants/mitigation/flood-mitigation-assistance,Conditional,"Funding addresses long-term flood risk to NFIP-insured structures and communities; it is not a general transportation grant."
POSTFIRE,Disaster Resilience,Hazard Mitigation Grant Program Post Fire,Federal Emergency Management Agency,Fire-declaration-triggered,"States, territories, and federally recognized Tribes affected by a qualifying Fire Management Assistance Grant declaration; local entities apply through them",Grant,Generally 75% federal and 25% nonfederal,"The application period opens with the first qualifying declaration of the fiscal year and generally closes six months after that fiscal year ends",https://www.fema.gov/grants/mitigation/post-fire,Conditional,"Road, culvert, drainage, and slope projects may fit when they reduce documented post-wildfire hazard risk."
STORM,Disaster Resilience,Safeguarding Tomorrow Revolving Loan Fund,Federal Emergency Management Agency,Recurring,"States, eligible territories, the District of Columbia, and federally recognized Tribes establish revolving funds that make loans to local governments",Capitalization grant and local low-interest loan,Applicant and loan terms vary,"FEMA capitalization-grant cycles and local revolving-loan availability vary",https://www.fema.gov/grants/mitigation/storm-rlf,Conditional,"Local projects must reduce natural-hazard and disaster risk under an approved loan-fund project list."
HSIP,Roadway Safety,Highway Safety Improvement Program,Federal Highway Administration,Ongoing formula program,"State and territorial transportation agencies; local and Tribal projects generally enter through the applicable state or territorial process",Formula funding and project delivery,"Generally 90% federal; certain safety devices and treatments may qualify for 100% federal share",Continuous state programming with state-specific calls where offered,https://highways.dot.gov/safety/hsip,Yes - conditional,"Guardrails, barriers, end treatments, and related roadside work can qualify when crash or risk analysis supports a fatal- or serious-injury reduction benefit."
PROTECT,Transportation Resilience,PROTECT Formula Program,Federal Highway Administration,Ongoing formula program,"States, the District of Columbia, Puerto Rico, and eligible transportation partners through state programming",Formula funding,"Generally 80% federal, with planning and incentive exceptions",Continuous state transportation programming,https://www.fhwa.dot.gov/infrastructure-investment-and-jobs-act/protect_formula.cfm,Conditional,"Supports transportation resilience planning and improvements for natural hazards, evacuation routes, and vulnerable infrastructure."
ER,Disaster Recovery,Emergency Relief Program,Federal Highway Administration,Disaster-triggered,"State transportation departments and federal land-management agencies; local road agencies coordinate through the state",Reimbursement and repair funding,"Normal federal-aid share generally applies; qualifying emergency work may receive a higher share",Available after qualifying natural disasters or catastrophic failures and an approved request,https://www.fhwa.dot.gov/programadmin/erelief.cfm,Conditional,"Restores eligible Federal-aid and federal-lands highways after serious damage; resilience improvements must meet Emergency Relief rules."
THP,Roadway Safety,Territorial Highway Program,Federal Highway Administration,Ongoing formula program,"American Samoa, Guam, Northern Mariana Islands, and U.S. Virgin Islands transportation agencies",Formula funding and project delivery,Program-specific federal share,Continuous territorial transportation programming,https://www.fhwa.dot.gov/pgc/index.cfm?ddisc=84&dsub=969,Yes - conditional,"Territories program eligible highway and safety projects; this is not a direct grant application for individuals."
''')


HAZARD_ROWS = parse_rows(r'''jurisdiction,agency,status,deadline,source_url,application_path,evidence_note
Alabama,Alabama Emergency Management Agency,Program active; current cycle uncertain,"Disaster-triggered or annual by program; confirm with AEMA",https://ema.alabama.gov/about/agency-divisions/,"Local governments, Tribes, and eligible nonprofits coordinate with the AEMA Hazard Mitigation Branch","The official overview is not a current NOFO; do not treat it as an open call."
Alaska,Alaska Division of Homeland Security and Emergency Management,No HMGP disaster intake open when checked,"Disaster-triggered; monitor state notices",https://ready.alaska.gov/Mitigation/HMGP,"State, local, Tribal, Alaska Native village, and eligible nonprofit subapplicants submit through the state","An approved mitigation plan and state prioritization are required."
American Samoa,American Samoa Office of Disaster Assistance and Petroleum Management,Disaster-triggered,"Cycle depends on a qualifying declaration",https://odapm.as.gov/hazardmitigation,"Territorial agencies and eligible local entities coordinate with ODAPM","The territorial page describes HMGP and the usual 75% federal share."
Arizona,Arizona Department of Emergency and Military Affairs,Recurring and disaster-triggered,"Program-specific state notices",https://dema.az.gov/emergency-management-landing-page/infrastructure-and-grant-administration/mitigation/mitigation_grant_programs,"State and local governments, special districts, and Tribes apply through Arizona DEMA","Ordinary road-safety work is not eligible without a natural-hazard mitigation purpose."
Arkansas,Arkansas Division of Emergency Management,Current cycle uncertain,"Contact ADEM for a current state deadline",https://adem.arkansas.gov/hazard-mitigation-grants,"Eligible local governments and other subapplicants apply through ADEM","The state portal is authoritative, but a current public deadline was not verified."
California,California Governor's Office of Emergency Services,Recurring and disaster-triggered,"State notices of interest and subapplication deadlines vary",https://www.caloes.ca.gov/office-of-the-director/operations/recovery-directorate/hazard-mitigation/hm-grant-opportunities/hma-hmgp/,"Local and state agencies, Tribes, special districts, and eligible nonprofits submit through Cal OES","State selection and FEMA eligibility review apply."
Colorado,Colorado Division of Homeland Security and Emergency Management,Recurring and disaster-triggered,"Program-specific state notices",https://dhsem.colorado.gov/grants,"Eligible local governments and partners coordinate with Colorado DHSEM","The umbrella page lists mitigation grant programs but does not establish a current open deadline."
Connecticut,Connecticut Division of Emergency Management and Homeland Security,Portal accepts applications or letters of intent; cycle deadline not stated,"Confirm the applicable cycle with DEMHS",https://portal.ct.gov/demhs/emergency-management/draft---recovery-and-hazard-mitigation-resilience-unit/disaster-recovery-and-hazard-mitigation-resilience-home/copy-of-hazard-mitigation-and-resiliency/copy-of-building-resilient-infrastructure-and-communities/copy-of-apply_bric,"State and local agencies, Tribes, and program-eligible nonprofits submit through DEMHS","Portal availability does not guarantee that every FEMA program has an open award cycle."
Delaware,Delaware Emergency Management Agency,Current cycle uncertain,"No current deadline posted",https://www.dema.delaware.gov/recovery/,"Government officials and eligible entities coordinate directly with DEMA","The page is a program gateway, not a current NOFO."
District of Columbia,DC Homeland Security and Emergency Management Agency,FY2024/25 BRIC round closed,"Future project-idea and federal deadlines will be posted by HSEMA",https://hsema.dc.gov/page/building-resilient-infrastructure-and-communities-program,"DC agency partners submit ideas to HSEMA, which applies to FEMA","Individuals and businesses cannot apply directly."
Florida,Florida Division of Emergency Management,FY2026 notice-of-interest period closed,"Closed 2026-08-14; future formal dates depend on FEMA and FDEM",https://www.floridadisaster.org/dem/mitigation/builing-resilient-infrastructure-and-communities-bric-grant-program/,"State agencies, Tribes, and local governments submit an NOI to FDEM before an invited FEMA GO subapplication","The state NOI deadline passed three days before this review."
Georgia,Georgia Emergency Management and Homeland Security Agency,Rolling preapplications,"Rolling; federal cycles still control award timing",https://gema.georgia.gov/bric,"Public agencies submit a GEMA/HS preapplication and invited applications proceed in FEMA GO","A preapplication is not an award guarantee."
Guam,Guam Homeland Security Office of Civil Defense,Disaster-triggered and recurring,"Program-specific territorial notices",https://ghs.guam.gov/programs/hazard-mitigation-program,"Government entities and eligible nonprofits coordinate through Guam HSOCD","Territorial prioritization and FEMA review apply."
Hawaii,Hawaii Emergency Management Agency,Recurring and disaster-triggered,"Program-specific state notices",https://dod.hawaii.gov/hiema/hazard-mitigation/,"State and county agencies and qualifying nonprofits coordinate through HI-EMA","The umbrella page does not establish a single standing deadline."
Idaho,Idaho Office of Emergency Management,Disaster-triggered,"State notices follow qualifying declarations",https://ioem.idaho.gov/grants/disaster-grants/hazard-mitigation-grant-program-hmgp/,"State and local governments, Tribes, and eligible nonprofits submit through IOEM","An approved mitigation plan and state selection are required."
Kentucky,Kentucky Emergency Management,Program active; current cycle uncertain,"Declaration-specific or annual by program",https://www.kyem.ky.gov/recover-and-mitigate/disaster-mitigation,"Communities work with KYEM and the State Hazard Mitigation Officer","The page offers program support but is not a current NOFO."
Louisiana,Louisiana Governor's Office of Homeland Security and Emergency Preparedness,Program active; current cycle uncertain,"Annual or declaration-specific",https://gohsep.la.gov/recovery/hazard-mitigation/,"Eligible subapplicants submit through GOHSEP and use FEMA GO when directed","Historical notices must not be carried forward as current deadlines."
Maine,Maine Emergency Management Agency,FY2024/25 state rounds closed,"BRIC closed 2026-06-18; FMA closed 2026-07-06",https://www.maine.gov/mema/grants/mitigation-grants,"Communities, counties, Tribes, and eligible entities submit through MEMA and FEMA GO","Monitor MEMA for the next cycle."
Maryland,Maryland Department of Emergency Management,Program active; current deadline uncertain,"Cycle- or disaster-specific",https://mdem.maryland.gov/community/Pages/LocalJurisdictionHazardMitigation.aspx,"Local jurisdictions prepare applications with MDEM; households usually proceed through a locality","The page describes the route but not a current open deadline."
Massachusetts,Massachusetts Emergency Management Agency,FY2024/25 BRIC round closed; rolling statements of interest accepted,"BRIC closed 2026-06-08; statements of interest are rolling",https://www.mass.gov/hazard-mitigation-assistance-hma-grant-programs,"Eligible municipalities, state agencies, and other subapplicants file a MEMA Statement of Interest","A rolling statement of interest is an eligibility screen, not an open award cycle."
Mississippi,Mississippi Emergency Management Agency,FY2024/25 BRIC round closed,"Closed 2026-06-12",https://msema.org/about/about-mema/mitigation/grant-funding/building-resilient-infrastructure-and-communities,"Local governments, Tribes, and eligible entities submit through MEMA","Local entities do not apply directly to FEMA."
Montana,Montana Disaster and Emergency Services,Disaster-triggered,"State schedule generally follows a declaration",https://des.mt.gov/Grant-Programs/HMGP,"State, local, Tribal, and eligible nonprofit subapplicants submit through Montana DES","The normal federal share is 75% with a 25% nonfederal share."
Nevada,Nevada Division of Emergency Management,Recurring and disaster-triggered,"Program-specific state notices",https://www.oem.nv.gov/grants-management/recovery-and-mitigation-grants/,"Eligible state, local, Tribal, and nonprofit subapplicants coordinate through Nevada DEM","Annual and disaster-triggered programs have separate cycles."
New Hampshire,New Hampshire Homeland Security and Emergency Management,Current cycle uncertain,"No verified current deadline",https://www.dos.nh.gov/divisions/homeland-security-and-emergency-management,"Municipalities and eligible governmental entities submit a letter of intent to HSEM","The official agency surface confirms administration but not a current cycle."
New Jersey,New Jersey Office of Emergency Management,Official page is stale,"No verified 2026 deadline",https://www.nj.gov/njoem/mitigation/index.shtml,"Local governments and eligible subapplicants coordinate through NJOEM and applicable grant systems","Do not infer current availability from the page's older deadlines."
New Mexico,New Mexico Department of Homeland Security and Emergency Management,Disaster-triggered,"State notices follow qualifying declarations",https://www.dhsem.nm.gov/recovery/hazard-mitigation-grant-program-hmgp/,"Local, municipal, Tribal, state, quasi-governmental, and eligible nonprofit applicants submit through DHSEM","Projects must meet state and FEMA eligibility requirements."
New York,New York State Division of Homeland Security and Emergency Services,Current opportunities page is incomplete or stale,"No reliable general 2026 deadline posted",https://www.dhses.ny.gov/current-hazard-mitigation-funding-opportunities,"Eligible governmental and Tribal subapplicants work through DHSES","Contact DHSES before relying on availability."
North Carolina,North Carolina Emergency Management,FY2024/25 BRIC round closed,"LOI closed 2026-06-12; subapplication closed 2026-07-10",https://www.ncdps.gov/our-organization/emergency-management/hazard-mitigation/non-disaster-grants/notice-funding-availability-bric-fy24-25,"Local governments and Tribal Nations submit through NC Emergency Management","The state round is closed."
Northern Mariana Islands,CNMI Hazard Mitigation Grant Program,Disaster-triggered and active program administration,"Declaration- and program-specific",https://opd.gov.mp/library/agency/hazard-mitigation-grant-program.html,"CNMI agencies and eligible subapplicants coordinate through the territorial HMGP office","The official library and FY2025 reporting establish program administration, not a standing open call."
Oklahoma,Oklahoma Department of Emergency Management,HMGP and FMA rounds closed,"HMGP: no open opportunities; FMA closed 2026-07-24",https://oklahoma.gov/oem/programs-and-services/mitigation.html,"Local governments and Tribal Nations submit through OEM","Portal registration is not an open funding call."
Oregon,Oregon Department of Emergency Management,FY2024 FMA preapplication round closed,"Preapplications closed 2026-06-12",https://www.oregon.gov/oem/emresources/grants/pages/hma.aspx,"Local governments, special districts, and Tribal governments submit through Oregon OEM","Approved mitigation-plan requirements apply."
Pennsylvania,Pennsylvania Emergency Management Agency,FY2024/25 BRIC round closed,"LOI closed 2026-04-24; state application closed 2026-06-19",https://www.pa.gov/services/pema/resilient-infrastructure-grant,"Local governments and eligible organizations submit through PEMA","Year-round idea intake is not an open award cycle."
Puerto Rico,Puerto Rico Department of Housing and FEMA,Active match support for eligible HMGP projects,"Disaster- and project-specific",https://recuperacion.pr.gov/en/hazard-mitigation-grant-program/,"Municipalities, Puerto Rico agencies, and eligible community or nonprofit partners coordinate through Puerto Rico's recovery programs","CDBG-MIT may provide the nonfederal share for eligible HMGP projects."
Rhode Island,Rhode Island Emergency Management Agency,FY2024/25 BRIC round closed,"Project notice closed 2026-06-01; FEMA GO subapplication closed 2026-06-15",https://riema.ri.gov/planning-branch/hazard-mitigation/building-resilient-infrastructure-and-communities-bric-grant,"Municipalities and eligible subapplicants submit through RIEMA","The official page includes hazard-resilient road, bridge, and evacuation-route work."
South Carolina,South Carolina Emergency Management Division,Disaster-specific opportunities; current closing dates uncertain,"Declaration-specific",https://www.scemd.org/recover/mitigation/,"State and local governments, Tribes, and eligible nonprofits submit through SCEMD","Do not infer that every listed disaster intake remains open."
Tennessee,Tennessee Emergency Management Agency,Program active; current deadline uncertain,"Annual or declaration-specific",https://www.tn.gov/tema/emergency-community/mitigation/mitigation-grant-programs.html,"Eligible subapplicants use the state preapplication or State Hazard Mitigation Office route","The umbrella page does not publish a 2026 deadline."
Texas,Texas Division of Emergency Management and Texas Water Development Board,Opportunity-specific; FY2024 FMA closed,"FMA closed 2026-06-25; other deadlines vary",https://www.tdem.texas.gov/mitigation/hazard-mitigation-section,"Local jurisdictions work through TDEM; FMA is administered through TWDB","There is no standing direct-grant window."
U.S. Virgin Islands,Virgin Islands Territorial Emergency Management Agency,Program administration active; current cycle uncertain,"Disaster- and program-specific",https://vitema.vi.gov/about-us/divisions/,"Territorial agencies and eligible subapplicants coordinate with VITEMA Grants Management","The current agency page confirms grant administration but not an open HMGP deadline."
Utah,Utah Division of Emergency Management,Disaster-triggered and recurring,"Program-specific state notices",https://hazards.utah.gov/services/,"State and local governments, Tribes, and eligible nonprofits coordinate through Utah DEM","Utah administers FEMA HMA but does not provide a standing state mitigation fund."
Vermont,Vermont Emergency Management,Official page may be stale; future ideas accepted,"No verified current award deadline",https://vem.vermont.gov/funding/mitigation,"Municipalities, state agencies, regional planning commissions, and eligible public entities submit a VEM preapplication","Confirm current federal program status with VEM."
Virginia,Virginia Department of Emergency Management,Open-opportunities page lists HMGP and FMA; deadline not shown,"Confirm deadline with VDEM",https://vdem.virginia.gov/divisions/finance/grants/hazard-mitigation-assistance-grant-programs/,"Cities, counties, towns, planning districts, state agencies, and Tribal governments apply through VDEM","The official page supports availability but omits the closing date."
Washington,Washington Emergency Management Division,Existing catalog record retained,"Disaster-triggered",https://mil.wa.gov/recovery,"Eligible state, local, and Tribal governments submit through Washington EMD","The integration script will not add a duplicate of the existing Washington HMGP record."
West Virginia,West Virginia Emergency Management Division,Current cycle uncertain,"No current deadline posted",https://emd.wv.gov/,"Local jurisdictions coordinate with WVEMD Recovery Grants","Do not assume a current competitive cycle or state match without confirmation."
Wyoming,Wyoming Office of Homeland Security,Most recent extension closed; notices of interest accepted,"Extension closed 2026-06-23; future ideas may be submitted",https://hls.wyo.gov/grants/hma,"Eligible state, local, Tribal, and nonprofit subapplicants coordinate through Wyoming HLS","A notice of interest does not guarantee an open award cycle."
''')


ROADWAY_ROWS = parse_rows(r'''jurisdiction,agency,status,deadline,source_url,application_path,guardrail_fit,evidence_note
Alabama,Alabama Department of Transportation,Active; application materials published,"Deadline not stated",https://www.dot.state.al.us/programs/HSIP.html,"Counties and cities use ALDOT's HSIP application and safety portal",Yes - conditional,"Guardrail must respond to a qualifying safety problem supported by analysis."
Alaska,Alaska Department of Transportation and Public Facilities,Ongoing state program,"Continuous programming",https://dot.alaska.gov/stwddes/dcstraffic/hsip.shtml,"DOT regions identify and program data-driven safety projects",Yes,"Alaska DOT also publishes a Central Region guardrail inventory and upgrade program."
Arizona,Arizona Department of Transportation,Ongoing state program,"Continuous programming",https://azdot.gov/planning/traffic-safety/strategic-highway-safety-plan,"State and local partners coordinate through ADOT safety planning",Yes - conditional,"The state plan includes guardrail and cable-barrier countermeasures."
Arkansas,Arkansas Department of Transportation,Current local HSIP intake uncertain,"No verified current deadline",https://ardot.gov/divisions/local-programs/,"Local agencies should confirm the HSIP route with ARDOT Local Programs",Conditional,"An official federal report documented guardrail work but not a current local call."
California,California Department of Transportation,Cycle 13 open,"Due 2026-11-02",https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/apply-now,"Eligible local agencies apply through Caltrans Local Assistance; an LRSP is required",Yes - conditional,"Projects must meet the active call's safety and eligibility criteria."
Colorado,Colorado Department of Transportation,FY2029 review complete; next cycle upcoming,"FY2030 local-agency cycle expected to begin in December 2026",https://www.codot.gov/safety/traffic-safety/data-analysis/hsip,"Eligible local and Tribal public-road agencies submit under CDOT's call",Yes - conditional,"The current program page covers all public roads and announces the next local-agency cycle."
Connecticut,Connecticut Department of Transportation,Active FFY2026 program,"Continuous programming; no statewide call located",https://portal.ct.gov/dot/traffic-engineering/traffic-and-safety-engineering,"Municipalities coordinate with CTDOT Safety Engineering and may request a road-safety audit",Yes - conditional,"CTDOT selects projects on state and local public roads."
Delaware,Delaware Department of Transportation,Program documented; current cycle uncertain,"Annual internal programming",https://projectdevelopmentmanualtest.deldot.gov/index.php/Chapter_2_-_Project_Origination_and_Planning,"DelDOT Traffic Engineering screens and programs projects",Yes,"The official manual expressly lists guardrail installation or enhancement."
District of Columbia,District Department of Transportation,Active internal capital program,"Continuous internal programming",https://ddot.dc.gov/page/traffic-safety-ddot,"DDOT identifies and programs projects; public safety reports are not grant applications",Yes - conditional,"No direct external infrastructure-grant path was found."
Florida,Florida Department of Transportation,Active through Florida GAP,"District and program cycles vary",https://www.fdot.gov/fpo/lp/flgap/home,"Eligible local agencies register and apply through Florida GAP",Yes - conditional,"Guardrail needs crash or risk support and district coordination."
Georgia,Georgia Department of Transportation,Ongoing subject to annual availability,"Timing varies",https://www.dot.ga.gov/PartnerSmart/Public/Documents/LocalGovernmentManual.pdf,"Local governments coordinate with GDOT district Off-System Coordinators",Yes - conditional,"GDOT invests HSIP funds on local roads through state-local agreements."
Hawaii,Hawaii Department of Transportation,Ongoing state program,"Continuous STIP programming",https://hidot.hawaii.gov/highways/shsp/,"HDOT programs safety improvements on public roads",Yes - conditional,"Guardrail projects appear in state programming, but no direct local grant call was found."
Idaho,Idaho Transportation Department,Program documented; current cycle uncertain,"Continuous ITIP programming",https://apps.itd.idaho.gov/Apps/Fund/itip2024/FY24-ITIP.pdf,"Local agencies coordinate through ITD and Local Highway Technical Assistance Council",Yes,"Official programming includes local HSIP and guardrail projects."
Kentucky,Kentucky Transportation Cabinet,Ongoing state program,"Continuous programming",https://transportation.ky.gov/TrafficOperations/Pages/Highway-Safety-Improvement-Program.aspx,"Local agencies coordinate with KYTC districts and Traffic Operations",Yes - conditional,"Roadway departure is an explicit HSIP investment category."
Louisiana,Louisiana Department of Transportation and Development,Active program,"Ongoing as funding becomes available",https://dotd.la.gov/about/office-of-project-delivery/planning/highway-safety/highway-safety-improvement-program/,"Local agencies initiate proposals through DOTD districts or Regional Safety Coalitions",Yes - conditional,"Lane departure is an explicit emphasis area."
Maine,Maine Department of Transportation,Ongoing through STIP,"Project-specific availability",https://www.maine.gov/dot/sites/maine.gov.dot/files/inline-files/2024-2027%20Statewide%20Transportation%20Improvement%20Program.pdf,"Projects are programmed through MaineDOT and regional or local transportation processes",Yes,"The official STIP includes obsolete cable guardrail replacement with HSIP funds."
Maryland,Maryland Department of Transportation State Highway Administration,Local fund documented; current 2026 solicitation uncertain,"Historically annual; confirm current date",https://roads.maryland.gov/mdotsha/pages/pressreleasedetails.aspx?PageId=818&newsId=4157,"Counties with a Local Road Safety Plan submit systemic projects to MDOT SHA",Yes - conditional,"The located state notice is older, so current timing requires confirmation."
Massachusetts,Massachusetts Department of Transportation,Active and programmed,"Continuous TIP and STIP programming",https://www.mass.gov/info-details/highway-safety-improvement-program,"Municipal projects advance through MPO prioritization and MassDOT safety review",Yes - conditional,"Routine replacement alone may not meet HSIP's data-driven criteria."
Mississippi,Mississippi Department of Transportation,Current application path uncertain,"No verified current deadline",https://mdot.ms.gov/documents/Planning/Manuals/LTAP/Highway%20Safety%20Improvement%20Program.pdf,"Local agencies should confirm the current route with MDOT Planning or Traffic Engineering",Conditional,"The official manual is older and does not prove a current local call."
Montana,Montana Department of Transportation,Ongoing state and local program,"Continuous programming",https://www.mdt.mt.gov/pubinvolve/us191/docs/US191-Appendix5-Funding.pdf,"Local road agencies coordinate applications with MDT",Yes,"Official guidance identifies HSIP on any public road and includes guardrail."
Nevada,Nevada Department of Transportation,2025 local cycle closed,"Monitor for the next cycle",https://www.dot.nv.gov/safety/traffic-safety-engineering/highways-safety-improvement-program-hsip/hsip-local-infrastructure-safety-program,"Local governments, counties, Tribes, and planning agencies use the state local-safety process",Yes,"The official page expressly includes guardrails and barriers."
New Hampshire,New Hampshire Department of Transportation,Ongoing; current schedule uncertain,"Road-safety-audit requests may be accepted outside a formal call; confirm with NHDOT",https://www.dot.nh.gov/about-nh-dot/divisions-bureaus-districts/highway-design/safety-section/highway-safety-improvement,"Local agencies coordinate with NHDOT Safety and regional planning commissions",Yes - conditional,"The page was access-restricted during review; direct availability needs confirmation."
New Jersey,New Jersey Department of Transportation,Active annual program,"Dates vary by MPO",https://nj.gov/transportation/about/safety/hsip.shtm,"Counties and municipalities submit candidate projects through their MPO",Yes - conditional,"The official program provides a direct local-government pathway."
New Mexico,New Mexico Department of Transportation,Ongoing state program,"Continuous programming",https://www.dot.nm.gov/target-zero/,"Local partners coordinate safety projects through NMDOT and regional planning channels",Yes - conditional,"The public page does not provide a direct local application deadline."
New York,New York State Department of Transportation,Active state-administered program,"Continuous TIP and STIP programming",https://www.dot.ny.gov/divisions/operating/osss/highway-repository/RedBook.pdf,"Local sponsors coordinate with NYSDOT regions and MPOs",Yes,"The official Red Book discusses guardrail and appropriate funding use."
North Carolina,North Carolina Department of Transportation,Ongoing data-driven program,"Continuous; no direct local grant deadline located",https://www.ncdot.gov/initiatives-policies/safety/traffic-safety/Pages/identifying-areas-improvements.aspx,"Local agencies submit safety concerns and coordinate with NCDOT divisions",Yes - conditional,"Engineering review must support a fatal- or serious-injury reduction benefit."
Oklahoma,Oklahoma Department of Transportation,Current public application path uncertain,"No verified current deadline",https://oklahoma.gov/odot/programs-and-projects/programs/transportation-programs/shsp.html,"Projects enter through ODOT and MPO planning channels",Conditional,"The official safety plan is not an application page."
Oregon,Oregon Department of Transportation,Active All Roads Transportation Safety program,"Program cycles and state programming vary",https://www.oregon.gov/odot/Engineering/Pages/Highway-Safety.aspx,"State and local public-road projects enter through ODOT's all-roads safety process",Yes - conditional,"Guardrail must be supported by crash or risk analysis."
Pennsylvania,Pennsylvania Department of Transportation,Active; approximately $132 million annually,"Annual and continuous regional programming",https://www.pa.gov/agencies/penndot/about-penndot/strategic-planning-and-operations/safety-infrastructure-improvement-programs,"Projects originate through PennDOT districts and MPO/RPO planning partners",Yes,"PennDOT specifically funds cable median barriers and other roadway-departure countermeasures."
Puerto Rico,Puerto Rico Highways and Transportation Authority,Ongoing federally aided safety programming,"Continuous STIP programming",https://act.dtop.pr.gov/oficinas/ingenieria-de-transito/plan-estrategico-de-seguridad-vial,"PRHTA programs islandwide safety projects through the STIP",Yes - conditional,"This is state-programmed funding, not a direct public grant."
Rhode Island,Rhode Island Department of Transportation,Active state program,"Ongoing programming",https://www.dot.ri.gov/safety/reports/docs/Highway_Safety_Improvement_Program.pdf,"RIDOT identifies and programs projects; local governments coordinate with the Office of Safety",Yes,"The current report expressly lists guardrail among safety countermeasures."
South Carolina,South Carolina Department of Transportation,Program documented; current local intake uncertain,"No verified current local deadline",https://www.scdot.org/content/dam/scdot-legacy/business/pdf/roadway/2017_SCDOT_Roadway_Design_Manual.pdf,"Projects are developed through SCDOT Traffic Engineering",Yes,"The official manual includes obsolete guardrail and bridge-rail work, but the application route is uncertain."
Tennessee,Tennessee Department of Transportation,Program available to local governments,"Current solicitation timing not stated",https://www.tn.gov/content/dam/tn/tdot/programdevelopment/LGG_Manual.pdf,"Local governments coordinate through TDOT Local Programs and planning channels",Yes,"TDOT guidance says qualifying guardrail installation may receive 100% federal funding."
Texas,Texas Department of Transportation,2026 call complete,"2027 call planned but not issued",https://www.txdot.gov/about/programs/highway-safety-engineering.html,"TxDOT districts, MPOs, and local governments submit during the annual call",Yes,"TxDOT identifies barriers, fixed-object treatment, and off-system improvements as uses."
Utah,Utah Department of Transportation,Active all-public-roads program,"Continuous programming",https://connect.udot.utah.gov/docs/highway-safety-improvement-program-manual/,"Local and Tribal road agencies coordinate through UDOT's HSIP process",Yes,"UDOT materials include barrier and guardrail safety work."
Vermont,Vermont Agency of Transportation,Ongoing state program,"Continuous programming",https://vtrans.vermont.gov/highway,"Municipalities coordinate through VTrans Municipal Assistance and safety staff",Yes - conditional,"Official materials support all-public-road safety work but do not show a direct open call."
Virginia,Virginia Department of Transportation,2026 fall intake suspended,"No 2026 applications accepted",https://www.vdot.virginia.gov/doing-business/technical-guidance-and-support/traffic-operations/vhsip/,"Localities normally submit through the SMART Portal during the annual intake",Yes - conditional,"The 2026 intake is closed by policy."
Washington,Washington State Department of Transportation,County and city cycles closed,"City cycle closed 2026-03-06; monitor future calls",https://wsdot.wa.gov/business-wsdot/support-local-programs/funding-programs/highway-safety-improvement-program,"Eligible counties and cities use WSDOT Local Programs calls",Yes,"WSDOT programs guardrail work when safety criteria are met."
West Virginia,West Virginia Division of Highways,Active state-managed program,"Continuous internal programming",https://transportation.wv.gov/traffic-engineering-division,"WVDOT districts identify projects through crash and risk data",Yes,"The official STIP includes districtwide HSIP guardrail upgrades."
Wyoming,Wyoming Department of Transportation,Active FY2026 program,"Continuous state programming",https://www.dot.state.wy.us/home/dot_safety/safety-management-system.html,"WYDOT programs projects through its HSIP implementation plan",Yes,"The FY2026 plan expressly includes guardrail upgrades."
''')


def load_catalog() -> dict:
    raw = DATA.read_text(encoding="utf-8").strip()
    if not raw.startswith(PREFIX) or not raw.endswith(";"):
        raise ValueError("Unexpected data.js assignment format")
    return json.loads(raw[len(PREFIX):-1])


def write_catalog(catalog: dict) -> None:
    DATA.write_text(
        PREFIX + json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
        newline="\n",
    )


def national_item(row: dict[str, str]) -> dict:
    category = row["category"]
    tags = "disaster resilience; hazard mitigation; emergency preparedness; infrastructure"
    if "Roadway" in category:
        tags += "; transportation; roadway safety; guardrails; barriers"
    item = {
        "item_id": f"RERC-FND-2026-NAT-{row['program_key']}",
        "item_type": "Funding",
        "title": row["title"],
        "organization": row["agency"],
        "status": row["status"],
        "last_checked": CHECKED,
        "geography": NATIONAL,
        "eligible_users": row["eligible"],
        "project_stage": "Mixed",
        "topic_tags": tags,
        "support_type": row["support"],
        "amount_or_cost": "Varies by allocation, declaration, or selected project",
        "match_or_cost": row["match"],
        "deadline_or_availability": row["deadline"],
        "summary": row["evidence_note"],
        "why_it_matters": row["evidence_note"],
        "source_url": row["source_url"],
    }
    if row["program_key"] == "PROTECT":
        item["geography"] = "Multi-State"
        item["covered_states"] = PROTECT_PLACES
        item["coverage_note"] = "PROTECT formula funding is apportioned to the 50 states, District of Columbia, and Puerto Rico."
        item["coverage_source_url"] = row["source_url"]
    elif row["program_key"] == "THP":
        item["geography"] = "Multi-State"
        item["covered_states"] = ["American Samoa", "Guam", "Northern Mariana Islands", "U.S. Virgin Islands"]
        item["coverage_note"] = "The Territorial Highway Program serves the four listed territories."
        item["coverage_source_url"] = row["source_url"]
    return item


def state_item(row: dict[str, str], category: str) -> dict:
    roadway = category == "Roadway Safety"
    code = "HSIP" if roadway else "HMA"
    slug = row["jurisdiction"].upper().replace(" ", "-").replace(".", "")
    title = (
        f"{row['jurisdiction']} Highway Safety Improvement Program and Local Road Safety Route"
        if roadway else f"{row['jurisdiction']} Hazard Mitigation Assistance Funding Route"
    )
    guardrail = row.get("guardrail_fit", "Conditional")
    summary = row["evidence_note"]
    if roadway:
        summary += f" Guardrail fit: {guardrail}."
    else:
        summary += " Transportation work must have a documented natural-hazard mitigation purpose."
    return {
        "item_id": f"RERC-FND-2026-{code}-{slug}",
        "item_type": "Funding",
        "title": title,
        "organization": row["agency"],
        "status": row["status"],
        "last_checked": CHECKED,
        "geography": row["jurisdiction"],
        "eligible_users": row["application_path"],
        "project_stage": "Mixed",
        "topic_tags": (
            "transportation; roadway safety; guardrails; barriers; rural roads; traffic safety"
            if roadway else
            "disaster resilience; hazard mitigation; flood; wildfire; emergency preparedness; infrastructure"
        ),
        "support_type": (
            "State-administered formula funding and project delivery"
            if roadway else "State-administered federal grant route"
        ),
        "amount_or_cost": "Varies by allocation, declaration, or selected project",
        "match_or_cost": (
            "Generally 90% federal; exceptions and state or local shares vary"
            if roadway else "Generally 75% federal and 25% nonfederal; exceptions may apply"
        ),
        "deadline_or_availability": row["deadline"],
        "summary": summary,
        "why_it_matters": summary,
        "source_url": row["source_url"],
    }


def main() -> int:
    catalog = load_catalog()
    existing_ids = {item["item_id"] for item in catalog["items"]}
    existing_urls = {item["source_url"].rstrip("/").lower() for item in catalog["items"]}
    candidates = [national_item(row) for row in NATIONAL_ROWS]
    candidates.extend(state_item(row, "Disaster Resilience") for row in HAZARD_ROWS if row["jurisdiction"] != "Washington")
    candidates.extend(state_item(row, "Roadway Safety") for row in ROADWAY_ROWS)
    with MIDWEST_SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        candidates.extend(state_item(row, row["category"]) for row in csv.DictReader(handle))

    additions = []
    updates = []
    skipped_duplicate_urls = []
    existing_index = {item["item_id"]: index for index, item in enumerate(catalog["items"])}
    for item in candidates:
        if item["item_id"] in existing_index:
            index = existing_index[item["item_id"]]
            current = catalog["items"][index]
            if current != item:
                old_url = current["source_url"].rstrip("/").lower()
                existing_urls.discard(old_url)
                catalog["items"][index] = item
                existing_urls.add(item["source_url"].rstrip("/").lower())
                updates.append(item["item_id"])
            continue
        url_key = item["source_url"].rstrip("/").lower()
        if url_key in existing_urls:
            skipped_duplicate_urls.append({"item_id": item["item_id"], "source_url": item["source_url"]})
            continue
        additions.append(item)
        existing_ids.add(item["item_id"])
        existing_urls.add(url_key)

    catalog["items"].extend(additions)
    catalog["updated"] = CHECKED
    catalog["counts"] = {
        "combined": len(catalog["items"]),
        "funding": sum(item["item_type"] == "Funding" for item in catalog["items"]),
        "resources": sum(item["item_type"] == "Resource" for item in catalog["items"]),
    }
    write_catalog(catalog)
    export_catalog(catalog)

    catalog_by_id = {item["item_id"]: item for item in catalog["items"]}
    integrated_items = [catalog_by_id[item["item_id"]] for item in candidates if item["item_id"] in catalog_by_id]
    retained_existing_ids = ["RERC-FND-WA-2026-008"]
    integrated_items.extend(catalog_by_id[item_id] for item_id in retained_existing_ids if item_id in catalog_by_id)

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "item_id", "jurisdiction", "category", "status", "deadline_or_availability",
        "source_url", "application_path", "support_type", "guardrail_fit", "evidence_note",
    ]
    with EVIDENCE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in integrated_items:
            roadway = "roadway safety" in item["topic_tags"]
            writer.writerow({
                "item_id": item["item_id"],
                "jurisdiction": item["geography"],
                "category": "Roadway Safety" if roadway else "Disaster Resilience",
                "status": item["status"],
                "deadline_or_availability": item["deadline_or_availability"],
                "source_url": item["source_url"],
                "application_path": item["eligible_users"],
                "support_type": item["support_type"],
                "guardrail_fit": "Conditional" if roadway else "Natural-hazard nexus required",
                "evidence_note": item["summary"],
            })

    report = {
        "status": "PASS",
        "checked": CHECKED,
        "added_this_run": len(additions),
        "updated_this_run": len(updates),
        "updated_item_ids": updates,
        "added_or_updated_records": len(candidates),
        "retained_existing_records": retained_existing_ids,
        "coverage_evidence_records": len(integrated_items),
        "skipped_duplicate_urls": skipped_duplicate_urls,
        "catalog_counts": catalog["counts"],
        "hazard_jurisdictions": sorted({item["geography"] for item in integrated_items if "-HMA-" in item["item_id"]} | {"Washington"}),
        "roadway_jurisdictions": sorted({item["geography"] for item in integrated_items if "-HSIP-" in item["item_id"]}),
        "territorial_roadway_coverage": ["American Samoa", "Guam", "Northern Mariana Islands", "U.S. Virgin Islands"],
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
