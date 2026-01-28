"""
RAG (Retrieval Augmented Generation) Service
Handles document loading, chunking, and retrieval for knowledge-based responses
"""
import os
import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from ..config.settings import RAG_KNOWLEDGE_DIR, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP


@dataclass
class DocumentChunk:
    """A chunk of text from a document"""
    content: str
    source: str
    chunk_id: int
    metadata: Dict


@dataclass 
class RetrievalResult:
    """Result of a retrieval query"""
    chunks: List[DocumentChunk]
    query: str
    total_chunks_searched: int


class SimpleRAGService:
    """
    Simple RAG implementation using keyword matching
    For production, consider using vector embeddings with a proper vector DB
    """
    
    def __init__(self, knowledge_dir: str = None):
        self.knowledge_dir = knowledge_dir or RAG_KNOWLEDGE_DIR
        self.chunks: List[DocumentChunk] = []
        self.documents: Dict[str, str] = {}
        self._loaded = False
        
    def ensure_knowledge_dir(self):
        """Create knowledge directory if it doesn't exist"""
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)
            print(f"✅ Created knowledge base directory: {self.knowledge_dir}")
            
            # Create a sample document
            sample_path = os.path.join(self.knowledge_dir, "README.md")
            sample_content = """# Knowledge Base

This folder contains documents that the AI can reference when responding to customer inquiries.

## How to Add Documents

1. Add text files (.txt), markdown files (.md), or JSON files (.json) to this folder
2. The system will automatically load and index them
3. Documents are chunked for better retrieval

## Supported Formats

- `.txt` - Plain text files
- `.md` - Markdown files  
- `.json` - JSON files (will be converted to readable text)

## Tips

- Use clear headings and sections
- Include common questions and answers
- Add product documentation, FAQs, policies, etc.
- Keep documents focused on specific topics
"""
            with open(sample_path, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            print(f"✅ Created sample knowledge base document: {sample_path}")
    
    def load_documents(self) -> int:
        """Load all documents from the knowledge directory"""
        self.ensure_knowledge_dir()
        
        self.documents = {}
        self.chunks = []
        
        supported_extensions = {'.txt', '.md', '.json'}
        
        for root, dirs, files in os.walk(self.knowledge_dir):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in supported_extensions:
                    continue
                    
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, self.knowledge_dir)
                
                try:
                    content = self._load_file(filepath, ext)
                    if content:
                        self.documents[rel_path] = content
                        print(f"📄 Loaded: {rel_path} ({len(content)} chars)")
                except Exception as e:
                    print(f"❌ Error loading {filepath}: {e}")
        
        # Chunk all documents
        for source, content in self.documents.items():
            doc_chunks = self._chunk_text(content, source)
            self.chunks.extend(doc_chunks)
        
        self._loaded = True
        print(f"✅ Loaded {len(self.documents)} documents, {len(self.chunks)} chunks")
        return len(self.documents)
    
    def _load_file(self, filepath: str, ext: str) -> Optional[str]:
        """Load a file based on its extension"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if ext == '.json':
            # Convert JSON to readable text
            try:
                data = json.loads(content)
                return self._json_to_text(data)
            except json.JSONDecodeError:
                return content
        
        return content
    
    def _json_to_text(self, data, prefix="") -> str:
        """Convert JSON structure to readable text"""
        lines = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._json_to_text(value, prefix + "  "))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}Item {i+1}:")
                    lines.append(self._json_to_text(item, prefix + "  "))
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")
            
        return "\n".join(lines)
    
    def _chunk_text(self, text: str, source: str) -> List[DocumentChunk]:
        """Split text into chunks with overlap"""
        chunks = []
        
        # Clean up text
        text = text.strip()
        if not text:
            return chunks
        
        # Split by paragraphs first, then by sentences if needed
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        chunk_id = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # If adding this paragraph exceeds chunk size, save current and start new
            if len(current_chunk) + len(para) > RAG_CHUNK_SIZE:
                if current_chunk:
                    chunks.append(DocumentChunk(
                        content=current_chunk.strip(),
                        source=source,
                        chunk_id=chunk_id,
                        metadata={"type": "text"}
                    ))
                    chunk_id += 1
                    
                    # Keep overlap from end of current chunk
                    if RAG_CHUNK_OVERLAP > 0:
                        overlap_text = current_chunk[-RAG_CHUNK_OVERLAP:]
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                content=current_chunk.strip(),
                source=source,
                chunk_id=chunk_id,
                metadata={"type": "text"}
            ))
        
        return chunks
    
    def search(self, query: str, top_k: int = 3) -> RetrievalResult:
        """
        Search for relevant chunks using keyword matching
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            RetrievalResult with matched chunks
        """
        if not self._loaded:
            self.load_documents()
        
        if not self.chunks:
            return RetrievalResult(chunks=[], query=query, total_chunks_searched=0)
        
        # Extract keywords from query
        keywords = self._extract_keywords(query.lower())
        
        # Score each chunk based on keyword matches
        scored_chunks = []
        for chunk in self.chunks:
            score = self._score_chunk(chunk.content.lower(), keywords)
            if score > 0:
                scored_chunks.append((chunk, score))
        
        # Sort by score descending
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k
        top_chunks = [chunk for chunk, score in scored_chunks[:top_k]]
        
        return RetrievalResult(
            chunks=top_chunks,
            query=query,
            total_chunks_searched=len(self.chunks)
        )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'just', 'and', 'but', 'if', 'or', 'because', 'until', 'while', 'this',
            'that', 'these', 'those', 'what', 'which', 'who', 'whom', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my',
            'your', 'his', 'its', 'our', 'their', 'please', 'help', 'need', 'want'
        }
        
        # Tokenize
        words = re.findall(r'\b[a-z]+\b', text)
        
        # Filter stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _score_chunk(self, chunk_text: str, keywords: List[str]) -> float:
        """Score a chunk based on keyword presence"""
        if not keywords:
            return 0.0
            
        matches = 0
        for keyword in keywords:
            if keyword in chunk_text:
                matches += 1
                # Bonus for exact word match (not just substring)
                if re.search(rf'\b{re.escape(keyword)}\b', chunk_text):
                    matches += 0.5
        
        # Normalize by number of keywords
        return matches / len(keywords)
    
    def get_context_for_query(self, query: str, max_tokens: int = 1000) -> str:
        """
        Get relevant context for a customer query
        
        Args:
            query: Customer's question/email
            max_tokens: Approximate max length of context
            
        Returns:
            Formatted context string from relevant documents
        """
        results = self.search(query, top_k=5)
        
        if not results.chunks:
            return ""
        
        context_parts = []
        current_length = 0
        
        for chunk in results.chunks:
            chunk_text = f"[From: {chunk.source}]\n{chunk.content}"
            
            # Rough token estimate (4 chars per token)
            estimated_tokens = len(chunk_text) / 4
            
            if current_length + estimated_tokens > max_tokens:
                break
                
            context_parts.append(chunk_text)
            current_length += estimated_tokens
        
        if context_parts:
            return "\n\n---\n\n".join(context_parts)
        
        return ""
    
    def add_document(self, filename: str, content: str) -> bool:
        """
        Add a new document to the knowledge base
        
        Args:
            filename: Name for the document file
            content: Document content
            
        Returns:
            True if successful
        """
        self.ensure_knowledge_dir()
        
        filepath = os.path.join(self.knowledge_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Reload documents
            self.load_documents()
            return True
        except Exception as e:
            print(f"❌ Error adding document: {e}")
            return False
    
    def list_documents(self) -> List[str]:
        """List all documents in the knowledge base"""
        self.ensure_knowledge_dir()
        
        documents = []
        for root, dirs, files in os.walk(self.knowledge_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, self.knowledge_dir)
                documents.append(rel_path)
        
        return documents


# Global RAG service instance
_rag_service: Optional[SimpleRAGService] = None


def get_rag_service() -> SimpleRAGService:
    """Get the global RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = SimpleRAGService()
    return _rag_service


def initialize_rag() -> bool:
    """Initialize the RAG service and load documents"""
    try:
        service = get_rag_service()
        count = service.load_documents()
        print(f"✅ RAG service initialized with {count} documents")
        return True
    except Exception as e:
        print(f"❌ Error initializing RAG service: {e}")
        return False


def get_context_for_email(email_body: str) -> str:
    """Get relevant context for an email query"""
    service = get_rag_service()
    return service.get_context_for_query(email_body)
