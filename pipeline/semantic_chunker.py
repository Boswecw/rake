"""
Semantic Chunking Module for Rake Pipeline

This module provides intelligent chunking based on semantic similarity
using sentence embeddings to detect topic boundaries.

Key Features:
    - Accurate token counting using tiktoken
    - Semantic boundary detection via sentence embeddings
    - Configurable similarity threshold
    - Multiple chunking strategies (token, semantic, hybrid)

Example:
    >>> from pipeline.semantic_chunker import SemanticChunker, ChunkingStrategy
    >>> chunker = SemanticChunker(
    ...     chunk_size=500,
    ...     strategy=ChunkingStrategy.HYBRID
    ... )
    >>> chunks = await chunker.chunk_document(document)
"""

import asyncio
import logging
import tiktoken
import numpy as np
from typing import List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer
from models.document import CleanedDocument, Chunk

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Chunking strategy options."""
    TOKEN_BASED = "token_based"          # Original: split by tokens only
    SEMANTIC = "semantic"                 # New: split by semantic boundaries
    HYBRID = "hybrid"                     # New: combine both approaches


@dataclass
class SemanticBoundary:
    """Represents a detected semantic boundary in text."""
    position: int                         # Sentence index
    similarity_score: float               # Similarity with next sentence
    is_boundary: bool                     # Whether this is a topic boundary


class SemanticChunker:
    """
    Intelligent chunker that uses semantic similarity to detect topic boundaries.
    
    Instead of blindly splitting at token limits, this chunker:
    1. Splits text into sentences
    2. Generates embeddings for each sentence
    3. Calculates similarity between adjacent sentences
    4. Identifies topic boundaries (low similarity)
    5. Creates chunks that respect semantic coherence
    
    Attributes:
        chunk_size: Target chunk size in tokens
        overlap: Overlap size in tokens
        strategy: Chunking strategy (token/semantic/hybrid)
        similarity_threshold: Threshold for detecting topic boundaries
        embedding_model: Sentence transformer model for embeddings
        tokenizer: Tiktoken tokenizer for accurate token counting
    
    Example:
        >>> chunker = SemanticChunker(
        ...     chunk_size=500,
        ...     overlap=50,
        ...     strategy=ChunkingStrategy.HYBRID,
        ...     similarity_threshold=0.5
        ... )
        >>> chunks = await chunker.chunk_document(document)
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        strategy: ChunkingStrategy = ChunkingStrategy.HYBRID,
        similarity_threshold: float = 0.5,
        embedding_model: str = "all-MiniLM-L6-v2",  # Fast, lightweight model
        tokenizer_model: str = "cl100k_base"
    ):
        """
        Initialize semantic chunker.
        
        Args:
            chunk_size: Target chunk size in tokens
            overlap: Overlap size in tokens
            strategy: Chunking strategy
            similarity_threshold: Threshold for semantic boundaries (0-1)
                                  Lower = more boundaries (shorter chunks)
                                  Higher = fewer boundaries (longer chunks)
            embedding_model: Sentence transformer model name
            tokenizer_model: Tiktoken model for token counting
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = strategy
        self.similarity_threshold = similarity_threshold
        
        # Initialize tiktoken for accurate token counting
        self.tokenizer = tiktoken.get_encoding(tokenizer_model)
        
        # Initialize sentence transformer for semantic embeddings
        # Only load if semantic or hybrid strategy
        self.embedding_model = None
        if strategy in (ChunkingStrategy.SEMANTIC, ChunkingStrategy.HYBRID):
            logger.info(f"Loading sentence transformer model: {embedding_model}")
            self.embedding_model = SentenceTransformer(embedding_model)
        
        logger.info(
            f"SemanticChunker initialized: strategy={strategy.value}, "
            f"chunk_size={chunk_size}, overlap={overlap}, "
            f"similarity_threshold={similarity_threshold}"
        )
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens accurately using tiktoken.
        
        Args:
            text: Text to count tokens for
        
        Returns:
            Accurate token count
        
        Example:
            >>> tokens = chunker.count_tokens("Hello, world!")
            >>> print(tokens)  # Accurate count, not estimation
        """
        return len(self.tokenizer.encode(text))
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Uses simple regex for now. Could be enhanced with NLTK or spaCy
        for better accuracy.
        
        Args:
            text: Text to split
        
        Returns:
            List of sentences
        """
        import re
        # Enhanced sentence splitting (handles abbreviations better)
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def _detect_semantic_boundaries(
        self,
        sentences: List[str]
    ) -> List[SemanticBoundary]:
        """
        Detect semantic boundaries between sentences using embeddings.
        
        Algorithm:
        1. Generate embeddings for all sentences
        2. Calculate cosine similarity between adjacent sentences
        3. Mark low-similarity pairs as boundaries
        
        Args:
            sentences: List of sentences
        
        Returns:
            List of semantic boundaries
        """
        if not self.embedding_model or len(sentences) < 2:
            return []
        
        # Generate embeddings for all sentences
        embeddings = self.embedding_model.encode(sentences)
        
        # Calculate cosine similarity between adjacent sentences
        boundaries: List[SemanticBoundary] = []
        
        for i in range(len(sentences) - 1):
            # Cosine similarity between current and next sentence
            similarity = np.dot(embeddings[i], embeddings[i + 1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
            )
            
            # Mark as boundary if similarity is below threshold
            is_boundary = similarity < self.similarity_threshold
            
            boundaries.append(SemanticBoundary(
                position=i,
                similarity_score=float(similarity),
                is_boundary=is_boundary
            ))
        
        return boundaries
    
    async def _chunk_token_based(
        self,
        sentences: List[str],
        document: CleanedDocument
    ) -> List[Chunk]:
        """
        Original token-based chunking (no semantic awareness).
        
        Args:
            sentences: List of sentences
            document: Parent document
        
        Returns:
            List of chunks
        """
        chunks: List[Chunk] = []
        current_chunk = []
        current_tokens = 0
        chunk_position = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    document=document,
                    content=chunk_text,
                    position=chunk_position,
                    token_count=current_tokens,
                    strategy="token_based"
                ))
                chunk_position += 1
                
                # Start new chunk with overlap
                if self.overlap > 0:
                    overlap_sentences = current_chunk[-(len(current_chunk) // 4):]
                    current_chunk = overlap_sentences + [sentence]
                    current_tokens = sum(self.count_tokens(s) for s in current_chunk)
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Save final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._create_chunk(
                document=document,
                content=chunk_text,
                position=chunk_position,
                token_count=self.count_tokens(chunk_text),
                strategy="token_based"
            ))
        
        return chunks
    
    async def _chunk_semantic(
        self,
        sentences: List[str],
        document: CleanedDocument
    ) -> List[Chunk]:
        """
        Pure semantic chunking (respect topic boundaries).
        
        Args:
            sentences: List of sentences
            document: Parent document
        
        Returns:
            List of chunks
        """
        # Detect semantic boundaries
        boundaries = await self._detect_semantic_boundaries(sentences)
        
        chunks: List[Chunk] = []
        current_chunk = []
        current_tokens = 0
        chunk_position = 0
        
        for i, sentence in enumerate(sentences):
            sentence_tokens = self.count_tokens(sentence)
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
            
            # Check if we should split here
            should_split = False
            
            # Split at semantic boundary
            if i < len(boundaries) and boundaries[i].is_boundary:
                should_split = True
            
            # Also split if exceeding max size (safety limit)
            if current_tokens > self.chunk_size * 1.5:
                should_split = True
            
            # Save chunk if splitting
            if should_split and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    document=document,
                    content=chunk_text,
                    position=chunk_position,
                    token_count=current_tokens,
                    strategy="semantic",
                    boundary_score=boundaries[i].similarity_score if i < len(boundaries) else None
                ))
                chunk_position += 1
                current_chunk = []
                current_tokens = 0
        
        # Save final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._create_chunk(
                document=document,
                content=chunk_text,
                position=chunk_position,
                token_count=self.count_tokens(chunk_text),
                strategy="semantic"
            ))
        
        return chunks
    
    async def _chunk_hybrid(
        self,
        sentences: List[str],
        document: CleanedDocument
    ) -> List[Chunk]:
        """
        Hybrid chunking: respect semantic boundaries but enforce token limits.
        
        Best of both worlds:
        - Prefers semantic boundaries for splitting
        - Falls back to token-based if chunk gets too large
        
        Args:
            sentences: List of sentences
            document: Parent document
        
        Returns:
            List of chunks
        """
        # Detect semantic boundaries
        boundaries = await self._detect_semantic_boundaries(sentences)
        
        chunks: List[Chunk] = []
        current_chunk = []
        current_tokens = 0
        chunk_position = 0
        
        for i, sentence in enumerate(sentences):
            sentence_tokens = self.count_tokens(sentence)
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
            
            # Determine if we should split
            should_split = False
            split_reason = None
            
            # Priority 1: Hard limit - must split if exceeding max size
            if current_tokens > self.chunk_size:
                should_split = True
                split_reason = "token_limit"
            
            # Priority 2: Semantic boundary + soft limit
            elif i < len(boundaries) and boundaries[i].is_boundary:
                if current_tokens >= self.chunk_size * 0.7:  # 70% of target
                    should_split = True
                    split_reason = "semantic_boundary"
            
            # Save chunk if splitting
            if should_split and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    document=document,
                    content=chunk_text,
                    position=chunk_position,
                    token_count=current_tokens,
                    strategy="hybrid",
                    split_reason=split_reason,
                    boundary_score=boundaries[i].similarity_score if i < len(boundaries) else None
                ))
                chunk_position += 1
                
                # Start new chunk with overlap if at token limit
                if split_reason == "token_limit" and self.overlap > 0:
                    overlap_sentences = current_chunk[-(len(current_chunk) // 4):]
                    current_chunk = overlap_sentences
                    current_tokens = sum(self.count_tokens(s) for s in current_chunk)
                else:
                    current_chunk = []
                    current_tokens = 0
        
        # Save final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._create_chunk(
                document=document,
                content=chunk_text,
                position=chunk_position,
                token_count=self.count_tokens(chunk_text),
                strategy="hybrid"
            ))
        
        return chunks
    
    def _create_chunk(
        self,
        document: CleanedDocument,
        content: str,
        position: int,
        token_count: int,
        strategy: str,
        boundary_score: Optional[float] = None,
        split_reason: Optional[str] = None
    ) -> Chunk:
        """
        Create a Chunk object with metadata.
        
        Args:
            document: Parent document
            content: Chunk content
            position: Chunk position
            token_count: Accurate token count
            strategy: Chunking strategy used
            boundary_score: Semantic boundary score (if applicable)
            split_reason: Reason for split (hybrid mode)
        
        Returns:
            Chunk object
        """
        metadata = {
            **document.metadata,
            "chunk_strategy": strategy,
            "chunk_size_tokens": self.chunk_size,
            "overlap_tokens": self.overlap,
            "actual_tokens": token_count,
        }
        
        if boundary_score is not None:
            metadata["boundary_similarity"] = round(boundary_score, 3)
        
        if split_reason:
            metadata["split_reason"] = split_reason
        
        return Chunk(
            document_id=document.id,
            content=content,
            metadata=metadata,
            position=position,
            token_count=token_count,
            start_char=0,  # Would need full document to calculate accurately
            end_char=len(content),
            tenant_id=document.tenant_id
        )
    
    async def chunk_document(
        self,
        document: CleanedDocument
    ) -> List[Chunk]:
        """
        Chunk a document using the selected strategy.
        
        Args:
            document: Cleaned document to chunk
        
        Returns:
            List of chunks
        
        Example:
            >>> chunks = await chunker.chunk_document(document)
            >>> print(f"Created {len(chunks)} chunks")
            >>> print(f"Avg tokens: {sum(c.token_count for c in chunks) / len(chunks):.0f}")
        """
        # Split into sentences
        sentences = self._split_into_sentences(document.content)
        
        if not sentences:
            return []
        
        # Apply strategy
        if self.strategy == ChunkingStrategy.TOKEN_BASED:
            chunks = await self._chunk_token_based(sentences, document)
        elif self.strategy == ChunkingStrategy.SEMANTIC:
            chunks = await self._chunk_semantic(sentences, document)
        else:  # HYBRID
            chunks = await self._chunk_hybrid(sentences, document)
        
        logger.info(
            f"Chunked document {document.id}: "
            f"{len(sentences)} sentences → {len(chunks)} chunks "
            f"(strategy={self.strategy.value})"
        )
        
        return chunks


# Example usage
if __name__ == "__main__":
    async def test_semantic_chunker():
        """Test the semantic chunker with sample text."""
        from models.document import CleanedDocument
        
        # Create test document with topic shifts
        test_doc = CleanedDocument(
            id="test-doc-1",
            source="test",
            content="""
            Artificial intelligence has revolutionized many industries. Machine learning algorithms 
            can now process vast amounts of data. Deep learning models achieve remarkable accuracy 
            in image recognition tasks.
            
            The weather today is quite pleasant. It's sunny with a gentle breeze. Perfect for 
            outdoor activities. Many people are enjoying the park.
            
            Quantum computing represents a paradigm shift in computation. Quantum bits, or qubits, 
            can exist in superposition states. This enables quantum computers to solve certain 
            problems exponentially faster than classical computers.
            """.strip(),
            metadata={"test": True},
            word_count=100,
            char_count=500
        )
        
        # Test different strategies
        strategies = [
            ChunkingStrategy.TOKEN_BASED,
            ChunkingStrategy.SEMANTIC,
            ChunkingStrategy.HYBRID
        ]
        
        for strategy in strategies:
            print(f"\n{'='*60}")
            print(f"Testing strategy: {strategy.value}")
            print('='*60)
            
            chunker = SemanticChunker(
                chunk_size=50,  # Small for testing
                overlap=10,
                strategy=strategy,
                similarity_threshold=0.6
            )
            
            chunks = await chunker.chunk_document(test_doc)
            
            print(f"\nCreated {len(chunks)} chunks:\n")
            for chunk in chunks:
                print(f"Chunk {chunk.position}:")
                print(f"  Tokens: {chunk.token_count}")
                print(f"  Strategy: {chunk.metadata.get('chunk_strategy')}")
                if 'boundary_similarity' in chunk.metadata:
                    print(f"  Boundary score: {chunk.metadata['boundary_similarity']}")
                if 'split_reason' in chunk.metadata:
                    print(f"  Split reason: {chunk.metadata['split_reason']}")
                print(f"  Content preview: {chunk.content[:80]}...")
                print()
    
    asyncio.run(test_semantic_chunker())
