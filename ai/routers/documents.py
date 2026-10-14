import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import io
import re

from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateDocumentRequest(BaseModel):
    document_type: str
    jurisdiction: str
    parties: str
    document_purpose: str
    clauses: list[str] = []
    special_provisions: list[str] = []
    conversation_summary: str | None = None
    full_context: str | None = None


class GenerateDocumentResponse(BaseModel):
    content_markdown: str
    title: str
    document_type: str


def markdown_to_pdf_bytes(title: str, content_markdown: str) -> bytes:
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1.2 * inch,
        leftMargin=1.2 * inch,
        topMargin=1.2 * inch,
        bottomMargin=1.2 * inch,
    )

    styles = getSampleStyleSheet()

    doc_title_style = ParagraphStyle(
        'DocTitle',
        fontSize=18,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor('#1a1a1a'),
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontSize=10,
        fontName='Helvetica',
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#666666'),
    )

    heading1_style = ParagraphStyle(
        'H1',
        fontSize=12,
        fontName='Helvetica-Bold',
        spaceBefore=16,
        spaceAfter=6,
        textColor=colors.HexColor('#1a1a1a'),
        borderPad=4,
    )

    heading2_style = ParagraphStyle(
        'H2',
        fontSize=11,
        fontName='Helvetica-Bold',
        spaceBefore=12,
        spaceAfter=4,
        textColor=colors.HexColor('#333333'),
    )

    body_style = ParagraphStyle(
        'Body',
        fontSize=10,
        fontName='Helvetica',
        leading=16,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#1a1a1a'),
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        fontSize=10,
        fontName='Helvetica',
        leading=15,
        spaceAfter=4,
        leftIndent=20,
        textColor=colors.HexColor('#1a1a1a'),
    )

    story = []

    # Header
    story.append(Paragraph(title, doc_title_style))
    story.append(Paragraph("Legal Document", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a1a1a')))
    story.append(Spacer(1, 0.2 * inch))

    lines = content_markdown.split('\n')
    skip_first_h1 = True

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            story.append(Spacer(1, 0.05 * inch))
            continue
        if line_stripped.startswith('```'):
            continue
        if line_stripped.startswith('# '):
            if skip_first_h1:
                skip_first_h1 = False
                continue
            story.append(Paragraph(line_stripped[2:], heading1_style))
        elif line_stripped.startswith('## '):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc')))
            story.append(Paragraph(line_stripped[3:], heading1_style))
        elif line_stripped.startswith('### '):
            story.append(Paragraph(line_stripped[4:], heading2_style))
        elif line_stripped.startswith('---'):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc')))
            story.append(Spacer(1, 0.05 * inch))
        elif line_stripped.startswith('- ') or line_stripped.startswith('* '):
            text = line_stripped[2:]
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{text}", bullet_style))
        elif re.match(r'^\d+\.', line_stripped):
            text = re.sub(r'^\d+\.\s*', '', line_stripped)
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            num = line_stripped.split('.')[0]
            story.append(Paragraph(f"<b>{num}.</b>&nbsp;&nbsp;{text}", body_style))
        else:
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line_stripped)
            # Style BLANK markers distinctly
            text = re.sub(r'\[BLANK: (.*?)\]', r'<font color="#CC0000">[ ___________ : \1 ]</font>', text)
            story.append(Paragraph(text, body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


@router.post("/generate", response_model=GenerateDocumentResponse)
def generate_document(request: GenerateDocumentRequest):
    logger.info(
        "document_generation_requested",
        extra={"document_type": request.document_type, "jurisdiction": request.jurisdiction},
    )
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )

    clauses_text = "\n".join(f"- {c}" for c in request.clauses) if request.clauses else "None specified"
    provisions_text = "\n".join(f"- {p}" for p in request.special_provisions) if request.special_provisions else "None specified"

    prompt = f"""You are a legal document drafting specialist. Generate a comprehensive, \
professionally formatted legal document based on the following context.

DOCUMENT DETAILS:
- Document Type: {request.document_type}
- Jurisdiction: {request.jurisdiction}
- Parties: {request.parties}
- Purpose: {request.document_purpose}

CLAUSES TO INCLUDE:
{clauses_text}

SPECIAL PROVISIONS:
{provisions_text}

CONVERSATION CONTEXT:
{request.conversation_summary or request.full_context or "No additional context provided."}

REQUIREMENTS:
- Generate a complete, professionally formatted legal document
- Include all standard clauses for this document type under {request.jurisdiction} law
- Include all the specific clauses and provisions listed above
- Add any additional clauses a lawyer would typically include for this document type and jurisdiction that protect both parties
- Use clear, precise legal language appropriate for {request.jurisdiction}
- Include signature blocks for all parties
- Include date fields
- Structure with clear section headings
- CRITICAL: Do NOT use bracket placeholders like [INSERT NAME] or [TBD]. For information provided \
in the context, use the actual values. For information NOT provided, use this exact format: \
**[BLANK: description]** — for example **[BLANK: Party Address]** or **[BLANK: Effective Date]**. \
This makes blanks visible and clearly labeled in both the document view and PDF.
- If any critical information is missing, make reasonable assumptions and note them at the top

Return the document in markdown format. Use ## for section headings, ### for subsections, \
**bold** for defined terms, and standard paragraph text for clause content.

Start with the document title as # heading, then a brief introduction paragraph, then the sections."""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        content_markdown = response.content.strip()
        if content_markdown.startswith("```"):
            lines = content_markdown.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            content_markdown = "\n".join(lines).strip()

        title_match = re.match(r'^#\s+(.+)', content_markdown)
        title = title_match.group(1) if title_match else f"{request.document_type} Agreement"

        logger.info(
            "document_generation_completed",
            extra={"document_type": request.document_type, "content_length": len(content_markdown)},
        )

        return GenerateDocumentResponse(
            content_markdown=content_markdown,
            title=title,
            document_type=request.document_type,
        )

    except Exception as e:
        logger.error("document_generation_failed", exc_info=True, extra={"document_type": request.document_type})
        raise HTTPException(
            status_code=500,
            detail=f"Document generation failed: {str(e)}",
        )


@router.post("/generate-pdf")
def generate_pdf(request: GenerateDocumentRequest):
    doc_response = generate_document(request)

    try:
        pdf_bytes = markdown_to_pdf_bytes(
            title=doc_response.title,
            content_markdown=doc_response.content_markdown,
        )
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{doc_response.title.replace(" ", "_")}.pdf"'
            }
        )
    except Exception as e:
        logger.error("pdf_generation_failed", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(e)}",
        )

class MarkdownToPdfRequest(BaseModel):
    title: str
    content_markdown: str

@router.post("/markdown-to-pdf")
def markdown_to_pdf(request: MarkdownToPdfRequest):
    try:
        pdf_bytes = markdown_to_pdf_bytes(
            title=request.title,
            content_markdown=request.content_markdown,
        )
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
        )
    except Exception as e:
        logger.error("pdf_conversion_failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF conversion failed: {str(e)}")