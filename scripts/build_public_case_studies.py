from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


PROGRAMS = {
    "Recreation Economy for Rural Communities",
    "Local Foods, Local Places",
    "EPA Brownfields Success Stories",
    "EPA Examples of Smart Growth Communities and Projects",
    "U.S. Climate Resilience Toolkit",
    "USDA Rural Development Success Stories",
}

# Program rosters and annual planning-assistance summaries remain in Protos, but
# they are not public case studies until a project-specific implementation source exists.
EXCLUDED_PUBLIC_PROGRAMS = {
    "Recreation Economy for Rural Communities",
    "Local Foods, Local Places",
}

SOURCE_TYPES = {
    "epa_rerc_partner_page",
    "epa_lflp_summary_report_pdf",
    "epa_brownfields_success_story_html",
    "epa_brownfields_success_story_pdf",
    "epa_smart_growth_example_detail_page",
    "us_climate_resilience_toolkit_case_page",
    "usda_rd_success_story_browser_seed",
}

PUBLIC_HOSTS = {
    "www.epa.gov",
    "epa.gov",
    "toolkit.climate.gov",
    "www.rd.usda.gov",
    "rd.usda.gov",
}

PLACE_OVERRIDES = {
    "Relocating the Native Village of Shishmaref, Alaska Due to Coastal Erosion": "Shishmaref",
    "Recertifying Utility Workers in a Small, Remote Community": "Multiple communities",
    "Adapting to Rising Tides in San Francisco Bay, California": "San Francisco Bay Area",
    "California State Coastal Conservancy: Gravel Beach and Berm for Shorebird Habitat Creation, Erosion Control and Flood Protection": "San Francisco Bay shoreline",
    "Lakewood, CO: Housing and the Arts at Lamar Street Station": "Lakewood",
    "Coastal Adaptation Plan for the Town of Groton, Connecticut": "Groton",
    "Brownfield to Brewery: DNREC delivers a win-win in Delaware": "Multiple communities",
    "Climate Change and the Florida Keys": "Florida Keys",
    "Climate Change in Port Heiden, AK": "Port Heiden",
    "Florida's Community Resiliency Initiative": "Multiple communities",
    "Oglethorpe Power's Acquisition of Walton County Power Strengthens Reliability and Affordability in Rural Georgia": "Monroe and rural Georgia",
    "Ferrous Site, Lawrence, Mass.": "Lawrence",
    "Shubuta, MS: Strengthening Shubuta": "Shubuta",
    "Ralls County Electric's Vision for a Stronger, Smarter Grid": "Ralls County service area",
    "CR4HC Case Study: University of Nebraska": "Omaha",
    "Planning for Climate Resilience-City of Asheville, North Carolina": "Asheville",
    "Minnkota Power Cooperative's $60 Million Infrastructure Upgrade for a Stronger Future": "Eastern North Dakota and northwestern Minnesota",
    "A Successful Transformation: Allentown Waterfront - Allentown, PA": "Allentown",
    "Former Alcoa Research Park New Kensington, PA": "New Kensington",
    "Homewood Senior Housing & Caf\u00e9 Homewood Ave, Pittsburgh, PA.": "Pittsburgh",
    "Pittsburgh, PA: Luxury Living with an Industrial Legacy": "Pittsburgh",
    "Brownfields Success Story: Common Success at Cooper Commons LLC": "Multiple communities",
    "Overbrook Environmental Education Center Becomes Community Hub: Philadelphia, PA": "Philadelphia",
    "Finding Solutions Through Distance Learning Technology": "Chamberlain and rural school communities",
    "Spearfish, SD Climate Resiliency Plan": "Spearfish",
    "Training a Workforce to Bring Nature-based Solutions into Every Project": "Puerto Rico and U.S. Virgin Islands",
    "City Market - South End (Onion River Co-op), Burlington, Vt.": "Burlington",
    "Vermont Climate Action Plan": "Multiple communities",
    "Promoting Ecotourism to Conserve a Watershed in Virginia": "Lower Chickahominy watershed",
    "The Edge of Something Special: Williamsburg, VA": "Williamsburg",
    "Seattle, WA: Redevelopment Yields Much-Needed Affordable Housing": "Seattle",
    "A Successful Transformation: The Adamston Commons": "Clarksburg",
    "Wellsburg, WV: A Local Manufacturing Expansion Takes Flight": "Wellsburg",
    "Beech Bottom, WV: Forging a New Future in Steel Country": "Beech Bottom",
    "Ranson and Charles Town, WV: A Tale of Two Cities": "Ranson and Charles Town",
    "A Successful Transformation: From Wasted Lot to Reading Hot\u2010Spot": "Shepherdstown",
    "Boosting Community Storm Resilience in Alaska": "Coastal Alaska communities",
    "Wood for Life, a Collaborative Partnership to Provide Wood to the Navajo Nation and Hopi Tribe": "Navajo Nation and Hopi Tribe",
    "Hillsboro, OR: Navigating a New River Launch": "Hillsboro",
    "Ambler, PA: Repowering a Historic Landmark": "Ambler",
    "Richmond, VA: Cheers to a Revitalized Neighborhood": "Richmond",
    "Drought Response and Recovery Project for Water Utilities in North Marin Water District, CA": "North Marin Water District",
    "Drought Response and Recovery Project for Water Utilities in Tuolumne Utilities District, CA": "Tuolumne Utilities District",
    "Drought Response and Recovery Project for Water Utilities in Hogansville, GA": "Hogansville",
    "Drought Response and Recovery Project for Water Utilities in Hays and Russell, KS": "Hays and Russell",
    "Drought Response and Recovery Project for Water Utilities in Las Vegas, NM": "Las Vegas",
    "Drought Response and Recovery Project for Water Utilities in Clinton, OK": "Clinton",
    "Drought Response and Recovery Project for Water Utilities in Spicewood Beach, TX": "Spicewood Beach",
    "Drought Response and Recovery Project for Water Utilities in Castine, Maine": "Castine",
    "Grand Isle: Louisiana's First Line of Defense from Coastal Flooding": "Grand Isle",
    "Virginia Beach Becomes Sea Level Wise": "Virginia Beach",
    "Integrating Climate Change into the Planning and Operations of the Apostle Islands National Lakeshore, WI": "Apostle Islands National Lakeshore",
    "WaterFire Arts Center, Providence, R.I.": "Providence",
    "Alligator River National Wildlife Refuge/ Albemarle-Pamlico Peninsula Climate Adaptation Project": "Albemarle-Pamlico Peninsula",
}

PLACE_TYPE_OVERRIDES = {
    "Climate Change in Port Heiden, AK": "tribal_community",
    "Addressing Links Between Climate and Public Health in Alaska Native Villages": "tribal_community",
    "Alaska Native Villages Work to Enhance Local Economies as They Minimize Environmental Risks": "tribal_community",
    "Assessing the Timing and Extent of Coastal Change in Western Alaska": "tribal_community",
    "I\u00f1upiat Work to Preserve Food and Traditions on Alaska's North Slope": "tribal_community",
    "Lapwai, Idaho Local Foods, Local Places Summary Report": "tribal_community",
    "Mission, South Dakota Local Foods, Local Places Summary Report": "tribal_community",
    "Relocating the Native Village of Shishmaref, Alaska Due to Coastal Erosion": "tribal_community",
    "Recertifying Utility Workers in a Small, Remote Community": "statewide_or_multi_community",
    "Brownfield to Brewery: DNREC delivers a win-win in Delaware": "statewide_or_multi_community",
    "Florida's Community Resiliency Initiative": "statewide_or_multi_community",
    "Vermont Climate Action Plan": "statewide_or_multi_community",
    "Brownfields Success Story: Common Success at Cooper Commons LLC": "statewide_or_multi_community",
    "Adapting to Rising Tides in San Francisco Bay, California": "county_or_region",
    "California State Coastal Conservancy: Gravel Beach and Berm for Shorebird Habitat Creation, Erosion Control and Flood Protection": "county_or_region",
    "Climate Change and the Florida Keys": "county_or_region",
    "Oglethorpe Power's Acquisition of Walton County Power Strengthens Reliability and Affordability in Rural Georgia": "county_or_region",
    "Ralls County Electric's Vision for a Stronger, Smarter Grid": "county_or_region",
    "Minnkota Power Cooperative's $60 Million Infrastructure Upgrade for a Stronger Future": "county_or_region",
    "Finding Solutions Through Distance Learning Technology": "county_or_region",
    "Training a Workforce to Bring Nature-based Solutions into Every Project": "county_or_region",
    "Promoting Ecotourism to Conserve a Watershed in Virginia": "county_or_region",
    "Boosting Community Storm Resilience in Alaska": "statewide_or_multi_community",
    "Drought Response and Recovery Project for Water Utilities in North Marin Water District, CA": "county_or_region",
    "Drought Response and Recovery Project for Water Utilities in Tuolumne Utilities District, CA": "county_or_region",
    "Drought Response and Recovery Project for Water Utilities in Hays and Russell, KS": "statewide_or_multi_community",
    "Integrating Climate Change into the Planning and Operations of the Apostle Islands National Lakeshore, WI": "county_or_region",
    "Buffelgrass Removal, Fire, and Climate Adaptation": "county_or_region",
    "Forest Thinning to Restore Fire Resilience at Lassen Volcanic National Park": "county_or_region",
    "Great Lakes Restoration Initiative Pollinator Task Force": "county_or_region",
    "Alligator River National Wildlife Refuge/ Albemarle-Pamlico Peninsula Climate Adaptation Project": "county_or_region",
    "Expanding an Indigenous Environmental Monitoring Network: Community-driven Stewardship of Land and Water": "tribal_community",
}
STATE_OVERRIDES = {
    "WaterFire Arts Center, Providence, R.I.": "Rhode Island",
}

TITLE_OVERRIDES = {
    "Alligator River National Wildlife Refuge/ Albemarle-Pamlico Peninsula Climate Adaptation Project": "Alligator River National Wildlife Refuge / Albemarle-Pamlico Peninsula Climate Adaptation Project",
}

TOPIC_OVERRIDES = {
    "250 Birge St., Brattleboro, Vt.": [
        "Brownfields", "Land Revitalization", "Public Park", "Floodplain Restoration", "Flood Resilience"
    ],
}

SUMMARY_OVERRIDES = {
    "Alligator River National Wildlife Refuge/ Albemarle-Pamlico Peninsula Climate Adaptation Project": "The Nature Conservancy and the U.S. Fish and Wildlife Service evaluated adaptation strategies for coastal refuge lands threatened by sea-level rise across North Carolina's Albemarle-Pamlico Peninsula in Dare and Hyde Counties. The project tested shoreline stabilization and habitat restoration approaches to improve regional resilience.",
    "Expanding an Indigenous Environmental Monitoring Network: Community-driven Stewardship of Land and Water": "St. Paul Island and Indigenous partners expanded a Tribally governed environmental monitoring network that combines Indigenous knowledge, community priorities, and climate data. The shared platform supports local decisions about land, water, wildlife, and changing coastal conditions.",
    "Great Lakes Restoration Initiative Pollinator Task Force": "EPA funded the Great Lakes Restoration Initiative Pollinator Task Force to coordinate native bee conservation across the Great Lakes Basin. The partnership supports actions that improve native bee abundance, distribution, diversity, and resilience.",
    "250 Birge St., Brattleboro, Vt.": "Brattleboro cleaned a former industrial property at 250 Birge Street, restored its floodplain, and created a public park along Whetstone Brook. The project reduced flood risk while returning contaminated riverfront land to community use.",
    "South Dakota Governor's House Program - Providing Affordable Housing for 30 Years": "The South Dakota Governor's House Program combines affordable home production with correctional workforce training. Participants build energy-efficient two- and three-bedroom homes that can be placed in communities across South Dakota.",
    "Hillsboro, OR: Navigating a New River Launch": "An abandoned riverside property in Hillsboro was assessed and redeveloped as a public launch on the Tualatin River. The project created safer access for paddling and other outdoor recreation.",
    "Ambler, PA: Repowering a Historic Landmark": "Ambler restored the former Keasbey and Mattison Boiler House for new use after decades of industrial activity. Brownfields work helped return a long-vacant landmark to the community.",
    "Richmond, VA: Cheers to a Revitalized Neighborhood": "Richmond reused a former industrial site in Fulton Hill for a brewery, distribution facility, and tasting room. The project brought new investment and activity to the neighborhood.",
    "WaterFire Arts Center, Providence, R.I.": "WaterFire transformed a contaminated industrial property in Providence into a community arts center and nonprofit headquarters. EPA Brownfields support helped the organization open performance, exhibition, and community space in 2017.",
    "St. Johnsbury Hardware Store Site, St. Johnsbury, Vt.": "A former downtown hardware store in St. Johnsbury was assessed and cleaned up, then reopened as a craft distillery and event space. EPA Brownfields funding helped address vapor risks and support a new downtown business.",
    "Three Rivers Trailhead, St. Johnsbury, Vt.": "St. Johnsbury cleaned up an abandoned brownfield and built a trailhead connecting downtown to the Lamoille Valley Rail Trail. EPA assessment and cleanup funds helped remove a deteriorated building and open access to recreation.",
    "A Successful Transformation: Allentown Waterfront - Allentown, PA": "Allentown began redeveloping a 26-acre contaminated industrial site along the Lehigh River as a mixed-use waterfront district. The project reconnects underused land with the river and the surrounding community.",
    "Pittsburgh, PA: Luxury Living with an Industrial Legacy": "A former steel foundry in Pittsburgh's Lawrenceville neighborhood was redeveloped as The Foundry at 41st, an apartment community with shared space. The design keeps visible links to the area's industrial history.",
    "Revitalizing Rural Virginia Pulaski, Virginia": "Pulaski cleared the former Virginia Wood Products site and prepared the underused industrial property for redevelopment. The project supports continued investment near the town's historic core.",
    "Beech Bottom, WV: Forging a New Future in Steel Country": "The Beech Bottom Industrial Park reused a former steel plant and attracted more than $20 million in investment and about 700 jobs after redevelopment began in 2014.",
    "Weirton, WV: A Former Coal Mine Springs to Life": "Weirton and regional partners assessed a former coal mine and prepared the land for a business park. The reuse supported new local businesses, including a bakery that opened in 2016.",
    "Weirton, WV: From Abandoned School to Main Event": "Weirton used EPA brownfields assessment and cleanup grants to address asbestos at the former Cove Elementary School site. The city opened the Weirton Event Center there in 2012 for community events and outdoor concerts.",
    "Wellsburg, WV: A Local Manufacturing Expansion Takes Flight": "Wellsburg and regional partners assessed and cleaned the former Banner Fiberboard property. Eagle Manufacturing opened a distribution center and office on the site, adding 32 full-time jobs and returning the property to productive use.",
    "Shubuta, MS: Strengthening Shubuta": "Shubuta used brownfields planning and cleanup support to address underused property and strengthen the small-town community. The project connects land reuse with local revitalization goals.",
    "Overbrook Environmental Education Center Becomes Community Hub: Philadelphia, PA": "Philadelphia's Overbrook Environmental Education Center transformed a former quarry and contaminated commercial sites into an urban environmental education and community hub. Brownfields assessment, cleanup, and reuse planning support expansion toward affordable housing, public space, a health center, and a community food and wellness center.",
    "Akwesasne, New York (2022)": "The Saint Regis Mohawk Tribe brought the Akwesasne community together to build on cultural tourism, economic development, and infrastructure plans, including a new heritage center, an art gallery, and green spaces along the St. Regis River.",
    "Buchanan, Virginia (2022)": "Buchanan planned Main Street improvements, support for outdoor recreation businesses, and stronger connections between the town, the James River, nearby mountains, and regional trails.",
    "Loyal, Wisconsin Local Foods, Local Places Summary Report": "Loyal focused its action plan on strengthening the Loyal Farmers Market through vendor support, coordination, and training, and finding a new site that could attract more vendors and customers while helping revitalize downtown.",
    "Fort Pierce, Florida Local Foods, Local Places Summary Report": "Fort Pierce planned new ways for residents of the historic Lincoln Park neighborhood to access healthy local food, exercise, and learn why protecting Moore's Creek water quality matters.",
    "Fulton, New York (2025)": "Fulton plans to connect downtown and waterfront assets, engage residents, and expand access to cultural, educational, and recreational activities.",
    "Smart Growth Publications: Old North St. Louis - St. Louis, Missouri": "Old North St. Louis used EPA technical assistance to develop a neighborhood growth plan that would preserve historic character, add sustainable features, and reflect resident and stakeholder goals.",
    "Branch Street, Pawtucket, R.I.": "Pawtucket transformed a Branch Street site along the Blackstone River from illegal dumping and invasive growth into 29 affordable homes. EPA Brownfields assessment and cleanup support helped prepare the former residential and industrial land for reuse.",
    "Carlisle, Pennsylvania - Carlisle Goes Vertical": "Carlisle used a 2013 EPA Area-Wide Planning Grant to create conceptual transportation, stormwater, and redevelopment plans for three catalyst brownfield sites in the borough's northwest quadrant.",
    "Norristown, PA: Redevelopment Gets Fired Up": "Norristown assessed and reused a former firehouse as Five Saints Distillery. The business opened in 2016 and also serves as a music and community event venue.",
    "St. Johnsbury Glove Factory, St. Johnsbury, Vt.": "St. Johnsbury redeveloped a former textile factory that had been vacant for about 20 years into an animal hospital. EPA Brownfields assessment support helped prepare the gateway property for its 2021 reopening.",
    "Newell, WV: Former Football Field Scores a Victory at Home": "Newell assessed a former school football field and found no major environmental hazards, clearing the 3.5-acre property for redevelopment. The county then sold the site for reuse as a car dealership.",
    "25 Southgate Street, Worcester, Mass.": "Worcester cleaned and redeveloped a former manufacturing and foundry site in the South Worcester Industrial Park as a 50,000-square-foot home for a century-old baking company. EPA, state, and city funding helped prepare the eight-acre industrial park.",
    "Albany General Store, Albany, Vt.": "Albany rebuilt its general store after a 2013 fire and reopened it as a place for residents to gather. EPA Brownfields support provided part of the nearly $1 million project, alongside public, private, and local donor funding.",
    "Children's Museum & Theatre of Maine, Portland, Maine": "Portland assessed and cleaned former railroad and industrial land at Thompson's Point for redevelopment that includes a new home for the Children's Museum and Theatre of Maine.",
    "The Park Theatre, Jaffrey, N.H.": "Jaffrey replaced a former movie and vaudeville theatre with a new performing arts center in 2020. Brownfields assessment helped the community clean and redevelop the site after the old building was demolished in 2013.",
    "Wood Island Life Saving Station, Kittery, Maine": "Kittery is restoring a former Coast Guard lifesaving station on Wood Island as a maritime history museum. The project combines brownfields cleanup, historic preservation, and public interpretation.",
    "Ceredo, WV: A Community with Its Heart in the Right Place": "Ceredo used EPA Brownfields assessment support to help the Golden Girl Group Home evaluate land for transitional housing for young women leaving foster care. The project aimed to pair safe housing with independent-living support.",
    "Goodyear Industrial Campus, Windsor, Vt.": "Windsor cleaned a former Goodyear manufacturing site and reused it for a solar array that can provide about 500 kilowatts of energy. EPA Brownfields revolving loan funds helped finance the environmental cleanup.",
    "A Successful Transformation: The Adamston Commons": "Clarksburg assessed and cleaned a former glass manufacturing site contaminated by heavy metals, lead, arsenic, and asbestos. Redevelopment began in 2009, turning the long-vacant property into Adamston Commons commercial and retail space.",
    "Aurora, CO: Flying High Again": "Aurora used EPA planning and revolving loan support to prepare the vacant 22-acre Stanley Aviation campus for redevelopment. The former manufacturing site is part of a sustainable mixed-use community planned for roughly 18,000 residents.",
    "Lakewood, CO: Housing and the Arts at Lamar Street Station": "Lakewood replaced abandoned buildings and contaminated land near the Lamar Street light-rail station with a transit-oriented arts district and 110 sustainably designed homes, including live-work studios.",
    "Yorklyn, DE: Clean Water Funds Brownfield Redevelopment": "Delaware began cleaning and redeveloping former paper and fiber mill land in Yorklyn after industrial activity contaminated nearby soil and groundwater. The project supports mixed-use and commercial reuse in the Auburn Valley area.",
    "Chicago, IL: Strong Roots in Professional Growth": "Chicago nonprofit OAI provides environmental health, safety, and job training with support from EPA's Environmental Workforce Development and Job Training program. Its programs serve about 4,000 residents each year and report job placement for more than 85 percent of graduates.",
    "Waterloo, IA: From Brownfields to Revitalized Downtown": "Waterloo used Brownfields assessment, cleanup, and state-response support to address contaminated and underused downtown properties. Reuse includes riverfront housing, a human-services campus, public recreation, and mixed-use development.",
    "Lexington, KY: Revitalization on the Docket": "Lexington formed a public-private partnership to restore its historic 1898 county courthouse after environmental hazards forced the building to close. The reuse plan brought together a museum, restaurant, bar, visitor center, and event space.",
    "Lincoln, NE: A Heyday in West Haymarket": "Lincoln used EPA targeted Brownfields assessments to help transform former rail yards, a manufactured-gas site, and other underused land in West Haymarket. The district now includes a civic arena, hotels, community space, offices, retail, and homes.",
    "Woodbridge Township, NJ: Bringing Clean Energy to an Abandoned Waterfront": "Woodbridge Township investigated groundwater contamination at a 185-acre former chemical manufacturing property along the Raritan River. The reuse plan includes the Woodbridge Energy Center and Woodbridge Waterfront Park.",
    "Empowered by Innovation Philadelphia, Pennsylvania": "Philadelphia reused contaminated industrial land along the Lower Schuylkill River for mixed commercial and research activity. The University of Pennsylvania's Pennovation Center became a cornerstone of the emerging innovation district.",
    "From Glass to Green Jeannette, Pennsylvania": "Jeannette began cleaning and redeveloping the former Jeannette Glass plant after years of vacancy and industrial contamination. The work prepared the site for new industrial and commercial use.",
    "'Erie' Assessments in Two Abandoned Facilities Erie County, Pennsylvania": "Erie County used EPA assessment grants to investigate contamination at the former Erie Malleable Iron and Quin-T Tech Paper and Boards facilities. Planned reuse includes industrial and office space with green space in the target area.",
    "Former Alcoa Research Park New Kensington, PA": "New Kensington assessed a former Alcoa research park and found isolated asbestos and lead paint that required abatement. Redevelopment of two buildings created about 40,000 square feet for ten small businesses and roughly 30 initial jobs.",
    "Shell Distribution Facility McKees Rocks/Stowe, PA.": "McKees Rocks and Stowe cleaned and improved a former rail yard that became a CSX intermodal facility in 2017. The site was later leased for transportation supporting the Shell cracker plant, with adjacent land planned for distribution buildings.",
    "Homewood Senior Housing & Café Homewood Ave, Pittsburgh, PA.": "Pittsburgh used EPA assessment funding to investigate two former gas-station properties in Homewood and remove petroleum-stained soil. The site was redeveloped with 41 affordable senior homes, a cafe, and neighborhood retail space.",
    "Lawrenceville's Foundry Willow St. /Lawrenceville, Pittsburgh, PA.": "Pittsburgh assessed a vacant steel-fabrication property in Lawrenceville where heavy metals exceeded residential standards. A clean-soil cap helped the project secure financing and proceed toward residential redevelopment.",
    "Coventry, RI: Attracting Wildlife to a Former Dumping Ground": "Coventry cleaned a former construction dumping ground at 100 Sandy Bottom Road and pursued a public park with restored wetland habitat. The project combined community recreation with wildlife protection.",
    "Aberdeen, SD: Continuing a Legacy of Learning": "Aberdeen purchased a deteriorated former church and school block in 2011 and assessed it for reuse. The city planned the downtown property as a new public library and community learning space.",
    "Austin, TX: Festival Beach Food Forest": "Austin residents and local organizations shaped public parkland near Festival Beach into a food forest with fruit trees, edible plants, and medicinal herbs available to the community. Brownfields assessment helped support the public reuse effort.",
    "Roanoke, Virginia - Roanoke Railway to Reuse": "Roanoke assessed and planned cleanup of former railway and industrial land in the South Jefferson area. Redevelopment brought offices and medical facilities to sites affected by industrial contamination.",
    "A Tasteful Redevelopment for a Former Gas Station Northampton County, Virginia": "Northampton County used EPA assessment funding to investigate an idle former gas station and auto-repair property. The work identified petroleum releases and an aging underground tank, helping the buyer arrange removal and reuse the site for commercial sea-salt production.",
    "Janesville, WI: Locally Driven Revitalization Plan Turns Riverfront Brownfields into a Downtown Destination": "Janesville used Brownfields assessment and area-wide planning to create an action plan for former industrial land near its riverfront, including the closed General Motors assembly plant. The plan coordinates housing, parks, retail, and community gathering spaces.",
    "Great Falls, MT: Taking Back Downtown One Brownfield at a Time": "Great Falls used EPA targeted assessment and revolving loan support to clean and reuse several downtown brownfields. Projects converted former gas-station, livery, and bank properties into a coffee shop and park, a hotel and pub, and nonprofit offices.",
    "Poplar, MT: Making Things Right at a Former Airfield": "Poplar partners addressed petroleum contamination at a former airfield and worked with the Fort Peck Assiniboine and Sioux Tribes, federal partners, and a nonprofit to build a sustainable village with housing, recreation, and transportation uses.",
    "Two Rivers, Wisconsin (2025)": "Two Rivers plans to address brownfield cleanup, shoreline erosion, and water quality while reimagining downtown as an outdoor recreation hub connected to the watershed and regional attractions. The project also supports recreation businesses and year-round opportunities for residents and visitors.",
    "Park County, Wyoming (2025)": "The Powell Economic Partnership and community partners aim to create a countywide outdoor recreation strategy, expand safe recreation opportunities, support sustainable tourism and local jobs, and strengthen stewardship of natural resources.",
    "Yreka, California (2022)": "The Siskiyou Economic Development Council and partners worked to grow Yreka's downtown amenities and improve physical connections to outdoor recreation.",
    "Republic, Washington (2025)": "Tri County Economic Development District and community partners plan to position Republic as a regional outdoor recreation hub, help local businesses benefit from tourism, and expand recreation opportunities for residents.",
    "Drought Response and Recovery Project for Water Utilities in North Marin Water District, CA": "EPA's case study documents how North Marin Water District responded to drought, with lessons for small and midsized drinking water utilities.",
    "Drought Response and Recovery Project for Water Utilities in Tuolumne Utilities District, CA": "EPA's case study documents how Tuolumne Utilities District responded to drought, with lessons for small and midsized drinking water utilities.",
    "Drought Response and Recovery Project for Water Utilities in Hogansville, GA": "EPA's case study documents how Hogansville's drinking water utility responded to drought, with lessons for small and midsized water systems.",
    "Drought Response and Recovery Project for Water Utilities in Hays and Russell, KS": "EPA's case study documents how the cities of Hays and Russell responded to drought, with lessons for small and midsized drinking water utilities.",
    "Drought Response and Recovery Project for Water Utilities in Castine, Maine": "EPA's case study documents how Castine's drinking water utility responded to drought, with lessons for small and midsized water systems.",
    "Drought Response and Recovery Project for Water Utilities in Las Vegas, NM": "EPA's case study documents how Las Vegas, New Mexico, responded to drought, with lessons for small and midsized drinking water utilities.",
    "Drought Response and Recovery Project for Water Utilities in Spicewood Beach, TX": "EPA's case study documents how Spicewood Beach's drinking water utility responded to drought, with lessons for small and midsized water systems.",
}

EXCLUDED_TITLES = {
    "A Former Coal Mine Springs to Life",
}

INTERNAL_MARKERS = (
    "protos treats",
    "protos indexes",
    "record remains flagged",
    "image rights",
    "internal source",
    "local source",
)


def compact(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def repair_text(value: object) -> str:
    text = compact(value).replace("\u00a0", " ")
    markers = ("Ã", "Â", "â", "Æ", "ï¿½", "\ufffd")
    for _ in range(3):
        current_score = sum(text.count(marker) for marker in markers)
        if not current_score:
            break
        candidates = [text]
        for encoding in ("cp1252", "latin-1"):
            try:
                candidates.append(text.encode(encoding).decode("utf-8"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                try:
                    candidates.append(text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore"))
                except (LookupError, UnicodeError):
                    pass
        best = min(candidates, key=lambda item: sum(item.count(marker) for marker in markers))
        if best == text:
            break
        text = best
    text = text.replace("ÆŸ", "ti").replace("\u019f", "ti")
    text = re.sub(r"\bun-\s+derutilized\b", "underutilized", text, flags=re.I)
    return text.strip()


def valid_place(value: str, title: str) -> bool:
    lowered = value.lower()
    if not value or len(value) > 72 or ":" in value or lowered.startswith(("of ", "the ", "a ", "an ")):
        return False
    if any(token in lowered for token in (
        "$", "combined value", "grant recipient", "grant type", "authority", "commission",
        "district", "department", "agency", "foundation", "partnership", " inc", "company",
        "industrial development", "climate action plan", "successful transformation", "workers in",
        "planning for", "brownfield to", "site description",
    )):
        return False
    title_words = set(re.findall(r"[a-z]{4,}", title.lower()))
    place_words = set(re.findall(r"[a-z]{4,}", lowered))
    return not (len(place_words) >= 5 and len(place_words - title_words) <= 1)
def place_from_title(title: str) -> str:
    parts = [part.strip(" .") for part in title.split(",") if part.strip(" .")]
    if len(parts) < 2:
        return ""
    candidate = parts[-2]
    if ":" in candidate:
        candidate = candidate.rsplit(":", 1)[-1].strip()
    if not candidate or len(candidate) > 55:
        return ""
    return candidate


def clean_theme(value: object) -> str:
    theme = repair_text(value)
    lowered = theme.lower()
    if len(theme) > 48:
        return ""
    if "steel fabrication" in lowered:
        return "Steel Fabrication"
    if any(marker in lowered for marker in ("complete evaluation", "funded through", "recipient", "contamination")):
        return ""
    if re.search(r"\b(and|for|an|the|of|to|with|in)\.?$", lowered):
        return ""
    return theme


def clean_summary(candidate: str) -> str:
    return repair_text(candidate)


def strip_public_source_labels(candidate: str, title: str) -> str:
    text = repair_text(candidate)
    text = re.sub(r"^R1 Success Story:\s*", "", text, flags=re.I)
    if text.lower().startswith(title.lower()):
        text = text[len(title) :].lstrip(" .:-")
    text = re.sub(r"^\(pdf\)\s*\([^)]*\)\s*", "", text, flags=re.I)
    text = re.sub(r"\s+as pictured above\b", "", text, flags=re.I)
    return text.strip()

def summary_is_public_ready(candidate: str, title: str) -> bool:
    lowered = candidate.lower()
    if len(candidate) < 55 or len(candidate) > 560:
        return False
    if any(marker in candidate for marker in ("Ã", "Â", "â", "Æ", "ï¿½", "\ufffd")):
        return False
    if any(marker in lowered for marker in ("epa grant recipients", "epa grant types", "site description", "site descrip", "photo courtesy", "image lessons learned", "figure 1", "years awarded", "grant types:", "grants and resources:")):
        return False
    if candidate[:1].islower() or "\u019f" in candidate:
        return False
    title_norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    candidate_norm = re.sub(r"[^a-z0-9]+", " ", lowered).strip()
    repeated = f"{title_norm} is a climate resilience toolkit case record for {title_norm}"
    return candidate_norm != repeated


def bounded_source_sentence(value: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", repair_text(value).replace("; ", ". "), maxsplit=1)[0].strip(" -")
    if not sentence:
        return ""
    words = sentence.split()
    if len(words) <= 49:
        return sentence if sentence[-1] in ".!?" else sentence + "."
    boundaries: list[int] = []
    for match in re.finditer(r",\s+|\s+(?:and|while|as well as|including|which|that)\s+", sentence, re.I):
        word_count = len(sentence[: match.start()].split())
        if 20 <= word_count <= 46:
            boundaries.append(match.start())
    if not boundaries:
        return ""
    clipped = sentence[: boundaries[-1]].strip(" ,;:-")
    return clipped + "." if len(clipped) >= 55 else ""

def planning_summary(case: dict, title: str) -> str:
    long_summary = repair_text((case.get("summary") or {}).get("long"))
    for marker in ("The cited EPA description says:", "For this partner community, the report states:"):
        if marker not in long_summary:
            continue
        segment = long_summary.split(marker, 1)[1].strip()
        lowered = segment.lower()
        stops = [
            lowered.find(stop)
            for stop in (" epa describes", " the case is useful", " protos indexes", " the record is source-backed")
            if lowered.find(stop) >= 0
        ]
        if stops:
            segment = segment[: min(stops)]
        sentence_ready = re.sub(r";\s*(and|or)\s+", r", \1 ", segment, flags=re.I)
        sentence_ready = re.sub(r";\s*([a-z])", lambda match: ". " + match.group(1).upper(), sentence_ready)
        summary = sentence_summary(sentence_ready) or bounded_source_sentence(segment)
        if summary_is_public_ready(summary, title):
            return summary
    return ""


def fallback_summary(title: str, program: str, place: str, state: str, themes: list[str], year: str) -> str:
    location = state if place == "Multiple communities" else f"{place}, {state}"
    topic_text = ", ".join(theme.lower() for theme in themes[:3] if theme) or "community priorities"
    when = f"In {year}, " if year else ""
    if program == "Recreation Economy for Rural Communities":
        return f"{when}{location} received EPA planning assistance to connect outdoor recreation with {topic_text}. The official RERC page identifies the partner community and its planning focus."
    if program == "Local Foods, Local Places":
        return f"{when}{location} used Local Foods, Local Places planning assistance to work on {topic_text}. The official summary report records the community's goals and action steps."
    if program == "EPA Brownfields Success Stories":
        return f"This EPA success story describes how {location} addressed {title.lower()} and related land-reuse work. The official page provides the cleanup, partners, and results."
    if program == "EPA Examples of Smart Growth Communities and Projects":
        return f"This EPA example describes {title.lower()} in {location}, with lessons related to {topic_text}."
    if program == "U.S. Climate Resilience Toolkit":
        return f"This federal case study describes {title.lower()} in {location}, with lessons related to {topic_text}."
    return f"This USDA Rural Development story describes {title.lower()} in {location}, with details about {topic_text}."
def public_url(value: object) -> str:
    url = compact(value)
    if not url.startswith(("https://", "http://")):
        return ""
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return url if host.lower() in PUBLIC_HOSTS else ""


def sentence_summary(value: object, max_chars: int = 500) -> str:
    text = clean_summary(repair_text(value))
    if not text:
        return ""
    artifacts = (
        "photo credit", "photo courtesy", "pictured here", "download success story",
        "epa grant recipient", "epa grant type", "current use:", "former use",
        "supporting environmental excellence", "apply for local foods", "image lessons learned",
        "figure 1", "years awarded", "site descrip", "grant types:", "grants and resources:",
    )
    selected: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence = sentence.strip(" -")
        lowered = sentence.lower()
        if len(sentence) < 35 or len(sentence) > 300 or len(sentence.split()) > 42:
            continue
        if any(marker in lowered for marker in artifacts):
            continue
        if re.search(r"\b(?:protos|record remains|image rights|source manifest)\b", lowered):
            continue
        if re.search(r"\b(?:the|a|an|of|for|with|from|to|and|or|u\.s)\.?$", lowered):
            continue
        candidate = " ".join(selected + [sentence])
        if len(candidate) > max_chars:
            break
        selected.append(sentence)
        if len(selected) >= 2:
            break
    result = " ".join(selected)
    if result and result[-1] not in ".!?":
        result += "."
    return result


def public_case_prefix(case: dict) -> str:
    long_summary = repair_text((case.get("summary") or {}).get("long"))
    if not long_summary:
        return ""
    lowered = long_summary.lower()
    cut_points = [lowered.find(marker) for marker in INTERNAL_MARKERS if lowered.find(marker) >= 0]
    if cut_points:
        long_summary = long_summary[: min(cut_points)]
    return long_summary.strip()


def first_public_narrative(source: dict, case: dict) -> str:
    source_candidates: list[str] = []
    for unit in source.get("extracted_units", []):
        fields = unit.get("fields") or {}
        source_candidates.extend(
            repair_text(fields.get(key))
            for key in ("source_text", "summary", "description", "project_description")
        )
        source_candidates.append(repair_text(unit.get("text")))
    case_candidates = [
        public_case_prefix(case),
        *(repair_text(item.get("text")) for item in case.get("takeaways", [])),
        repair_text((case.get("summary") or {}).get("short")),
    ]
    if source.get("source_type") in {"epa_lflp_summary_report_pdf", "epa_rerc_partner_page"}:
        candidates = [case_candidates[-1], *case_candidates[:-1], *source_candidates]
    else:
        candidates = [*source_candidates, *case_candidates]
    for candidate in candidates:
        lowered = candidate.lower()
        if any(marker in lowered for marker in INTERNAL_MARKERS):
            continue
        summary = sentence_summary(candidate)
        if summary:
            return summary
    return ""

def year_for(case: dict, program_name: str) -> str:
    lookup = (case.get("geography") or {}).get("lookup_context") or {}
    values = [
        compact(lookup.get("year")),
        compact(lookup.get("year_published")),
    ]
    if program_name not in {"EPA Examples of Smart Growth Communities and Projects"}:
        values.append(compact((case.get("programs") or [{}])[0].get("project_or_round")))
    for value in values:
        match = re.search(r"\b(19|20)\d{2}\b", value)
        if match:
            return match.group(0)
    return ""

def stage_for(case: dict, program_name: str, source_url: str) -> str:
    if program_name == "EPA Brownfields Success Stories":
        return "Cleanup"
    if program_name in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"}:
        return "Planning"
    if program_name in {"EPA Examples of Smart Growth Communities and Projects", "USDA Rural Development Success Stories"}:
        return "Implementation"
    if "action-plan" in source_url or "action plan" in repair_text(case.get("title")).lower():
        return "Planning"
    return "Implementation"


def normalized_place_type(case: dict, place: str, state: str) -> str:
    title = repair_text(case.get("title"))
    if title in PLACE_TYPE_OVERRIDES:
        return PLACE_TYPE_OVERRIDES[title]
    geography = case.get("geography") or {}
    raw = repair_text(geography.get("place_type"))
    context = " ".join(
        [
            title,
            place,
            raw,
        ]
    ).lower()
    if re.search(r"\b(tribal|tribe|native village|reservation|pueblo|navajo|hopi|passamaquoddy)\b", context):
        return "tribal_community"
    if place == "Multiple communities":
        return "statewide_or_multi_community"
    if re.search(r"\b(county|region|regional|service area|watershed|bay area|shoreline|florida keys)\b", raw.lower() + " " + place.lower()):
        return "county_or_region"
    return "town_or_city"
def build_record(case_path: Path, checked_on: str) -> dict | None:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    program = (case.get("programs") or [{}])[0]
    program_name = compact(program.get("program_name"))
    if program_name not in PROGRAMS:
        return None
    if program_name in EXCLUDED_PUBLIC_PROGRAMS:
        return None

    geography = case.get("geography") or {}
    title = repair_text(case.get("title"))
    if title in EXCLUDED_TITLES:
        return None
    state = STATE_OVERRIDES.get(title, repair_text(geography.get("state")))
    place = PLACE_OVERRIDES.get(title, repair_text(geography.get("place_name")))
    if title not in PLACE_OVERRIDES and (place.lower() == state.lower() or not valid_place(place, title)):
        place = place_from_title(title) or "Multiple communities"
    if not state or state == "Unknown" or not place:
        return None
    if int((case.get("qaqc") or {}).get("blocker_count", 0) or 0):
        return None

    manifest_path = case_path.parent / compact(case.get("source_manifest"))
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = next(
        (
            item
            for item in manifest.get("sources", [])
            if item.get("source_type") in SOURCE_TYPES
            and item.get("review_status") not in {"blocked", "not_started"}
            and public_url(item.get("origin_path_or_url"))
        ),
        None,
    )
    if not source:
        return None

    summary = first_public_narrative(source, case)
    themes = [
        clean_theme(theme)
        for theme in case.get("themes", [])
        if clean_theme(theme)
        and clean_theme(theme).lower()
        not in {
            "rerc",
            "rural development",
            "case study",
            program_name.lower(),
            "epa success story",
            state.lower(),
        }
    ]
    themes = TOPIC_OVERRIDES.get(title, list(dict.fromkeys(themes))[:8])
    if not themes:
        fallback_theme = clean_theme(case.get("case_type"))
        themes = [fallback_theme] if fallback_theme else []

    title = re.sub(r"^RERC Partner Community:\s*", "", title, flags=re.I)
    source_url = public_url(source.get("origin_path_or_url"))
    year = year_for(case, program_name)
    summary = SUMMARY_OVERRIDES.get(title, summary)
    summary = strip_public_source_labels(summary, title)
    if program_name in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"}:
        summary = SUMMARY_OVERRIDES.get(title) or planning_summary(case, title) or summary
    if not summary_is_public_ready(summary, title):
        summary = fallback_summary(title, program_name, place, state, themes, year)
    if program_name in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"} and place != "Multiple communities" and place.lower() not in summary.lower():
        summary = f"{place}: {summary}"
    if summary[-1] not in ".!?":
        summary += "."
    item_id = "RERC-CASE-" + re.sub(r"[^A-Z0-9]+", "-", compact(case.get("case_id")).upper()).strip("-")
    display_title = TITLE_OVERRIDES.get(title, title)
    return {
        "item_id": item_id,
        "item_type": "Case Study",
        "title": display_title,
        "organization": program_name,
        "status": (
            "Planning assistance example"
            if program_name in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"}
            else "Published case study"
        ),
        "last_checked": checked_on,
        "geography": state,
        "eligible_users": "Communities looking for comparable examples",
        "project_stage": stage_for(case, program_name, source_url),
        "topic_tags": "; ".join(themes),
        "support_type": "Case study",
        "amount_or_cost": "",
        "match_or_cost": "",
        "deadline_or_availability": year,
        "summary": summary,
        "why_it_matters": "",
        "source_url": source_url,
        "case_place": place,
        "case_state": state,
        "case_place_type": normalized_place_type(case, place, state),
        "case_program": program_name,
        "case_year": year,
        "case_partners": "; ".join(
            item for item in (repair_text(value) for value in case.get("partners", [])[:5])
            if item and len(item) <= 90 and "$" not in item
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a public-safe RERC case-study projection from Protos.")
    parser.add_argument("--protos-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checked-on", default=date.today().isoformat())
    args = parser.parse_args()

    case_root = args.protos_root / "data" / "cases"
    records = [
        record
        for path in sorted(case_root.rglob("case.json"))
        if (record := build_record(path, args.checked_on))
    ]
    records.sort(key=lambda item: (item["case_state"], item["case_place"], item["title"]))
    serialized = json.dumps(
        {
            "generated_at": args.checked_on,
            "provenance": "Official federal community examples with public links; no images or private administrative fields.",
            "items": records,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if re.search(r"[A-Z]:\\|Z:\\|D:\\", serialized, flags=re.I):
        raise RuntimeError("Public case-study bundle contains a local Windows path.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("window.RERC_CASE_STUDIES=" + serialized + ";\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "PASS", "count": len(records), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
