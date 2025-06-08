import click
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import List, Union

from ai_service import AIServiceCaller
from pdf_reader import read_pdf, ProblemPDFPage
from pdf_writer import write_code_annotations_to_pdf


@click.group()
def cli():
    pass

@cli.command(help="""
Arguments:
  pdf_path: Path to the PDF file.
""")
@click.argument("pdf_path")
@click.option(
    "--get-formatting-suggestions", 
    "-c", 
    is_flag=True,
    help="Send problematic code text to AI service for reformatting suggestions."
    )
@click.option(
    "--load-from-json", 
    "-l", 
    help="Load code block data and formatting suggestions from JSON file."
    )
def check_pdf_code(pdf_path, get_formatting_suggestions=False, load_from_json=None):
    """
    Check PDF for code blocks with long lines, and annotate
    PDF copy to flag said blocks.
    """
    if not pdf_path:
        raise click.UsageError('`pdf_path` argument is required.')
    
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file() or pdf_path.suffix.lower() != '.pdf':
        raise ValueError('`pdf_path` must be a valid path to a PDF file.')    
    
    if load_from_json:
        json_input_path = Path(load_from_json)
        if not json_input_path.is_file() or json_input_path.suffix.lower() != '.json':
            raise ValueError('`--load-from-json` option requires a valid path to a JSON file.')    
    elif not click.prompt("Script requires a PDF with yellow code-eyeballer blocks. Do you wish to continue? (y/n)").strip().lower() in ['y', 'yes']: 
        click.echo("Exiting...")
        sys.exit(0)
    else:
        json_input_path = None

    output_dir = pdf_path.parent
    output_pdf_path = output_dir / f"{pdf_path.stem}_{int(time.time())}.pdf"
  
    click.echo(f"Extracting data from PDF at {pdf_path}...")

    if not load_from_json or not json_input_path:
        # Get pages with problematic code blocks
        pages_w_problematic_code = read_pdf(pdf_path)

        if pages_w_problematic_code:
            if get_formatting_suggestions:
                service_caller = AIServiceCaller()
                click.echo(f"Sending data to AI service for analysis...")

                for i, page in enumerate(pages_w_problematic_code):

                    for j, block in enumerate(page.problem_code_blocks):

                        click.echo(f"Processing problematic code block {j+1} of {len(page.problem_code_blocks)} on page {i+1} of {len(pages_w_problematic_code)} with problem code blocks...")

                        fail_str = 'UNABLE_TO_ASSESS'

                        # TODO: should we ask just for the offending lines?

                        prompt_content = ''.join([
                            "Please reformat this code block, following the standard conventions ",
                            "of the programming language shown, so that no line is longer than ",
                            f"{block.chars_fit} characters, including spaces:\n\n",
                            "```\n",
                            f"{block.full_text}"
                            "```\n",
                            "If you're unable to correctly reformat the code, ",
                            f"please simply respond with: {fail_str}\n\n",
                            f"In your reponse, please provide ONLY the reformatted code or {fail_str}.\n\n",
                            "Do NOT provide any notes or commentary."
                        ])

                        # call AI service
                        response = service_caller.call_ai_service(
                            service_caller.create_prompt(prompt_content)
                        )

                        # add response to block
                        if response:
                            response = response.strip()
                            if not fail_str in response:
                                block.suggested_reformat = response
                
            # write analyses to file in case user wants to reload in future
            # e.g., user needs a new annotated PDF and doesn't want to rerun AI service
            page_data_save_filepath = output_dir / f"page_data_backup_{int(time.time())}.json"
            with open(str(page_data_save_filepath), 'w') as f:
                json.dump([p.model_dump(mode="json") for p in pages_w_problematic_code], f)
            click.echo(f"Raw page data (JSON format) backed up at {page_data_save_filepath}")

    else:
        # load code block and suggestions data from JSON
        with open(json_input_path, "r") as f:
            pages_data = json.load(f)       
        pages_w_problematic_code = [ProblemPDFPage.model_validate(p) for p in pages_data]

    if pages_w_problematic_code:
        # generate annotated PDF representation and write to file
        click.echo("Writing annotations to PDF...")
        annotated_pdf = write_code_annotations_to_pdf(
            pages_w_problematic_code=pages_w_problematic_code, 
            original_pdf_filepath=pdf_path,
            should_suggest_resolution=(get_formatting_suggestions or load_from_json)
        )
        annotated_pdf.save(output_pdf_path)
        annotated_pdf.close()
        click.echo(f"Annotated PDF written to {output_pdf_path}")
    else:
        click.echo("No problematic code blocks found.")

    # TODO: optionally write back txt (or csv?)


if __name__ == '__main__':
    cli()
