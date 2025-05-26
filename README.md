# Odisha RERA Projects Scraper

A Python-based web scraper that extracts registered real estate project details from the official [Odisha RERA](https://rera.odisha.gov.in/projects/project-list) website using **Selenium** and saves them into a CSV file.

---

## Features

Scrapes the first 6 projects from the portal  
Extracts:

- RERA Registration Number
- Project Name
- Promoter Name
- Promoter Address
- GST Number

Headless and non-headless browser mode  
Saves output to CSV  
Logs progress and errors

---

## Project Structure

```
├── rera_scraper.py           # Main Python script
├── odisha_rera_projects.csv  # Output CSV (after running)
├── README.md                 # Project documentation
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/rera-scraper.git
cd rera-scraper
```

### 2. Install Dependencies

Install packages using pip:

```bash
pip install selenium pandas
```

### 3. Set Up ChromeDriver

- Install [Google Chrome](https://www.google.com/chrome/)
- Download [ChromeDriver](https://sites.google.com/chromium.org/driver/) matching your Chrome version
- Add `chromedriver` to your system PATH or place it in the project folder

---

## How to Run

```bash
python rera_scraper.py
```

The script will:

1. Open the Odisha RERA portal
2. Automatically scroll to load project entries
3. Click on the first 6 project “View Details” buttons
4. Extract overview and promoter information
5. Save results to `odisha_rera_projects.csv`
6. Display the results in the terminal

To run in headless mode (no browser window):

```python
scraper = OdishaRERAScraper(headless=True)
```

---

## Disclaimer

> **This scraper is for educational purposes only.**  
> Please respect the terms of service of the Odisha RERA portal.  
> Do not use this script for commercial scraping without proper authorization.

---

## Acknowledgements

- [Selenium WebDriver](https://www.selenium.dev/)
- [Odisha RERA Portal](https://rera.odisha.gov.in/)
