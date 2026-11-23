from ddgs import DDGS
import requests
import pandas as pd
import time
import difflib
from playwright.sync_api import sync_playwright

def string_similarity(str1, str2):
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def link_from_isin(name, isin, context):
    if "vanguard" in name.lower():
        url = f"site:vanguard.co.uk/professional/product {isin}"
    else:
        url = f"site:trustnet.com/factsheets {isin}"
    with DDGS() as ddgs:
        results = ddgs.text(
            url,
            max_results=10
        )


    results = [r for r in results if "www2" not in r['href']]
    for r in results:
        page = context.new_page()
        page.goto(r['href'], wait_until="domcontentloaded")
        print(name)
        if isin in page.content():
            print(r['href'])
            return r['href']
    

    '''
    for r in results:
        print(f"{name} : {r['href']} - string similarity: {string_similarity(name, r['title'])}")
        print(f"URL: {r['href']}")
        print()
    '''
    '''
    result =max(results, key=lambda r: string_similarity(name, r['href']))['href'] 
    '''
    #print(name)
    #print(results)
    #print()
    #return result


fund_list = pd.read_excel("Preferred Fund List.xlsx", sheet_name="Sept 2026").to_dict(orient="records")
isin_list = []
for fund in fund_list:
    if fund['Buy, Hold, Review or Sell'] == "Buy" and not pd.isna(fund["ISIN Code"]):
        isin_list.append({"Fund Name": fund["Fund Name"], "ISIN Code": fund["ISIN Code"]})

link_list = {}

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    for info in isin_list:
        isin = info["ISIN Code"]
        name = info["Fund Name"]
        while True:
            try:
                link = link_from_isin(name, isin, context)
                link_list[isin] = link
                break
            except Exception as e:
                print(f"Error occurred for ISIN {isin}: {e}. Retrying...")
                time.sleep(1)
                continue

    browser.close()

df = pd.DataFrame.from_dict(link_list, orient="index", columns=["URL"])
df.to_csv("urls.csv")

    
