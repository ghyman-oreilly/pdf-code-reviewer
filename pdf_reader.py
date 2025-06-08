import fitz
import os
from typing import List, Union, Optional
from pathlib import Path
from pydantic import BaseModel


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

    # List to store minimum text block x0 on each page,
    # for determining x1 threshold for code lines
    min_x0s = []

    # Convert each page to an image
    for page_num in range(len(pdf_document)):
        # Get the page
        page = pdf_document[page_num]

    x0s = []
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip():  # non-empty
                    x0s.append(span["bbox"][0])  # raw x0 without rounding
    if x0s:
        min_x0s.append(min(x0s))

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
