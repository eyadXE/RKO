import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from .config import (
    BASE_URL,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    SEARCH_PATH,
    USER_AGENT,
)

JOB_LINK_RE = re.compile(r"/jobs/p/[^\"?#]+", re.IGNORECASE)


def get_robot_parser() -> Optional[RobotFileParser]:
    robots_url = urljoin(BASE_URL, "/robots.txt")
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        return None
    return parser


def can_fetch(parser: Optional[RobotFileParser], url: str) -> bool:
    if parser is None:
        return False
    return parser.can_fetch(USER_AGENT, url)

    
def build_search_url(query: str, start: int) -> str:
    params = {"a": "hpb", "q": query, "start": start}
    return f"{BASE_URL}{SEARCH_PATH}?{urlencode(params)}"


def fetch_page(session: requests.Session, url: str) -> Optional[str]:
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return None

    if response.status_code in (403, 429):
        return None
    if response.status_code != 200:
        return None
    return response.text


def extract_job_links(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if JOB_LINK_RE.search(href):
            links.append(urljoin(BASE_URL, href))
    return sorted(set(links))


def _clean_html_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    if not isinstance(value, str):
        value = str(value)
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def _get_meta_content(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", property=prop)
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


def _extract_section_text(soup: BeautifulSoup, header_text: str) -> str:
    header = soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4")
        and tag.get_text(strip=True).lower() == header_text.lower()
    )
    if not header:
        return ""

    parent = header.parent
    if parent:
        for child in parent.find_all(recursive=False):
            if child == header or child.name in ("style", "script"):
                continue
            text = child.get_text(" ", strip=True)
            if text:
                return text

    next_div = header.find_next(
        lambda tag: tag.name == "div" and tag.get_text(strip=True)
    )
    if next_div:
        return next_div.get_text(" ", strip=True)
    return ""


def _extract_employment_types(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if not h1 or not h1.parent:
        return ""
    types: List[str] = []
    for anchor in h1.parent.find_all("a", href=True):
        text = anchor.get_text(strip=True)
        href = anchor["href"]
        if not text or "jobs" not in href.lower():
            continue
        if text.lower().startswith("apply"):
            continue
        if text not in types:
            types.append(text)
    return ", ".join(types)


def _extract_company_location(soup: BeautifulSoup) -> tuple[str, str]:
    company = ""
    location = ""
    for strong in soup.find_all("strong"):
        text = strong.get_text(" ", strip=True)
        if not text:
            continue
        if " - " in text and "," in text:
            company_part, location_part = text.split(" - ", 1)
            company = company_part.strip()
            location = location_part.strip()
            break
    if not location:
        strong = soup.find(
            "strong",
            string=lambda value: isinstance(value, str)
            and value.strip().startswith("-")
            and "," in value,
        )
        if strong:
            location = strong.get_text(" ", strip=True).lstrip("-").strip()
    return company, location


def _extract_skills(soup: BeautifulSoup) -> List[str]:
    header = soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4")
        and tag.get_text(strip=True).lower().startswith("skills")
    )
    if not header:
        return []
    parent = header.parent
    if parent:
        tags = [
            anchor.get_text(strip=True)
            for anchor in parent.find_all("a")
            if anchor.get_text(strip=True)
        ]
        if tags:
            return tags
        for child in parent.find_all(recursive=False):
            if child == header or child.name in ("style", "script"):
                continue
            text = child.get_text(" ", strip=True)
            if text:
                parts = [
                    part.strip()
                    for part in re.split(r"[,/|\u00b7]+", text)
                    if part.strip()
                ]
                return parts
    return []


def parse_job_posting(url: str, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    data: Optional[Dict[str, Any]] = None
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or script.get_text(strip=True)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    data = item
                    break
        elif isinstance(payload, dict) and payload.get("@type") == "JobPosting":
            data = payload
        if data:
            break

    title = ""
    company = ""
    location = ""
    employment_type = ""
    industry = ""
    description = ""
    requirements = ""
    date_posted = ""
    experience = ""
    skills: List[str] = []

    if data:
        title = _clean_html_text(data.get("title"))
        description = _clean_html_text(data.get("description"))
        employment_type = _clean_html_text(data.get("employmentType"))
        date_posted = _clean_html_text(data.get("datePosted"))
        experience = _clean_html_text(data.get("experienceRequirements"))

        industry_value = data.get("industry")
        if isinstance(industry_value, list):
            industry = ", ".join(_clean_html_text(item) for item in industry_value)
        else:
            industry = _clean_html_text(industry_value)

        org = data.get("hiringOrganization")
        if isinstance(org, dict):
            company = _clean_html_text(org.get("name"))
        else:
            company = _clean_html_text(org)

        job_loc = data.get("jobLocation")
        if isinstance(job_loc, list) and job_loc:
            job_loc = job_loc[0]
        if isinstance(job_loc, dict):
            address = job_loc.get("address", {})
            if isinstance(address, dict):
                parts = [
                    _clean_html_text(address.get("addressLocality")),
                    _clean_html_text(address.get("addressRegion")),
                    _clean_html_text(address.get("addressCountry")),
                ]
                location = ", ".join(part for part in parts if part)

        skills_value = data.get("skills")
        if isinstance(skills_value, list):
            skills = [_clean_html_text(item) for item in skills_value if item]
        elif isinstance(skills_value, str):
            skills = [
                item.strip()
                for item in re.split(r"[,/|\n]+", skills_value)
                if item.strip()
            ]

    if not title:
        heading = soup.find("h1")
        if heading:
            title = heading.get_text(strip=True)

    if not description:
        description = _extract_section_text(soup, "Job Description")

    requirements = _extract_section_text(soup, "Job Requirements")
    if not skills:
        skills = _extract_skills(soup)

    if not employment_type:
        employment_type = _extract_employment_types(soup)

    if not company or not location:
        html_company, html_location = _extract_company_location(soup)
        if not company:
            company = html_company
        if not location:
            location = html_location

    if not location:
        meta_location = ", ".join(
            part
            for part in (
                _get_meta_content(soup, "og:locality"),
                _get_meta_content(soup, "og:region"),
                _get_meta_content(soup, "og:country_name"),
            )
            if part
        )
        if meta_location:
            location = meta_location

    record = {
        "source": "wuzzuf",
        "url": url,
        "title": title,
        "company": company,
        "location": location,
        "employment_type": employment_type,
        "industry": industry,
        "experience_level": experience,
        "description": description,
        "requirements": requirements,
        "skills": skills,
        "posted_date": date_posted,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    return record


def _crawl_query(
    session: requests.Session,
    parser: RobotFileParser,
    query: str,
    max_records: int,
    max_pages: int,
    seen_links: set[str],
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    for page in range(max_pages):
        if len(results) >= max_records:
            return results

        search_url = build_search_url(query, start=page * 10)
        if not can_fetch(parser, search_url):
            print("robots.txt disallows search URL. Stopping query.")
            break

        html = fetch_page(session, search_url)
        if html is None:
            print("Search page blocked or unavailable. Stopping query.")
            break

        job_links = extract_job_links(html)
        if not job_links:
            print("No job links found on search page. Stopping query.")
            break

        for link in job_links:
            if link in seen_links:
                continue
            seen_links.add(link)

            if not can_fetch(parser, link):
                continue

            job_html = fetch_page(session, link)
            if job_html is None:
                print("Job page blocked or unavailable. Stopping query.")
                return results

            results.append(parse_job_posting(link, job_html))
            if len(results) >= max_records:
                return results

            time.sleep(REQUEST_DELAY)

        time.sleep(REQUEST_DELAY)

    return results


def crawl_jobs_multi(
    queries: List[str], max_records: int, max_pages: int
) -> List[Dict[str, Any]]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    parser = get_robot_parser()
    if parser is None:
        print("robots.txt unavailable. Skipping scrape.")
        return []

    results: List[Dict[str, Any]] = []
    seen_links: set[str] = set()

    for query in queries:
        if len(results) >= max_records:
            break
        results = _crawl_query(
            session, parser, query, max_records, max_pages, seen_links, results
        )

    return results


def crawl_jobs(query: str, max_records: int, max_pages: int) -> List[Dict[str, Any]]:
    return crawl_jobs_multi([query], max_records, max_pages)
