"""
Web Scraper Module
Handles GPW website scraping and data extraction.
"""

from bs4 import BeautifulSoup
import requests
import pandas as pd
import os
from datetime import datetime
from tqdm import tqdm
import re
from typing import List, Tuple, Optional


# Use absolute path based on script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_PATH = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "REPORTS")

URL = "https://www.gpw.pl/ajaxindex.php"


def extract_rate_changes(text: str) -> str:
    """Extract and clean rate change values from text."""
    text = text.replace("Zmiana ", "")
    text = text.replace(",", ".")
    return text.replace("%", "")


def split_header(header: str) -> list:
    """
    Split report header into [date, report_type, category].
    
    Example: "19-09-2024 15:41:53 | Bieżący | ESPI | 22/2024" 
    → ["19-09-2024", "Bieżący", "ESPI"]
    
    Args:
        header: Raw header string from GPW
    
    Returns:
        List with [date, report_type, category]
    """
    header = header.split("|")[:-1]  # Remove last unknown parameter
    header = [el.strip() for el in header]
    
    # Extract only date part (dd-MM-YYYY) from datetime string
    if header and " " in header[0]:
        header[0] = header[0].split()[0]
    
    if len(header) == 2:
        header.insert(2, "unknown")
    
    return header


def map_report_type_to_enum(report_type: str) -> Optional[str]:
    """
    Map Polish report type names to database enum values.
    
    Mapping:
    - "Bieżący" / "Current" → "current"
    - "Półroczny" / "Semi-annual" → "semi-annual"
    - "Kwartalny" / "Quarterly" → "quarterly"
    - "Śródroczny" / "Interim" → "interim"
    - "Roczny" / "Annual" → "annual"
    """
    if not report_type:
        return None
    
    report_type_lower = report_type.lower().strip()
    
    mapping = {
        "bieżący": "current",
        "current": "current",
        "rb": "current",
        "półroczny": "semi-annual",
        "semi-annual": "semi-annual",
        "p": "semi-annual",
        "kwartalny": "quarterly",
        "quarterly": "quarterly",
        "q": "quarterly",
        "śródroczny": "interim",
        "interim": "interim",
        "o": "interim",
        "roczny": "annual",
        "annual": "annual",
        "r": "annual",
    }
    
    return mapping.get(report_type_lower, None)


def map_report_category_to_enum(category: str) -> Optional[str]:
    """
    Map report category to database enum values.
    
    Mapping:
    - "ESPI" → "ESPI"
    - "EBI" → "EBI"
    """
    if not category:
        return None
    
    category_upper = category.upper().strip()
    
    # Only allow valid enum values
    if category_upper in ["ESPI", "EBI"]:
        return category_upper
    
    return None


def download_file(url: str, path: str):
    """Download file from URL with progress bar."""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))

    with open(path, "wb") as f:
        with tqdm(total=total_size, unit="iB", unit_scale=True) as pbar:
            for data in response.iter_content(chunk_size=1024):
                f.write(data)
                pbar.update(len(data))


def get_file_name(
    report_id: int, file_id: int, company_name: str, file_title: str
) -> str:
    """Generate standardized filename for downloaded report."""
    file_title = re.sub(r"\s+", " ", file_title)
    return f"{company_name} report {report_id} file {file_id} {file_title}"


def get_attachments(url: str, filetype: List[str]) -> Tuple[List[str], List[str]]:
    """
    Extract attachment URLs and names from report page.
    
    Args:
        url: Report page URL
        filetype: List of file types to download (e.g., ["PDF", "HTML"])
    
    Returns:
        Tuple of (download_urls, attachment_names)
    """
    if len(filetype) == 0:
        return [], []

    download_attachments_url = []
    attachment_names = []

    response = requests.get(url)
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    report_attachments = soup.find_all("tr", attrs={"class": "dane"})

    for attachment in report_attachments:
        file_name = attachment.find("a").text.strip()
        file_link = (
            "https://espiebi.pap.pl/espi/pl/reports/view/"
            + attachment.find("a")["href"]
        )
        if "pdf" in file_name[-4:] and "PDF" in filetype:
            download_attachments_url.append(file_link)
            attachment_names.append(file_name)
        elif "html" in file_name[-4:] and "HTML" in filetype:
            download_attachments_url.append(file_link)
            attachment_names.append(file_name)

    return download_attachments_url, attachment_names


def scrape_gpw_reports(
    company: str,
    limit: int,
    date: str,
    report_type: List[str],
    report_category: List[str]
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Scrape GPW reports for given company and filters.
    
    Args:
        company: Company name/ticker
        limit: Maximum number of reports to fetch
        date: Date or date range (DD-MM-YYYY or DD-MM-YYYY - DD-MM-YYYY)
        report_type: List of report types (current, quarterly, etc.)
        report_category: List of categories (ESPI, EBI)
    
    Returns:
        Tuple of (DataFrame with reports, error_message)
        If successful: (df, None)
        If failed: (None, error_message)
    """
    # Validate date format
    if date != "":
        if " - " in date:
            try:
                date_parts = date.split(" - ")
                datetime.strptime(date_parts[0].strip(), "%d-%m-%Y")
                datetime.strptime(date_parts[1].strip(), "%d-%m-%Y")
            except Exception as e:
                return None, "Wrong date format (expected: DD-MM-YYYY - DD-MM-YYYY)"
        else:
            try:
                datetime.strptime(date, "%d-%m-%Y")
            except Exception as e:
                return None, "Wrong date format (expected: DD-MM-YYYY)"

    # Map report types to GPW API format
    url_report_type = []
    if "current" in report_type:
        url_report_type.append("RB")
    if "semi-annual" in report_type:
        url_report_type.append("P")
    if "quarterly" in report_type:
        url_report_type.append("Q")
    if "interim" in report_type:
        url_report_type.append("O")
    if "annual" in report_type:
        url_report_type.append("R")

    # Prepare request payload
    payload = {
        "action": "GPWEspiReportUnion",
        "start": "ajaxSearch",
        "page": "komunikaty",
        "format": "html",
        "lang": "PL",
        "letter": "",
        "offset": "0",
        "limit": limit,
        "categoryRaports[]": report_category,
        "typeRaports[]": url_report_type,
        "search-xs": company,
        "searchText": company,
        "date": date,
    }

    # Make request
    try:
        response = requests.post(URL, data=payload)
        response.raise_for_status()
    except Exception as e:
        return None, f"Request to GPW failed: {e}"

    # Parse HTML
    soup = BeautifulSoup(response.text, "html.parser")
    
    links = []
    titles = []
    dates = []
    type_reports = []
    category_reports = []
    exchange_rates = []
    rate_changes = []

    report_list = soup.findAll("li")

    # Extract data from each report
    for report in report_list:
        links.append("https://www.gpw.pl/" + report.find("a")["href"])
        report_header = split_header(report.find("span", attrs={"class": "date"}).text)

        if report.find("p").text.strip() == "":
            titles.append("UNTITLED " + report_header[1] + " REPORT")
        else:
            titles.append(report.find("p").text.strip())
        
        dates.append(report_header[0])
        type_reports.append(report_header[1])
        category_reports.append(report_header[2])
        
        # Extract rate changes
        profit_change = report.find(
            "span", attrs={"class": "profit margin-left-30 pull-right"}
        )
        loss_change = report.find(
            "span", attrs={"class": "loss margin-left-30 pull-right"}
        )

        if profit_change is not None:
            exchange_rates.append(float(extract_rate_changes(profit_change.text)))
        else:
            exchange_rates.append(float("-" + extract_rate_changes(loss_change.text)))

        rate_change = (
            report.find("span", attrs={"class": "summary margin-left-30 pull-right"})
            .text.replace(",", ".")
            .replace("Kurs", "")
        )
        rate_changes.append(float(rate_change))

    # Create DataFrame
    report_df = pd.DataFrame(
        {
            "date": dates,
            "title": titles,
            "report type": type_reports,
            "report category": category_reports,
            "exchange rate": exchange_rates,
            "rate change": rate_changes,
            "link": links,
        }
    )

    return report_df, None


def download_report_files(
    report_df: pd.DataFrame,
    company: str,
    download_file_types: List[str]
) -> List[str]:
    """
    Download attachments for all reports in DataFrame.
    
    Args:
        report_df: DataFrame with report data
        company: Company name
        download_file_types: List of file types to download ["PDF", "HTML"]
    
    Returns:
        List of downloaded filenames
    """
    if len(download_file_types) == 0:
        return []

    # Ensure company directory exists
    company_dir = os.path.join(REPORTS_PATH, company)
    os.makedirs(company_dir, exist_ok=True)

    downloaded_file_names = []
    links = report_df['link'].tolist()

    # Download attachments from every report
    for i, link in enumerate(links):
        attachments, file_titles = get_attachments(link, download_file_types)
        for j, (attachment, name) in enumerate(zip(attachments, file_titles)):
            filename = get_file_name(
                report_id=i + 1,
                file_id=j + 1,
                company_name=company,
                file_title=name,
            )
            file_path = os.path.join(REPORTS_PATH, company, filename)
            
            # Download file
            downloaded_file_names.append(filename)
            download_file(attachment, file_path)

    return downloaded_file_names
