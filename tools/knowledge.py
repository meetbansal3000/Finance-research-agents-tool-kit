"""
tools/knowledge.py - Local Knowledge Base Engine powered by ChromaDB (Upgrade 5)
Provides local, free, persistent semantic indexing and citation-backed search for:
- Corporate Filings (/library/filings/)
- Earnings Transcripts (/library/transcripts/)
- Research Notes (/library/notes/)

Enforces metadata preservation (company, ticker, document type, date, source URL, page/section)
and formats exact citations for research agents.
"""

import os
import sys
import re
import json
import hashlib
import datetime
from typing import Dict, Any, List, Optional, Tuple

import chromadb
from chromadb.config import Settings

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Directory defaults
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBRARY_DIR = os.path.join(PROJECT_ROOT, "library")
FILINGS_DIR = os.path.join(LIBRARY_DIR, "filings")
TRANSCRIPTS_DIR = os.path.join(LIBRARY_DIR, "transcripts")
NOTES_DIR = os.path.join(LIBRARY_DIR, "notes")
DEFAULT_CHROMA_DIR = os.path.join(LIBRARY_DIR, "chroma_db")

class LocalKnowledgeBase:
    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = "financial_research_library"
    ):
        self.persist_dir = persist_dir or DEFAULT_CHROMA_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Financial research filings, transcripts, and analyst notes"}
        )

    def extract_document_chunks(
        self,
        filepath: str,
        chunk_size: int = 800,
        chunk_overlap: int = 150
    ) -> List[Dict[str, Any]]:
        """
        Extract text from file and split sensibly by page (PDF), HTML sections, or Markdown headings.
        Returns a list of dicts: {'text': str, 'page_or_section': str, 'chunk_idx': int}.
        """
        ext = os.path.splitext(filepath)[1].lower()
        chunks = []

        if ext == ".pdf":
            chunks = self._extract_pdf(filepath, chunk_size, chunk_overlap)
        elif ext in (".htm", ".html"):
            chunks = self._extract_html(filepath, chunk_size, chunk_overlap)
        else:
            chunks = self._extract_text(filepath, chunk_size, chunk_overlap)

        return chunks

    def _extract_pdf(self, filepath: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        chunks = []
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                for page_idx, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text() or ""
                    page_label = f"Page {page_idx}"
                    page_chunks = self._chunk_text_block(page_text, page_label, chunk_size, chunk_overlap)
                    chunks.extend(page_chunks)
        except Exception as e:
            # Fallback if pdfplumber fails
            chunks = self._extract_text(filepath, chunk_size, chunk_overlap)
        return chunks

    def _extract_html(self, filepath: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        chunks = []
        from bs4 import BeautifulSoup
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Remove scripts and style tags
        for script in soup(["script", "style", "meta", "noscript"]):
            script.decompose()

        # Identify major SEC items or headings
        current_section = "General Filing Content"
        elements = soup.find_all(["h1", "h2", "h3", "h4", "p", "table", "div"])

        current_block = []
        char_count = 0

        for el in elements:
            tag_name = el.name.lower()
            text = el.get_text(separator=" ", strip=True)
            if not text:
                continue
            text = text.replace('\xa0', ' ').replace('\u200b', ' ').replace('', "'")
            text = re.sub(r'\s+', ' ', text).strip()

            # Check if this element defines a new section or item
            header_match = re.search(r'(ITEM\s+[0-9]+[A-Z]?\.?|PART\s+[I|V|X]+|CONSOLIDATED\s+[A-Z\s]+)', text, re.IGNORECASE)
            if (tag_name in ("h1", "h2", "h3") or header_match) and len(text) < 120:
                if current_block:
                    block_text = " ".join(current_block)
                    chunks.extend(self._chunk_text_block(block_text, current_section, chunk_size, chunk_overlap))
                    current_block = []
                    char_count = 0
                current_section = text.strip()
                continue

            current_block.append(text)
            char_count += len(text)

            if char_count >= chunk_size:
                block_text = " ".join(current_block)
                chunks.extend(self._chunk_text_block(block_text, current_section, chunk_size, chunk_overlap))
                current_block = []
                char_count = 0

        if current_block:
            block_text = " ".join(current_block)
            chunks.extend(self._chunk_text_block(block_text, current_section, chunk_size, chunk_overlap))

        return chunks

    def _extract_text(self, filepath: str, chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        chunks = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Split into sections by Markdown headings or SEC Item headers
        section_pattern = re.compile(r'(?:^|\n)(#{1,4}\s+[^\n]+|(?:ITEM|Item)\s+[0-9]+[A-Za-z]?\.?[^\n]*)')
        parts = section_pattern.split(content)

        if len(parts) > 1:
            current_sec = "Overview"
            for i in range(1, len(parts), 2):
                header = parts[i].strip()
                body = parts[i+1].strip() if i+1 < len(parts) else ""
                current_sec = header
                chunks.extend(self._chunk_text_block(body, current_sec, chunk_size, chunk_overlap))
        else:
            chunks = self._chunk_text_block(content, "General Text", chunk_size, chunk_overlap)

        return chunks

    def _chunk_text_block(
        self,
        text: str,
        section_label: str,
        chunk_size: int = 800,
        overlap: int = 150
    ) -> List[Dict[str, Any]]:
        """Split a block of text into overlapping character chunks while preserving section label."""
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            return []

        if len(text) <= chunk_size:
            return [{"text": text, "page_or_section": section_label}]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Snap to sentence or word boundary if possible
            if end < len(text):
                boundary = text.rfind(". ", start, end)
                if boundary != -1 and boundary > start + (chunk_size // 2):
                    end = boundary + 1

            chunk_str = text[start:end].strip()
            if chunk_str:
                chunks.append({"text": chunk_str, "page_or_section": section_label})

            if end >= len(text):
                break
            start = max(start + 1, end - overlap)

        return chunks

    def infer_metadata(self, filepath: str, user_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Infer ticker, company, document type, date, and source URL from filepath."""
        filename = os.path.basename(filepath)
        norm_path = filepath.replace("\\", "/")

        # Document type inference
        doc_type = "note"
        if "filings" in norm_path:
            doc_type = "filing"
        elif "transcripts" in norm_path:
            doc_type = "transcript"
        elif "notes" in norm_path:
            doc_type = "note"

        # Ticker inference
        ticker = "UNKNOWN"
        ticker_match = re.search(r'([A-Za-z0-9\.\-_]+?)(?:_|-|\b)', filename)
        if ticker_match:
            candidate = ticker_match.group(1).upper()
            if candidate in ("AAPL", "MSFT", "GOOGL", "AMZN", "TCS", "TCS.NS"):
                ticker = candidate
            elif "_" in filename:
                ticker = filename.split("_")[0].upper()

        # Date inference
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2}|\d{8})', filename)
        if date_match:
            raw_d = date_match.group(1).replace("_", "-")
            if len(raw_d) == 8 and raw_d.isdigit():
                date_str = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:]}"
            else:
                date_str = raw_d

        # Company mapping
        company_map = {
            "AAPL": "Apple Inc.",
            "TCS.NS": "Tata Consultancy Services Limited",
            "TCS": "Tata Consultancy Services Limited",
            "MSFT": "Microsoft Corporation",
            "GOOGL": "Alphabet Inc."
        }
        company = company_map.get(ticker, f"{ticker} Corporation")

        meta = {
            "ticker": ticker,
            "company": company,
            "document_type": doc_type,
            "date": date_str,
            "source_url": filepath,
            "filename": filename
        }

        if user_metadata:
            meta.update({k: v for k, v in user_metadata.items() if v is not None})

        return meta

    def ingest_file(
        self,
        filepath: str,
        document_type: Optional[str] = None,
        ticker: Optional[str] = None,
        company: Optional[str] = None,
        date: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> int:
        """
        Ingest a file into Chroma vector store with chunking and metadata.
        Returns the number of chunks added.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        user_meta = {}
        if document_type: user_meta["document_type"] = document_type
        if ticker: user_meta["ticker"] = ticker.upper()
        if company: user_meta["company"] = company
        if date: user_meta["date"] = date
        if source_url: user_meta["source_url"] = source_url

        base_meta = self.infer_metadata(filepath, user_meta)
        chunks = self.extract_document_chunks(filepath)

        if not chunks:
            return 0

        doc_hash = hashlib.md5(f"{filepath}_{os.path.getmtime(filepath)}".encode("utf-8")).hexdigest()[:8]
        
        ids = []
        documents = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{base_meta['ticker']}_{doc_hash}_c{idx:04d}"
            chunk_meta = dict(base_meta)
            chunk_meta["page_or_section"] = chunk["page_or_section"]
            chunk_meta["chunk_index"] = idx

            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append(chunk_meta)

        # Batch upsert into Chroma
        batch_size = 200
        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )

        return len(chunks)

    def ingest_directory(self, dir_path: str, document_type: Optional[str] = None) -> Dict[str, int]:
        """Ingest all supported documents in a directory."""
        if not os.path.exists(dir_path):
            return {}

        results = {}
        supported_exts = {".pdf", ".txt", ".md", ".htm", ".html", ".json"}

        for root, _, files in os.walk(dir_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_exts:
                    full_path = os.path.join(root, file)
                    count = self.ingest_file(full_path, document_type=document_type)
                    results[file] = count

        return results

    def ingest_all_library(self) -> Dict[str, Any]:
        """Ingest all files across /library/filings/, /library/transcripts/, and /library/notes/."""
        summary = {
            "filings": self.ingest_directory(FILINGS_DIR, document_type="filing"),
            "transcripts": self.ingest_directory(TRANSCRIPTS_DIR, document_type="transcript"),
            "notes": self.ingest_directory(NOTES_DIR, document_type="note")
        }
        return summary

    def search(
        self,
        query: str,
        ticker: Optional[str] = None,
        document_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search local Chroma knowledge base with optional metadata filtering.
        Returns top matching passages with full citation data.
        """
        where_filter = None
        filters = []
        if ticker:
            filters.append({"ticker": ticker.upper()})
        if document_type:
            filters.append({"document_type": document_type})

        if len(filters) == 1:
            where_filter = filters[0]
        elif len(filters) > 1:
            where_filter = {"$and": filters}

        total_items = self.collection.count()
        if total_items == 0:
            return []

        actual_k = min(top_k, total_items)
        results = self.collection.query(
            query_texts=[query],
            n_results=actual_k,
            where=where_filter
        )

        hits = []
        if not results or not results["documents"] or not results["documents"][0]:
            return hits

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        ids = results["ids"][0]
        distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)

        for i in range(len(docs)):
            meta = metas[i]
            citation_str = (
                f"[Citation: {meta.get('ticker')} | {meta.get('document_type')} | "
                f"{meta.get('filename')} | {meta.get('page_or_section')} | "
                f"Date: {meta.get('date')} | Source: {meta.get('source_url')}]"
            )
            hits.append({
                "id": ids[i],
                "text": docs[i],
                "metadata": meta,
                "distance": distances[i],
                "citation": citation_str
            })

        return hits

    def status(self) -> Dict[str, Any]:
        """Return knowledge base status and entry count."""
        count = self.collection.count()
        return {
            "persist_dir": self.persist_dir,
            "collection_name": self.collection.name,
            "total_chunks": count
        }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity Local Knowledge Base (ChromaDB)")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Ingest subcommand
    ingest_p = subparsers.add_parser("ingest", help="Ingest a specific file or directory")
    ingest_p.add_argument("path", type=str, help="Path to file or folder")
    ingest_p.add_argument("--type", type=str, choices=["filing", "transcript", "note"], default=None, help="Document type")
    ingest_p.add_argument("--ticker", type=str, default=None, help="Ticker symbol")
    ingest_p.add_argument("--company", type=str, default=None, help="Company name")
    ingest_p.add_argument("--date", type=str, default=None, help="Document date (YYYY-MM-DD)")
    ingest_p.add_argument("--url", type=str, default=None, help="Primary source URL")

    # Ingest-all subcommand
    subparsers.add_parser("ingest-all", help="Scan and ingest /library/filings/, /library/transcripts/, and /library/notes/")

    # Search subcommand
    search_p = subparsers.add_parser("search", help="Search the knowledge base")
    search_p.add_argument("query", type=str, help="Search query string")
    search_p.add_argument("--ticker", type=str, default=None, help="Filter by ticker")
    search_p.add_argument("--type", type=str, choices=["filing", "transcript", "note"], default=None, help="Filter by document type")
    search_p.add_argument("--top-k", type=int, default=5, help="Number of results to return")

    # Status subcommand
    subparsers.add_parser("status", help="Show knowledge base status and chunk count")

    args = parser.parse_args()
    kb = LocalKnowledgeBase()

    if args.command == "ingest":
        if os.path.isdir(args.path):
            res = kb.ingest_directory(args.path, document_type=args.type)
            print(f"Ingested {len(res)} files from {args.path}:")
            for f, c in res.items():
                print(f"  - {f}: {c} chunks")
        else:
            c = kb.ingest_file(
                args.path,
                document_type=args.type,
                ticker=args.ticker,
                company=args.company,
                date=args.date,
                source_url=args.url
            )
            print(f"Successfully ingested {args.path} ({c} chunks).")

    elif args.command == "ingest-all":
        summary = kb.ingest_all_library()
        print("Ingestion Summary for /library/:")
        for cat, items in summary.items():
            print(f"  [{cat}]: {len(items)} files, {sum(items.values())} chunks")

    elif args.command == "search":
        hits = kb.search(args.query, ticker=args.ticker, document_type=args.type, top_k=args.top_k)
        print(f"\nFound {len(hits)} matching results for query: '{args.query}'\n")
        for i, hit in enumerate(hits, start=1):
            print(f"--- [Result #{i} | Distance: {hit['distance']:.4f}] ---")
            print(f"{hit['citation']}")
            print(f"Excerpt: {hit['text']}\n")

    elif args.command == "status":
        stat = kb.status()
        print(f"Chroma Knowledge Base: {stat['collection_name']}")
        print(f"Storage Directory: {stat['persist_dir']}")
        print(f"Total Chunks Indexed: {stat['total_chunks']}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
