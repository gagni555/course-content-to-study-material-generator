import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from app.schemas.document import NormalizedDocument
from app.models.concept import ConceptCreate
import re
from collections import Counter, defaultdict
import spacy
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    Analyzes document content to extract concepts, identify relationships, and build knowledge representations
    """
    
    def __init__(self):
        # Load spaCy model for NLP processing
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy 'en_core_web_sm' model not found. Please install it with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Load sentence transformer model for semantic similarity
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Define patterns for identifying important content
        self.definition_patterns = [
            r"(?i)is defined as",
            r"(?i)refers to",
            r"(?i)means",
            r"(?i)is the",
            r"(?i)are the"
        ]
        
        self.example_indicators = [
            "for example", "for instance", "e.g.", "such as", "namely", "like"
        ]
    
    async def analyze_content(self, normalized_document: NormalizedDocument) -> Dict[str, Any]:
        """
        Analyze the normalized document content to extract concepts and relationships
        """
        # Check cache first using document ID
        if hasattr(normalized_document, 'document_id'):
            cached_result = await document_cache.get_analyzed_content(normalized_document.document_id)
            if cached_result:
                logger.info(f"Retrieved analyzed content from cache: {normalized_document.document_id}")
                return cached_result
        
        try:
            # Extract concepts from the document
            concepts = await self._extract_concepts(normalized_document)
            
            # Identify relationships between concepts
            relationships = await self._identify_relationships(concepts, normalized_document)
            
            # Build knowledge graph
            knowledge_graph = await self._build_knowledge_graph(concepts, relationships)
            
            # Create concept map data structure
            concept_map = await self._create_concept_map(concepts, relationships)
            
            analysis_result = {
                "concepts": concepts,
                "relationships": relationships,
                "knowledge_graph": knowledge_graph,
                "concept_map": concept_map,
                "content_chunks": await self._chunk_content(normalized_document)
            }
            
            # Cache the result if we have a document ID
            if hasattr(normalized_document, 'document_id'):
                await document_cache.set_analyzed_content(normalized_document.document_id, analysis_result)
            
            return analysis_result
        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            raise
    
    async def _extract_concepts(self, normalized_document: NormalizedDocument) -> List[Dict[str, Any]]:
        """
        Extract key concepts from the document with importance scoring
        """
        concepts = []
        all_text = " ".join([section["content"] for section in normalized_document.sections])
        
        # Process with spaCy if available
        if self.nlp:
            doc = self.nlp(all_text)
            
            # Extract named entities
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            
            # Extract noun chunks as potential concepts
            noun_chunks = [chunk.text for chunk in doc.noun_chunks]
            
            # Combine entities and noun chunks
            potential_concepts = list(set(entities + [(chunk, "MISC") for chunk in noun_chunks]))
            
            # Score concepts by frequency and position
            text_lower = all_text.lower()
            concept_scores = {}
            
            for concept_text, label in potential_concepts:
                # Skip very short or very long concepts
                if len(concept_text) < 2 or len(concept_text) > 10:
                    continue
                
                # Count occurrences
                count = len(re.findall(r'\b' + re.escape(concept_text.lower()) + r'\b', text_lower))
                
                # Calculate importance score based on frequency and position
                score = self._calculate_importance_score(concept_text, all_text, count)
                
                if score > 0.1:  # Only include concepts with reasonable importance
                    concepts.append({
                        "term": concept_text,
                        "definition": await self._find_definition(concept_text, normalized_document),
                        "importance_score": score,
                        "category": label,
                        "examples": await self._find_examples(concept_text, normalized_document),
                        "related_concepts": [],
                        "page_reference": await self._find_page_reference(concept_text, normalized_document)
                    })
        else:
            # Fallback to simple keyword extraction if spaCy is not available
            words = re.findall(r'\b[A-Za-z]{4,}\b', all_text)  # Only words with 4+ characters
            word_freq = Counter(words)
            total_words = len(words)
            
            for word, freq in word_freq.items():
                score = freq / total_words  # Simple frequency-based scoring
                
                if score > 0.001:  # Only include reasonably frequent terms
                    concepts.append({
                        "term": word,
                        "definition": f"Term '{word}' from the document",
                        "importance_score": score,
                        "category": "TERM",
                        "examples": [],
                        "related_concepts": [],
                        "page_reference": "1"  # Default reference
                    })
        
        # Sort concepts by importance score
        concepts.sort(key=lambda x: x["importance_score"], reverse=True)
        
        return concepts
    
    def _calculate_importance_score(self, concept: str, all_text: str, frequency: int) -> float:
        """
        Calculate importance score based on multiple factors
        """
        # Base score on frequency
        base_score = min(frequency / 10.0, 0.5)  # Cap at 0.5 for frequency
        
        # Boost score if concept appears early in document
        first_occurrence = all_text.lower().find(concept.lower())
        position_factor = 1.0 if first_occurrence < len(all_text) * 0.3 else 0.7 if first_occurrence < len(all_text) * 0.6 else 0.5
        
        # Boost score if concept appears in headings
        heading_boost = 0.2 if self._appears_in_heading(concept, all_text) else 0.0
        
        # Calculate final score
        final_score = (base_score * position_factor) + heading_boost
        return min(final_score, 1.0)  # Cap at 1.0
    
    def _appears_in_heading(self, concept: str, all_text: str) -> bool:
        """
        Check if concept appears in what might be a heading (simplified approach)
        """
        # This is a simplified heuristic - in a full implementation, we'd use the section structure
        lines = all_text.split('\n')
        for line in lines[:10]:  # Check first few lines
            if concept.lower() in line.lower() and len(line) < 100:  # Short lines might be headings
                return True
        return False
    
    async def _find_definition(self, concept: str, normalized_document: NormalizedDocument) -> str:
        """
        Find a definition for the concept in the document
        """
        all_content = " ".join([section["content"] for section in normalized_document.sections])
        
        # Look for definition patterns around the concept
        for pattern in self.definition_patterns:
            matches = re.finditer(pattern, all_content, re.IGNORECASE)
            for match in matches:
                # Get the sentence containing the pattern
                start = max(0, match.start() - 200)
                end = min(len(all_content), match.end() + 200)
                sentence = all_content[start:end]
                
                if concept.lower() in sentence.lower():
                    return sentence.strip()
        
        # If no definition pattern found, return the first occurrence with context
        concept_pos = all_content.lower().find(concept.lower())
        if concept_pos != -1:
            start = max(0, concept_pos - 10)
            end = min(len(all_content), concept_pos + len(concept) + 100)
            return all_content[start:end].strip()
        
        return f"Definition for '{concept}' not found in document"
    
    async def _find_examples(self, concept: str, normalized_document: NormalizedDocument) -> List[str]:
        """
        Find examples related to the concept in the document
        """
        examples = []
        all_content = " ".join([section["content"] for section in normalized_document.sections])
        
        # Look for example indicators near the concept
        for indicator in self.example_indicators:
            # Create pattern without truncating the regex itself
            pattern = rf"({indicator}.*?{re.escape(concept)}|{re.escape(concept)}.*?{indicator})"
            matches = re.findall(pattern, all_content, re.IGNORECASE)
            examples.extend([match.strip() for match in matches if len(match.strip()) > 5])
        
        return examples[:5]  # Return at most 5 examples
    
    async def _find_page_reference(self, concept: str, normalized_document: NormalizedDocument) -> str:
        """
        Find the page reference for the concept
        """
        for section in normalized_document.sections:
            if concept.lower() in section["content"].lower():
                return str(section["position"]["page"])
        return "1"  # Default to page 1 if not found
    
    async def _identify_relationships(self, concepts: List[Dict[str, Any]], normalized_document: NormalizedDocument) -> List[Dict[str, Any]]:
        """
        Identify relationships between concepts
        """
        relationships = []
        concept_terms = [c["term"] for c in concepts]
        
        # Calculate semantic similarity between concepts
        concept_embeddings = self.sentence_model.encode(concept_terms)
        
        # Compare each concept with every other concept
        for i, concept1 in enumerate(concepts):
            for j, concept2 in enumerate(concepts):
                if i >= j:  # Avoid duplicate relationships and self-relationships
                    continue
                
                # Calculate similarity
                similarity = cosine_similarity(
                    [concept_embeddings[i]], 
                    [concept_embeddings[j]]
                )[0][0]
                
                # If similarity is high enough, create a relationship
                if similarity > 0.5:  # Threshold for relationship
                    # Determine relationship type based on context
                    relationship_type = await self._determine_relationship_type(
                        concept1["term"], 
                        concept2["term"], 
                        normalized_document
                    )
                    
                    relationships.append({
                        "from": concept1["term"],
                        "to": concept2["term"],
                        "type": relationship_type,
                        "strength": float(similarity),
                        "description": f"{concept1['term']} is related to {concept2['term']}"
                    })
        
        return relationships
    
    async def _determine_relationship_type(self, concept1: str, concept2: str, normalized_document: NormalizedDocument) -> str:
        """
        Determine the type of relationship between two concepts
        """
        all_content = " ".join([section["content"] for section in normalized_document.sections])
        text_lower = all_content.lower()
        
        # Look for specific relationship indicators
        concept1_pos = text_lower.find(concept1.lower())
        concept2_pos = text_lower.find(concept2.lower())
        
        if concept1_pos == -1 or concept2_pos == -1:
            return "related_to"
        
        # Get the text between the concepts
        start_pos = min(concept1_pos, concept2_pos)
        end_pos = max(concept1_pos, concept2_pos)
        distance = abs(concept1_pos - concept2_pos)
        
        # Extract context around the concepts
        context_start = max(0, start_pos - 10)
        context_end = min(len(all_content), end_pos + 100)
        context = all_content[context_start:context_end].lower()
        
        # Check for specific relationship patterns
        if re.search(rf"{re.escape(concept1.lower())}.*?causes.*?{re.escape(concept2.lower())}|{re.escape(concept2.lower())}.*?caused by.*?{re.escape(concept1.lower())}", context):
            return "causes"
        elif re.search(rf"{re.escape(concept1.lower())}.*?part of.*?{re.escape(concept2.lower())}|{re.escape(concept2.lower())}.*?contains.*?{re.escape(concept1.lower())}", context):
            return "part_of"
        elif re.search(rf"{re.escape(concept1.lower())}.*?is a.*?{re.escape(concept2.lower())}|{re.escape(concept1.lower())}.*?type of.*?{re.escape(concept2.lower())}", context):
            return "is_a"
        elif re.search(rf"{re.escape(concept1.lower())}.*?contrasts with.*?{re.escape(concept2.lower())}|{re.escape(concept1.lower())}.*?opposite of.*?{re.escape(concept2.lower())}", context):
            return "contrasts_with"
        elif distance < 100:  # Concepts appear close together
            return "associated_with"
        else:
            return "related_to"
    
    async def _build_knowledge_graph(self, concepts: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a knowledge graph from concepts and relationships
        """
        graph = {
            "nodes": [],
            "edges": []
        }
        
        # Add nodes (concepts)
        for concept in concepts:
            graph["nodes"].append({
                "id": concept["term"],
                "label": concept["term"],
                "properties": {
                    "definition": concept["definition"],
                    "importance": concept["importance_score"],
                    "category": concept["category"]
                }
            })
        
        # Add edges (relationships)
        for relationship in relationships:
            graph["edges"].append({
                "from": relationship["from"],
                "to": relationship["to"],
                "label": relationship["type"],
                "properties": {
                    "strength": relationship["strength"],
                    "description": relationship["description"]
                }
            })
        
        return graph
    
    async def _create_concept_map(self, concepts: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a concept map representation for visualization
        """
        # Select top concepts for the map (to avoid overcrowding)
        top_concepts = sorted(concepts, key=lambda x: x["importance_score"], reverse=True)[:20]
        top_concept_terms = [c["term"] for c in top_concepts]
        
        # Filter relationships to only include top concepts
        filtered_relationships = [
            r for r in relationships 
            if r["from"] in top_concept_terms and r["to"] in top_concept_terms
        ]
        
        concept_map = {
            "nodes": [
                {
                    "id": c["term"],
                    "label": c["term"],
                    "importance": c["importance_score"],
                    "definition": c["definition"][:100] + "..." if len(c["definition"]) > 100 else c["definition"]
                } for c in top_concepts
            ],
            "edges": filtered_relationships,
            "metadata": {
                "total_concepts": len(concepts),
                "top_concepts_count": len(top_concepts),
                "relationships_count": len(filtered_relationships)
            }
        }
        
        return concept_map
    
    async def _chunk_content(self, normalized_document: NormalizedDocument) -> List[Dict[str, Any]]:
        """
        Chunk the document content for processing
        """
        chunks = []
        current_chunk = ""
        chunk_size = 0
        max_chunk_size = 1000  # tokens/approximate words
        
        for section in normalized_document.sections:
            section_text = section["content"]
            
            if len(current_chunk) + len(section_text) < max_chunk_size:
                current_chunk += " " + section_text
                chunk_size += len(section_text)
            else:
                if current_chunk.strip():
                    chunks.append({
                        "content": current_chunk.strip(),
                        "metadata": {
                            "position": section["position"],
                            "type": section["type"]
                        }
                    })
                
                current_chunk = section_text
                chunk_size = len(section_text)
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "metadata": {
                    "position": normalized_document.sections[-1]["position"] if normalized_document.sections else {"page": 1, "order": 1},
                    "type": normalized_document.sections[-1]["type"] if normalized_document.sections else "paragraph"
                }
            })
        
        return chunks


# Singleton instance
content_analyzer = ContentAnalyzer()