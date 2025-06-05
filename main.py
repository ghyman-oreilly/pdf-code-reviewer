import click
from pathlib import Path
import shutil
import tempfile
from typing import List, Union

from image_analyzer import PDFPageAnalyzer, PDFPageAnalysis
from helpers import get_data_uri_for_image
from pdf_reader import pdf_to_images


@click.group()
def cli():
    pass

@cli.command(help="""
Arguments:
  pdf_path: Path to the PDF file.
""")
@click.argument("pdf_path")
def start(pdf_path):

    if not pdf_path:
        raise click.UsageError('`pdf_path` argument is required.')
    
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file() or pdf_path.suffix.lower() != '.pdf':
        raise ValueError('`pdf_path` must be a valid path to a PDF file.')    
    
    text_width_inches: float = 4.8 # TODO: make configurable (via menu?)
    should_suggest_resolution = True # TODO: make configurable

    # Create a temporary directory that will be cleaned up when the system restarts
    temp_dir = tempfile.mkdtemp(prefix='pdf_images_')
    
    click.echo(f"Extracting pages and data from PDF at {pdf_path}...")

    # Generate images from PDF
    try:
        page_images = pdf_to_images(pdf_path, temp_dir)
    except Exception as e:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            click.echo(f"Unable to remove temporary images at {temp_dir}")
        raise e

    click.echo(f"Sending {len(page_images)} pages to AI service for analysis...")

    page_analyses: Union[List[PDFPageAnalysis], List] = []

    # process page_images
    for i, page_image in enumerate(page_images):

        click.echo(f"Processing page {i+1} of {len(page_images)}...")

        # enrich page_image with base64_string (lazy loaded)
        image_filepath = page_image.image_filepath
        image_data_uri = get_data_uri_for_image(image_filepath)

        # send images to ai_service and prompt, return responses
        pdf_page_analyzer = PDFPageAnalyzer()
        page_analysis = pdf_page_analyzer.assess_image(
            image_data_uri=image_data_uri, 
            text_width_inches=text_width_inches, 
            should_suggest_resolution=should_suggest_resolution, 
        )

        if page_analysis:
            page_analyses.append(page_analysis)
    
    # TODO: write back to copy of PDF or, optionally, txt (or csv?)

    # clean up temp_dir recursively at the end
    shutil.rmtree(temp_dir)



if __name__ == '__main__':
    cli()
