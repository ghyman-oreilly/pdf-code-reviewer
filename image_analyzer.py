from dotenv import load_dotenv
import openai
import os
from typing import Union

from pdf_reader import PDFPageImage

# load env variables from .env
load_dotenv()

# initialize client
api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)

# TODO: interpret response / read into useable format

class PDFPageAnalyzer:
    def __init__(self, model="gpt-4.1"):
        self.model = model

    def create_prompt(
            self, 
            image_data_uri: str, 
            text_width_inches: Union[str, float, int],
            fail_string: str = 'UNABLE_TO_ASSESS',
            no_issues_str: str = 'NO_ISSUES',
            issues_str: str = 'ISSUES_FOUND',
            should_suggest_resolution: bool = True,
            detail="high"
        ):
        """
        Build the full user prompt for an AI service call.

        Args:
            page_image (PDFPageImage): The page image object containing metadata like page number and dimensions
            image_data_uri (str): Complete data URI (format: data:<mimetype>;base64,<encoded-data>)
            fail_string (str, optional): String to use when assessment fails. Defaults to 'UNABLE_TO_ASSESS'
            no_issues_str (str, optional): String to use when assessment finds no issues. Defaults to 'NO_ISSUES'
            ...

        Returns:
            str: The formatted prompt string ready for the AI service
        """

        if not isinstance(text_width_inches, str):
            text_width_inches = str(text_width_inches)

        input_text = "Your task is to assess this image of a PDF page.\n\n"

        input_text += "Please check this PDF page to see if any code is running beyond the text area on the right side of the page.\n\n"

        input_text += f"If there is not, please simply respond with:\n\nSTATUS: {no_issues_str}.\n\n"

        input_text += f"If there is, please respond: \n\nSTATUS: {issues_str}.\n\n" 
        
        input_text += "Then provide the height from the top of the page, in inches, of each code block with lines running beyond the text area, in this format:\n\n"

        input_text += "**ISSUE LOCATIONS**\nISSUE 1 LOCATION: N.N inches\nISSUE 2 LOCATION: N.N inches\netc.\n\n"
        
        input_text += f"You can use the page's text width as a reference measurement. It is {text_width_inches} inches wide.\n\n"

        if should_suggest_resolution:
            input_text += "If you are able to provide a reformatting suggestion for each problematic code block on the page, you should do so in this format:"

            input_text += "**ISSUE REFORMATTING**\nISSUE 1 REFORMATTED: [reformated code here]\nISSUE 2 REFORMATTED: [reformated code here]\netc.\n\n"

        input_text += "IMPORTANT: DO NOT PROVIDE ANY OTHER NOTES OR COMMENTARY.\n\n"

        input_text += f"If you are uncertain how to or unable to assess the image, respond:\n\nSTATUS: {fail_string}"
       
        return [
            {
                "role": "user",
                "content": [
                    { "type": "input_text", "text": input_text },
                    {
                        "type": "input_image",
                        "image_url": image_data_uri,
                        "detail": detail
                    },
                ],
            }
        ]

    def assess_image(
            self, 
            image_data_uri: str, 
            text_width_inches: Union[str, float, int],
            fail_string: str = 'UNABLE_TO_ASSESS',
            no_issues_str: str = 'NO_ISSUES',
            issues_str: str = 'ISSUES_FOUND',
            should_suggest_resolution: bool = True,
            detail="high"        
    ):
        """
        Generates sends image and prompt to AI for assessment.
        """
        prompt = self.create_prompt(
            image_data_uri, 
            text_width_inches, 
            fail_string, 
            no_issues_str, 
            issues_str, 
            should_suggest_resolution, 
            detail
        )
        
        response = client.responses.create(
            model=self.model,
            input=prompt
        )
        
        return response.output_text
    