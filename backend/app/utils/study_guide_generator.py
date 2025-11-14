import asyncio
import logging
from typing import Dict, List, Any, Optional
from app.schemas.document import NormalizedDocument
from app.models.study_guide import StudyGuideContent, SummarySection, Question, Concept
from app.utils.content_analyzer import content_analyzer
from app.utils.validation import quality_assurance
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from app.config import settings
import json

logger = logging.getLogger(__name__)


class StudyGuideGenerator:
    """
    Generates study guides with summaries, questions, and concept maps from analyzed content
    """
    
    def __init__(self):
        # Initialize LLMs based on settings
        if settings.anthropic_api_key:
            self.primary_llm = ChatAnthropic(
                model_name=settings.default_llm_model,
                temperature=0.3,
                anthropic_api_key=settings.anthropic_api_key
            )
        elif settings.openai_api_key:
            self.primary_llm = ChatOpenAI(
                model_name="gpt-4",
                temperature=0.3,
                openai_api_key=settings.openai_api_key
            )
        else:
            # Fallback to a mock or local model for testing
            self.primary_llm = None
            logger.warning("No LLM API key found. Using mock responses for testing.")
    
    async def generate_study_guide(
        self, 
        normalized_document: NormalizedDocument, 
        detail_level: str = "standard",
        include_questions: bool = True,
        include_concept_map: bool = True,
        include_flashcards: bool = True
    ) -> StudyGuideContent:
        """
        Generate a complete study guide from the normalized document
        """
        try:
            # Analyze the content to extract concepts and relationships
            analysis_result = await content_analyzer.analyze_content(normalized_document)
            
            # Generate summaries based on Bloom's Taxonomy
            summary_sections = await self._generate_summaries(
                normalized_document, 
                analysis_result, 
                detail_level
            )
            
            # Generate practice questions
            questions = []
            if include_questions:
                questions = await self._generate_questions(
                    normalized_document, 
                    analysis_result, 
                    detail_level
                )
            
            # Prepare concepts for the study guide
            concepts = [
                Concept(
                    term=c["term"],
                    definition=c["definition"],
                    importance_score=c["importance_score"],
                    related_concepts=c.get("related_concepts", []),
                    examples=c.get("examples", []),
                    page_reference=c.get("page_reference", "1")
                )
                for c in analysis_result["concepts"]
            ]
            
            # Create concept map
            concept_map = analysis_result["concept_map"] if include_concept_map else None
            
            # Generate flashcards
            flashcards = []
            if include_flashcards:
                flashcards = await self._generate_flashcards(concepts)
            
            study_guide = StudyGuideContent(
                title=normalized_document.metadata.get("title", "Study Guide"),
                summary_sections=summary_sections,
                questions=questions,
                concepts=concepts,
                concept_map=concept_map,
                flashcards=flashcards
            )
            
            # Validate the generated study guide
            validation_results = await quality_assurance.validate_study_guide(study_guide, normalized_document)
            
            # Log validation results
            logger.info(f"Study guide validation completed. Score: {validation_results['overall_score']:.2f}")
            if not validation_results['passed']:
                logger.warning(f"Study guide validation issues: {validation_results['issues']}")
            
            return study_guide
        except Exception as e:
            logger.error(f"Error generating study guide: {str(e)}")
            raise
    
    async def _generate_summaries(
        self, 
        normalized_document: NormalizedDocument, 
        analysis_result: Dict[str, Any], 
        detail_level: str
    ) -> List[SummarySection]:
        """
        Generate multi-level summaries following Bloom's Taxonomy
        """
        try:
            # Determine content length for appropriate summary length
            all_content = " ".join([section["content"] for section in normalized_document.sections])
            content_length = len(all_content)
            
            # Define summary lengths based on detail level
            if detail_level == "brief":
                max_length = min(500, content_length // 4)
            elif detail_level == "detailed":
                max_length = min(2000, content_length // 2)
            else:  # standard
                max_length = min(1000, content_length // 3)
            
            # Create a summary for each Bloom's level
            bloom_levels = [
                ("remember", "Focus on key facts, definitions, and terminology"),
                ("understand", "Explain main concepts and ideas in your own words"),
                ("apply", "Show how concepts can be used in practical situations"),
                ("analyze", "Break down complex ideas and examine relationships"),
                ("evaluate", "Assess the validity of arguments and evidence"),
                ("create", "Combine elements in new ways to form a unique whole")
            ]
            
            summaries = []
            
            for level, description in bloom_levels:
                summary_content = await self._generate_single_summary(
                    normalized_document, 
                    level, 
                    description, 
                    max_length
                )
                
                if summary_content:
                    summaries.append(SummarySection(
                        level=level,
                        content=summary_content,
                        examples=[]
                    ))
            
            return summaries
        except Exception as e:
            logger.error(f"Error generating summaries: {str(e)}")
            # Return a basic summary in case of error
            all_content = " ".join([section["content"] for section in normalized_document.sections])
            return [SummarySection(
                level="understand",
                content=all_content[:500] + "..." if len(all_content) > 500 else all_content,
                examples=[]
            )]
    
    async def _generate_single_summary(
        self, 
        normalized_document: NormalizedDocument, 
        bloom_level: str, 
        description: str, 
        max_length: int
    ) -> str:
        """
        Generate a single summary for a specific Bloom's level
        """
        if not self.primary_llm:
            # Mock response for testing
            return f"Summary for {bloom_level} level (mock response for testing)"
        
        try:
            # Prepare document content
            content_parts = []
            for section in normalized_document.sections:
                content_parts.append(f"Section Type: {section['type']}")
                content_parts.append(f"Content: {section['content'][:500]}")  # Limit content length
            document_content = "\n\n".join(content_parts)
            
            # Create prompt for summary generation
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""
                You are an expert educational content summarizer. Your goal is to create clear, accurate summaries that help students learn.

                RULES:
                1. Preserve all key facts and definitions
                2. Use hierarchical structure (main points → supporting details)
                3. Include specific examples when provided in source
                4. Cite page numbers in [p.X] format
                5. Use active voice and present tense
                6. Never add information not in the source
                7. The summary should be appropriate for Bloom's Taxonomy level: {bloom_level}
                8. {description}
                """),
                ("human", f"""
                Document Content:
                {document_content}

                Task: Create a summary focused on the {bloom_level} level of Bloom's Taxonomy. {description}

                The summary should be comprehensive but concise, not exceeding {max_length} characters.
                """)
            ])
            
            chain = prompt | self.primary_llm
            response = await chain.ainvoke({})
            
            return response.content[:max_length]
        except Exception as e:
            logger.error(f"Error generating single summary: {str(e)}")
            return f"Summary for {bloom_level} level - Error occurred during generation"
    
    async def _generate_questions(
        self, 
        normalized_document: NormalizedDocument, 
        analysis_result: Dict[str, Any], 
        detail_level: str
    ) -> List[Question]:
        """
        Generate practice questions based on the content and concepts
        """
        if not self.primary_llm:
            # Mock response for testing
            return [
                Question(
                    id="mock1",
                    question_text="What are the key concepts in this material?",
                    question_type="short_answer",
                    correct_answer="The key concepts are defined in the material",
                    options=None,
                    difficulty="medium",
                    topic="General",
                    page_reference="1"
                )
            ]
        
        try:
            questions = []
            
            # Define question generation rules based on Bloom's levels
            bloom_questions = {
                "remember": {
                    "types": ["multiple_choice", "fill_blank", "true_false"],
                    "verbs": ["identify", "define", "recall", "list"],
                    "count": 3 if detail_level == "detailed" else 2 if detail_level == "standard" else 1
                },
                "understand": {
                    "types": ["short_answer", "matching"],
                    "verbs": ["explain", "summarize", "compare", "classify"],
                    "count": 3 if detail_level == "detailed" else 2 if detail_level == "standard" else 1
                },
                "apply": {
                    "types": ["problem_solving", "case_study"],
                    "verbs": ["calculate", "demonstrate", "apply", "solve"],
                    "count": 2 if detail_level == "detailed" else 1 if detail_level == "standard" else 1
                },
                "analyze": {
                    "types": ["short_essay", "diagram_labeling"],
                    "verbs": ["analyze", "differentiate", "investigate"],
                    "count": 1 if detail_level == "detailed" else 1 if detail_level == "standard" else 0
                }
            }
            
            # Prepare document content
            content_parts = []
            for section in normalized_document.sections:
                content_parts.append(f"Section Type: {section['type']}")
                content_parts.append(f"Content: {section['content'][:300]}")  # Limit content length
            document_content = "\n\n".join(content_parts)
            
            # Generate questions for each Bloom's level
            for bloom_level, config in bloom_questions.items():
                if config["count"] == 0:
                    continue
                
                for i in range(config["count"]):
                    question_text, question_type, correct_answer, options = await self._generate_single_question(
                        document_content, 
                        analysis_result, 
                        bloom_level, 
                        config["verbs"]
                    )
                    
                    if question_text:
                        questions.append(Question(
                            id=f"{bloom_level}_{i+1}",
                            question_text=question_text,
                            question_type=question_type,
                            correct_answer=correct_answer,
                            options=options,
                            difficulty="medium",  # Could be adjusted based on complexity
                            topic="General",  # Could be more specific based on content
                            page_reference="1"  # Would be determined from context
                        ))
            
            return questions
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            return []
    
    async def _generate_single_question(
        self, 
        document_content: str, 
        analysis_result: Dict[str, Any], 
        bloom_level: str, 
        action_verbs: List[str]
    ) -> tuple:
        """
        Generate a single question based on the content
        """
        try:
            # Select a random action verb
            import random
            action_verb = random.choice(action_verbs)
            
            # Create prompt for question generation
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""
                You are an expert educational question generator. Create questions that test understanding at the {bloom_level} level of Bloom's Taxonomy.
                
                Question types and formats:
                - multiple_choice: Provide 4 options with one correct answer
                - short_answer: Open-ended question requiring a brief explanation
                - true_false: Statement that is either true or false
                - essay: Question requiring detailed response
                - problem_solving: Question requiring application of concepts
                
                RULES:
                - Questions must be answerable from the provided content
                - Include plausible distractors for multiple choice questions
                - Questions should be clear and unambiguous
                - Match difficulty to the Bloom's level
                """),
                ("human", f"""
                Document Content:
                {document_content}
                
                Key Concepts:
                {str(analysis_result['concepts'][:5])}  # Use top 5 concepts
                
                Task: Generate a {bloom_level}-level question that uses the action verb '{action_verb}'.
                The question should be based on the provided content and test understanding at the {bloom_level} level.
                
                Respond in the following JSON format:
                {{
                    "question_text": "The actual question text",
                    "question_type": "multiple_choice|short_answer|true_false|essay|problem_solving",
                    "correct_answer": "The correct answer",
                    "options": ["Option 1", "Option 2", "Option 3", "Option 4"]  // Only for multiple_choice
                }}
                
                Make sure the response is valid JSON.
                """)
            ])
            
            chain = prompt | self.primary_llm
            response = await chain.ainvoke({})
            
            # Parse the response
            response_text = response.content.strip()
            
            # Try to extract JSON from the response
            try:
                # Look for JSON between curly braces
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    question_data = json.loads(json_str)
                    
                    return (
                        question_data.get("question_text", ""),
                        question_data.get("question_type", "short_answer"),
                        question_data.get("correct_answer", ""),
                        question_data.get("options")
                    )
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract question from text
                lines = response_text.split('\n')
                question_text = lines[0] if lines else "Sample question"
                return question_text, "short_answer", "Sample answer", None
            
            return "Sample question", "short_answer", "Sample answer", None
        except Exception as e:
            logger.error(f"Error generating single question: {str(e)}")
            return "What are the key concepts in this material?", "short_answer", "The key concepts are defined in the material", None
    
    async def _generate_flashcards(self, concepts: List[Concept]) -> List[Dict[str, str]]:
        """
        Generate flashcards from the concepts
        """
        flashcards = []
        
        for concept in concepts[:10]:  # Limit to top 10 concepts
            # Create front of card (question/prompt)
            front = f"What is {concept.term}?"
            
            # Create back of card (answer)
            back = f"{concept.definition}"
            if concept.examples:
                back += f"\n\nExample: {concept.examples[0]}"
            
            flashcards.append({
                "front": front,
                "back": back
            })
        
        return flashcards


# Singleton instance
study_guide_generator = StudyGuideGenerator()