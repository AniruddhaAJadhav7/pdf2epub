import io
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from ebooklib import epub
from docx import Document
from PIL import Image
import fitz  # PyMuPDF
import xml.etree.ElementTree as ET
import uuid
import pdfplumber  # New addition to handle tables

# Function to extract images from a PDF file
def extract_images_from_pdf(pdf_content):
    images = []
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))
            images.append((f"image_{page_num}_{img_index}.{image_ext}", image))
    return images

# Function to extract tables from PDF using pdfplumber
def extract_tables_from_pdf(pdf_content):
    tables = []
    with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables())
    return tables

# Enhanced PDF to EPUB conversion function
def pdf_to_epub(pdf_content, original_filename):
    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(original_filename.rsplit('.', 1)[0])
    book.set_language('en')

    # Extract text
    output = io.StringIO()
    extract_text_to_fp(io.BytesIO(pdf_content), output, laparams=LAParams())
    pdf_text = output.getvalue()

    # Extract images
    images = extract_images_from_pdf(pdf_content)

    # Extract tables
    tables = extract_tables_from_pdf(pdf_content)

    # Create chapters for text
    chapters = []
    for i, paragraph in enumerate(pdf_text.split('\n\n')):
        if paragraph.strip():
            chapter = epub.EpubHtml(title=f'Section {i + 1}', file_name=f'section_{i + 1}.xhtml')
            chapter.content = f'<h2>Section {i + 1}</h2><p>{paragraph}</p>'
            book.add_item(chapter)
            chapters.append(chapter)

    # Add tables as separate sections
    for table_index, table in enumerate(tables):
        table_html = '<table border="1" style="width:100%; border-collapse: collapse;">'
        for row in table:
            table_html += '<tr>' + ''.join([f'<td>{cell}</td>' for cell in row]) + '</tr>'
        table_html += '</table>'
        
        table_chapter = epub.EpubHtml(title=f'Table {table_index + 1}', file_name=f'table_{table_index + 1}.xhtml')
        table_chapter.content = f'<h2>Table {table_index + 1}</h2>{table_html}'
        book.add_item(table_chapter)
        chapters.append(table_chapter)

    # Add images
    for img_filename, img in images:
        img_item = epub.EpubImage()
        img_item.file_name = f"images/{img_filename}"
        img_buffer = io.BytesIO()
        img.save(img_buffer, format=img.format)
        img_item.content = img_buffer.getvalue()
        book.add_item(img_item)

        # Add image to a new chapter
        img_chapter = epub.EpubHtml(title=f'Image: {img_filename}', file_name=f'image_{img_filename}.xhtml')
        img_chapter.content = f'<img src="images/{img_filename}" alt="{img_filename}"/>'
        book.add_item(img_chapter)
        chapters.append(img_chapter)

    # Define Table of Contents
    book.toc = tuple(chapters)

    # Add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define CSS style
    style = '''
        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
        h1, h2 { color: #2c3e50; }
        p { text-align: justify; }
        img { max-width: 100%; height: auto; display: block; margin: 20px auto; }
        table { width: 100%; border-collapse: collapse; margin: 20px auto; }
        td, th { border: 1px solid #000; padding: 8px; text-align: left; }
    '''
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    # Add CSS file
    book.add_item(epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=style))

    # Write to in-memory file
    epub_file = io.BytesIO()
    epub.write_epub(epub_file, book, {})
    epub_file.seek(0)

    return epub_file

# DOCX to EPUB conversion with improved image and table handling
def docx_to_epub(docx_content, original_filename):
    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(original_filename.rsplit('.', 1)[0])
    book.set_language('en')

    doc = Document(io.BytesIO(docx_content))

    chapters = []
    for i, paragraph in enumerate(doc.paragraphs):
        if paragraph.text.strip():
            chapter = epub.EpubHtml(title=f'Paragraph {i + 1}', file_name=f'paragraph_{i + 1}.xhtml')
            chapter.content = f'<h2>Paragraph {i + 1}</h2><p>{paragraph.text}</p>'
            book.add_item(chapter)
            chapters.append(chapter)

    # Add images
    for i, rel in enumerate(doc.part.rels.values()):
        if "image" in rel.target_ref:
            img_byte_array = rel.target_part.blob
            img = Image.open(io.BytesIO(img_byte_array))
            img_filename = f"image_{i}.{img.format.lower()}"
            
            img_item = epub.EpubImage()
            img_item.file_name = f"images/{img_filename}"
            img_item.content = img_byte_array
            book.add_item(img_item)

            # Add image to a new chapter
            img_chapter = epub.EpubHtml(title=f'Image: {img_filename}', file_name=f'image_{img_filename}.xhtml')
            img_chapter.content = f'<img src="images/{img_filename}" alt="{img_filename}"/>'
            book.add_item(img_chapter)
            chapters.append(img_chapter)

    # Define Table of Contents
    book.toc = tuple(chapters)

    # Add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define CSS style
    style = '''
        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
        h1, h2 { color: #2c3e50; }
        p { text-align: justify; }
        img { max-width: 100%; height: auto; display: block; margin: 20px auto; }
    '''
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    # Add CSS file
    book.add_item(epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=style))

    # Write to in-memory file
    epub_file = io.BytesIO()
    epub.write_epub(epub_file, book, {})
    epub_file.seek(0)

    return epub_file
