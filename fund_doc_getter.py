import requests
import time
import string
import pandas as pd
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

def clean_fund_name(name):
    # Remove trailing country
    name = re.sub(r'\s+in\s+[A-Z]{2}$', '', name)

    # Remove trailing price/share-value style tokens
    name = re.sub(r'\s+(?:Ord(?:inary)?\s*)?(?:£|\$|GBP)?\d+(?:\.\d+)?[Pp]?$', '', name)

    # Remove repeated trailing metadata tokens
    metadata = re.compile(
        r'\s+(?:'
        r'Acc|Inc|Dis|Ord|Ordinary|GBP|USD|EUR|'
        r'A|B|C|I|W|X|Y|Z|'
        r'Inst|INA|Hedged'
        r')$'
    )

    previous = None
    while previous != name:
        previous = name
        name = metadata.sub('', name)

    return name.strip()

def clean_filename(filename):
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    cleaned_filename = ''.join(c for c in filename if c in valid_chars)
    return clean_fund_name(cleaned_filename)


def get_pdf_link(fund_name, html, doc):
    if "vanguard" in fund_name.lower():
        match = html.find("span", string=f"{doc}")
        if not match:
            match = html.find("span", string="NURS KII")
        pdf_link = match.find_parent("a")["href"]
        return pdf_link
    else:
        doc = doc_name2url_name[doc]
        pdf_link = str(html.find("a", string=lambda s: s and doc in s))
        #pdf_link = str(html.find_all("a", href=lambda href: href and f"{doc}URL" in href))
        pdf_link = pdf_link.split("pdf=")[1].split(".pdf")[0] + ".pdf"
        pdf_link = pdf_link.replace("%2f", "/").replace("%3a", ":")
        return pdf_link

def get_fund_html(fund, context):

    url = isin2url.get(fund["ISIN Code"])

    if not url:
        return None


    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded")

    html = BeautifulSoup(page.content(), "html.parser")
    if "This fund does not subscribe to Trustnet" in html.text:
        print(f"Fund {fund['Fund Name']} does not subscribe to Trustnet.")
        return None

    page.close()
    return html


fund_list_path = "Preferred Fund List.xlsx"
funds = pd.read_excel(fund_list_path, sheet_name=pd.ExcelFile(fund_list_path).sheet_names[-1]).to_dict(orient="records")

isin2url = pd.read_csv("urls.csv", index_col=0).to_dict()["URL"]

doc_name2url_name = {
    "KIID": "Key Investor Information Document",
    "Factsheet": "Provider's Own Factsheet"}

with sync_playwright() as p:
    htmls = {}
    browser = p.chromium.launch()
    context = browser.new_context()

    for fund in [funds[1], funds[2]]:
        if fund['Buy, Hold, Review or Sell'] != "Buy" or pd.isna(fund["ISIN Code"]):
            continue

        html = get_fund_html(fund, context)

        if html is None:
            continue

        htmls[fund["Fund Name"]] = html
        time.sleep(1)

    browser.close()

for fund_name, html in htmls.items():
    for doc in ["KIID", "Factsheet"]:
        try:
            pdf_link = get_pdf_link(fund_name, html, doc)
            pdf = requests.get(pdf_link)

            with open(f"{clean_filename(fund_name)}_{doc}.pdf", "wb") as pdf_file:
                pdf_file.write(pdf.content)
        except Exception:
            print(f"Could not find {doc} for {fund_name}.")
