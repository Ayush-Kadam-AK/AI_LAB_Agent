from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException
from bs4 import BeautifulSoup
import time

class BrowserUtils:
    def __init__(self, llm_utils=None):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.wait = WebDriverWait(self.driver, 10)
        self.llm_utils = llm_utils
        self.locator_cache = {}
        self.by_map = {
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "xpath": By.XPATH,
            "css": By.CSS_SELECTOR,
            "tag": By.TAG_NAME,
            "link_text": By.LINK_TEXT,
            "partial_link_text": By.PARTIAL_LINK_TEXT
        }

    def open_website(self, url):
        try:
            self.driver.get(url)
            print(f"Website opened: {url}")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True
        except Exception as e:
            print(f"Failure: Could not open website - {str(e)}")
            return False

    def _find_element(self, locator):
        current_url = self.driver.current_url
        cache_key = (current_url, locator)
        
        # Check cache first
        if cache_key in self.locator_cache:
            by_type, by_value = self.locator_cache[cache_key]
            try:
                print(f"Debug: Using cached locator: {by_type}='{by_value}' for '{locator}'")
                return self.wait.until(EC.element_to_be_clickable((by_type, by_value)))
            except Exception:
                del self.locator_cache[cache_key]
                print(f"Debug: Cached locator for '{locator}' failed, removed from cache")
        
        # Use LLM to suggest multiple locators
        if self.llm_utils:
            print(f"Debug: Using LLM to find locators for '{locator}'")
            html_content = self.driver.page_source[:5000]  # Limit to avoid token overflow
            prompt = f"""
            Analyze the following HTML content and suggest up to three possible locators for the element matching '{locator}'. Return them as a list of tuples, e.g., [('id', 'search_form_input'), ('name', 'q'), ('xpath', '//input[@type="search"]')]. Prioritize the most specific and reliable locators.

            HTML: {html_content}
            Target: {locator}
            """
            llm_response = self.llm_utils.llm.invoke(prompt).strip()
            try:
                locators = eval(llm_response)  # Expecting a list of tuples
                for locator_type, locator_value in locators:
                    try:
                        by_type = self.by_map[locator_type]
                        element = self.wait.until(EC.element_to_be_clickable((by_type, locator_value)))
                        self.locator_cache[cache_key] = (by_type, locator_value)
                        print(f"Debug: Found element with LLM-suggested locator: {locator_type}='{locator_value}'")
                        return element
                    except:
                        continue
            except Exception as e:
                print(f"Debug: Failed to parse LLM response for locators - {str(e)}")
        
        # Fallback to predefined strategies
        print(f"Debug: Attempting fallback locator strategies for '{locator}'")
        fallback_locators = self.get_fallback_locators(locator)
        for by_type, by_value in fallback_locators:
            try:
                element = self.wait.until(EC.element_to_be_clickable((by_type, by_value)))
                print(f"Debug: Found element with fallback locator: {by_type}='{by_value}'")
                return element
            except:
                continue
        
        raise Exception(f"Failed to find element for '{locator}' after trying all strategies")

    def get_fallback_locators(self, locator_name):
        locator_name = locator_name.lower()
        if "search" in locator_name and ("field" in locator_name or "box" in locator_name):
            return [
                (By.CSS_SELECTOR, "input[name='q']"),
                (By.CSS_SELECTOR, "input[type='search']"),
                (By.XPATH, "//input[contains(@placeholder, 'search')]"),
                (By.CSS_SELECTOR, "input#search"),
                (By.CSS_SELECTOR, "input.search"),
                (By.ID, "searchInput"),
                (By.ID, "search_form_input_homepage"),
            ]
        elif "button" in locator_name and "search" in locator_name:
            return [
                (By.ID, "search_button_homepage"),  # DuckDuckGo specific
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'search')]"),
                (By.CSS_SELECTOR, "button#search"),
                (By.CSS_SELECTOR, "button.search"),
            ]
        if "button" in locator_name:
            return [
            (By.ID, locator_name),
            (By.NAME, locator_name),
            (By.CSS_SELECTOR, f"button#{locator_name}"),
            (By.CSS_SELECTOR, f"button.{locator_name}"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, f"//button[contains(text(), '{locator_name.replace('-', ' ')}')]"),
            (By.CSS_SELECTOR, f"button#{locator_name.replace('-', '')}"),
            (By.CSS_SELECTOR, f"button.{locator_name.replace('-', '')}"),
            ]
        if "search" in locator_name:
            return [
                (By.CSS_SELECTOR, "input[type='search']"),
                (By.CSS_SELECTOR, "input[name='q']"),
                (By.XPATH, "//input[contains(@placeholder, 'search')]"),
                (By.CSS_SELECTOR, "input#search"),
                (By.CSS_SELECTOR, "input.search"),
            ]
        elif "button" in locator_name:
            return [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'search')]"),
                (By.CSS_SELECTOR, "button#search"),
                (By.CSS_SELECTOR, "button.search"),
            ]
        elif "username" in locator_name or "login" in locator_name:
            return [
                (By.ID, "username"),
                (By.NAME, "username"),
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.XPATH, "//input[@placeholder='Username']"),
            ]
        else:  # Generic fallback for unknown elements
            return [
                (By.ID, locator_name),
                (By.NAME, locator_name),
                (By.CSS_SELECTOR, f"#{locator_name}"),
                (By.CSS_SELECTOR, f".{locator_name}"),
            ]

    def execute_actions(self, requirement):
        try:
            iframe = requirement.get("iframe")
            if iframe:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                iframe_found = False
                for ifr in iframes:
                    if ifr.get_attribute("id") == iframe or ifr.get_attribute("name") == iframe:
                        self.driver.switch_to.frame(ifr)
                        print(f"Switched to iframe '{iframe}'")
                        iframe_found = True
                        break
                if not iframe_found:
                    print(f"Warning: Could not find iframe '{iframe}' - proceeding without it")
            
            # Process inputs (e.g., typing into fields)
            for input_key, input_value in requirement.get("inputs", {}).items():
                element = self._find_element(input_key)
                element.clear()
                element.send_keys(input_value)
                print(f"Entered '{input_value}' into '{input_key}'")
            
            # Process actions (e.g., clicking buttons)
            for action in requirement.get("actions", []):
                element = self._find_element(action["element_id"])
                if action["type"] == "click":
                    element.click()
                    print(f"Clicked '{action['element_id']}'")
                    # Optional: Wait for validation element after click
                    if "validation_element_id" in requirement:
                        self._find_element(requirement["validation_element_id"])
                        print(f"Confirmed '{requirement['validation_element_id']}' appeared after click")
            
            # Validate outcome if specified
            if "validation_element_id" in requirement:
                self._find_element(requirement["validation_element_id"])
                print(f"Validated presence of '{requirement['validation_element_id']}'")
            
            return None
        except (WebDriverException, StaleElementReferenceException) as e:
            return f"Failure: Action execution error - {str(e)}"
        except Exception as e:
            return f"Failure: Action execution error - Unexpected error: {str(e)}"
        finally:
            self.driver.switch_to.default_content()  # Reset to main content

    def validate_result(self, expected_output, llm_utils):
        try:
            actual_output = self.driver.find_element(By.TAG_NAME, "body").text.strip()
            if not actual_output:
                return "Failure: No content found on the page"

            relevance_prompt = llm_utils.llm.invoke(
                f"""
                Determine if the following actual webpage content is semantically related to the expected output. Consider broader context, such as whether the content describes items, results, or information related to the expected output. Answer 'yes' or 'no' with a brief explanation.

                Actual content: {actual_output[:1000]}... (truncated for brevity)
                Expected output: {expected_output}

                Answer:
                """
            ).strip().lower()

            if "yes" in relevance_prompt.split("\n")[0]:
                return f"Success: Webpage content is semantically related - Expected '{expected_output}', found in '{actual_output[:100]}...' ({relevance_prompt})"
            else:
                return f"Failure: Webpage content not related - Expected '{expected_output}', got '{actual_output[:100]}...' ({relevance_prompt})"
        except Exception as e:
            return f"Failure: Validation error - {str(e)}"

    def cleanup(self):
        self.driver.quit()