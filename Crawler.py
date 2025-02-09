import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import re


def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def get_pdf_link_and_title(paper_url):
    response = requests.get(paper_url)
    if response.status_code != 200:
        print(f"Failed to retrieve paper page: {paper_url}")
        return None, None

    soup = BeautifulSoup(response.text, 'html.parser')


    paper_button = soup.find('a', string='Paper')
    if paper_button and 'href' in paper_button.attrs:
        pdf_url = urljoin(paper_url, paper_button['href'])
        if pdf_url.endswith('.pdf'):
            # Extract the paper title
            title_tag = soup.find('h4')
            if title_tag:
                title = title_tag.text.strip()
                return pdf_url, title

    print(f"No PDF or title found on page: {paper_url}")
    return None, None


def download_pdf(pdf_url, title, year_dir):
    sanitized_title = sanitize_filename(title)
    pdf_name = f"{sanitized_title}.pdf"
    pdf_path = os.path.join(year_dir, pdf_name)

    if os.path.exists(pdf_path):
        print(f"Skipping {pdf_name}, already exists.")
        return

    try:
        pdf_response = requests.get(pdf_url, stream=True)
        if pdf_response.status_code == 200:
            with open(pdf_path, 'wb') as pdf_file:
                for chunk in pdf_response.iter_content(chunk_size=1024):
                    if chunk:
                        pdf_file.write(chunk)
            print(f"Downloaded: {pdf_name} -> {year_dir}")
        else:
            print(f"Failed to download {pdf_name}: HTTP {pdf_response.status_code}")
    except Exception as e:
        print(f"Failed to download {pdf_name}: {e}")


def process_year(year_url, download_dir):
    year = year_url.split('/')[-2]


    year_dir = os.path.join(download_dir, year)
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)


    response = requests.get(year_url)
    if response.status_code != 200:
        print(f"Failed to retrieve year page: {year_url}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    paper_links = []


    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/paper_files/paper/' in href and '/hash/' in href:
            paper_links.append(urljoin(year_url, href))

    if not paper_links:
        print(f"No paper links found for year: {year}")
        return

    print(f"Found {len(paper_links)} papers for year {year}. Downloading PDFs...")


    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for paper_url in paper_links:
            pdf_url, title = get_pdf_link_and_title(paper_url)
            if pdf_url and title:
                futures.append(executor.submit(download_pdf, pdf_url, title, year_dir))


        for future in as_completed(futures):
            future.result()


def download_pdfs(base_url, download_dir):

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    response = requests.get(base_url)
    if response.status_code != 200:
        print("Failed to retrieve main webpage")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    year_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/paper_files/paper/' in href:
            year_links.append(urljoin(base_url, href))

    if not year_links:
        print("No year links found on the main page.")
        return

    print(f"Found {len(year_links)} year links. Searching for papers...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_year, year_url, download_dir) for year_url in year_links]
        for future in as_completed(futures):
            future.result()

    print("Download complete!")

# Main Execution
base_url = "https://papers.nips.cc/"
download_directory = "../Python_Downloaded_PDFs"
download_pdfs(base_url, download_directory)