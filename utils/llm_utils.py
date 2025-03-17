from langchain.prompts import PromptTemplate
from langchain_community.llms import OpenAI
from langchain_core.runnables import RunnableSequence

class LLMUtils:
    def __init__(self):
        self.llm = OpenAI(temperature=0)
        self.setup_prompts()

    def setup_prompts(self):
        self.requirement_prompt = PromptTemplate(
            input_variables=["user_input"],
            template="""
            Convert the following natural language instruction into a JSON-like dictionary for web automation. Use the following specific IDs for known websites:
            - For Sauce Demo (e.g., login pages): 'user-name' for username, 'password' for password, 'login-button' for login button.
            - For search pages: 'search' for search box, 'searchButton' or 'button' for search button.
            - For dropdowns: 'cars' for car selection, 'submit' for submit button.
            Include:
            - 'inputs': a dictionary of field names to values for text input.
            - 'actions': a list of dictionaries, each with 'type' (e.g., 'click', 'select', 'keypress'), 'element_id', and optional 'value'. Use 'keypress' with 'ENTER' for 'press Enter'.
            - 'iframe': an optional iframe ID only if explicitly mentioned (e.g., 'in the frame'); otherwise, omit it.
            Focus only on the actions specified; do not add validation elements.

            Instruction: {user_input}

            Output as a Python dictionary string:
            """
        )
        self.requirement_chain = RunnableSequence(self.requirement_prompt | self.llm)

        self.expected_prompt = PromptTemplate(
            input_variables=["user_input"],
            template="""
            Extract the expected output as a simple string from the following input, representing what the webpage should show after the actions:

            Input: {user_input}

            Output:
            """
        )
        self.expected_chain = RunnableSequence(self.expected_prompt | self.llm)

    def parse_requirement(self, user_input):
        try:
            requirement_str = self.requirement_chain.invoke({"user_input": user_input})
            requirement = eval(requirement_str)
            if not isinstance(requirement, dict):
                raise ValueError("Parsed requirement is not a dictionary")
            return requirement
        except Exception as e:
            print(f"Error parsing requirement: {str(e)}")
            return None

    def parse_expected_output(self, user_input):
        try:
            output = self.expected_chain.invoke({"user_input": user_input}).strip()
            if not isinstance(output, str) or not output:
                raise ValueError("Invalid expected output provided")
            return output
        except Exception as e:
            print(f"Error parsing expected output: {str(e)}")
            return None