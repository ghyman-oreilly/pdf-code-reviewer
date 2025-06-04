import base64
import mimetypes
from pathlib import Path
from typing import Union


def get_mimetype(filepath: Union[str, Path]) -> str:
    """
    Return mimetype string for given filepath (Posix Path).
    """
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type is None:
        raise ValueError(f"Could not determine MIME type for file: {filepath}")
   
    return mime_type


def get_data_uri_for_image(filepath: Union[str, Path]) -> str:
    """
    Read an image file and return a base64-encoded string.
    
    Args:
        filepath (Union[str, Path]): Path to the image file
    
    Returns:
        str: Complete data URI (format: data:<mimetype>;base64,<encoded-data>)
    """
    with open(filepath, "rb") as image_file:
        encoded_bytes = base64.b64encode(image_file.read())
        data_uri = f"data:{get_mimetype(filepath)};base64,{encoded_bytes.decode("utf-8")}"
        return data_uri
    