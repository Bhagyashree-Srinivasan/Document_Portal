import sys
from pathlib import Path
import fitz
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from datetime import datetime, timezone
import uuid

class DocumentIngestion:
    """
    Handles saving, reading, and combining of PDFs for comparison with session-based versioning.
    """
    def __init__(self, base_dir: str = "data/document_comparison", session_id=None):
        self.log = CustomLogger().get_logger(__name__)
        self.base_dir = Path(base_dir)
        self.session_id = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.session_path = self.base_dir / self.session_id
        self.session_path.mkdir(parents=True, exist_ok=True)

        self.log.info("DocumentIngestion initialized", session_path=str(self.session_path))

    def save_uploaded_files(self, reference_file, actual_file):
        """
        Saves uploaded files to the specified directory.
        """
        try:

            ref_path = self.session_path/ reference_file.name
            actual_path = self.session_path/ actual_file.name

            if not reference_file.name.lower().endswith('.pdf') or not actual_file.name.lower().endswith('.pdf'):
                raise ValueError("Only PDF files are allowed.")
            
            with open(ref_path, 'wb') as f:
                f.write(reference_file.get_buffer())

            with open(actual_path, 'wb') as f:
                f.write(actual_file.get_buffer())

            self.log.info("Files saved successfully", reference = str(ref_path), actual= str(actual_path),
                          session = self.session_id)
            return ref_path, actual_path
        except Exception as e:
            self.log.error(f"Error saving uploaded file: {str(e)}")
            raise DocumentPortalException("Error while saving uploaded files.", sys)

    def read_pdf(self, pdf_path: Path) -> str:
        """
        Reads a PDF file and extracts text from each page.
        """
        try:
            with fitz.open(pdf_path) as doc:
                if doc.is_encrypted:
                    raise ValueError("PDF is encrypted and cannot be read.", pdf_path.name)
                all_text = []
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    text = page.get_text() #type: ignore

                    if text.strip():
                        all_text.append(f"\n --- Page {page_num+1} --- \n{text.strip()}")

            self.log.info("Successfully read PDF", file = str(pdf_path), pages = len(all_text))
            return "\n".join(all_text)
        except Exception as e:
            self.log.error(f"Error reading PDF: {str(e)}")
            raise DocumentPortalException("Error while reading PDF.", sys)
        
    def combine_documents(self) -> str:
        """
        Combines the content of all PDF documents in the session folder into a single string.
        """
        try:
            doc_parts  = []

            for file in sorted(self.session_path.iterdir()):
                if file.is_file() and file.suffix.lower() == '.pdf':
                    content = self.read_pdf(file)
                    doc_parts.append(f"Document: {file.name}\n{content}")

            combined_text = "\n\n".join(doc_parts)
            self.log.info("Documents combined successfully", count=len(doc_parts), session=str(self.session_id))
            return combined_text
        except Exception as e:
            self.log.error(f"Error combining documents: {str(e)}")
            raise DocumentPortalException("Error while combining documents.", sys)
        
    def clean_old_sessions(self, keep_latest: int = 3):
        """
        Cleans up old session directories, keeping only the latest N sessions.
        """
        try:
            sessions_folders = sorted(
                [f for f in self.base_dir.iterdir() if f.is_dir()],
                reverse = True
            )
            for folder in sessions_folders[keep_latest:]:
                for file in folder.iterdir():
                    file.unlink()
                folder.rmdir()
                self.log.info("Old session cleaned up", path=str(folder))
        
        except Exception as e:
            self.log.error(f"Error cleaning old sessions: {str(e)}")
            raise DocumentPortalException("Error while cleaning old sessions.", sys)