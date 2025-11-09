from bs4 import BeautifulSoup
import requests
import pandas as pd
import os
from datetime import datetime
from tqdm import tqdm
import re
from summary import summarize_document_with_kmeans_clustering
from database_connection import (
    insert_company,
    get_company_id,
    insert_report,
    insert_search_history,
    insert_summary_report,
    insert_downloaded_file,
    calculate_md5,
    file_exists_by_md5,
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
    # Extract only date part (dd-MM-YYYY) from datetime string
    if header and " " in header[0]:
        header[0] = header[0].split()[0]
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


def get_summaries(files: list, company: str, model_name: str = "llama3.2:latest") -> str:
    """
    Generate summaries for all PDF and HTML files.
    Optimized: processes files in parallel-ready batches to reduce wait time.
    """
    text = ""
    # Filter for both PDF and HTML files
    document_files = [f for f in files if f.endswith((".pdf", ".html", ".htm"))]
    
    if not document_files:
        return "*No documents to summarize*"
    
    print(f"Processing {len(document_files)} document files for {company}...")
    
    for i, f in enumerate(document_files, 1):
        path = f"./REPORTS/{company}/{f}"
        text += f"\n## File {i}/{len(document_files)}: {f} ##\n"
        if os.path.exists(path):
            print(f"  Summarizing {i}/{len(document_files)}: {f}...")
            try:
                summary = summarize_document_with_kmeans_clustering(path, model_name)
                text += summary + "\n"
            except Exception as e:
                text += f"Error processing {f}: {str(e)}\n"
        else:
            text += f"File not found: {path}\n"
    
    return text


def generate_summary_report(
    job_name: str,
    company: str,
    date: str,
    report_df: pd.DataFrame,
    summaries: str,
    model_name: str,
    downloaded_files_count: int
) -> str:
    """
    Generuje zbiorczy raport w formacie Markdown i zapisuje do pliku.
    
    Args:
        company: Nazwa firmy
        date: Zakres dat lub pusta string
        report_df: DataFrame z raportami
        summaries: Tekstowe podsumowania dokumentów
        model_name: Nazwa użytego modelu AI
        downloaded_files_count: Liczba pobranych plików
    
    Returns:
        Ścieżka do wygenerowanego pliku
    """
    # Utwórz katalog na zbiorcze raporty
    summary_dir = "./SUMMARY_REPORTS"
    os.makedirs(summary_dir, exist_ok=True)
    
    # Nazwa pliku z timestampem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company}_{timestamp}_summary.md"
    filepath = os.path.join(summary_dir, filename)
    
    # Parsuj zakres dat jeśli jest
    date_from_str = "N/A"
    date_to_str = "N/A"
    if date and " - " in date:
        parts = date.split(" - ")
        date_from_str = parts[0].strip()
        date_to_str = parts[1].strip()
    elif date:
        date_from_str = date_to_str = date
    
    # Generuj treść raportu w Markdown
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Zbiorczy Raport GPW - {company}\n\n")
        f.write(f"**Wygenerowano:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")
        
        # Metadata
        f.write(f"## 📊 Informacje o raporcie\n\n")
        f.write(f"- **Firma:** {company}\n")
        f.write(f"- **Okres:** {date_from_str} - {date_to_str}\n")
        f.write(f"- **Liczba raportów:** {len(report_df)}\n")
        f.write(f"- **Pobranych plików:** {downloaded_files_count}\n")
        f.write(f"- **Model AI:** {model_name}\n\n")
        f.write(f"---\n\n")
        
        # Tabela raportów
        f.write(f"## 📋 Lista raportów\n\n")
        if not report_df.empty:
            f.write(report_df.to_markdown(index=False))
            f.write("\n\n")
        else:
            f.write("*Brak raportów*\n\n")
        
        f.write(f"---\n\n")
        
        # Podsumowania AI
        f.write(f"## 🤖 Podsumowania dokumentów (AI)\n\n")
        f.write(summaries)
        f.write("\n\n")
        
        f.write(f"---\n\n")
        f.write(f"*Raport wygenerowany automatycznie przez GPW Scraper*\n")
    
    print(f"\n✅ Zbiorczy raport zapisany: {filepath}")
    
    # Oblicz rozmiar pliku
    file_size = os.path.getsize(filepath)
    
    # Zapisz metadata do bazy danych (v2.0)
    try:
        insert_summary_report(
            job_name=job_name,
            company=company,
            date_from=date_from_str if date_from_str != "N/A" else None,
            date_to=date_to_str if date_to_str != "N/A" else None,
            report_count=len(report_df),
            document_count=len(summaries),
            file_path=filepath,
            file_format='markdown',
            file_size=file_size,
            model_used=model_name,
            summary_preview=summaries[0][:200] if summaries else None,
            tags=[company.lower(), job_name.replace("_", "-")]
        )
        print(f"✅ Metadata zapisane do bazy danych")
    except Exception as e:
        print(f"⚠️  Błąd zapisu do bazy: {e}")
    
    return filepath


def scrape(
    company: str,
    limit: int,
    date: str,
    report_type: list,
    report_category: list,
    download_csv: bool,
    download_file_types: list,
    model_name: str = "llama3.2:latest",
    job_name: str = "manual",  # Nowy parametr dla identyfikacji zadania
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
        # Sprawdź czy to zakres dat (format: "dd-mm-yyyy - dd-mm-yyyy")
        if " - " in date:
            try:
                date_parts = date.split(" - ")
                datetime.strptime(date_parts[0].strip(), "%d-%m-%Y")
                datetime.strptime(date_parts[1].strip(), "%d-%m-%Y")
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
                    None,  # summary_report_path
                )
        else:
            # Pojedyncza data
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
                    None,  # summary_report_path
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

    response = requests.post(URL, data=payload)
    try:
        response.raise_for_status()
    except Exception as e:
        return (
            f"Request to GPW failed: {e}",
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
            None,  # summary_report_path
        )

    soup = BeautifulSoup(response.text, "html.parser")

    os.makedirs(REPORTS_PATH, exist_ok=True)

    links = []
    titles = []
    dates = []
    type_reports = []
    category_reports = []
    exchange_rates = []
    rate_changes = []

    report_list = soup.findAll("li")

    insert_search_history(
        company_name=company,
        report_amount=limit,
        download_type=" ".join(download_file_types),
        report_date=date,
        report_type=" ".join(report_type) if report_type else None,
        report_category=" ".join(report_category) if report_category else None,
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

    # Insert company and get ID (v2.0 database)
    company_id = insert_company(company.lower())
    if not company_id:
        company_id = get_company_id(company.lower())
    
    # Insert all reports and store their IDs
    report_ids = []
    for d, t, rt, rc, er, rch, l in zip(
        dates,
        titles,
        type_reports,
        category_reports,
        exchange_rates,
        rate_changes,
        links,
    ):
        report_id = insert_report(
            company_id=company_id,
            date=d,
            title=t,
            report_type=rt,
            report_category=rc,
            exchange_rate=er,
            rate_change=rch,
            link=l
        )
        report_ids.append(report_id)

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
                file_path = f"./REPORTS/{company}/{filename}"
                
                # Download file
                downloaded_file_names.append(filename)
                download_file(attachment, file_path)
                downloaded_files += 1
                
                # Calculate MD5 and register in database (v2.0)
                try:
                    md5_hash = calculate_md5(file_path)
                    if md5_hash and not file_exists_by_md5(md5_hash):
                        file_type = filename.split('.')[-1].lower()
                        file_size = os.path.getsize(file_path)
                        
                        # Get corresponding report_id (if available)
                        report_id = report_ids[i] if i < len(report_ids) else None
                        
                        insert_downloaded_file(
                            company=company.lower(),
                            report_id=report_id,
                            file_name=filename,
                            file_path=file_path,
                            file_type=file_type,
                            file_size=file_size,
                            md5_hash=md5_hash,
                            is_summarized=False
                        )
                        print(f"✓ Zarejestrowano plik w bazie: {filename}")
                    elif md5_hash:
                        print(f"⚠ Plik już istnieje (MD5): {filename}")
                except Exception as e:
                    print(f"⚠ Błąd rejestracji pliku {filename}: {e}")

    current_path = os.getcwd()

    if len(download_file_types) != 0:
        output_info += f"downloaded {downloaded_files} files "

    if download_csv:
        report_df.to_csv(f"./REPORTS/{company}/{company}({limit}) report.csv")
        # os.startfile(f"{current_path}\\REPORTS\\{company}\\{company}({limit}) report.csv")
        if_downloaded = True
        output_info += f"| CSV file saved"

    summaries = "*No documents to summarize*"
    # Summarize if PDF or HTML files were downloaded
    if "PDF" in download_file_types or "HTML" in download_file_types:
        summaries = get_summaries(downloaded_file_names, company, model_name)

    # Generuj zbiorczy raport w formacie Markdown
    summary_report_path = None
    if summaries != "*No documents to summarize*" and len(downloaded_file_names) > 0:
        summary_report_path = generate_summary_report(
            job_name=job_name,  # Przekaż job_name
            company=company,
            date=date,
            report_df=report_df,
            summaries=summaries,
            model_name=model_name,
            downloaded_files_count=len(downloaded_file_names)
        )

    if if_downloaded:
        return (
            f"SUCCESS! {output_info}\n files saved in:\n\t\t {current_path}\\REPORTS\\{company}",
            report_df,
            summaries,
            summary_report_path,  # Zwróć też ścieżkę do zbiorczego raportu
        )

    return f"SUCCESS! {output_info}", report_df, summaries, summary_report_path
