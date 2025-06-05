import fitz
import logging
from pathlib import Path
from typing import List, Union

from image_analyzer import PDFPageAnalysis


logger = logging.getLogger(__name__)


def write_page_analyses_to_pdf(
		page_analyses: List[PDFPageAnalysis], 
		original_pdf_filepath: Union[str, Path],
		annotate_failed_analyses: bool = False,
		inches_from_left: float = None, # inches from left of pdf page for locating annotation
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
		page_analysis = next(iter([pa for pa in page_analyses if pa.page_num == page_num]), None)

		if not page_analysis:
			continue

		if page_analysis.analysis_failed:
			if not annotate_failed_analyses:
				logger.warning(f"Analysis failed on PDF p. {page_num + 1} (absolute doc page number).")
			else:
				add_text_annotation_to_page(
					page=page,
					annotation_text="PROD: Page analysis failed.",
				)
			continue
		elif not page_analysis.page_has_issue:
			logger.info(f"No issues found on PDF p. {page_num + 1} (absolute doc page number).")
			continue
		
		for page_issue in page_analysis.page_problematic_code_blocks:
			inches_from_top = page_issue.inches_from_top or None
		
			annotation_text = f"Code running into margin.\n\n{'AI-generated reformatting suggestion:\n\n' + page_issue.reformatting_suggestion if should_suggest_resolution and page_issue.reformatting_suggestion else ''}"

			add_text_annotation_to_page(
				page=page,
				annotation_text=annotation_text,
				inches_from_left=inches_from_left,
				inches_from_top=inches_from_top
			)
	
	return doc

		
def add_text_annotation_to_page(
	page, # pymupdf representation of pdf page
	annotation_text: str,
	inches_from_left: Union[float, None] = None,
	inches_from_top: Union[float, None] = None
):
	try:
		page_rect = page.rect
	except Exception as e:
		logger.error(f"Unable to obtain rect from page. {e}")
		return None

	if not annotation_text:
		return None

	page_width = page_rect.width

	if inches_from_left*72 > page_width:
		logger.error(f"Invalid value for `inches_from_left`: {inches_from_left}. Must be less than {page_width*72}. Falling back to default.")
		inches_from_left = None

	if not inches_from_top:
		if not inches_from_left:
			point = (page_width - 72, 72) # 1 inch from right, 1 inch from top
		else:
			point = (inches_from_left/72, 72)
	else:
		if not inches_from_left:
			inches_from_left = (page_width - 72)/72 # fallback/default inches from left
		try:
			point = (inches_from_left*72, inches_from_top*72) # point in inches to points
		except Exception as e:
			logger.error(f"Unable to calculate location for annotation on p. {page.page_num + 1} (absolute page num). {e}")
			return None
	
	annot = page.add_text_annot(
		point,
		annotation_text
	)
	annot.set_info(title="PDF Analysis Script")
	annot.update()


def write_page_analyses_to_text():
	"""
	Write page analyses to text.
	"""
	pass