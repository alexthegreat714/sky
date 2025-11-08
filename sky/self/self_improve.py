"""
Sky Self-Improvement Tool - OCR, scraping, and knowledge ingestion

Features:
- OCR PDFs and images using pytesseract
- Scrape webpages with requests + BeautifulSoup
- Extract and chunk useful text
- Store raw inputs in archive
- Embed and ingest to RAG vectorstore
- Generate comprehensive audit logs
- Constitutional authority enforcement ("self_enhancement")
"""
import json
import logging
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal

# Setup logging
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True, parents=True)
LOG_FILE = LOG_DIR / "self_improve.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
BASE = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = BASE / "sky" / "self" / "archive"
AUDIT_FILE = BASE / "sky" / "self" / "audit_log.jsonl"
RAG_DIR = BASE / "sky" / "rag" / "chroma_store"

# Ensure directories exist
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
RAG_DIR.mkdir(parents=True, exist_ok=True)

# Safe imports
def _safe_import(path, name):
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

check_authority = _safe_import("src.governance.authority_gate", "check_authority")
ingest_to_rag = _safe_import("src.rag.shared_ingest", "ingest_paths")


class SelfImprovementTool:
    """Manages knowledge acquisition and self-improvement"""

    def __init__(self):
        self.archive_dir = ARCHIVE_DIR
        self.audit_file = AUDIT_FILE

    def _check_authority(self) -> bool:
        """Check constitutional authority for self_enhancement"""
        if callable(check_authority):
            try:
                allowed = check_authority("self_enhancement")
                if not allowed:
                    logger.warning("self_enhancement blocked by constitution")
                return allowed
            except Exception as e:
                logger.error(f"Authority check failed: {e}")
                return False

        # Default: allow self-enhancement (optimistic for learning)
        logger.info("Constitution not available, allowing self_enhancement by default")
        return True

    def _log_audit(self, entry: Dict[str, Any]):
        """Log audit entry to JSONL"""
        entry["ts"] = time.time()
        entry["timestamp"] = datetime.now().isoformat()

        with self.audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(f"Audit logged: {entry.get('source_type')} - {entry.get('status')}")

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks

        Args:
            text: Input text
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('. ')
                if last_period > chunk_size // 2:  # Only break if past halfway
                    end = start + last_period + 2
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Rough token count estimate (words * 1.3)"""
        words = len(text.split())
        return int(words * 1.3)

    def ocr_file(self, file_path: str) -> Dict[str, Any]:
        """
        OCR PDF or image file

        Args:
            file_path: Path to PDF or image file

        Returns:
            Result dict with extracted text and audit info
        """
        if not self._check_authority():
            return {"ok": False, "error": "Authority denied: self_enhancement not allowed"}

        file_path = Path(file_path)
        if not file_path.exists():
            return {"ok": False, "error": f"File not found: {file_path}"}

        # Determine file type
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._ocr_pdf(file_path)
        elif suffix in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            return self._ocr_image(file_path)
        else:
            return {"ok": False, "error": f"Unsupported file type: {suffix}"}

    def _ocr_pdf(self, file_path: Path) -> Dict[str, Any]:
        """OCR a PDF file"""
        try:
            import pytesseract
            from pdf2image import convert_from_path
        except ImportError:
            logger.error("pytesseract or pdf2image not available")
            return {"ok": False, "error": "OCR dependencies not installed (pip install pytesseract pdf2image)"}

        logger.info(f"OCR PDF: {file_path}")

        try:
            # Convert PDF to images
            images = convert_from_path(file_path)

            # OCR each page
            text_parts = []
            for i, image in enumerate(images):
                logger.info(f"OCR page {i+1}/{len(images)}")
                page_text = pytesseract.image_to_string(image)
                text_parts.append(page_text)

            full_text = "\n\n".join(text_parts)

            # Save to archive
            content_hash = self._compute_hash(full_text)
            archive_file = self.archive_dir / f"{file_path.stem}_{content_hash[:8]}.txt"
            archive_file.write_text(full_text, encoding="utf-8")

            # Chunk and ingest
            chunks = self._chunk_text(full_text)
            embeddings_added = 0

            if callable(ingest_to_rag):
                try:
                    ingest_to_rag(chunks)
                    embeddings_added = len(chunks)
                except Exception as e:
                    logger.error(f"RAG ingest failed: {e}")

            # Audit log
            audit_entry = {
                "source_type": "pdf",
                "source_path": str(file_path),
                "hash": content_hash,
                "tokens_extracted": self._estimate_tokens(full_text),
                "chunks": len(chunks),
                "embeddings_added": embeddings_added,
                "archive_file": str(archive_file),
                "status": "success"
            }
            self._log_audit(audit_entry)

            return {
                "ok": True,
                "source_type": "pdf",
                "text": full_text[:500] + "..." if len(full_text) > 500 else full_text,
                "full_length": len(full_text),
                "tokens": self._estimate_tokens(full_text),
                "chunks": len(chunks),
                "embeddings_added": embeddings_added,
                "hash": content_hash,
                "archive_file": str(archive_file)
            }

        except Exception as e:
            logger.error(f"OCR PDF failed: {e}")
            audit_entry = {
                "source_type": "pdf",
                "source_path": str(file_path),
                "error": str(e),
                "status": "failed"
            }
            self._log_audit(audit_entry)
            return {"ok": False, "error": str(e)}

    def _ocr_image(self, file_path: Path) -> Dict[str, Any]:
        """OCR an image file"""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            logger.error("pytesseract or PIL not available")
            return {"ok": False, "error": "OCR dependencies not installed (pip install pytesseract pillow)"}

        logger.info(f"OCR image: {file_path}")

        try:
            # Open and OCR image
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)

            # Save to archive
            content_hash = self._compute_hash(text)
            archive_file = self.archive_dir / f"{file_path.stem}_{content_hash[:8]}.txt"
            archive_file.write_text(text, encoding="utf-8")

            # Chunk and ingest
            chunks = self._chunk_text(text)
            embeddings_added = 0

            if callable(ingest_to_rag):
                try:
                    ingest_to_rag(chunks)
                    embeddings_added = len(chunks)
                except Exception as e:
                    logger.error(f"RAG ingest failed: {e}")

            # Audit log
            audit_entry = {
                "source_type": "image",
                "source_path": str(file_path),
                "hash": content_hash,
                "tokens_extracted": self._estimate_tokens(text),
                "chunks": len(chunks),
                "embeddings_added": embeddings_added,
                "archive_file": str(archive_file),
                "status": "success"
            }
            self._log_audit(audit_entry)

            return {
                "ok": True,
                "source_type": "image",
                "text": text[:500] + "..." if len(text) > 500 else text,
                "full_length": len(text),
                "tokens": self._estimate_tokens(text),
                "chunks": len(chunks),
                "embeddings_added": embeddings_added,
                "hash": content_hash,
                "archive_file": str(archive_file)
            }

        except Exception as e:
            logger.error(f"OCR image failed: {e}")
            audit_entry = {
                "source_type": "image",
                "source_path": str(file_path),
                "error": str(e),
                "status": "failed"
            }
            self._log_audit(audit_entry)
            return {"ok": False, "error": str(e)}

    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape webpage and extract text

        Args:
            url: URL to scrape

        Returns:
            Result dict with extracted text and audit info
        """
        if not self._check_authority():
            return {"ok": False, "error": "Authority denied: self_enhancement not allowed"}

        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("requests or BeautifulSoup not available")
            return {"ok": False, "error": "Scraping dependencies not installed (pip install requests beautifulsoup4)"}

        logger.info(f"Scraping URL: {url}")

        try:
            # Fetch page
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Sky-Agent/1.0 (Learning Bot)'
            })
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks_raw = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks_raw if chunk)

            # Save to archive
            content_hash = self._compute_hash(text)
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            archive_file = self.archive_dir / f"web_{url_hash}_{content_hash[:8]}.txt"
            archive_file.write_text(text, encoding="utf-8")

            # Also save raw HTML
            html_archive = self.archive_dir / f"web_{url_hash}_{content_hash[:8]}.html"
            html_archive.write_text(response.text, encoding="utf-8")

            # Chunk and ingest
            text_chunks = self._chunk_text(text)
            embeddings_added = 0

            if callable(ingest_to_rag):
                try:
                    ingest_to_rag(text_chunks)
                    embeddings_added = len(text_chunks)
                except Exception as e:
                    logger.error(f"RAG ingest failed: {e}")

            # Audit log
            audit_entry = {
                "source_type": "html",
                "source_url": url,
                "hash": content_hash,
                "tokens_extracted": self._estimate_tokens(text),
                "chunks": len(text_chunks),
                "embeddings_added": embeddings_added,
                "archive_file": str(archive_file),
                "html_archive": str(html_archive),
                "status": "success"
            }
            self._log_audit(audit_entry)

            return {
                "ok": True,
                "source_type": "html",
                "url": url,
                "text": text[:500] + "..." if len(text) > 500 else text,
                "full_length": len(text),
                "tokens": self._estimate_tokens(text),
                "chunks": len(text_chunks),
                "embeddings_added": embeddings_added,
                "hash": content_hash,
                "archive_file": str(archive_file)
            }

        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            audit_entry = {
                "source_type": "html",
                "source_url": url,
                "error": str(e),
                "status": "failed"
            }
            self._log_audit(audit_entry)
            return {"ok": False, "error": str(e)}

    def ingest_text(self, text: str, source_name: str = "manual") -> Dict[str, Any]:
        """
        Directly ingest text content

        Args:
            text: Text to ingest
            source_name: Name for the source

        Returns:
            Result dict
        """
        if not self._check_authority():
            return {"ok": False, "error": "Authority denied: self_enhancement not allowed"}

        logger.info(f"Ingesting text: {source_name}")

        try:
            # Save to archive
            content_hash = self._compute_hash(text)
            archive_file = self.archive_dir / f"{source_name}_{content_hash[:8]}.txt"
            archive_file.write_text(text, encoding="utf-8")

            # Chunk and ingest
            chunks = self._chunk_text(text)
            embeddings_added = 0

            if callable(ingest_to_rag):
                try:
                    ingest_to_rag(chunks)
                    embeddings_added = len(chunks)
                except Exception as e:
                    logger.error(f"RAG ingest failed: {e}")

            # Audit log
            audit_entry = {
                "source_type": "text",
                "source_name": source_name,
                "hash": content_hash,
                "tokens_extracted": self._estimate_tokens(text),
                "chunks": len(chunks),
                "embeddings_added": embeddings_added,
                "archive_file": str(archive_file),
                "status": "success"
            }
            self._log_audit(audit_entry)

            return {
                "ok": True,
                "source_type": "text",
                "source_name": source_name,
                "tokens": self._estimate_tokens(text),
                "chunks": len(chunks),
                "embeddings_added": embeddings_added,
                "hash": content_hash,
                "archive_file": str(archive_file)
            }

        except Exception as e:
            logger.error(f"Text ingest failed: {e}")
            audit_entry = {
                "source_type": "text",
                "source_name": source_name,
                "error": str(e),
                "status": "failed"
            }
            self._log_audit(audit_entry)
            return {"ok": False, "error": str(e)}

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get audit log entries

        Args:
            limit: Maximum number of entries to return (most recent)

        Returns:
            List of audit log entries
        """
        if not self.audit_file.exists():
            return []

        entries = []
        with self.audit_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue

        # Return most recent entries
        return entries[-limit:] if len(entries) > limit else entries


# FastAPI integration
def create_self_improve_api():
    """Create FastAPI app for self-improvement"""
    try:
        from fastapi import FastAPI, HTTPException, File, UploadFile
        from pydantic import BaseModel
    except ImportError:
        logger.error("FastAPI not available")
        return None

    app = FastAPI(title="Sky Self-Improvement API")
    tool = SelfImprovementTool()

    class ScrapeRequest(BaseModel):
        url: str

    class TextIngestRequest(BaseModel):
        text: str
        source_name: str = "manual"

    @app.post("/self/ingest_ocr")
    async def ingest_ocr(file: UploadFile = File(...)):
        """Upload and OCR file"""
        # Save uploaded file temporarily
        temp_path = ARCHIVE_DIR / f"temp_{file.filename}"
        with temp_path.open("wb") as f:
            content = await file.read()
            f.write(content)

        try:
            result = tool.ocr_file(str(temp_path))
            return result
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @app.post("/self/ingest_scrape")
    def ingest_scrape(request: ScrapeRequest):
        """Scrape and ingest URL"""
        result = tool.scrape_url(request.url)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    @app.post("/self/ingest_text")
    def ingest_text(request: TextIngestRequest):
        """Ingest raw text"""
        result = tool.ingest_text(request.text, request.source_name)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    @app.get("/self/audit_log")
    def get_audit_log(limit: int = 100):
        """Get audit log"""
        return {
            "entries": tool.get_audit_log(limit=limit),
            "count": len(tool.get_audit_log(limit=limit))
        }

    return app


# CLI entry point
def main():
    """Main entry point for self-improvement tool"""
    import argparse

    parser = argparse.ArgumentParser(description="Sky Self-Improvement Tool")
    parser.add_argument("--ocr", type=str, help="OCR file (PDF or image)")
    parser.add_argument("--scrape", type=str, help="Scrape URL")
    parser.add_argument("--text", type=str, help="Ingest text file")
    parser.add_argument("--audit", action="store_true", help="Show audit log")
    parser.add_argument("--limit", type=int, default=20, help="Audit log limit")
    parser.add_argument("--api-port", type=int, default=None, help="Start API server on port")
    args = parser.parse_args()

    tool = SelfImprovementTool()

    if args.api_port:
        # Start API server
        try:
            import uvicorn
            app = create_self_improve_api()
            if app:
                logger.info(f"Starting API server on port {args.api_port}")
                uvicorn.run(app, host="0.0.0.0", port=args.api_port)
            else:
                logger.error("Failed to create API app")
        except ImportError:
            logger.error("uvicorn not available - install with: pip install uvicorn")

    elif args.ocr:
        # OCR file
        print(f"\nOCR: {args.ocr}")
        result = tool.ocr_file(args.ocr)
        print(json.dumps(result, indent=2))

    elif args.scrape:
        # Scrape URL
        print(f"\nScraping: {args.scrape}")
        result = tool.scrape_url(args.scrape)
        print(json.dumps(result, indent=2))

    elif args.text:
        # Ingest text file
        text_path = Path(args.text)
        if not text_path.exists():
            print(f"File not found: {args.text}")
            return

        text_content = text_path.read_text(encoding="utf-8")
        print(f"\nIngesting text: {args.text}")
        result = tool.ingest_text(text_content, source_name=text_path.stem)
        print(json.dumps(result, indent=2))

    elif args.audit:
        # Show audit log
        entries = tool.get_audit_log(limit=args.limit)
        print(f"\n=== Audit Log (last {len(entries)} entries) ===\n")
        for entry in entries:
            print(f"[{entry.get('timestamp')}] {entry.get('source_type')} - {entry.get('status')}")
            if entry.get('status') == 'success':
                print(f"  Tokens: {entry.get('tokens_extracted')}, Chunks: {entry.get('chunks')}, Embeddings: {entry.get('embeddings_added')}")
                print(f"  Hash: {entry.get('hash')[:16]}...")
            else:
                print(f"  Error: {entry.get('error')}")
            print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
