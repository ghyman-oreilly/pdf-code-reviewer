from dotenv import load_dotenv
from pydantic import BaseModel
import openai
import os
import re
from typing import Union, List, Tuple

from pdf_reader import PDFPageImage

# load env variables from .env
load_dotenv()

# initialize client
api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)


class ProblematicCodeBlock(BaseModel):
    page_issue_num: int
    inches_from_top: Union[float, None] = None
    reformatting_suggestion: Union[str, None] = None


class PDFPageAnalysis(BaseModel):
    analysis_failed: Union[bool, None] = None
    page_has_issue: Union[bool, None] = None
    page_problematic_code_blocks: Union[List[ProblematicCodeBlock], List] = []


class PDFPageAnalyzer:
    def __init__(self, model="gpt-4.1"):
        self.model = model

    def _create_prompt(
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

        input_text += f"If there is not, please simply respond with:\n\nCONCLUSION: {no_issues_str}.\n\n"

        input_text += f"If there is, please respond: \n\nCONCLUSION: {issues_str}.\n\n" 
        
        input_text += "Then provide the height from the top of the page, in inches, of each code block with lines running beyond the text area, in this format:\n\n"

        input_text += "**ISSUE LOCATIONS**\nISSUE 1 LOCATION: N.N inches\nISSUE 2 LOCATION: N.N inches\netc.\n\n"
        
        input_text += f"You can use the page's text width as a reference measurement. It is {text_width_inches} inches wide.\n\n"

        if should_suggest_resolution:
            input_text += "If you are able to provide a reformatting suggestion for each problematic code block on the page, you should do so in this format:"

            input_text += "**ISSUE REFORMATTING**\nISSUE 1 REFORMATTED: [reformated code here]\nISSUE 2 REFORMATTED: [reformated code here]\netc.\n\n"

        input_text += "IMPORTANT: DO NOT PROVIDE ANY OTHER NOTES OR COMMENTARY.\n\n"

        input_text += f"If you are uncertain how to or unable to assess the image, respond:\n\nCONCLUSION: {fail_string}"
       
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

    def _call_ai_service(
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
        prompt = self._create_prompt(
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
        Call AI service for analysis of PDF page image,
        looking for long code lines, and transform
        result into useable data.
        """
        page_problematic_code_blocks = []
        
        raw_page_analysis = self._call_ai_service(
            image_data_uri, 
            text_width_inches, 
            fail_string, 
            no_issues_str, 
            issues_str, 
            should_suggest_resolution, 
            detail
        )

        if re.search(fail_string, raw_page_analysis, flags=re.I):
            # analysis failed
            return PDFPageAnalysis(analysis_failed=True)
        
        if not re.search(issues_str, raw_page_analysis, flags=re.I):
            # no page issue found
            """
            TODO: consider that this is a shortcut;
            should we just check for issue_locations 
            and issue_reformatting instead? maybe get
            some testing in and see how it goes
            """
            return PDFPageAnalysis(page_has_issue=False)

        # issue(s) found?
        issue_locations = re.findall(r'ISSUE\s+(\d+)\s+LOCATION:\s*(\d+\.?\d*)\s*inches', raw_page_analysis, flags=re.I)
        issue_reformatting_suggestions = re.findall(r'ISSUE\s+(\d+)\s+REFORMATTED:\s*(```.*?[^`]+```)', raw_page_analysis, flags=(re.I | re.DOTALL))
        
        if not issue_locations and not issue_reformatting_suggestions:
            # analysis failed
            return PDFPageAnalysis(analysis_failed=True)
        
        # combine data into tuples, one for each numbered issue
        locations_and_code_suggestions = self._combine_loc_and_formatting_tuples(issue_locations, issue_reformatting_suggestions)

        # prepare ProblematicCodeBlocks
        for location_and_code_suggestion in locations_and_code_suggestions:
            page_problematic_code_blocks.append(
                ProblematicCodeBlock(
                    page_issue_num=int(location_and_code_suggestion[0]),
                    inches_from_top=location_and_code_suggestion[1],
                    reformatting_suggestion=location_and_code_suggestion[2]
                )
            )
        
        return PDFPageAnalysis(
            page_has_issue=True,
            page_problematic_code_blocks=page_problematic_code_blocks
        )


    def _combine_loc_and_formatting_tuples(
            self,
            locations: Union[Tuple, None], 
            reformattings: Union[Tuple, None]
        ):
        """
        Combine location and code format suggestion tuples based
        on issue number.
        
        Args:
            locations: list[(issue_num, inches_from_top)] or None
            reformattings: list[(issue_num, reformatting)] or None
        Return:
            list[(issue_num, inches_from_tope, reformatting)]
        """
        # Handle None inputs
        locations = locations or []
        reformattings = reformattings or []
        
        # Create dictionaries keyed by the first element of each tuple
        loc_dict = dict(locations)
        ref_dict = dict(reformattings)
        
        # Get all unique keys
        all_keys = set(loc_dict.keys()) | set(ref_dict.keys())
        
        # Combine the pairs, using None for missing values
        result = []
        for key in all_keys:
            result.append((key, loc_dict.get(key), ref_dict.get(key)))
            
        return result



            




            


