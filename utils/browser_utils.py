from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException
import time

class BrowserUtils:
    def __init__(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.wait = WebDriverWait(self.driver, 10)

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
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
            try:
                if locator.startswith("["):
                    return self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, locator)))
                # Direct ID attempt
                element = self.wait.until(EC.element_to_be_clickable((By.ID, locator)))
                return element
            except (StaleElementReferenceException, WebDriverException) as e:
                attempts += 1
                print(f"Debug: Retry {attempts}/{max_attempts} for locator '{locator}' due to {str(e)}")
                time.sleep(1)
            except Exception:
                # Fallback logic
                print(f"Debug: Fallback triggered for locator '{locator}'")
                if locator == "username" or locator == "user-name":
                    return self.wait.until(EC.element_to_be_clickable((By.ID, "user-name")))
                elif locator == "password":
                    return self.wait.until(EC.element_to_be_clickable((By.ID, "password")))
                elif locator == "login-button" or locator == "login_button":
                    return self.wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
                elif locator == "search" or locator == "search_box":
                    if "duckduckgo.com" in self.driver.current_url:
                        return self.wait.until(EC.element_to_be_clickable((By.ID, "search_form_input")))
                    elif "wikipedia.org" in self.driver.current_url:
                        return self.wait.until(EC.element_to_be_clickable((By.ID, "searchInput")))
                elif locator in ["button", "search_button", "searchButton"]:
                    return self.wait.until(EC.element_to_be_clickable((By.ID, "searchButton")))
                elif locator == "cars" or locator == "car_selection":
                    return self.wait.until(EC.element_to_be_clickable((By.ID, "cars")))
                elif locator == "submit":
                    return self.wait.until(EC.element_to_be_clickable((By.ID, "submit")))
                attempts += 1
                print(f"Debug: Retry {attempts}/{max_attempts} for locator '{locator}' - no fallback match")
                time.sleep(1)

        raise Exception(f"Failed to find element with locator '{locator}' after {max_attempts} attempts")

    def execute_actions(self, requirement):
        try:
            iframe = requirement.get("iframe")
            if iframe:
                try:
                    self.driver.switch_to.frame(iframe)
                    print(f"Switched to iframe '{iframe}'")
                except:
                    print(f"Warning: Could not switch to iframe '{iframe}' - proceeding without it")

            inputs = requirement.get("inputs", {})
            for field_id, value in inputs.items():
                element = self._find_element(field_id)
                print(f"Entering '{value}' into '{field_id}'")
                element.clear()
                element.send_keys(value)

            actions = requirement.get("actions", [])
            for action in actions:
                action_type = action.get("type")
                element_id = action.get("element_id")
                value = action.get("value")

                if not element_id:
                    raise ValueError("Action missing element_id")

                element = self._find_element(element_id)
                if action_type == "click":
                    print(f"Clicking '{element_id}'")
                    element.click()
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                elif action_type == "select":
                    if not value:
                        raise ValueError(f"Select action on {element_id} requires a value")
                    print(f"Selecting '{value}' in '{element_id}'")
                    from selenium.webdriver.support.ui import Select
                    Select(element).select_by_visible_text(value)
                elif action_type == "keypress":
                    if not value:
                        raise ValueError(f"Keypress action on {element_id} requires a value")
                    print(f"Pressing '{value}' on '{element_id}'")
                    element.send_keys(getattr(Keys, value.upper(), value))
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                else:
                    raise ValueError(f"Unsupported action type '{action_type}'")
                time.sleep(1)

            print("Debug: Page content after actions:", self.driver.find_element(By.TAG_NAME, "body").text[:100])
            return None
        except (WebDriverException, StaleElementReferenceException) as e:
            return f"Failure: Action execution error - {str(e)}"
        except Exception as e:
            return f"Failure: Action execution error - Unexpected error: {str(e)}"
        finally:
            if iframe:
                self.driver.switch_to.default_content()

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