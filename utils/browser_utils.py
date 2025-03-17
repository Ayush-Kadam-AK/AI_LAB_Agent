from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException, TimeoutException, NoSuchElementException
import time
import json

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

    def _find_element(self, locator, retries=2):
        current_url = self.driver.current_url
        cache_key = (current_url, locator)
        
        if cache_key in self.locator_cache:
            by_type, by_value = self.locator_cache[cache_key]
            try:
                print(f"Debug: Using cached locator: {by_type}='{by_value}' for '{locator}'")
                return self.wait.until(EC.element_to_be_clickable((by_type, by_value)))
            except Exception:
                del self.locator_cache[cache_key]
                print(f"Debug: Cached locator for '{locator}' failed, removed from cache")
        
        for attempt in range(retries + 1):
            print(f"Debug: Attempt {attempt + 1} to find locator for '{locator}'")
            html_content = self.driver.page_source[:10000]
            prompt = f"""
            Given the following HTML content, suggest up to three reliable locators for an element matching '{locator}'. 
            Return them as a valid JSON array of arrays, e.g., [["id", "search_form_input"], ["name", "q"], ["xpath", "//input[@type='search']"]].
            Prioritize unique IDs, then names, then CSS selectors or XPath based on attributes like type, placeholder, class, or role.
            For buttons (e.g., 'search_button', 'login_button'), prioritize elements with type='submit', role='button', or text/icon content (e.g., 'Search', magnifying glass).
            Ensure the locators are specific, clickable, or interactable, and match the element’s purpose (e.g., input for 'search_box', button for 'search_button').
            Return only the JSON array string, with no extra text, comments, or formatting.

            HTML: {html_content}
            Target: {locator}
            """
            try:
                llm_response = self.llm_utils.llm.invoke(prompt).content.strip()
                print(f"Debug: Raw LLM locator response: {llm_response}")
                locators = json.loads(llm_response)
                for locator_type, locator_value in locators:
                    try:
                        by_type = self.by_map[locator_type]
                        print(f"Debug: Trying LLM-suggested locator: {locator_type}='{locator_value}'")
                        element = self.wait.until(EC.element_to_be_clickable((by_type, locator_value)))
                        self.locator_cache[cache_key] = (by_type, locator_value)
                        print(f"Debug: Found element with locator: {locator_type}='{locator_value}'")
                        return element
                    except (NoSuchElementException, TimeoutException) as e:
                        print(f"Debug: Locator {locator_type}='{locator_value}' failed - {str(e)}")
                        continue
            except json.JSONDecodeError as e:
                print(f"Debug: Failed to parse LLM response as JSON - {str(e)}")
            except Exception as e:
                print(f"Debug: Failed to process LLM response or find element - {str(e)}")
            
            if attempt < retries:
                print("Debug: Retrying after brief delay...")
                time.sleep(2)
        
        raise Exception(f"Failed to find element for '{locator}' after {retries + 1} attempts")

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
            
            for input_key, input_value in requirement.get("inputs", {}).items():
                element = self._find_element(input_key)
                element.clear()
                element.send_keys(input_value)
                print(f"Entered '{input_value}' into '{input_key}'")
            
            for action in requirement.get("actions", []):
                element = self._find_element(action["element_id"])
                if action["type"] == "click":
                    element.click()
                    print(f"Clicked '{action['element_id']}'")
                    if "validation_element_id" in requirement:
                        self.wait.until(EC.presence_of_element_located((By.ID, requirement["validation_element_id"])))
                        print(f"Confirmed '{requirement['validation_element_id']}' appeared after click")
                elif action["type"] == "keypress":
                    key_value = action["value"].lower()
                    if key_value == "enter":
                        element.send_keys(Keys.ENTER)
                        print(f"Pressed Enter on '{action['element_id']}'")
                    else:
                        element.send_keys(action["value"])
                        print(f"Pressed '{action['value']}' on '{action['element_id']}'")
                    if "validation_element_id" in requirement:
                        self.wait.until(EC.presence_of_element_located((By.ID, requirement["validation_element_id"])))
                        print(f"Confirmed '{requirement['validation_element_id']}' appeared after keypress")
            
            if "validation_element_id" in requirement:
                self._find_element(requirement["validation_element_id"])
                print(f"Validated presence of '{requirement['validation_element_id']}'")
            
            return None
        except NoSuchElementException as e:
            return f"Failure: Action execution error - Element not found: {str(e)}"
        except StaleElementReferenceException as e:
            return f"Failure: Action execution error - Stale element: {str(e)}"
        except TimeoutException as e:
            return f"Failure: Action execution error - Timeout waiting for element: {str(e)}"
        except WebDriverException as e:
            return f"Failure: Action execution error - WebDriver issue: {str(e)}"
        except Exception as e:
            return f"Failure: Action execution error - Unexpected error: {str(e)}"
        finally:
            self.driver.switch_to.default_content()

    def validate_result(self, expected_output, llm_utils):
        try:
            actual_output = self.driver.find_element(By.TAG_NAME, "body").text.strip()
            if not actual_output:
                return "Failure: No content found on the page"

            relevance_prompt = f"""
            Determine if the following actual webpage content is semantically related to the expected output. 
            Consider broader context, such as whether the content includes search results, descriptions, or information 
            related to the expected output. Answer 'yes' or 'no' with a brief explanation.

            Actual content: {actual_output[:1000]}... (truncated for brevity)
            Expected output: {expected_output}

            Answer:
            """
            relevance_response = llm_utils.llm.invoke(relevance_prompt).content.strip().lower()
            if "yes" in relevance_response.split("\n")[0]:
                return f"Success: Webpage content is semantically related - Expected '{expected_output}', found in '{actual_output[:100]}...' ({relevance_response})"
            else:
                return f"Failure: Webpage content not related - Expected '{expected_output}', got '{actual_output[:100]}...' ({relevance_response})"
        except Exception as e:
            return f"Failure: Validation error - {str(e)}"

    def cleanup(self):
        self.driver.quit()