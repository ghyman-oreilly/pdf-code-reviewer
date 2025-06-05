import click
import json
from pathlib import Path
import shutil
import tempfile
import time
from typing import List, Union

from image_analyzer import PDFPageAnalyzer, PDFPageAnalysis, generate_page_analyses_from_file
from helpers import get_data_uri_for_image
from pdf_reader import pdf_to_images
from pdf_writer import write_page_analyses_to_pdf


@click.group()
def cli():
    pass

@cli.command(help="""
Arguments:
  pdf_path: Path to the PDF file.
""")
@click.argument("pdf_path")
@click.option(
    "--existing-page-analyses-json", 
    "-e", 
    help="Provide the filepath of a JSON file of page analyses to annotate your PDF with."
    )
def start(pdf_path, existing_page_analyses_json=None):

    generate_image_files = True # we'll set to false if JSON being passed in

    if not pdf_path:
        raise click.UsageError('`pdf_path` argument is required.')
    
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file() or pdf_path.suffix.lower() != '.pdf':
        raise ValueError('`pdf_path` must be a valid path to a PDF file.')    
    
    if existing_page_analyses_json:
        existing_page_analyses_json = Path(existing_page_analyses_json)
        generate_image_files = False
        if not existing_page_analyses_json.is_file() or existing_page_analyses_json.suffix.lower() != '.json':
            raise ValueError('`--use-existing-page-analyses` option requires valid path to a JSON file.')  

    output_dir = pdf_path.parent
    output_pdf_path = output_dir / f"{pdf_path.stem}_{int(time.time())}.pdf"

    annotation_inches_from_left = 6.0 # TODO make configurable
    text_width_inches: float = 4.8 # TODO: make configurable (via menu?)
    should_suggest_resolution = True # TODO: make configurable

    # Create a temporary directory that will be cleaned up when the system restarts
    temp_dir = tempfile.mkdtemp(prefix='pdf_images_')
    
    click.echo(f"Extracting pages and data from PDF at {pdf_path}...")

    # Generate images from PDF
    try:
        page_images = pdf_to_images(pdf_path, temp_dir, generate_image_files=generate_image_files)
    except Exception as e:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            click.echo(f"Unable to remove temporary images at {temp_dir}")
        raise e

    if not existing_page_analyses_json:
        click.echo(f"Sending {len(page_images)} pages to AI service for analysis...")

        page_analyses: Union[List[PDFPageAnalysis], List] = []

        # process page_images
        for i, page_image in enumerate(page_images):

            click.echo(f"Processing page {i+1} of {len(page_images)}...")

            page_num = page_image.pdf_page

            # enrich page_image with base64_string (lazy loaded)
            image_filepath = page_image.image_filepath
            image_data_uri = get_data_uri_for_image(image_filepath)

            # send images to ai_service and prompt, return responses
            pdf_page_analyzer = PDFPageAnalyzer()
            page_analysis = pdf_page_analyzer.assess_image(
                page_num=page_num,
                image_data_uri=image_data_uri, 
                text_width_inches=text_width_inches, 
                should_suggest_resolution=should_suggest_resolution, 
            )
            if page_analysis:
                page_analyses.append(page_analysis)

            
        if page_analyses:
            # write analyses to file in case user wants to reload in future
            # e.g., user needs a new annotated PDF and doesn't want to rerun analysis service
            analyses_save_filepath = output_dir / f"page_analyses_backup_{int(time.time())}.json"
            with open(str(analyses_save_filepath), 'w') as f:
                json.dump([pa.model_dump() for pa in page_analyses], f)
            click.echo(f"Raw page analyses (JSON format) backed up at {analyses_save_filepath}")
    else:
        page_analyses: List[PDFPageAnalysis] = generate_page_analyses_from_file(existing_page_analyses_json)
    
    click.echo("Writing annotations to PDF...")

    # generate annotated PDF representation and write to file
    annotated_pdf = write_page_analyses_to_pdf(
		page_analyses=page_analyses, 
		original_pdf_filepath=pdf_path,
		annotate_failed_analyses=False,
		inches_from_left=annotation_inches_from_left,
		should_suggest_resolution=should_suggest_resolution
	)
    annotated_pdf.save(output_pdf_path)
    annotated_pdf.close()
    click.echo(f"Annotated PDF written to {output_pdf_path}")

    # TODO: optionally write back txt (or csv?)
    # TODO: option to include annotation for failed page analyses in output PDF

    # clean up temp_dir recursively at the end
    shutil.rmtree(temp_dir)



if __name__ == '__main__':
    cli()
