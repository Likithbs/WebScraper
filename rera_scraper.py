import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OdishaRERAScraper:
    def __init__(self, headless=False):
        """Initialize the scraper with Chrome WebDriver"""
        self.setup_driver(headless)
        self.projects_data = []
        
    def setup_driver(self, headless=False):
        """Set up Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 20)
        
    def navigate_to_projects_page(self):
        """Navigate to the RERA projects list page"""
        try:
            logger.info("Navigating to RERA projects page...")
            self.driver.get("https://rera.odisha.gov.in/projects/project-list")
            
            # Wait for the projects to load
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'View Details')] | //a[contains(text(), 'View Details')]")))
            time.sleep(5)
            logger.info("Successfully loaded projects page")
            
        except Exception as e:
            logger.error(f"Failed to load projects page: {e}")
            raise
    
    def find_all_view_details_buttons(self):
        """Find all View Details buttons on the page"""
        try:
            # Wait for page to fully load and scroll to load all projects
            time.sleep(3)
            
            # Scroll to load all content
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Find View Details buttons
            buttons = []
            selectors = [
                "//button[contains(text(), 'View Details')]",
                "//a[contains(text(), 'View Details')]"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem not in buttons:
                            buttons.append(elem)
                except:
                    continue
            
            logger.info(f"Found {len(buttons)} View Details buttons")
            return buttons[:6]  # Return first 6 buttons
            
        except Exception as e:
            logger.error(f"Error finding View Details buttons: {e}")
            return []
    
    def extract_project_overview_data(self):
        """Extract basic project data from the overview page"""
        project_data = {}
        
        try:
            # Wait for page to load completely
            time.sleep(5)
            
            # Extract RERA Registration Number (both RP/ and PS/ formats)
            rera_selectors = [
                "//*[contains(text(), 'RP/') or contains(text(), 'PS/')]",
                "//*[contains(text(), 'RERA Regd')]//following-sibling::*//*[contains(text(), 'RP/') or contains(text(), 'PS/')]",
                "//*[contains(text(), 'Registration')]//following-sibling::*//*[contains(text(), 'RP/') or contains(text(), 'PS/')]",
                "//span[contains(text(), 'RP/') or contains(text(), 'PS/')]",
                "//div[contains(text(), 'RP/') or contains(text(), 'PS/')]",
                "//p[contains(text(), 'RP/') or contains(text(), 'PS/')]"
            ]
            
            for selector in rera_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and ('RP/' in text or 'PS/' in text):
                            # Updated regex to handle both RP/ and PS/ formats
                            rera_pattern = r'(RP|PS)/\d{1,2}/\d{4}/\d{4,6}'
                            rera_match = re.search(rera_pattern, text)
                            if rera_match:
                                project_data['RERA_Regd_No'] = rera_match.group()
                                logger.info(f"Found RERA number: {rera_match.group()}")
                                break
                    if 'RERA_Regd_No' in project_data:
                        break
                except Exception as e:
                    logger.debug(f"RERA selector failed: {e}")
                    continue
            
            # Extract Project Name - more comprehensive approach
            # First try to get the actual project name from the page structure
            name_selectors = [
                # Look for project name in structured data
                "//*[contains(text(), 'Project Name')]//following-sibling::*[1]",
                "//*[contains(text(), 'Project Name')]//parent::*//following-sibling::*[1]",
                "//*[contains(text(), 'Project Name')]//following::text()[normalize-space()][1]",
                # Look for main headings that aren't generic
                "//h1[not(contains(text(), 'Details')) and not(contains(text(), 'Overview')) and not(contains(text(), 'Project')) and string-length(normalize-space()) > 3]",
                "//h2[not(contains(text(), 'Details')) and not(contains(text(), 'Overview')) and not(contains(text(), 'Project')) and string-length(normalize-space()) > 3]",
                "//h3[not(contains(text(), 'Details')) and not(contains(text(), 'Overview')) and not(contains(text(), 'Project')) and string-length(normalize-space()) > 3]",
                # Look in card titles or project containers
                "//*[contains(@class, 'card-title')][not(contains(text(), 'Details'))][not(contains(text(), 'Overview'))]",
                "//*[contains(@class, 'project-title')]",
                "//*[contains(@class, 'project-name')]",
                # Look for emphasized text that might be project name
                "//strong[not(contains(text(), 'Details')) and not(contains(text(), 'Overview')) and string-length(normalize-space()) > 5]",
                "//b[not(contains(text(), 'Details')) and not(contains(text(), 'Overview')) and string-length(normalize-space()) > 5]"
            ]
            
            for selector in name_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # Filter out unwanted text
                        if (text and len(text) > 3 and 
                            'Details' not in text and 
                            'Overview' not in text and 
                            'Project' not in text and
                            'RERA' not in text and
                            'Registration' not in text and
                            text != 'Projects'):
                            project_data['Project_Name'] = text
                            logger.info(f"Found project name: {text}")
                            break
                    if 'Project_Name' in project_data:
                        break
                except Exception as e:
                    logger.debug(f"Name selector failed: {e}")
                    continue
            
            # If still no project name found, try alternative methods
            if 'Project_Name' not in project_data:
                try:
                    # Look for any text that appears to be a project name near RERA number
                    if 'RERA_Regd_No' in project_data:
                        rera_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{project_data['RERA_Regd_No']}')]")
                        for rera_elem in rera_elements:
                            # Look for nearby text that might be project name
                            parent = rera_elem.find_element(By.XPATH, "./..")
                            siblings = parent.find_elements(By.XPATH, "./*")
                            for sibling in siblings:
                                text = sibling.text.strip()
                                if (text and len(text) > 5 and 
                                    project_data['RERA_Regd_No'] not in text and
                                    'Details' not in text and 
                                    'Overview' not in text and
                                    text != 'Projects'):
                                    project_data['Project_Name'] = text
                                    logger.info(f"Found project name near RERA: {text}")
                                    break
                            if 'Project_Name' in project_data:
                                break
                except Exception as e:
                    logger.debug(f"Alternative name search failed: {e}")
            
            # Last resort - check page title
            if 'Project_Name' not in project_data:
                try:
                    page_title = self.driver.title
                    if page_title and 'RERA' in page_title:
                        title_parts = page_title.split('-')
                        for part in title_parts:
                            part = part.strip()
                            if (part and len(part) > 3 and 
                                'RERA' not in part and 
                                'Odisha' not in part and
                                'Details' not in part):
                                project_data['Project_Name'] = part
                                logger.info(f"Found project name in title: {part}")
                                break
                except Exception as e:
                    logger.debug(f"Title extraction failed: {e}")
            
            logger.info(f"Extracted overview data: {project_data}")
            return project_data
            
        except Exception as e:
            logger.error(f"Error extracting overview data: {e}")
            return project_data
    
    def click_promoter_tab(self):
        """Click on Promoter Details tab with improved reliability"""
        try:
            # Multiple ways to find and click the promoter tab
            tab_selectors = [
                "//a[contains(text(), 'Promoter Details')]",
                "//button[contains(text(), 'Promoter Details')]",
                "//li[contains(text(), 'Promoter Details')]",
                "//*[contains(@class, 'nav') and contains(text(), 'Promoter')]",
                "//*[@role='tab' and contains(text(), 'Promoter')]",
                "//a[@href='#promoter-details']",
                "//a[contains(@href, 'promoter')]",
                "//*[contains(@class, 'tab') and contains(text(), 'Promoter')]"
            ]
            
            for selector in tab_selectors:
                try:
                    tab_elements = self.driver.find_elements(By.XPATH, selector)
                    for tab_element in tab_elements:
                        if tab_element.is_displayed():
                            # Try different click methods
                            try:
                                self.wait.until(EC.element_to_be_clickable(tab_element))
                                tab_element.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", tab_element)
                            
                            time.sleep(4)
                            logger.info("Successfully clicked Promoter Details tab")
                            return True
                except Exception as e:
                    logger.debug(f"Tab selector failed: {selector} - {e}")
                    continue
            
            logger.warning("Could not find or click Promoter Details tab")
            return False
            
        except Exception as e:
            logger.error(f"Error clicking promoter tab: {e}")
            return False
    
    def extract_promoter_details(self):
        """Extract promoter details from the Promoter Details tab"""
        promoter_data = {}
        
        try:
            # Click on Promoter Details tab
            if not self.click_promoter_tab():
                logger.warning("Could not access promoter details tab")
                return promoter_data
            
            # Wait for content to load
            time.sleep(4)
            
            # Extract Company Name with comprehensive selectors
            company_selectors = [
                "//*[contains(text(), 'Company Name')]//following-sibling::*[1]",
                "//*[contains(text(), 'Company Name')]//following-sibling::*/text()[normalize-space()][1]",
                "//*[contains(text(), 'Company Name')]//parent::*//following-sibling::*[1]",
                "//*[contains(text(), 'Company Name')]//following::*[contains(text(), 'M/S') or contains(text(), 'PVT') or contains(text(), 'LTD')][1]",
                "//*[contains(text(), 'M/S') and (contains(text(), 'PVT') or contains(text(), 'LTD') or contains(text(), 'PRIVATE'))]",
                "//*[contains(text(), 'DEVELOPERS') or contains(text(), 'BUILDERS') or contains(text(), 'CONSTRUCTION')][contains(text(), 'PVT') or contains(text(), 'LTD')]",
                "//strong[contains(text(), 'M/S')]",
                "//b[contains(text(), 'M/S')]",
                "//span[contains(text(), 'M/S')]",
                "//div[contains(text(), 'M/S')]",
                "//p[contains(text(), 'M/S')]"
            ]
            
            for selector in company_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 5:
                            # Check if it looks like a company name
                            company_keywords = ['M/S', 'PVT', 'LTD', 'PRIVATE', 'DEVELOPERS', 'BUILDERS', 'CONSTRUCTION', 'INFRA']
                            if any(keyword in text.upper() for keyword in company_keywords):
                                promoter_data['Promoter_Name'] = text
                                logger.info(f"Found company name: {text}")
                                break
                    if 'Promoter_Name' in promoter_data:
                        break
                except Exception as e:
                    logger.debug(f"Company selector failed: {e}")
                    continue
            
            # Extract Registered Office Address
            address_selectors = [
                "//*[contains(text(), 'Registered Office Address')]//following-sibling::*[1]",
                "//*[contains(text(), 'Registered Office Address')]//following-sibling::*/text()[normalize-space()][1]",
                "//*[contains(text(), 'Registered Office Address')]//parent::*//following-sibling::*[1]",
                "//*[contains(text(), 'Office Address')]//following-sibling::*[1]",
                "//*[contains(text(), 'Address')]//following-sibling::*[contains(text(), 'PO-') or contains(text(), 'PIN') or contains(text(), 'Dist')]",
                "//*[contains(text(), 'PO-') and (contains(text(), 'PIN') or contains(text(), 'Dist'))]",
                "//*[contains(text(), 'Dist.') and (contains(text(), 'PIN') or contains(text(), 'PO-') or contains(text(), 'Odisha'))]",
                "//*[contains(text(), 'Odisha') and contains(text(), '-') and string-length(normalize-space()) > 20]"
            ]
            
            for selector in address_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 15:
                            # Check if it looks like an address
                            address_keywords = ['PO-', 'PIN', 'Dist', 'Odisha', 'Plot', 'Road', 'Street']
                            if any(keyword in text for keyword in address_keywords):
                                promoter_data['Promoter_Address'] = text
                                logger.info(f"Found address: {text}")
                                break
                    if 'Promoter_Address' in promoter_data:
                        break
                except Exception as e:
                    logger.debug(f"Address selector failed: {e}")
                    continue
            
            # Extract GST Number
            gst_selectors = [
                "//*[contains(text(), 'GST No')]//following-sibling::*[1]",
                "//*[contains(text(), 'GST No')]//following-sibling::*/text()[normalize-space()][1]",
                "//*[contains(text(), 'GST No')]//parent::*//following-sibling::*[1]",
                "//*[contains(text(), 'GST')]//following-sibling::*[1]",
                # Look for 15-character alphanumeric strings that look like GST numbers
                "//*[text()[matches(., '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$')]]",
                "//span[string-length(normalize-space(text())) = 15 and contains(text(), 'A')]",
                "//div[string-length(normalize-space(text())) = 15 and contains(text(), 'A')]",
                "//p[string-length(normalize-space(text())) = 15 and contains(text(), 'A')]"
            ]
            
            for selector in gst_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) >= 10:
                            # Clean and validate GST format
                            gst_clean = re.sub(r'[^A-Z0-9]', '', text.upper())
                            if len(gst_clean) == 15 and gst_clean[2:7].isalpha() and gst_clean[:2].isdigit():
                                promoter_data['GST_No'] = gst_clean
                                logger.info(f"Found GST number: {gst_clean}")
                                break
                            elif len(text) >= 15 and any(char.isalpha() for char in text) and any(char.isdigit() for char in text):
                                promoter_data['GST_No'] = text
                                logger.info(f"Found GST number: {text}")
                                break
                    if 'GST_No' in promoter_data:
                        break
                except Exception as e:
                    logger.debug(f"GST selector failed: {e}")
                    continue
            
            logger.info(f"Extracted promoter data: {promoter_data}")
            return promoter_data
            
        except Exception as e:
            logger.error(f"Error extracting promoter details: {e}")
            return promoter_data
    
    def scrape_project_details(self, button_index):
        """Scrape details for a single project using button index"""
        try:
            # Navigate back to main page
            self.navigate_to_projects_page()
            
            # Find all buttons again (they get stale after navigation)
            view_details_buttons = self.find_all_view_details_buttons()
            
            if button_index >= len(view_details_buttons):
                logger.warning(f"Button index {button_index} out of range")
                return None
            
            button = view_details_buttons[button_index]
            
            # Scroll to the button and ensure it's clickable
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(2)
            
            # Click the button
            try:
                self.wait.until(EC.element_to_be_clickable(button))
                button.click()
            except:
                self.driver.execute_script("arguments[0].click();", button)
            
            # Wait for the detail page to load
            time.sleep(6)
            
            # Extract project overview data
            project_data = self.extract_project_overview_data()
            
            # Extract promoter details
            promoter_data = self.extract_promoter_details()
            
            # Combine all data
            complete_data = {**project_data, **promoter_data}
            
            # Ensure all required fields are present (even if empty)
            required_fields = ['RERA_Regd_No', 'Project_Name', 'Promoter_Name', 'Promoter_Address', 'GST_No']
            for field in required_fields:
                if field not in complete_data:
                    complete_data[field] = ''
            
            logger.info(f"Scraped project {button_index + 1}: {complete_data}")
            return complete_data
            
        except Exception as e:
            logger.error(f"Error scraping project details for index {button_index}: {e}")
            return None
    
    def scrape_all_projects(self):
        """Main method to scrape all project data"""
        try:
            self.navigate_to_projects_page()
            
            # Find all View Details buttons first
            view_details_buttons = self.find_all_view_details_buttons()
            
            if not view_details_buttons:
                logger.error("No View Details buttons found")
                return
            
            logger.info(f"Found {len(view_details_buttons)} projects to scrape")
            
            # Scrape each project by index
            for i in range(min(6, len(view_details_buttons))):
                logger.info(f"Scraping project {i + 1}/6...")
                
                project_data = self.scrape_project_details(i)
                
                if project_data:
                    self.projects_data.append(project_data)
                    logger.info(f"Successfully scraped project {i + 1}")
                else:
                    logger.warning(f"Failed to scrape project {i + 1}")
                    # Add empty record to maintain count
                    empty_data = {
                        'RERA_Regd_No': '',
                        'Project_Name': '',
                        'Promoter_Name': '',
                        'Promoter_Address': '',
                        'GST_No': ''
                    }
                    self.projects_data.append(empty_data)
                
                # Add delay between requests
                time.sleep(3)
            
            logger.info(f"Completed scraping {len(self.projects_data)} projects")
            
        except Exception as e:
            logger.error(f"Error in main scraping process: {e}")
    
    def save_to_csv(self, filename="odisha_rera_projects.csv"):
        """Save scraped data to CSV file"""
        if self.projects_data:
            df = pd.DataFrame(self.projects_data)
            # Reorder columns
            column_order = ['RERA_Regd_No', 'Project_Name', 'Promoter_Name', 'Promoter_Address', 'GST_No']
            df = df.reindex(columns=column_order)
            df.to_csv(filename, index=False)
            logger.info(f"Data saved to {filename}")
            print(f"\nData saved to {filename}")
            print(f"Total projects scraped: {len(self.projects_data)}")
            return df
        else:
            logger.warning("No data to save")
            return None
    
    def display_data(self):
        """Display scraped data"""
        if self.projects_data:
            df = pd.DataFrame(self.projects_data)
            print("\n" + "="*100)
            print("SCRAPED ODISHA RERA PROJECTS DATA")
            print("="*100)
            
            for i, project in enumerate(self.projects_data, 1):
                print(f"\nProject {i}:")
                print("-" * 50)
                print(f"RERA Regd. No: {project.get('RERA_Regd_No', 'N/A')}")
                print(f"Project Name: {project.get('Project_Name', 'N/A')}")
                print(f"Promoter Name: {project.get('Promoter_Name', 'N/A')}")
                print(f"Promoter Address: {project.get('Promoter_Address', 'N/A')}")
                print(f"GST No: {project.get('GST_No', 'N/A')}")
            
            return df
        else:
            print("No data available to display")
            return None
    
    def close(self):
        """Close the webdriver"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            logger.info("WebDriver closed")

def main():
    """Main function to run the scraper"""
    scraper = None
    try:
        print("Starting Odisha RERA Projects Scraper...")
        print("This will scrape the first 6 projects from the RERA website.")
        
        # Initialize scraper (set headless=True to run without browser window)
        scraper = OdishaRERAScraper(headless=False)
        
        # Scrape all projects
        scraper.scrape_all_projects()
        
        # Display results
        df = scraper.display_data()
        
        # Save to CSV
        scraper.save_to_csv()
        
        print("\nScraping completed successfully!")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        logger.error(f"Main function error: {e}")
    
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()