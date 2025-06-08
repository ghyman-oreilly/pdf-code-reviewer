import fitz
import logging
from pathlib import Path
from typing import List, Union, Tuple

from pdf_reader import ProblemPDFPage


logger = logging.getLogger(__name__)


def write_code_annotations_to_pdf(
        pages_w_problematic_code: List[ProblemPDFPage], 
        original_pdf_filepath: Union[str, Path],
        should_suggest_resolution: bool = False
    ):
    """
    Create a copy of input PDF with annotations
    at the locations of found issues.

    Returns a pymupdf representation of annotated doc.
    """
    doc = fitz.open(original_pdf_filepath)

    for page_num in range(doc.page_count):
        page = doc[page_num]

        # get first matching page_analysis (there should be 1 or none)
        problem_page = next(iter([p for p in pages_w_problematic_code if p.page_num == page_num]), None)

        if not problem_page:
            continue

        for problem_block in problem_page.problem_code_blocks:		
            suggested_reformat = problem_block.suggested_reformat
            annotation_point = (problem_block.allotted_rect.x1, problem_block.allotted_rect.y0)

            if should_suggest_resolution and suggested_reformat:
                annotation_text = f"Code running into margin.\n\nAI-generated reformatting suggestion:\n\n {problem_block.suggested_reformat}"
            else:
                annotation_text = "Code running into margin."

            add_text_annotation_to_page(
                page=page,
                annotation_text=annotation_text,
                annotation_point=annotation_point
            )
    
    return doc

        
def add_text_annotation_to_page(
    page,  # PyMuPDF page
    annotation_text: str,
    annotation_point: Tuple[float, float]
):
    try:
        page_rect = page.rect
    except Exception as e:
        logger.error(f"Unable to obtain rect from page. {e}")
        return None
    
    if not annotation_text or not annotation_point:
        return None
    
    if not page_rect.contains(fitz.Point(annotation_point)):
        logger.error(f"Annotation point {annotation_point} is outside the page bounds.")
        return None
    
    try:
        annot = page.add_text_annot(annotation_point, annotation_text)
        annot.set_info(title="PDF Analysis Script")
        annot.update()
        return annot
    except Exception as e:
        logger.error(f"Error adding annotation: {e}")
        return None


def generate_text_lines_from_problem_pages(
        pages_w_problematic_code: list[ProblemPDFPage]
    ):
    text_lines = []

    if not pages_w_problematic_code:
        return []

    for page in pages_w_problematic_code:
        page_num = page.page_num + 1 # human-friendly numbering
        num_blocks = len(page.problem_code_blocks)
        text_lines.append(f"********** START PDF Page {page_num} (absolute page) **********\n\n")
        blocks = page.problem_code_blocks
        for i, block in enumerate(blocks):
            # add code block existing text
            text_lines.append(f"***** START Problematic Code Block {i+1} of {num_blocks} *****\n")
            text_lines.append(block.full_text)
            text_lines.append("\n")
            text_lines.append(f"***** END Problematic Code Block {i+1} of {num_blocks} *****\n\n")

            # add code block suggested text
            suggested_text = block.suggested_reformat
            if suggested_text:
                text_lines.append(f"***** START Suggested Code Block {i+1} of {num_blocks} *****\n")
                text_lines.append(suggested_text)
                text_lines.append("\n")
                text_lines.append(f"***** END Suggested Code Block {i+1} of {num_blocks} *****\n\n")
        text_lines.append(f"********** END PDF Page {page_num} (absolute page) **********\n\n")
    
    return text_lines
