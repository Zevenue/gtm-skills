"""
TheirStack API client for job search.

Usage:
    python utils/theirstack.py search --domains "stripe.com,notion.so" --days 30
    python utils/theirstack.py search --names "Stripe,Notion" --days 30
    python utils/theirstack.py search --domains "stripe.com" --title "SDR,BDR" --days 14
    python utils/theirstack.py search --domains "stripe.com,notion.so" --title "SDR" --per-company 1
    python utils/theirstack.py search --domains "stripe.com" --days 30 --format json
    python utils/theirstack.py credits
"""

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL = "https://api.theirstack.com"


def get_api_key():
    key = os.environ.get("THEIRSTACK_API_KEY")
    if not key:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.environ.get("THEIRSTACK_API_KEY")
    if not key:
        print("Error: THEIRSTACK_API_KEY not found in environment or .env file.", file=sys.stderr)
        print("Get your key at: https://app.theirstack.com/settings/api", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(method, endpoint, body=None):
    key = get_api_key()
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"API error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)


def search_jobs(
    domains=None,
    names=None,
    days=30,
    job_titles=None,
    country_codes=None,
    limit=25,
    page=0,
    min_employees=None,
    max_employees=None,
    funding_stages=None,
    remote=None,
    include_description=False,
):
    body = {
        "posted_at_max_age_days": days,
        "limit": limit,
        "page": page,
        "order_by": [{"field": "date_posted", "desc": True}],
    }

    if domains:
        body["company_domain_or"] = domains
    if names:
        body["company_name_partial_match_or"] = names
    if job_titles:
        body["job_title_or"] = job_titles
    if country_codes:
        body["job_country_code_or"] = country_codes
    if min_employees is not None:
        body["min_employee_count"] = min_employees
    if max_employees is not None:
        body["max_employee_count"] = max_employees
    if funding_stages:
        body["funding_stage_or"] = funding_stages
    if remote is not None:
        body["remote"] = remote

    body["include_total_results"] = True

    result = api_request("POST", "/v1/jobs/search", body)
    return result


def check_credits():
    return api_request("GET", "/v0/billing/credit-balance")


def apply_per_company_limit(result, per_company):
    """Trim results to at most `per_company` jobs per company domain."""
    if per_company is None:
        return result
    jobs = result.get("data", [])
    counts = {}
    filtered = []
    for job in jobs:
        domain = job.get("company_domain", "unknown")
        counts[domain] = counts.get(domain, 0) + 1
        if counts[domain] <= per_company:
            filtered.append(job)
    result = dict(result)
    result["data"] = filtered
    return result


def format_jobs_markdown(result, include_description=False):
    jobs = result.get("data", [])
    total = result.get("total_results", len(jobs))
    lines = []
    lines.append(f"## Job Search Results ({total} total, showing {len(jobs)})\n")

    if not jobs:
        lines.append("No jobs found matching the criteria.\n")
        return "\n".join(lines)

    # Group by company
    by_company = {}
    for job in jobs:
        domain = job.get("company_domain", "unknown")
        company_name = job.get("company_object", {}).get("name", domain) if job.get("company_object") else domain
        key = f"{company_name} ({domain})"
        if key not in by_company:
            by_company[key] = []
        by_company[key].append(job)

    for company_key, company_jobs in by_company.items():
        lines.append(f"### {company_key} - {len(company_jobs)} job(s)\n")

        # Company info from first job
        co = company_jobs[0].get("company_object") or {}
        info_parts = []
        if co.get("employee_count"):
            info_parts.append(f"{co['employee_count']} employees")
        if co.get("funding_stage"):
            info_parts.append(f"Funding: {co['funding_stage']}")
        if co.get("total_funding_usd"):
            info_parts.append(f"Raised: ${co['total_funding_usd']:,.0f}")
        if co.get("industry"):
            info_parts.append(f"Industry: {co['industry']}")
        if co.get("city") and co.get("country"):
            info_parts.append(f"HQ: {co['city']}, {co['country']}")
        if info_parts:
            lines.append(f"*{' | '.join(info_parts)}*\n")

        for job in company_jobs:
            title = job.get("job_title", "Unknown")
            url = job.get("url") or job.get("final_url") or ""
            date = job.get("date_posted", "")
            location = job.get("location", "")
            remote_flag = " (Remote)" if job.get("remote") else ""
            salary = job.get("salary_string", "")

            line = f"- **{title}**"
            if location:
                line += f" - {location}{remote_flag}"
            if date:
                line += f" | Posted: {date}"
            if salary:
                line += f" | {salary}"
            if url:
                line += f" | [Link]({url})"
            lines.append(line)

            if include_description and job.get("description"):
                desc = job["description"][:300].replace("\n", " ").strip()
                lines.append(f"  > {desc}...")

        lines.append("")

    return "\n".join(lines)


def format_jobs_json(result):
    return json.dumps(result, indent=2)


def main():
    parser = argparse.ArgumentParser(description="TheirStack job search CLI")
    sub = parser.add_subparsers(dest="command")

    # search command
    sp = sub.add_parser("search", help="Search for job postings")
    sp.add_argument("--domains", help="Comma-separated company domains (e.g., stripe.com,notion.so)")
    sp.add_argument("--names", help="Comma-separated company names (partial match)")
    sp.add_argument("--days", type=int, default=30, help="Max age of job posting in days (default: 30)")
    sp.add_argument("--title", help="Comma-separated job title keywords (e.g., SDR,BDR,Sales)")
    sp.add_argument("--country", help="Comma-separated ISO2 country codes (e.g., US,CA)")
    sp.add_argument("--limit", type=int, default=25, help="Max results per page (default: 25)")
    sp.add_argument("--page", type=int, default=0, help="Page number (0-indexed)")
    sp.add_argument("--min-employees", type=int, help="Min employee count filter")
    sp.add_argument("--max-employees", type=int, help="Max employee count filter")
    sp.add_argument("--funding", help="Comma-separated funding stages (e.g., seed,series_a,series_b)")
    sp.add_argument("--remote", action="store_true", default=None, help="Remote jobs only")
    sp.add_argument("--per-company", type=int, default=None, help="Max jobs to return per company (e.g., 1 for one job per company)")
    sp.add_argument("--description", action="store_true", help="Include job description snippets")
    sp.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")

    # credits command
    sub.add_parser("credits", help="Check API credit balance")

    args = parser.parse_args()

    if args.command == "credits":
        balance = check_credits()
        print(json.dumps(balance, indent=2))

    elif args.command == "search":
        if not args.domains and not args.names:
            print("Error: provide --domains or --names", file=sys.stderr)
            sys.exit(1)

        domains = [d.strip() for d in args.domains.split(",")] if args.domains else None
        names = [n.strip() for n in args.names.split(",")] if args.names else None
        titles = [t.strip() for t in args.title.split(",")] if args.title else None
        countries = [c.strip() for c in args.country.split(",")] if args.country else None
        funding = [f.strip() for f in args.funding.split(",")] if args.funding else None

        result = search_jobs(
            domains=domains,
            names=names,
            days=args.days,
            job_titles=titles,
            country_codes=countries,
            limit=args.limit,
            page=args.page,
            min_employees=args.min_employees,
            max_employees=args.max_employees,
            funding_stages=funding,
            remote=True if args.remote else None,
            include_description=args.description,
        )

        if args.per_company is not None:
            result = apply_per_company_limit(result, args.per_company)

        if args.format == "json":
            print(format_jobs_json(result))
        else:
            print(format_jobs_markdown(result, include_description=args.description))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
