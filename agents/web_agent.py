from utils.browser_utils import BrowserUtils
from utils.llm_utils import LLMUtils

class WebAutomationAgent:
    def __init__(self):
        self.llm = LLMUtils()
        self.browser = BrowserUtils(llm_utils=self.llm)

    def run(self, url):
        if not self.browser.open_website(url):
            return "Could not proceed due to website opening failure."

        print("\nWebsite is now open. Inspect it if needed (e.g., via browser DevTools).")
        print("Describe the requirement in plain English (e.g., 'Type python into the search box and click search'):")
        requirement_input = input("Enter requirement: ")
        print("\nDescribe the expected output in plain English (e.g., 'Python-related content'):")
        expected_input = input("Enter expected output: ")

        requirement = self.llm.parse_requirement(requirement_input)
        expected_output = self.llm.parse_expected_output(expected_input)

        if not requirement or not expected_output:
            self.browser.cleanup()
            return "Invalid input. Exiting."

        print(f"\nParsed requirement: {requirement}")
        print(f"Parsed expected output: {expected_output}")

        action_result = self.browser.execute_actions(requirement)
        if action_result:
            return action_result

        result = self.browser.validate_result(expected_output, self.llm)
        return result