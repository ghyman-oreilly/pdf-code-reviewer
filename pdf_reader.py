import fitz
import logging
from typing import Union, Optional
from pathlib import Path
from pydantic import BaseModel


# init logger
logger = logging.getLogger(__name__)


class Rectangle(BaseModel):
    x0: float # left edge (min x)
    x1: float # right edge (max x)
    y0: float # top edge (min y)
    y1: float # bottom edge (max y)

    def as_fitz_rect(self):
        import fitz
        return fitz.Rect(self.x0, self.y0, self.x1, self.y1)

    @classmethod
    def from_fitz_rect(cls, rect):
        return cls(x0=rect.x0, x1=rect.x1, y0=rect.y0, y1=rect.y1)

    def width(self):
        return self.x1 - self.x0

    def height(self):
        return self.y1 - self.y0


class ProblemCodeBlock(BaseModel):
    allotted_rect: Rectangle
    full_text_rect: Rectangle
    full_text: str
    font_size: Union[float, None] = None
    suggested_reformat: Union[str, None] = None

    @property
    def chars_fit(self) -> Optional[int]:
        if not self.font_size:
            return None
        char_width_factor = 0.5 # estimated width as percentage of point size
        est_char_width = self.font_size * char_width_factor
        return int(self.allotted_rect.width() // est_char_width)

class ProblemPDFPage(BaseModel):
    filepath: Union[str, Path]
    page_num: int
    problem_code_blocks: list[ProblemCodeBlock]


def read_pdf(pdf_path: Union[str, Path]):

    pages_w_problematic_code: Union[list[ProblemPDFPage], list] = []
    
    doc = fitz.open(pdf_path)

    code_eyeballer_found = False

    for page_num, page in enumerate(doc):
       
        problematic_code_on_page: Union[list[ProblemCodeBlock], list] = []

        page_width = page.rect.width

        yellow_rects = []
        
        for d in page.get_drawings():
            # type if fill or rect and is yellow
            if (d['type'] == 'f' or d['type'] == 'rect') and is_yellow(d.get('fill')):
                yellow_rects.append(d['rect'])

        if yellow_rects:
            code_eyeballer_found = True

        for yrect in yellow_rects:
            font_size = None
            
            check_rect = fitz.Rect(yrect) 
            check_rect.x1 = page_width # expand to right edge

            # Get original clipped text and right-check expanded text
            # TODO: can use an edge tolerance on text_strict here 
            # (+= 2.0 [pixels], say) if adjustment to sensitivity is needed)
            text_strict = page.get_textbox(yrect).strip()
            text_check = page.get_textbox(check_rect).strip()

            if text_strict != text_check:

                # Expand yrect's right side to the page edge
                extended_rect = fitz.Rect(yrect)
                extended_rect.x1 = page_width  # full to right margin

                # Get full text from extended rectangle
                text_full = page.get_textbox(extended_rect).strip()

                # Get detailed text layout to extract font size
                text_dict = page.get_text("dict")
                for block in text_dict["blocks"]:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_rect = fitz.Rect(span["bbox"])
                            if span_rect.intersects(extended_rect):
                                font_size = span.get("size")
                                break
                        if font_size:
                            break
                    if font_size:
                        break

                problematic_code_on_page.append(
                    ProblemCodeBlock(
                        allotted_rect=Rectangle.from_fitz_rect(yrect),
                        full_text_rect=Rectangle.from_fitz_rect(extended_rect),
                        full_text=text_full,
                        font_size=(font_size or None)
                    )
                )
        
        if problematic_code_on_page:
            pages_w_problematic_code.append(
                ProblemPDFPage(
                    filepath=pdf_path,
                    page_num=page_num,
                    problem_code_blocks=problematic_code_on_page
                )
            )
    
    if not code_eyeballer_found:
        logger.warning("No code-eyeballer boxes found in PDF. Please make sure code-eyeballer CSS has been used.")

    return pages_w_problematic_code


def is_yellow(color, tolerance=0.05):
    if not color: return False
    r, g, b = color
    return abs(r - 1.0) < tolerance and abs(g - 1.0) < tolerance and b < tolerance

