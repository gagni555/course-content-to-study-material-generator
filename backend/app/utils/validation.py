import asyncio
import logging
from typing import Dict, List, Any, Optional
from app.models.study_guide import StudyGuideContent, Question, Concept
from app.schemas.document import NormalizedDocument

logger = logging.getLogger(__name__)


class QualityAssurance:
    """
    Validates generated content for accuracy, completeness, and quality
    """
    
    def __init__(self):
        pass
    
    async def validate_study_guide(self, study_guide: StudyGuideContent, source_document: NormalizedDocument) -> Dict[str, Any]:
        """
        Validate the entire study guide against quality criteria
        """
        validation_results = {
            "overall_score": 0.0,
            "passed": True,
            "issues": [],
            "summary_validations": [],
            "question_validations": [],
            "concept_validations": []
        }
        
        # Validate summaries
        summary_results = await self._validate_summaries(study_guide.summary_sections, source_document)
        validation_results["summary_validations"] = summary_results["validations"]
        if not summary_results["passed"]:
            validation_results["passed"] = False
            validation_results["issues"].extend(summary_results["issues"])
        
        # Validate questions
        question_results = await self._validate_questions(study_guide.questions, source_document)
        validation_results["question_validations"] = question_results["validations"]
        if not question_results["passed"]:
            validation_results["passed"] = False
            validation_results["issues"].extend(question_results["issues"])
        
        # Validate concepts
        concept_results = await self._validate_concepts(study_guide.concepts, source_document)
        validation_results["concept_validations"] = concept_results["validations"]
        if not concept_results["passed"]:
            validation_results["passed"] = False
            validation_results["issues"].extend(concept_results["issues"])
        
        # Calculate overall score
        total_checks = len(validation_results["summary_validations"]) + len(validation_results["question_validations"]) + len(validation_results["concept_validations"])
        passed_checks = sum(1 for v in validation_results["summary_validations"] if v["passed"]) + \
                       sum(1 for v in validation_results["question_validations"] if v["passed"]) + \
                       sum(1 for v in validation_results["concept_validations"] if v["passed"])
        
        validation_results["overall_score"] = passed_checks / total_checks if total_checks > 0 else 0.0
        
        return validation_results
    
    async def _validate_summaries(self, summaries: List, source_document: NormalizedDocument) -> Dict[str, Any]:
        """
        Validate summary sections
        """
        results = {
            "passed": True,
            "issues": [],
            "validations": []
        }
        
        all_content = " ".join([section["content"] for section in source_document.sections])
        
        for i, summary in enumerate(summaries):
            validation = {
                "section": f"summary_{i}",
                "passed": True,
                "issues": []
            }
            
            # Check if summary content is in source document (factual accuracy)
            if not self._check_content_in_source(summary.content, all_content):
                validation["passed"] = False
                validation["issues"].append("Summary contains information not present in source document")
                results["passed"] = False
                results["issues"].append(f"Summary {i} contains information not present in source document")
            
            # Check for minimum length
            if len(summary.content.strip()) < 50:
                validation["passed"] = False
                validation["issues"].append("Summary is too short")
                results["passed"] = False
                results["issues"].append(f"Summary {i} is too short")
            
            results["validations"].append(validation)
        
        return results
    
    async def _validate_questions(self, questions: List[Question], source_document: NormalizedDocument) -> Dict[str, Any]:
        """
        Validate questions
        """
        results = {
            "passed": True,
            "issues": [],
            "validations": []
        }
        
        all_content = " ".join([section["content"] for section in source_document.sections])
        
        for i, question in enumerate(questions):
            validation = {
                "section": f"question_{i}",
                "passed": True,
                "issues": []
            }
            
            # Check if question can be answered from source content
            if not self._check_question_answerable(question.question_text, all_content):
                validation["passed"] = False
                validation["issues"].append("Question cannot be answered from source content")
                results["passed"] = False
                results["issues"].append(f"Question {i} cannot be answered from source content")
            
            # For multiple choice questions, validate options
            if question.question_type == "multiple_choice" and question.options:
                if len(question.options) < 2:
                    validation["passed"] = False
                    validation["issues"].append("Multiple choice question has fewer than 2 options")
                    results["passed"] = False
                    results["issues"].append(f"Multiple choice question {i} has fewer than 2 options")
                
                # Check if correct answer is in options
                if question.correct_answer not in question.options:
                    validation["passed"] = False
                    validation["issues"].append("Correct answer is not among the options")
                    results["passed"] = False
                    results["issues"].append(f"Question {i} correct answer is not in options")
            
            # Check for ambiguity
            if self._check_question_ambiguous(question.question_text):
                validation["issues"].append("Question appears ambiguous")
                # Note: Ambiguous questions don't necessarily fail validation, but should be flagged
            
            results["validations"].append(validation)
        
        return results
    
    async def _validate_concepts(self, concepts: List[Concept], source_document: NormalizedDocument) -> Dict[str, Any]:
        """
        Validate concepts
        """
        results = {
            "passed": True,
            "issues": [],
            "validations": []
        }
        
        all_content = " ".join([section["content"] for section in source_document.sections])
        
        for i, concept in enumerate(concepts):
            validation = {
                "section": f"concept_{i}",
                "passed": True,
                "issues": []
            }
            
            # Check if concept is mentioned in source document
            if not self._check_content_in_source(concept.term, all_content):
                validation["passed"] = False
                validation["issues"].append(f"Concept '{concept.term}' not found in source document")
                results["passed"] = False
                results["issues"].append(f"Concept {i} '{concept.term}' not found in source document")
            
            # Check definition quality
            if len(concept.definition.strip()) < 10:
                validation["issues"].append(f"Definition for '{concept.term}' is too short")
            
            # Check for duplicate concepts
            other_concepts = [c for j, c in enumerate(concepts) if j != i]
            if any(self._check_concept_similarity(concept, other_concept) for other_concept in other_concepts):
                validation["issues"].append(f"Concept '{concept.term}' appears to be duplicate")
            
            results["validations"].append(validation)
        
        return results
    
    def _check_content_in_source(self, content: str, source: str) -> bool:
        """
        Check if content is present in source (with some tolerance for paraphrasing)
        """
        content_lower = content.lower()
        source_lower = source.lower()
        
        # Simple keyword matching with some tolerance
        content_words = set(content_lower.split()[:10])  # Check first 10 words
        source_words = set(source_lower.split())
        
        # At least 50% of content words should be in source
        if content_words:
            matching_words = content_words.intersection(source_words)
            return len(matching_words) / len(content_words) >= 0.5
        return True  # Empty content is considered valid
    
    def _check_question_answerable(self, question: str, source: str) -> bool:
        """
        Check if a question can be answered based on source content
        """
        # This is a simplified check - in a full implementation, 
        # we would use more sophisticated NLP techniques
        question_lower = question.lower()
        source_lower = source.lower()
        
        # Extract key terms from question
        import re
        question_terms = re.findall(r'\b\w{3,}\b', question_lower)
        
        # Check if most terms appear in source
        found_terms = [term for term in question_terms if term in source_lower]
        return len(found_terms) / len(question_terms) >= 0.6 if question_terms else True
    
    def _check_question_ambiguous(self, question: str) -> bool:
        """
        Check if a question is ambiguous
        """
        ambiguous_indicators = [
            "or", "either", "whether", "might", "could", "possibly"
        ]
        
        question_lower = question.lower()
        count = sum(1 for indicator in ambiguous_indicators if indicator in question_lower)
        return count > 2  # If more than 2 ambiguous indicators, flag as ambiguous
    
    def _check_concept_similarity(self, concept1: Concept, concept2: Concept) -> bool:
        """
        Check if two concepts are similar enough to be considered duplicates
        """
        # Simple string similarity check
        term1, term2 = concept1.term.lower(), concept2.term.lower()
        
        # Check if terms are similar (with some tolerance)
        if abs(len(term1) - len(term2)) <= 2:
            common_chars = sum(1 for a, b in zip(term1, term2) if a == b)
            similarity = common_chars / max(len(term1), len(term2), 1)
            return similarity > 0.8
        
        return False


# Singleton instance
quality_assurance = QualityAssurance()