from langchain.prompts import PromptTemplate
from langchain_community.llms import OpenAI
from langchain_core.runnables import RunnableSequence
import json
class LLMUtils:
    def __init__(self):
        self.llm = OpenAI(temperature=0)
        self.setup_prompts()

    def setup_prompts(self):
        self.requirement_prompt = PromptTemplate(
        input_variables=["user_input"],
        template="""
    Convert the following user instruction into a JSON-like dictionary for web automation. Include:
    - 'inputs': a dictionary of field_id: value pairs for text input.
    - 'actions': a list of dictionaries, each with 'type' (e.g., 'click', 'select', 'keypress'), 'element_id', and optional 'value'.
    - 'validation_element_id': the ID or CSS selector of the element to check after actions (must always be included).
    - 'iframe': an optional iframe ID if the actions or validation occur within an iframe.

    Ensure 'validation_element_id' is always provided, even if inferred from context.

    Instruction: {user_input}

    Output as a Python dictionary string:
    """
        )
        self.requirement_chain = RunnableSequence(self.requirement_prompt | self.llm)

        self.expected_prompt = PromptTemplate(
            input_variables=["user_input"],
            template="Extract the expected output as a string from: {user_input}\n\nOutput: "
        )
        self.expected_chain = RunnableSequence(self.expected_prompt | self.llm)

    def parse_requirement(self, user_input):
        try:
            requirement_str = self.requirement_chain.invoke({"user_input": user_input})
            requirement = json.loads(requirement_str)
            if not isinstance(requirement, dict):
                raise ValueError("Parsed requirement is not a dictionary")
            return requirement
        except Exception as e:
            print(f"Error parsing requirement: {str(e)}")
            return None

    def parse_expected_output(self, user_input):
        try:
            output = self.expected_chain.invoke({"user_input": user_input}).strip()
            return output.split("\n")[0]  # Ensure it's a single line of text
        except Exception as e:
            print(f"Error parsing expected output: {str(e)}")
            return None
    def check_relevance(self, expected_output, actual_output):
        prompt = f"""
    Determine if the actual output is contextually relevant to the expected output.

    Expected Output: {expected_output}
    Actual Output: {actual_output}

    Answer with a single word: "Yes" if relevant, "No" if not.
    """
        try:
            response = self.llm.invoke(prompt).strip()
            return response
        except Exception as e:
            print(f"Error in relevance check: {str(e)}")
            return "No"