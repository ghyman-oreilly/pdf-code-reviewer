import fitz
import os
from typing import List, Union, Optional
from pathlib import Path
from pydantic import BaseModel


class PDFPage(BaseModel):
    pass


class ProblemCodeBlock(BaseModel):
    pass


# Tolerance in points for right edge matching
EDGE_TOLERANCE = 2.0  # points


def read_pdf(pdf_path: Union[str, Path]):

    pages_w_problematic_code: Union[list[PDFPage], list] = []
    
    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc):
       
        page_width = page.rect.width

        yellow_rects = []
        
        for d in page.get_drawings():
            # type if fill or rect and is yellow
            if (d['type'] == 'f' or d['type'] == 'rect') and is_yellow(d.get('fill')):
                yellow_rects.append(d['rect'])

        for idx, yrect in enumerate(yellow_rects):
            check_rect = fitz.Rect(yrect)
            check_rect.x1 += EDGE_TOLERANCE

            # Get original clipped text and right-check expanded text
            text_strict = page.get_textbox(yrect).strip()
            text_check = page.get_textbox(check_rect).strip()

            if text_strict != text_check:
                print(f"⚠️ Overflow detected on p. {page_num},  yellow box #{idx+1} at {yrect}.")

                # Step 3: Expand yrect's right side to the page edge
                extended_rect = fitz.Rect(yrect)
                extended_rect.x1 = page_width  # full to right margin

                # Step 4: Get full text from extended rectangle
                text_full = page.get_textbox(extended_rect).strip()

                print("📌 Full text from extended box:")
                print("—" * 40)
                print(text_full)
                print("—" * 40)



def is_yellow(color, tolerance=0.05):
    if not color: return False
    r, g, b = color
    return abs(r - 1.0) < tolerance and abs(g - 1.0) < tolerance and b < tolerance

class PDFPageImage(BaseModel):
    image_filepath: Union[str, Path, None]
    pdf_page: int
    page_width_inches: float


def pdf_to_images(
        pdf_path: Union[str, Path], 
        temp_dir: Union[str, Path],
        generate_image_files: bool = True
    ) -> List[PDFPageImage]:
    """
    Convert PDF pages to images and store them in temporary files.
    
    Args:
        pdf_path: Path to the PDF file
        temp_dir: Directory to save images files at
        generate_image_files: use False if loading page analyses from JSON file (default True)
    
    Returns:
        List of PDFImage instances 
    """
    page_images: List[PDFPageImage] = []
    
    # Open the PDF
    pdf_document = fitz.open(pdf_path)
            
    # Convert each page to an image
    for page_num in range(len(pdf_document)):
        # Get the page
        page = pdf_document[page_num]

        # Get page width in inches
        width = page.rect.width / 72.0

        if generate_image_files:

            # Get the page's pixmap (image)
            pix = page.get_pixmap()
            
            # Create a temporary file path for this image
            temp_image_path = os.path.join(temp_dir, f"page_{page_num}.png")
            
            # Save the image
            pix.save(temp_image_path)
        
            # Create PDFPageImage instance
            page_image = PDFPageImage(
                image_filepath = temp_image_path,
                pdf_page = page_num,
                page_width_inches = width
            )
        else:
            # Create PDFPageImage instance
            page_image = PDFPageImage(
                image_filepath = None,
                pdf_page = page_num,
                page_width_inches = width
            )

        page_images.append(page_image)

    return page_images