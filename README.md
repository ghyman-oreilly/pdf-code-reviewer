# Lengthy Code Lines Finder

Tool for identifying and flagging lengthy lines of code in a PDF.

# TODO
* main: cli
* ~~pdf_reader: split pdf into images, map images to PDF pages~~
* ~~ai_service: analyze images, flagging instances of long code lines and providing coord in inches, problematic code, and reformatting suggestion~~
* ~~ai_service: translate response into a useful data structure~~
* ~~pdf_writer: write annotations back to pdf copy~~
* pdf_writer: optional txt output
* page size menu

* Options:
	* optionally exclude suggestions from pdf comments if loading from JSON file that includes them?
	* write annotations for failed page analyses?




# Options
* code-eyeballer PDF or standard (codeballer may be helpful for finding problematic code in notes, etc.)
* return code reformatting suggestions or do not
* output txt or csv instead of annotated pdf?
* pdf trim size --> default to most common, then have user select from menu if overriding (used in providing text width as reference measurement for ai service)
