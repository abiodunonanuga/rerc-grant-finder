#!/usr/bin/env python3
"""Add reviewed Round 2 references to the public RERC resource catalog."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


CHECKED_DATE = "2026-08-14"

TITLE_OVERRIDES = {
    "R2REF-003": "Indigenous-Led Tourism Partnership Toolkit",
    "R2REF-004": "ARISE Regional Multistate Collaboration Toolkit",
    "R2REF-008": "Travel Oregon Outdoor Recreation Development Resources",
    "R2REF-009": "Pennsylvania Outdoor Recreation Plan",
    "R2REF-010": "Pennsylvania Outdoor Recreation Plan Webinar: Community Engagement",
    "R2REF-011": "Pennsylvania Outdoor Recreation Plan Webinar: Implementation",
    "R2REF-012": "Pennsylvania Outdoor Recreation Webinar: Funding and Economic Development, Part 1",
    "R2REF-013": "Pennsylvania Outdoor Recreation Webinar: Funding and Economic Development, Part 2",
    "R2REF-014": "Pennsylvania Outdoor Recreation Webinar: Funding and Economic Development, Part 3",
    "R2REF-015": "Skowhegan Outdoor Recreation Plan",
    "R2REF-016": "Skowhegan Strategic Plan for Community Transformation",
    "R2REF-017": "Colorado Statewide Comprehensive Outdoor Recreation Plan",
    "R2REF-018": "The Conservation Fund Project Library",
    "R2REF-020": "Town Forest Recreation Planning Toolkit",
    "R2REF-026": "Parks, Trails, and Health Workbook",
    "R2REF-028": "Stewardship Mapping and Assessment Project",
    "R2REF-029": "Putting Smart Growth to Work in Rural Communities",
    "R2REF-031": "Why Some Places Thrive and Others Fail",
    "R2REF-036": "Power of 10+ Placemaking Guide",
    "R2REF-037": "Rebuilding Downtown: A Guidebook for Revitalization",
    "R2REF-032": "Resources for Transitioning Economies",
    "R2REF-033": "Planning for Prosperity in Small Towns and Rural Regions",
    "R2REF-035": "How to Do Creative Placemaking",
    "R2REF-038": "Community Wealth Building Action Guide",
    "R2REF-039": "USDA Rural Community Development Resources",
    "R2REF-040": "USDA Downtown Revitalization Resources",
    "R2REF-041": "Rural America Placemaking Toolkit",
    "R2REF-042": "EDA Tools for Economic Development",
    "R2REF-043": "Essential Smart Growth Fixes for Rural Communities",
    "R2REF-044": "Framework for a Smart Growth Economic Development Strategy",
    "R2REF-045": "Smart Growth Self-Assessment for Rural Communities",
    "R2REF-046": "Growing Rural Equitable Outdoor Recreation Economies",
    "R2REF-047": "Outdoor Recreation Satellite Account",
    "R2REF-049": "Recreation Is a Bigger Share of the U.S. Economy Than Agriculture or Mining",
    "R2REF-050": "Rural Recreation Counties Show More Population Resilience",
    "R2REF-051": "Headwaters Economics Outdoor Recreation Resources",
    "R2REF-054": "Economic Profile System",
    "R2REF-058": "National Governors Association Outdoor Recreation Learning Network",
    "R2REF-059": "River Access Planning Guide",
    "R2REF-060": "Northern Forest Outdoor Recreation Economy Symposium",
    "R2REF-061": "Outdoor Industry Association Research and Resources",
    "R2REF-064": "State-Level Outdoor Recreation Reports",
    "R2REF-067": "Outdoor Recreation Roundtable Resources",
    "R2REF-070": "National Outdoor Recreation Economic Data",
    "R2REF-071": "State Outdoor Recreation Economic Data",
    "R2REF-072": "Rural Economic Development Toolkit",
    "R2REF-074": "Elevating Outdoor Recreation Together",
    "R2REF-075": "Society of Outdoor Recreation Professionals Resource Library",
    "R2REF-076": "Federal Outdoor Recreation Trends and Economic Opportunities",
    "R2REF-077": "Recreation Economy at USDA: Resources for Rural Communities",
    "R2REF-078": "Recreation Economic Values for the National Forest System",
    "R2REF-079": "Gateway and Natural Amenity Region Community Toolkit",
    "R2REF-082": "FHWA Bicycle and Pedestrian Program",
    "R2REF-083": "FHWA Pedestrian and Bicycle Funding Opportunities",
    "R2REF-084": "Small Town and Rural Multimodal Networks",
    "R2REF-085": "Trails Research and Searchable Benefits Library",
    "R2REF-086": "Navigating Main Streets as Places",
    "R2REF-087": "Trail-Building Toolbox",
    "R2REF-088": "Trail Towns Resources",
    "R2REF-089": "Transportation Alternatives Program: Dollars and Deadlines",
    "R2REF-090": "Get to Know Your Neighborhood With a Walk Audit",
    "R2REF-091": "The Scenic Route: Creative Placemaking and Transportation",
}

ORGANIZATION_OVERRIDES = {
    "R2REF-003": "American Indigenous Tourism Association and partners",
    "R2REF-004": "Appalachian Regional Commission",
    "R2REF-008": "Travel Oregon",
    "R2REF-009": "Pennsylvania Department of Conservation and Natural Resources",
    "R2REF-010": "Pennsylvania Department of Conservation and Natural Resources",
    "R2REF-011": "Pennsylvania Department of Conservation and Natural Resources",
    "R2REF-012": "Pennsylvania Department of Conservation and Natural Resources",
    "R2REF-013": "Pennsylvania Department of Conservation and Natural Resources",
    "R2REF-014": "Pennsylvania Department of Conservation and Natural Resources",
    "R2REF-015": "Main Street Skowhegan and community partners",
    "R2REF-016": "Main Street Skowhegan and community partners",
    "R2REF-017": "Colorado Parks and Wildlife",
    "R2REF-018": "The Conservation Fund",
    "R2REF-020": "Vermont Urban and Community Forestry",
    "R2REF-021": "Vermont Urban and Community Forestry",
    "R2REF-022": "Vermont Urban and Community Forestry",
    "R2REF-023": "Vermont Urban and Community Forestry",
    "R2REF-024": "Vermont Urban and Community Forestry",
    "R2REF-025": "Vermont Urban and Community Forestry",
    "R2REF-026": "National Park Service and Centers for Disease Control and Prevention",
    "R2REF-028": "USDA Forest Service",
    "R2REF-029": "U.S. Environmental Protection Agency and partners",
    "R2REF-030": "Main Street America",
    "R2REF-031": "Virginia Municipal League",
    "R2REF-032": "National Association of Counties and partners",
    "R2REF-033": "National Association of Development Organizations",
    "R2REF-034": "National Association of Development Organizations",
    "R2REF-035": "National Endowment for the Arts",
    "R2REF-036": "Project for Public Spaces",
    "R2REF-037": "Smart Growth America",
    "R2REF-038": "The Democracy Collaborative",
    "R2REF-039": "USDA National Agricultural Library",
    "R2REF-040": "USDA National Agricultural Library",
    "R2REF-041": "USDA Rural Development and University of Kentucky",
    "R2REF-042": "U.S. Economic Development Administration",
    "R2REF-043": "U.S. Environmental Protection Agency",
    "R2REF-044": "U.S. Environmental Protection Agency",
    "R2REF-045": "U.S. Environmental Protection Agency",
    "R2REF-046": "Aspen Institute Community Strategies Group",
    "R2REF-047": "U.S. Bureau of Economic Analysis",
    "R2REF-048": "The Daily Yonder",
    "R2REF-049": "The Daily Yonder",
    "R2REF-050": "The Daily Yonder",
    "R2REF-051": "Headwaters Economics",
    "R2REF-052": "Headwaters Economics",
    "R2REF-053": "Headwaters Economics",
    "R2REF-054": "Headwaters Economics",
    "R2REF-055": "Headwaters Economics",
    "R2REF-056": "Headwaters Economics",
    "R2REF-057": "Headwaters Economics",
    "R2REF-058": "National Governors Association",
    "R2REF-059": "National Park Service",
    "R2REF-060": "Northern Forest Center",
    "R2REF-061": "Outdoor Industry Association",
    "R2REF-062": "Outdoor Industry Association",
    "R2REF-063": "Outdoor Industry Association and Headwaters Economics",
    "R2REF-064": "Outdoor Industry Association",
    "R2REF-065": "Outdoor Industry Association",
    "R2REF-066": "Outdoor Industry Association",
    "R2REF-067": "Outdoor Recreation Roundtable",
    "R2REF-068": "Outdoor Recreation Roundtable",
    "R2REF-069": "Outdoor Recreation Roundtable",
    "R2REF-070": "Outdoor Recreation Roundtable",
    "R2REF-071": "Outdoor Recreation Roundtable",
    "R2REF-072": "Outdoor Recreation Roundtable",
    "R2REF-073": "Outdoor Recreation Roundtable",
    "R2REF-074": "Utah State University Institute of Outdoor Recreation and Tourism",
    "R2REF-075": "Society of Outdoor Recreation Professionals",
    "R2REF-076": "USDA Forest Service Research and Development",
    "R2REF-077": "USDA Rural Development",
    "R2REF-078": "USDA Forest Service Research and Development",
    "R2REF-079": "Utah State University",
    "R2REF-082": "Federal Highway Administration",
    "R2REF-083": "Federal Highway Administration",
    "R2REF-084": "Federal Highway Administration",
    "R2REF-085": "Headwaters Economics",
    "R2REF-086": "Main Street America and Project for Public Spaces",
    "R2REF-087": "Rails-to-Trails Conservancy",
    "R2REF-088": "Rails-to-Trails Conservancy",
    "R2REF-089": "Safe Routes Partnership",
    "R2REF-090": "Safe Routes Partnership",
    "R2REF-091": "Transportation for America",
}

SUMMARY_OVERRIDES = {
    "R2REF-005": "Connects outdoor groups led by people of color, LGBTQIA+ people, people with disabilities, and other groups that have often been left out.",
    "R2REF-006": "Builds Black leadership and connections with nature through local programs and a national network.",
    "R2REF-008": "Offers guides and examples for planning outdoor recreation and tourism projects in Oregon.",
    "R2REF-030": "Offers guides, toolkits, articles, and some free resources for Main Street work. Some materials require membership.",
    "R2REF-031": "Explains practical ways communities can support growth while protecting what makes each place special.",
    "R2REF-034": "Shows how rural communities can build local wealth by using local skills, businesses, and other assets.",
    "R2REF-036": "Shows how to assess public places and add useful things for people to do.",
    "R2REF-043": "Lists policy changes rural communities can use to guide growth and protect local character.",
    "R2REF-044": "Helps communities build an economic development plan around local needs and assets.",
    "R2REF-045": "Provides a checklist for reviewing rural growth and development policies.",
    "R2REF-051": "Offers research and tools about land, outdoor recreation, and community growth.",
    "R2REF-054": "Creates free reports about people, jobs, land, and major industries for a community, county, or state.",
    "R2REF-067": "Offers policy, research, and industry resources about outdoor recreation.",
    "R2REF-068": "Shares real outdoor-industry jobs, career paths, and work-life experiences.",
    "R2REF-069": "Describes outdoor recreation jobs for people with different skills and training.",
    "R2REF-075": "Offers training, webinars, research, and tools for outdoor recreation professionals.",
    "R2REF-078": "Estimates the economic value of recreation across the National Forest System.",
    "R2REF-082": "Links to federal guidance about walking, biking, safety, design, and funding.",
    "R2REF-083": "Lists federal funding programs that may support walking and biking projects.",
    "R2REF-084": "Shows walking and biking network designs for small towns and rural areas.",
    "R2REF-085": "Provides research about trail use, benefits, and economic effects.",
    "R2REF-086": "Shows how transportation projects can make Main Streets safer and more welcoming.",
    "R2REF-087": "Provides tools for planning, building, and managing trails.",
    "R2REF-088": "Helps communities connect trails with downtown businesses, visitors, and local plans.",
    "R2REF-089": "Shows Transportation Alternatives Program funding and deadlines for each state.",
    "R2REF-090": "Provides a simple walk-audit guide for finding neighborhood safety and access problems.",
    "R2REF-015": "Summarizes Skowhegan's outdoor recreation goals, assets, priorities, and next steps for local economic and community development.",
    "R2REF-016": "Shares Skowhegan's strategic priorities for community and economic development and coordinated local action.",
    "R2REF-020": "Provides a step-by-step process and webinar series for planning public recreation in Vermont town forests.",
    "R2REF-028": "Explains how communities can map stewardship groups and activities to understand local conservation networks and partnerships.",
    "R2REF-032": "Offers tools and examples to help counties and regions diversify economies affected by industry change.",
    "R2REF-037": "Provides practical steps and examples for rebuilding and revitalizing downtowns.",
    "R2REF-039": "Collects USDA programs and information for rural community development.",
    "R2REF-040": "Collects USDA guides and examples for downtown and Main Street revitalization.",
    "R2REF-041": "Offers tools, examples, and training to help rural communities plan public places with local partners.",
    "R2REF-048": "Explains how outdoor recreation can create jobs, attract visitors, and support rural economic development.",
    "R2REF-049": "Summarizes federal data showing outdoor recreation's share of the U.S. economy.",
    "R2REF-050": "Reviews research showing that many rural recreation counties have retained or gained population better than similar places.",
    "R2REF-058": "Connects states with peer learning, policy examples, and resources for growing outdoor recreation economies.",
    "R2REF-060": "Shares presentations and lessons from a regional symposium on outdoor recreation in the Northern Forest.",
    "R2REF-072": "Provides practical steps for rural communities to use outdoor recreation in economic development.",
    "R2REF-079": "Provides planning tools and examples for gateway communities near public lands and natural amenities.",
}
GEOGRAPHY_OVERRIDES = {
    **{key: "Pennsylvania" for key in ("R2REF-009", "R2REF-010", "R2REF-011", "R2REF-012", "R2REF-013", "R2REF-014")},
    **{key: "Maine" for key in ("R2REF-015", "R2REF-016")},
    "R2REF-017": "Colorado",
    "R2REF-019": "New York",
    **{key: "Vermont" for key in ("R2REF-020", "R2REF-021", "R2REF-022", "R2REF-023", "R2REF-024", "R2REF-025")},
    "R2REF-031": "Virginia",
    "R2REF-060": "Maine; New Hampshire; New York; Vermont",
}

REPLACEMENTS = {
    "R2REF-007": {
        "source_url": "https://www.inclusiveoutdoors.org/",
        "summary": "Provides an inclusive outdoor recreation resource library developed with Together Outdoors and the Recreate Responsibly Coalition.",
        "support_type": "Resource hub",
    },    "R2REF-003": {
        "source_url": "https://americanindigenoustourism.org/destinations-international-toolkit/",
        "summary": "Helps destination organizations build respectful tourism partnerships that are led and governed by Indigenous communities.",
        "support_type": "Toolkit",
    },
    "R2REF-017": {
        "source_url": "https://cpw.state.co.us/conservation-plans",
        "summary": "Provides Colorado's current statewide outdoor recreation plan and supporting conservation planning resources.",
        "support_type": "Plan and data",
    },
    "R2REF-018": {
        "source_url": "https://www.conservationfund.org/our-impact/projects/",
        "summary": "Offers searchable conservation project examples, including work that protects outdoor access and supports rural economies.",
        "support_type": "Case-study collection",
    },
    "R2REF-019": {
        "source_url": "https://www.tompkinscountyny.gov/All-Departments/Planning-and-Sustainability/Tourism/Tourism-Plans",
        "summary": "Provides Tompkins County's adopted outdoor recreation tourism plan and related tourism planning resources.",
        "support_type": "Plan",
    },
    "R2REF-027": {
        "source_url": "https://www.tpl.org/resource/field-guide-creative-placemaking-and-parks",
        "summary": "Offers a field guide and eleven case studies showing how creative placemaking can strengthen parks and communities.",
        "support_type": "Guide and case studies",
    },    "R2REF-038": {
        "source_url": "https://www.democracycollaborative.org/community-wealth-building",
        "summary": "Explains community wealth building and provides an action guide, practical tools, and community examples.",
        "support_type": "Guide and case studies",
    },
    "R2REF-042": {
        "source_url": "https://www.eda.gov/resources/tools",
        "summary": "Collects federal tools for economic development planning, data analysis, project development, and local capacity building.",
        "support_type": "Resource hub",
    },    "R2REF-074": {
        "source_url": "https://digitalcommons.usu.edu/extension_curall/1897/",
        "summary": "Reviews state outdoor recreation offices and offers lessons for governments, nonprofits, and recreation partners.",
        "support_type": "Report",
    },
    "R2REF-076": {
        "source_url": "https://research.fs.usda.gov/treesearch/53247",
        "summary": "Summarizes participation trends and the economic activity supported by outdoor recreation on federal lands.",
        "support_type": "Research report",
    },
    "R2REF-077": {
        "source_url": "https://www.rd.usda.gov/sites/default/files/usdard_recreational_economy508.pdf",
        "summary": "Explains USDA programs and practical steps for rural communities building recreation economies through planning, business support, infrastructure, and conservation.",
        "support_type": "Guide",
    },
    "R2REF-080": {
        "source_url": "https://www.americantrails.org/resource-library",
        "summary": "Provides a searchable library for trail planning, design, conservation, funding, management, and maintenance.",
        "support_type": "Resource library",
    },
    "R2REF-081": {
        "source_url": "https://www.cdc.gov/physical-activity/php/community-design-visual-guide/index.html",
        "summary": "Shows how communities can connect activity-friendly routes with everyday destinations such as parks, schools, shops, and transit.",
        "support_type": "Visual guide",
    },    "R2REF-091": {
        "source_url": "https://creativeplacemaking.t4america.org/our-eight-approaches/",
        "summary": "Shows eight ways to use arts and culture in transportation planning, with local examples and supporting resources.",
        "support_type": "Guide and case studies",
    },
}

NEW_RESOURCES = [
    {
        "item_id": "RERC-RES-NEW-2026-001",
        "item_type": "Resource",
        "title": "River Town Review Toolkit",
        "organization": "National Park Service Rivers, Trails, and Conservation Assistance Program",
        "status": "Available",
        "last_checked": CHECKED_DATE,
        "geography": "Nationwide and U.S. territories",
        "eligible_users": "Local governments; Tribal governments; nonprofits; community groups; planners; tourism and business partners",
        "project_stage": "Planning",
        "topic_tags": "river; trails; outdoor recreation; tourism; downtown; planning; community engagement; accessibility",
        "support_type": "Toolkit",
        "amount_or_cost": "Free",
        "match_or_cost": "None",
        "deadline_or_availability": "Available online",
        "summary": "Guides communities through a local review of river access, trails, visitor services, downtown connections, and recreation businesses.",
        "why_it_matters": "Includes checklists, examples, and templates for making a river-town action plan.",
        "source_url": "https://www.nps.gov/orgs/rtca/river-town-review-toolkit.htm",
    },
    {
        "item_id": "RERC-RES-NEW-2026-002",
        "item_type": "Resource",
        "title": "Local Foods, Local Places Toolkit",
        "organization": "U.S. Environmental Protection Agency",
        "status": "Available",
        "last_checked": CHECKED_DATE,
        "geography": "Nationwide and U.S. territories",
        "eligible_users": "Local governments; Tribal governments; nonprofits; community groups; food-system partners; planners",
        "project_stage": "Planning",
        "topic_tags": "downtown; main street; food; economic development; planning; community engagement; action plan",
        "support_type": "Toolkit",
        "amount_or_cost": "Free",
        "match_or_cost": "None",
        "deadline_or_availability": "Available online",
        "summary": "Gives step-by-step workshop instructions and templates for local food and downtown projects.",
        "why_it_matters": "Communities can use its workshop steps and action table to plan recreation projects.",
        "source_url": "https://www.epa.gov/smartgrowth/local-foods-local-places-toolkit",
    },
    {
        "item_id": "RERC-RES-NEW-2026-003",
        "item_type": "Resource",
        "title": "Equitable Engagement Toolkit",
        "organization": "Oregon Department of Land Conservation and Development",
        "status": "Available",
        "last_checked": CHECKED_DATE,
        "geography": "Nationwide and U.S. territories",
        "eligible_users": "Local governments; Tribal governments; nonprofits; community groups; planners; consultants",
        "project_stage": "Planning",
        "topic_tags": "community engagement; equity; planning; data; mapping; local capacity",
        "support_type": "Toolkit and mapping tools",
        "amount_or_cost": "Free",
        "match_or_cost": "None",
        "deadline_or_availability": "Available online",
        "summary": "Provides worksheets, checklists, training, and mapping tools for reaching people who are often left out of planning.",
        "why_it_matters": "Any community can use these tools before it chooses projects or funding.",
        "source_url": "https://www.oregon.gov/lcd/About/Pages/Equitable-Engagement-Toolkit.aspx",
    },
    {
        "item_id": "RERC-RES-NEW-2026-004",
        "item_type": "Resource",
        "title": "2026 Oregon Recreational Trails Plan and Technical Toolkit",
        "organization": "Oregon Parks and Recreation Department",
        "status": "Available",
        "last_checked": CHECKED_DATE,
        "geography": "Oregon",
        "eligible_users": "Local governments; Tribal governments; state agencies; nonprofits; trail managers; planners",
        "project_stage": "Planning",
        "topic_tags": "trails; outdoor recreation; planning; funding; accessibility; stewardship; case studies",
        "support_type": "Plan and toolkit",
        "amount_or_cost": "Free",
        "match_or_cost": "None",
        "deadline_or_availability": "Available online",
        "summary": "Pairs Oregon's trail plan with guides, case studies, and public input.",
        "why_it_matters": "Shows how one state links trail goals, public input, funding, and next steps.",
        "source_url": "https://www.oregon.gov/oprd/prp/pages/pla-statewide-trails.aspx",
    },
]

SECTION_TOPICS = {
    "Community Engagement, Diversity, Equity, and Inclusion": "community engagement; equity; inclusion; outdoor access; planning; local capacity",
    "Community and State-Specific Strategies and Examples": "outdoor recreation; planning; case studies; economic development; local capacity",
    "Land Conservation, Stewardship, Parks, and Health": "parks; trails; health; conservation; stewardship; community engagement",
    "Main Street Revitalization and Economic Development": "downtown; main street; placemaking; economic development; business; planning",
    "Outdoor Recreation": "outdoor recreation; tourism; recreation economy; workforce; economic development; data",
    "Trails and Transportation": "trails; transportation; bike; pedestrian; mobility; planning; funding",
}

TOPIC_OVERRIDES = {
    "R2REF-017": "outdoor recreation; conservation; parks; trails; planning; public lands",
    "R2REF-018": "conservation; land; public access; outdoor recreation; case studies",
    "R2REF-019": "outdoor recreation; tourism; planning; trails; economic development",
    "R2REF-027": "parks; placemaking; arts; community engagement; conservation; case studies",
    "R2REF-056": "land use; conservation; outdoor recreation; economic development; planning",
    "R2REF-059": "river access; water access; paddling; outdoor recreation; planning; accessibility",
    "R2REF-078": "national forests; conservation; outdoor recreation; economic data",
    "R2REF-079": "gateway communities; public lands; conservation; planning; outdoor recreation",
    "R2REF-077": "outdoor recreation; recreation economy; rural development; infrastructure; business; conservation; planning",
    "R2REF-080": "trails; planning; design; conservation; funding; management; maintenance",
    "R2REF-081": "transportation; bike; pedestrian; transit; parks; health; safe access",
}
KIND_SUPPORT = {
    "Organization or resource hub": "Resource hub",
    "Toolkit or guide": "Toolkit or guide",
    "Data and analysis tool": "Data and analysis tool",
    "Case study collection": "Case-study collection",
    "Report or publication": "Report",
    "Webinar or video": "Webinar or video",
}


def fix_mojibake(value: str) -> str:
    text = str(value or "")
    if any(marker in text for marker in ("â€", "â€™", "â€œ", "â€“", "Ã")):
        try:
            text = text.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return " ".join(text.split())


def normalized_url(value: str) -> str:
    parts = urlsplit(value.strip())
    path = parts.path.rstrip("/") or "/"
    host = parts.netloc.lower()
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"} and path == "/watch":
        video_id = next((part.split("=", 1)[1] for part in parts.query.split("&") if part.startswith("v=")), "")
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else "https://www.youtube.com/watch"
    if host == "youtu.be":
        return f"https://www.youtube.com/watch?v={path.lstrip('/')}"
    return urlunsplit((parts.scheme.lower(), host, path, "", ""))


def load_catalog(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    prefix = "window.RERC_CATALOG = "
    if not text.startswith(prefix):
        raise ValueError(f"{path} does not contain the expected catalog assignment")
    payload = text[len(prefix) :].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def save_catalog(path: Path, catalog: dict) -> None:
    content = "window.RERC_CATALOG = " + json.dumps(
        catalog, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    path.write_text(content, encoding="utf-8", newline="\n")


def first_summary_sentence(description: str, title: str) -> str:
    text = fix_mojibake(description)
    for prefix in (title + ".", title):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix) :].lstrip(" .")
            break
    if not text:
        return f"Provides public information and examples related to {title.lower()}."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:2]).strip()
    if len(summary) > 420:
        summary = summary[:417].rsplit(" ", 1)[0] + "..."
    return summary


def organization_for(record: dict) -> str:
    ref_id = record["reference_id"]
    if ref_id in ORGANIZATION_OVERRIDES:
        return ORGANIZATION_OVERRIDES[ref_id]
    title = TITLE_OVERRIDES.get(ref_id, fix_mojibake(record["title"]))
    return title if len(title) <= 90 else "Public resource provider"


def record_to_item(record: dict) -> dict:
    ref_id = record["reference_id"]
    title = TITLE_OVERRIDES.get(ref_id, fix_mojibake(record["title"]))
    support_type = KIND_SUPPORT.get(record["resource_kind"], "Public resource")
    summary = SUMMARY_OVERRIDES.get(ref_id, first_summary_sentence(record["description"], title))
    source_url = record.get("final_url") or record["source_url"]
    if ref_id in REPLACEMENTS:
        override = REPLACEMENTS[ref_id]
        source_url = override["source_url"]
        summary = override["summary"]
        support_type = override["support_type"]
    geography = GEOGRAPHY_OVERRIDES.get(ref_id, "Nationwide and U.S. territories")
    return {
        "item_id": f"RERC-RES-R2-{int(ref_id.rsplit('-', 1)[1]):03d}",
        "item_type": "Resource",
        "title": title,
        "organization": organization_for(record),
        "status": "Available",
        "last_checked": CHECKED_DATE,
        "geography": geography,
        "eligible_users": "Local governments; Tribal governments and organizations; nonprofits; community groups; businesses; planners; economic development partners",
        "project_stage": "Planning",
        "topic_tags": TOPIC_OVERRIDES.get(ref_id, SECTION_TOPICS.get(record["section"], "outdoor recreation; planning; local capacity")),
        "support_type": support_type,
        "amount_or_cost": "Free public resource",
        "match_or_cost": "None",
        "deadline_or_availability": "Available online",
        "summary": summary,
        "source_url": source_url,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    audit = json.loads(args.audit.read_text(encoding="utf-8-sig"))
    catalog = load_catalog(args.catalog)

    records = audit["records"]
    selected = []
    held = []
    for record in records:
        ref_id = record["reference_id"]
        if record.get("already_in_public_catalog"):
            held.append({"reference_id": ref_id, "reason": "Already represented"})
            continue
        active = record["link_status"] in {"Active", "Active - redirected"}
        if active or ref_id in REPLACEMENTS:
            selected.append(record_to_item(record))
        else:
            held.append({"reference_id": ref_id, "reason": record["link_status"]})

    selected.extend(NEW_RESOURCES)
    selected_ids = {item["item_id"] for item in selected}
    existing_items = [
        item
        for item in catalog["items"]
        if item["item_id"] not in selected_ids
    ]
    existing_urls = {normalized_url(item["source_url"]) for item in existing_items}
    additions = []
    skipped_urls = []
    for item in selected:
        url_key = normalized_url(item["source_url"])
        if url_key in existing_urls:
            skipped_urls.append({"item_id": item["item_id"], "source_url": item["source_url"]})
            continue
        existing_urls.add(url_key)
        additions.append(item)

    catalog["items"] = existing_items + additions
    funding_count = sum(item["item_type"] == "Funding" for item in catalog["items"])
    resource_count = sum(item["item_type"] == "Resource" for item in catalog["items"])
    catalog["updated"] = CHECKED_DATE
    catalog["counts"] = {
        "combined": funding_count + resource_count,
        "funding": funding_count,
        "resources": resource_count,
    }
    save_catalog(args.catalog, catalog)

    report = {
        "status": "PASS",
        "checked": CHECKED_DATE,
        "source_references": len(records),
        "imported_round2_or_replacements": sum(
            item["item_id"].startswith("RERC-RES-R2-") for item in additions
        ),
        "imported_new_resources": sum(
            item["item_id"].startswith("RERC-RES-NEW-2026-") for item in additions
        ),
        "held_records": held,
        "skipped_duplicate_urls": skipped_urls,
        "catalog_counts": catalog["counts"],
        "resource_ids": [item["item_id"] for item in additions],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
