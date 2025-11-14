import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import markdown
from weasyprint import HTML, CSS
from app.models.study_guide import StudyGuideContent
import tempfile

logger = logging.getLogger(__name__)


class Exporter:
    """
    Handles export of study guides in various formats (PDF, Markdown, HTML, Anki)
    """
    
    def __init__(self):
        self.supported_formats = ["pdf", "markdown", "html", "anki", "json"]
    
    async def export_study_guide(
        self, 
        study_guide: StudyGuideContent, 
        export_format: str, 
        output_path: Optional[str] = None
    ) -> str:
        """
        Export a study guide in the specified format
        """
        if export_format not in self.supported_formats:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        if export_format == "pdf":
            return await self._export_to_pdf(study_guide, output_path)
        elif export_format == "markdown":
            return await self._export_to_markdown(study_guide, output_path)
        elif export_format == "html":
            return await self._export_to_html(study_guide, output_path)
        elif export_format == "anki":
            return await self._export_to_anki(study_guide, output_path)
        elif export_format == "json":
            return await self._export_to_json(study_guide, output_path)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    async def _export_to_pdf(self, study_guide: StudyGuideContent, output_path: Optional[str] = None) -> str:
        """
        Export study guide to PDF format
        """
        try:
            # First export to HTML then convert to PDF
            html_content = await self._create_html_content(study_guide)
            
            # Generate output path if not provided
            if not output_path:
                output_path = f"study_guide_{study_guide.title.replace(' ', '_')}.pdf"
            
            # Convert HTML to PDF using WeasyPrint
            html_doc = HTML(string=html_content)
            css = CSS(string='''
                @page {
                    size: A4;
                    margin: 1cm;
                    @bottom-right {
                        content: "Page " counter(page) " of " counter(pages);
                    }
                }
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }
                h1 {
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }
                h2 {
                    color: #34495e;
                    margin-top: 25px;
                }
                .summary-section {
                    margin-bottom: 20px;
                }
                .question {
                    background-color: #f8f9fa;
                    padding: 10px;
                    margin: 10px 0;
                    border-left: 3px solid #3498db;
                }
                .concept {
                    background-color: #e8f4fd;
                    padding: 8px;
                    margin: 5px 0;
                    border-radius: 4px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }
                th {
                    background-color: #f2f2f2;
                }
            ''')
            
            html_doc.write_pdf(output_path, stylesheets=[css])
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting to PDF: {str(e)}")
            raise
    
    async def _export_to_markdown(self, study_guide: StudyGuideContent, output_path: Optional[str] = None) -> str:
        """
        Export study guide to Markdown format
        """
        try:
            content_parts = []
            
            # Title
            content_parts.append(f"# {study_guide.title}\n")
            
            # Summaries
            if study_guide.summary_sections:
                content_parts.append("## Summaries\n")
                for section in study_guide.summary_sections:
                    content_parts.append(f"### {section.level.title()}\n")
                    content_parts.append(f"{section.content}\n")
                    
                    if section.examples:
                        content_parts.append("**Examples:**\n")
                        for example in section.examples:
                            content_parts.append(f"- {example}\n")
                    content_parts.append("\n")
            
            # Concepts
            if study_guide.concepts:
                content_parts.append("## Key Concepts\n")
                for concept in study_guide.concepts:
                    content_parts.append(f"- **{concept.term}**: {concept.definition}\n")
                    if concept.examples:
                        content_parts.append(f"  - Examples: {', '.join(concept.examples)}\n")
                    content_parts.append("\n")
            
            # Questions
            if study_guide.questions:
                content_parts.append("## Practice Questions\n")
                for i, question in enumerate(study_guide.questions, 1):
                    content_parts.append(f"### Question {i} ({question.question_type})\n")
                    content_parts.append(f"{question.question_text}\n")
                    
                    if question.options:
                        for j, option in enumerate(question.options, 1):
                            content_parts.append(f"{j}. {option}\n")
                    
                    content_parts.append(f"\n**Answer:** {question.correct_answer}\n\n")
            
            # Flashcards
            if study_guide.flashcards:
                content_parts.append("## Flashcards\n")
                for i, card in enumerate(study_guide.flashcards, 1):
                    content_parts.append(f"**Card {i}**\n")
                    content_parts.append(f"Q: {card['front']}\n")
                    content_parts.append(f"A: {card['back']}\n\n")
            
            markdown_content = "\n".join(content_parts)
            
            # Generate output path if not provided
            if not output_path:
                output_path = f"study_guide_{study_guide.title.replace(' ', '_')}.md"
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting to Markdown: {str(e)}")
            raise
    
    async def _export_to_html(self, study_guide: StudyGuideContent, output_path: Optional[str] = None) -> str:
        """
        Export study guide to HTML format
        """
        try:
            html_content = await self._create_html_content(study_guide)
            
            # Generate output path if not provided
            if not output_path:
                output_path = f"study_guide_{study_guide.title.replace(' ', '_')}.html"
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting to HTML: {str(e)}")
            raise
    
    async def _create_html_content(self, study_guide: StudyGuideContent) -> str:
        """
        Create HTML content for the study guide
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "<meta charset='UTF-8'>",
            f"<title>{study_guide.title}</title>",
            "<style>",
            '''
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }
            h2 {
                color: #34495e;
                margin-top: 30px;
            }
            h3 {
                color: #555;
                margin-top: 20px;
            }
            .summary-section {
                background-color: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
            }
            .question {
                background-color: #f8f9fa;
                padding: 15px;
                margin: 15px 0;
                border-left: 4px solid #3498db;
                border-radius: 0 5px 5px 0;
            }
            .concept {
                background-color: #e8f4fd;
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 3px solid #1abc9c;
            }
            .flashcard {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            .bloom-level {
                display: inline-block;
                background-color: #3498db;
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                margin-right: 10px;
            }
            ''',
            "</style>",
            "</head>",
            "<body>"
        ]
        
        # Title
        html_parts.append(f"<h1>{study_guide.title}</h1>")
        
        # Summaries
        if study_guide.summary_sections:
            html_parts.append("<h2>Summaries</h2>")
            for section in study_guide.summary_sections:
                html_parts.append(f"<div class='summary-section'>")
                html_parts.append(f"<h3><span class='bloom-level'>{section.level.title()}</span> {section.level.title()} Level</h3>")
                html_parts.append(f"<p>{section.content.replace(chr(10), '<br>')}</p>")
                
                if section.examples:
                    html_parts.append("<h4>Examples:</h4><ul>")
                    for example in section.examples:
                        html_parts.append(f"<li>{example}</li>")
                    html_parts.append("</ul>")
                
                html_parts.append("</div>")
        
        # Concepts
        if study_guide.concepts:
            html_parts.append("<h2>Key Concepts</h2>")
            for concept in study_guide.concepts:
                html_parts.append(f"<div class='concept'>")
                html_parts.append(f"<h3>{concept.term}</h3>")
                html_parts.append(f"<p><strong>Definition:</strong> {concept.definition}</p>")
                
                if concept.examples:
                    html_parts.append("<p><strong>Examples:</strong> ")
                    html_parts.append(", ".join(concept.examples))
                    html_parts.append("</p>")
                
                html_parts.append("</div>")
        
        # Questions
        if study_guide.questions:
            html_parts.append("<h2>Practice Questions</h2>")
            for i, question in enumerate(study_guide.questions, 1):
                html_parts.append(f"<div class='question'>")
                html_parts.append(f"<h3>Question {i}: {question.question_type.replace('_', ' ').title()}</h3>")
                html_parts.append(f"<p>{question.question_text}</p>")
                
                if question.options:
                    html_parts.append("<ul>")
                    for j, option in enumerate(question.options, 1):
                        html_parts.append(f"<li>{j}. {option}</li>")
                    html_parts.append("</ul>")
                
                html_parts.append(f"<p><strong>Answer:</strong> {question.correct_answer}</p>")
                html_parts.append("</div>")
        
        # Flashcards
        if study_guide.flashcards:
            html_parts.append("<h2>Flashcards</h2>")
            for i, card in enumerate(study_guide.flashcards, 1):
                html_parts.append(f"<div class='flashcard'>")
                html_parts.append(f"<h3>Card {i}</h3>")
                html_parts.append(f"<p><strong>Q:</strong> {card['front']}</p>")
                html_parts.append(f"<p><strong>A:</strong> {card['back']}</p>")
                html_parts.append("</div>")
        
        html_parts.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_parts)
    
    async def _export_to_anki(self, study_guide: StudyGuideContent, output_path: Optional[str] = None) -> str:
        """
        Export flashcards to Anki format (CSV for import)
        """
        try:
            csv_lines = ["Front,Back"]  # CSV header
            
            for card in study_guide.flashcards:
                # Escape quotes and commas in the content
                front = card['front'].replace('"', '""')
                back = card['back'].replace('"', '""')
                csv_lines.append(f'"{front}","{back}"')
            
            csv_content = "\n".join(csv_lines)
            
            # Generate output path if not provided
            if not output_path:
                output_path = f"study_guide_{study_guide.title.replace(' ', '_')}_anki.csv"
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting to Anki format: {str(e)}")
            raise
    
    async def _export_to_json(self, study_guide: StudyGuideContent, output_path: Optional[str] = None) -> str:
        """
        Export study guide to JSON format
        """
        try:
            # Convert the study guide to a dictionary
            study_guide_dict = {
                "title": study_guide.title,
                "summary_sections": [
                    {
                        "level": section.level,
                        "content": section.content,
                        "examples": section.examples
                    } for section in study_guide.summary_sections
                ],
                "questions": [
                    {
                        "id": q.id,
                        "question_text": q.question_text,
                        "question_type": q.question_type,
                        "correct_answer": q.correct_answer,
                        "options": q.options,
                        "difficulty": q.difficulty,
                        "topic": q.topic,
                        "page_reference": q.page_reference
                    } for q in study_guide.questions
                ],
                "concepts": [
                    {
                        "term": c.term,
                        "definition": c.definition,
                        "importance_score": c.importance_score,
                        "related_concepts": c.related_concepts,
                        "examples": c.examples,
                        "page_reference": c.page_reference
                    } for c in study_guide.concepts
                ],
                "concept_map": study_guide.concept_map,
                "flashcards": study_guide.flashcards
            }
            
            json_content = json.dumps(study_guide_dict, indent=2, ensure_ascii=False)
            
            # Generate output path if not provided
            if not output_path:
                output_path = f"study_guide_{study_guide.title.replace(' ', '_')}.json"
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            
            return output_path
        except Exception as e:
            logger.error(f"Error exporting to JSON: {str(e)}")
            raise


# Singleton instance
exporter = Exporter()