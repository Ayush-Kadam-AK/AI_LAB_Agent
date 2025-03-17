from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_openai import ChatOpenAI
import json
import os
class LLMUtils:
    def __init__(self):
        api_key=os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            api_key=api_key,  # Replace with your API key
            temperature=0
        )
        self.setup_prompts()

    def setup_prompts(self):
        self.requirement_prompt = PromptTemplate(
            input_variables=["user_input"],
            template="""
Convert the following user instruction into a valid JSON dictionary for web automation. Include:
- "inputs": a dictionary of field_id: value pairs for text input (e.g., "search_box": "text").
- "actions": a list of dictionaries, each with "type" (e.g., "click", "keypress"), "element_id", and optional "value".
- "validation_element_id": the ID or CSS selector of the element to check after actions (infer if not specified, e.g., "search_results" for searches).
- "iframe": set to null unless an iframe is explicitly mentioned.

Rules:
- If the instruction includes "press Enter", use a single "keypress" action with "value": "enter" on the input field.
- Avoid redundant text entry in "actions" if already in "inputs".
- Do not add unnecessary "click" actions unless explicitly stated (e.g., "click the search button").
- Ensure element IDs are descriptive and contextually relevant (e.g., "search_box" for search inputs).
- Return only the JSON string, with no extra text, comments, or formatting (e.g., no ```json markers).

Instruction: {user_input}

Output as a valid JSON string:
"""
        )
        self.requirement_chain = RunnableSequence(self.requirement_prompt | self.llm)

        self.expected_prompt = PromptTemplate(
            input_variables=["user_input"],
            template="""
Extract the expected output as a plain string from the following instruction. Return the full expected output exactly as provided, with no extra text or formatting.

Instruction: {user_input}

Output:
"""
        )
        self.expected_chain = RunnableSequence(self.expected_prompt | self.llm)

    def parse_requirement(self, user_input):
        try:
            requirement_str = self.requirement_chain.invoke({"user_input": user_input}).content.strip()
            print(f"Debug: Raw LLM requirement output: {requirement_str}")  # Log raw output for debugging
            requirement = json.loads(requirement_str)  # Parse as JSON
            if not isinstance(requirement, dict):
                raise ValueError("Parsed requirement is not a dictionary")
            return requirement
        except json.JSONDecodeError as e:
            print(f"Error parsing requirement: JSON decode error - {str(e)}")
            return None
        except Exception as e:
            print(f"Error parsing requirement: {str(e)}")
            return None

    def parse_expected_output(self, user_input):
        try:
            output = self.expected_chain.invoke({"user_input": user_input}).content.strip()
            print(f"Debug: Raw LLM expected output: {output}")  # Log raw output for debugging
            return output
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
            response = self.llm.invoke(prompt).content.strip()
            return response
        except Exception as e:
            print(f"Error in relevance check: {str(e)}")
            return "No"