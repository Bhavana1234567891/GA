import re
from pathlib import Path

import fitz  # PyMuPDF

from config.settings import (
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS
)


class PDFLoader:
    """
    Handles PDF validation, text extraction,
    cleaning and loading.
    """

    def validate_pdf(self, pdf_path: str) -> Path:
        """
        Validate the PDF before processing.
        """

        pdf_path = Path(pdf_path)

        # Check if file exists
        if not pdf_path.exists():
            raise FileNotFoundError(
                f"File not found: {pdf_path}"
            )

        # Check extension
        if pdf_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                "Only PDF files are supported."
            )

        # Check file size
        file_size = pdf_path.stat().st_size

        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"PDF size should be less than {MAX_FILE_SIZE_BYTES/(1024*1024)} MB."
            )

        return pdf_path

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from every page of the PDF.
        """

        try:

            document = fitz.open(pdf_path)

            text = ""

            for page in document:

                page_text = page.get_text()

                if page_text.strip():

                    text += page_text + "\n"

            document.close()

            return text

        except Exception as error:

            raise RuntimeError(
                f"Unable to read PDF.\n{error}"
            )

    def clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        """

        # Remove non printable characters
        text = "".join(
            char
            for char in text
            if char.isprintable() or char == "\n"
        )

        # Replace multiple spaces with single space
        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # Remove multiple blank lines
        text = re.sub(
            r"\n\s*\n+",
            "\n\n",
            text
        )

        return text.strip()

    def load_pdf(self, pdf_path: str) -> str:
        """
        Complete PDF processing pipeline.
        """

        validated_path = self.validate_pdf(
            pdf_path
        )

        extracted_text = self.extract_text(
            validated_path
        )

        cleaned_text = self.clean_text(
            extracted_text
        )

        if not cleaned_text:

            raise ValueError(
                "No readable text found in PDF."
            )

        return cleaned_text