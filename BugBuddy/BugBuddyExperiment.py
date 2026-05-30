
import re 
import io, zipfile, tarfile, gzip, bz2
from striprtf.striprtf import rtf_to_text
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from openpyxl import load_workbook



def remove_color_tags(text):
    # Removes {color}, {color:#hex}, {color:name}, {/color}, etc.
    return re.sub(r'\{/?color[^}]*\}', '', text)

def clean_jira_markup(text):
    if not text:
        return ""
    text = re.sub(r'\{[^}]+\}', '', text)          # remove {color}, {panel}, etc.
    text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', text)  # remove *bold* / **bold**
    text = re.sub(r'_(.*?)_', r'\1', text)          # remove _italic_
    text = re.sub(r'\[([^\|]+)\|[^\]]+\]', r'\1', text)  # [label|url] → label
    text = re.sub(r'h[1-6]\.\s*', '', text)         # remove h1. h2. headings
    text = re.sub(r'^\s*\*\s+', '- ', text, flags=re.MULTILINE)  # * bullet → -
    return text.strip()


def read_attachment(jira, attachment):
    raw_bytes = jira._session.get(attachment.content).content
    name = attachment.filename

    try:
        # RTF
        if name.endswith(".rtf") or raw_bytes[:5] == b'{\\rtf':
            return rtf_to_text(raw_bytes.decode("latin-1"))

        # PDF
        if name.endswith(".pdf") or raw_bytes[:4] == b'%PDF':
            return extract_pdf_text(io.BytesIO(raw_bytes))

        # DOCX (Word)
        if name.endswith(".docx"):
            doc = Document(io.BytesIO(raw_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        # XLSX (Excel)
        if name.endswith(".xlsx"):
            wb = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
            parts = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                parts.append(f"=== Sheet: {sheet} ===")
                for row in ws.iter_rows(values_only=True):
                    line = "\t".join(str(c) if c is not None else "" for c in row)
                    if line.strip():
                        parts.append(line)
            return "\n".join(parts)

        # TAR.BZ2
        if name.endswith((".tar.bz2", ".tbz2")) or raw_bytes[:3] == b'BZh':
            with tarfile.open(fileobj=io.BytesIO(raw_bytes), mode="r:bz2") as tf:
                parts = []
                for m in tf.getmembers():
                    f = tf.extractfile(m)
                    if f:
                        parts.append(f"=== {m.name} ===\n{f.read().decode('utf-8', errors='replace')}")
                return "\n\n".join(parts)

        # ZIP
        if zipfile.is_zipfile(io.BytesIO(raw_bytes)):
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                return "\n\n".join(
                    f"=== {n} ===\n{zf.read(n).decode('utf-8', errors='replace')}"
                    for n in zf.namelist()
                )
        # GZIP
        if raw_bytes[:2] == b'\x1f\x8b':
            raw_bytes = gzip.decompress(raw_bytes)
        
        # TAR (after possible gzip decompress)
        if tarfile.is_tarfile(io.BytesIO(raw_bytes)):
            with tarfile.open(fileobj=io.BytesIO(raw_bytes)) as tf:
                parts = []
                for m in tf.getmembers():
                    f = tf.extractfile(m)
                    if f:
                        parts.append(f"=== {m.name} ===\n{f.read().decode('utf-8', errors='replace')}")
                return "\n\n".join(parts)

        # Everything else → plain text
        return raw_bytes.decode("utf-8", errors="replace")

    except Exception as e:
        return f"Could not read {name}: {e}"




""" access Jira API to fetch the details of the issue and print the summary and description of the issue. """
from jira import JIRA

jira = JIRA(
    server=" https://jira.ngage.netapp.com",
    token_auth="ODQ2Mzc5NzIwMTMxOmlV9HWBWemi4GuzntuAG3lh1Sy8"
)


issue = jira.issue("CFSHELF-5078")
print(issue.fields.summary)
print(issue.fields.description)
print(issue.fields.status.name)
print(issue.fields.reporter.displayName)
print(issue.fields.subtasks)

description = issue.fields.description or ""
clean_description = remove_color_tags(description)
print(clean_description)

print(clean_jira_markup(issue.fields.description))



#issue = jira.issue("CFSHELF-3926", expand="renderedFields")
#print(issue.renderedFields.description)  # 

# Check if attachments exist
attachments = issue.fields.attachment
if attachments:
    print(f"Found {len(attachments)} attachment(s):")
    for attachment in attachments:
        print(f"  - {attachment.filename} ({attachment.size} bytes)")
        print(f"    URL: {attachment.content}")
else:
    print("No attachments")






# Usage
issue = jira.issue("CFSHELF-5078")
for att in issue.fields.attachment:
    print(f"\n{'='*40}\n{att.filename}\n{'='*40}")
    print(read_attachment(jira, att))


