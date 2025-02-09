import colorsys
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageTk

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_pdf_link_and_title(paper_url):
    response = requests.get(paper_url)
    if response.status_code != 200:
        return None, None

    soup = BeautifulSoup(response.text, 'html.parser')
    paper_button = soup.find('a', string='Paper')
    if paper_button and 'href' in paper_button.attrs:
        pdf_url = urljoin(paper_url, paper_button['href'])
        if pdf_url.endswith('.pdf'):
            title_tag = soup.find('h4')
            if title_tag:
                title = title_tag.text.strip()
                return pdf_url, title
    return None, None

def download_pdf(pdf_url, title, year_dir):
    sanitized_title = sanitize_filename(title)
    pdf_name = f"{sanitized_title}.pdf"
    pdf_path = os.path.join(year_dir, pdf_name)

    if os.path.exists(pdf_path):
        return

    try:
        pdf_response = requests.get(pdf_url, stream=True)
        if pdf_response.status_code == 200:
            with open(pdf_path, 'wb') as pdf_file:
                for chunk in pdf_response.iter_content(chunk_size=1024):
                    if chunk:
                        pdf_file.write(chunk)
    except Exception as e:
        pass

def process_year(year_url, download_dir):
    year = year_url.split('/')[-2]
    year_dir = os.path.join(download_dir, year)
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)

    response = requests.get(year_url)
    if response.status_code != 200:
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    paper_links = [urljoin(year_url, link['href']) for link in soup.find_all('a', href=True) if
                   '/paper_files/paper/' in link['href'] and '/hash/' in link['href']]

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(download_pdf, *get_pdf_link_and_title(paper_url), year_dir) for paper_url in
                   paper_links]
        for future in as_completed(futures):
            future.result()

def download_pdfs(base_url, download_dir, status_label):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    response = requests.get(base_url)
    if response.status_code != 200:
        status_label.config(text="Failed to retrieve main webpage")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    year_links = [urljoin(base_url, link['href']) for link in soup.find_all('a', href=True) if
                  '/paper_files/paper/' in link['href']]

    status_label.config(text=f"Found {len(year_links)} years. Downloading...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_year, year_url, download_dir) for year_url in year_links]
        for future in as_completed(futures):
            future.result()

    status_label.config(text="Download complete!")

def start_download():
    base_url = url_entry.get()
    if not base_url:
        messagebox.showerror("Error", "Please enter a valid URL")
        return

    download_dir = filedialog.askdirectory(title="Select Download Folder")
    if not download_dir:
        return

    status_label.config(text="Downloading PDFs... Please wait.")
    threading.Thread(target=download_pdfs, args=(base_url, download_dir, status_label), daemon=True).start()

root = tk.Tk()
root.title("Website Scrapper")
root.geometry("800x600")

bg_image = Image.open("bg.jpeg")
bg_image = bg_image.resize((800, 600), Image.LANCZOS)
bg_photo = ImageTk.PhotoImage(bg_image)

canvas = tk.Canvas(root, width=600, height=400)
canvas.pack(fill="both", expand=True)
canvas.create_image(0, 0, image=bg_photo, anchor="nw")

frame = tk.Frame(root)
frame.place(relx=0.5, rely=0.5, anchor="center")

tk.Label(frame, text="Enter URL:").pack(pady=5)
url_entry = tk.Entry(frame, width=70)
url_entry.pack(pady=5)

download_button = tk.Button(frame, text="Start Download", command=start_download)
download_button.pack(pady=10)

status_label = tk.Label(frame, text="", fg="blue")
status_label.pack(pady=5)

root.mainloop()