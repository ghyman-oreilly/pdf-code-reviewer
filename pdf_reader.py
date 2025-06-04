import fitz
import os
from typing import List, Union, Optional
from pathlib import Path
from pydantic import BaseModel


class PDFPageImage(BaseModel):
    image_filepath: Union[str, Path]
    pdf_page: int
    page_width_inches: float


def pdf_to_images(pdf_path: Union[str, Path], temp_dir: Union[str, Path]) -> List[PDFPageImage]:
    """
    Convert PDF pages to images and store them in temporary files.
    
    Args:
        pdf_path: Path to the PDF file
    
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
                    
        # Get the page's pixmap (image)
        pix = page.get_pixmap()
        
        # Get page width in inches
        width = page.rect.width / 72.0
        
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

        page_images.append(page_image)

    return page_images
