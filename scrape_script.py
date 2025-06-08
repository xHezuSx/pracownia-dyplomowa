from bs4 import BeautifulSoup
import requests
import pandas as pd
import os
from datetime import datetime
from tqdm import tqdm
import re
from summary import summarize_document_with_kmeans_clustering
from database_connection import (
    wstaw_firme,
    wstaw_dane,
    pobierz_klucz_firmy,
    wstaw_historie,
)

"""
Specify `REPORT_PATH` to save all downloaded reports anywhere you want
"""
REPORTS_PATH = "./REPORTS/"

URL = "https://www.gpw.pl/ajaxindex.php"


def extract_rate_changes(text) -> str:
    text = text.replace("Zmiana ", "")
    text = text.replace(",", ".")
    return text.replace("%", "")


def split_header(header) -> list:
    """
    splits for example `19-09-2024 15:41:53 | Bieżący | ESPI | 22/2024` into 3 main parts to
    -date
    -type report
    -category report

    function returns list of 3 elements. 0th element is data, 1st element is type reports, 2nd is category report
    """
    header = header.split("|")[
        :-1
    ]  # I do not know what is the last parameter, so I delete it
    header = [el.strip() for el in header]
    if len(header) == 2:
        header.insert(2, "unknown")
    return header


def download_file(url, path):
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
    file_title = re.sub(r"\s+", " ", file_title)
    return f"{company_name} report {report_id} file {file_id} {file_title}"


def get_attachments(url: str, filetype: list):
    if len(filetype) == 0:
        return []

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


def get_summaries(files: list, company: str) -> str:
    text = ""
    for f in files:
        path = f"./REPORTS/{company}/{f}"
        text += f"\n## {f} ##\n"
        if f.endswith(".pdf") and os.path.exists(path):
            text += summarize_document_with_kmeans_clustering(path)
    return text


def scrape(
    company: str,
    limit: int,
    date: str,
    report_type: list,
    report_category: list,
    download_csv: bool,
    download_file_types: list,
):
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

    if date != "":
        try:
            datetime.strptime(date, "%d-%m-%Y")
        except Exception as e:
            return (
                "Wrong date format",
                pd.DataFrame(
                    columns=[
                        "date",
                        "title",
                        "report type",
                        "report category",
                        "exchange rate",
                        "rate change",
                        "link",
                    ]
                ),
                [],
            )

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

    r = requests.post(URL, data=payload)
    soup = BeautifulSoup(r.content, "html.parser")

    os.makedirs(REPORTS_PATH, exist_ok=True)

    links = []
    titles = []
    dates = []
    type_reports = []
    category_reports = []
    exchange_rates = []
    rate_changes = []

    report_list = soup.findAll("li")

    wstaw_historie(
        company_name=company,
        report_amount=limit,
        download_type=" ".join(download_file_types),
        report_date=date,
        report_type=" ".join(report_type),
        report_category=" ".join(report_category),
    )

    # scraping main GPW page
    for report in report_list:
        links.append("https://www.gpw.pl/" + report.find("a")["href"])
        report_header = split_header(report.find("span", attrs={"class": "date"}).text)

        if (
            report.find("p").text.strip() == ""
        ):  # instead of adding empty title we pass information about type report
            titles.append("UNTITLED " + report_header[1] + " REPORT")
        else:
            titles.append(report.find("p").text.strip())
        dates.append(report_header[0])
        type_reports.append(report_header[1])
        category_reports.append(report_header[2])
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

    try:
        wstaw_firme(company.lower())
    except Exception as e:
        print("Znaleziono duplikat firmy")

    klucz_obcy = pobierz_klucz_firmy(company.lower())
    for d, t, rt, rc, er, rch, l in zip(
        dates,
        titles,
        type_reports,
        category_reports,
        exchange_rates,
        rate_changes,
        links,
    ):
        wstaw_dane(d, t, rt, rc, er, rch, l, klucz_obcy)

    output_info = ""
    if_downloaded = False

    if not os.path.exists("./REPORTS"):
        os.makedirs("./REPORTS")
    if not os.path.exists(f"./REPORTS/{company}") and (
        len(download_file_types) != 0 or download_csv
    ):
        if_downloaded = True
        os.makedirs(f"./REPORTS/{company}")

    downloaded_file_names = []

    # download attachments from every report site
    downloaded_files = 0
    if len(download_file_types) != 0:
        for i, link in enumerate(links):
            attachments, file_titles = get_attachments(link, download_file_types)
            for j, (attachment, name) in enumerate(zip(attachments, file_titles)):
                filename = get_file_name(
                    report_id=i + 1,
                    file_id=j + 1,
                    company_name=company,
                    file_title=name,
                )
                downloaded_file_names.append(filename)
                download_file(attachment, f"./REPORTS/{company}/{filename}")
                downloaded_files += 1

    current_path = os.getcwd()

    if len(download_file_types) != 0:
        output_info += f"downloaded {downloaded_files} files "

    if download_csv:
        report_df.to_csv(f"./REPORTS/{company}/{company}({limit}) report.csv")
        # os.startfile(f"{current_path}\\REPORTS\\{company}\\{company}({limit}) report.csv")
        if_downloaded = True
        output_info += f"| CSV file saved"

    summaries = "*No PDF to summary*"
    if "PDF" in download_file_types:
        summaries = get_summaries(downloaded_file_names, company)

    if if_downloaded:
        return (
            f"SUCCESS! {output_info}\n files saved in:\n\t\t {current_path}\\REPORTS\\{company}",
            report_df,
            summaries,
        )

    return f"SUCCESS! {output_info}", report_df, summaries
