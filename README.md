# PDF Code Reviewer

A script that identifies and flags lengthy code lines in a PDF, with an option for providing AI-generated reformatting suggestions.

## Requirements

* Python 3.9+
* OpenAI API key (if opting for reformatting suggestions)

## Setup

1. Clone the repository or download the source files:

	```bash
	git clone git@github.com:ghyman-oreilly/pdf-code-reviewer.git
	
	cd pdf-code-reviewer
	```

2. Install required dependencies:

	```bash
	pip install -r requirements.txt
	```

3. Create an `.env` file in the project directory to store your OpenAI key:

	```bash
	echo "OPENAI_API_KEY=your-key-here" >> .env
	```

## Usage

First, build a PDF using the code-eyeballer CSS to highlight blocks of code yellow. This script will not work with PDFs that don't have the code-eyeballer CSS enabled.

Then, to flag code blocks with lines that run outside the allocated text area, run the following command:

```bash
python main.py <path_to_pdf_file>
```

The script will output a copy of your PDF file with comment annotations flagging problematic code blocks, as well as a JSON data file (see Options for usage).

## Options

Several options are available for use with the main command:

* `--get-formatting-suggestions`, `-c`: Get an AI-generated formatting suggestion for each problematic code block. These are included in the comment annotations added to the PDF.

* `--load-from-json`, `-l`: Use this flag to provide the filepath to a JSON file containing data from a previous session. This can, for example, allow you to create a new annotated PDF copy, or output all your data to text file (see the next option), without having to send your PDF data to the AI service again.  

* `--text-file-output`, `-t`: Instead of outputting an annotated PDF, output a text file of the problematic code blocks and suggested reformats, as applicable. This option is offered in case you need a different format for reviewing or sharing the suggested reformatted code.
