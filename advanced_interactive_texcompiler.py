import streamlit as st
import os
import subprocess
from datetime import datetime
import re
import base64
from streamlit_ace import st_ace
import tempfile
import pdfminer
from pdfminer.high_level import extract_text
import fitz  # PyMuPDF

# Page config
st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")
st.title("📄 Elsevier LaTeX Compiler")

# File path setup
script_dir = os.path.dirname(os.path.abspath(__file__))
manuscript_dir = os.path.join(script_dir, "manuscript")

if not os.path.exists(manuscript_dir):
    st.error("❌ `manuscript/` directory not found.")
    st.stop()

# Load first .tex file found
tex_file_path = next((os.path.join(manuscript_dir, f) for f in os.listdir(manuscript_dir) if f.endswith(".tex")), None)
if not tex_file_path:
    st.error("❌ No `.tex` file found in `manuscript/`.")
    st.stop()

with open(tex_file_path, "r", encoding="utf-8") as f:
    tex_content = f.read()

# Extract TOC from LaTeX with more comprehensive pattern
def extract_toc_lines(content):
    toc = []
    # Pattern now captures chapters, parts, and numbered/unnumbered sections
    pattern = re.compile(r'\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\{([^}]*)\}')
    for i, line in enumerate(content.splitlines()):
        match = pattern.search(line)
        if match:
            level, title = match.group(1), match.group(2)
            indent = {
                "part": 0,
                "chapter": 1,
                "section": 2,
                "subsection": 3,
                "subsubsection": 4,
                "paragraph": 5,
                "subparagraph": 6
            }.get(level, 2)  # Default to section level if unknown
            toc.append({
                "title": title,
                "line": i,
                "indent": indent,
                "level": level,
                "full_line": line.strip()
            })
    return toc

toc_items = extract_toc_lines(tex_content)

# Initialize session state for editor and PDF
if 'editor_content' not in st.session_state:
    st.session_state.editor_content = tex_content
if 'selected_line' not in st.session_state:
    st.session_state.selected_line = 0
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = None
if 'last_compiled' not in st.session_state:
    st.session_state.last_compiled = None

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ Edit LaTeX File")

    # Enhanced TOC with hierarchy display and search
    with st.expander("📚 Table of Contents (Click to navigate)", expanded=True):
        if toc_items:
            search_query = st.text_input("🔍 Search sections...", "")
            
            # Filter TOC based on search
            filtered_toc = [item for item in toc_items 
                          if search_query.lower() in item['title'].lower()] if search_query else toc_items
            
            for i, item in enumerate(filtered_toc):
                # Create indentation based on level
                indent_space = "&nbsp;" * 4 * item['indent']
                button_label = f"{indent_space}▸ {item['title']} ({item['level']})"
                
                # Use columns to create a more structured layout
                col_a, col_b = st.columns([6, 1])
                with col_a:
                    if st.button(button_label, key=f"toc_{i}"):
                        st.session_state.selected_line = item["line"]
                with col_b:
                    if st.button("⚡", key=f"jump_{i}", help=f"Jump to {item['title']}"):
                        st.session_state.selected_line = item["line"]
        else:
            st.info("No sections found in LaTeX.")

    # Editor with persistent state and better navigation
    editor_args = {
        "value": st.session_state.editor_content,
        "language": "latex",
        "theme": "monokai",
        "key": "tex_editor",
        "height": 600,
        "cursor_position": (st.session_state.selected_line, 0),
        "auto_update": True,
        "font_size": 14,
        "wrap": True
    }
    
    edited_tex = st_ace(**editor_args)
    st.session_state.editor_content = edited_tex

    # Compilation controls
    auto_compile = st.checkbox("🔁 Auto-compile after saving", value=False)
    compile_triggered = False

    col_save, col_compile = st.columns(2)
    with col_save:
        if st.button("💾 Save Changes", help="Save changes to the LaTeX file"):
            with open(tex_file_path, "w", encoding="utf-8") as f:
                f.write(edited_tex)
            st.success("✅ Changes saved.")
            if auto_compile:
                compile_triggered = True
                st.rerun()  # Trigger a rerun to immediately show compilation

    with col_compile:
        if st.button("🛠 Compile LaTeX", help="Compile the LaTeX document to PDF"):
            compile_triggered = True
            st.rerun()  # Trigger a rerun to immediately show compilation

    if compile_triggered:
        try:
            with st.spinner("⏳ Compiling LaTeX..."):
                result = subprocess.run(
                    ["latexmk", "-pdf", "-interaction=nonstopmode", tex_file_path],
                    cwd=manuscript_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                pdf_path = os.path.splitext(tex_file_path)[0] + ".pdf"
                if result.returncode == 0 and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.session_state.pdf_data = f.read()
                    st.session_state.pdf_filename = f"compiled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    st.session_state.last_compiled = datetime.now()
                    st.success("✅ PDF compiled successfully.")
                else:
                    st.error("❌ Compilation failed.")
                    with st.expander("🔍 View compilation log"):
                        st.text_area("latexmk Output", result.stdout + result.stderr, height=200)
        except subprocess.TimeoutExpired:
            st.error("⏳ Compilation timed out.")
        except Exception as e:
            st.error(f"⚠️ Error: {e}")

with col2:
    st.subheader("📄 PDF Preview")
    
    if st.session_state.pdf_data:
        # Enhanced PDF viewing options
        pdf_view_mode = st.radio(
            "View Mode:",
            ["Embedded", "Text Content", "Page Images"],
            horizontal=True,
            help="Choose how to display the PDF"
        )
        
        if pdf_view_mode == "Embedded":
            # Improved embedded viewer with page navigation
            b64_pdf = base64.b64encode(st.session_state.pdf_data).decode("utf-8")
            pdf_view = f"""
            <iframe src="data:application/pdf;base64,{b64_pdf}#toolbar=1&navpanes=1&scrollbar=1"
                    width="100%" height="600" type="application/pdf"></iframe>
            """
            st.markdown(pdf_view, unsafe_allow_html=True)
            
        elif pdf_view_mode == "Text Content":
            # Extract text content from PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(st.session_state.pdf_data)
                tmp_path = tmp.name
            
            try:
                text = extract_text(tmp_path)
                st.text_area("PDF Text Content", text, height=600)
            except Exception as e:
                st.error(f"Failed to extract text: {e}")
            finally:
                os.unlink(tmp_path)
                
        elif pdf_view_mode == "Page Images":
            # Display PDF as page images with navigation
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(st.session_state.pdf_data)
                tmp_path = tmp.name
            
            try:
                doc = fitz.open(tmp_path)
                total_pages = doc.page_count
                
                col_page1, col_page2 = st.columns([2, 3])
                with col_page1:
                    page_num = st.number_input(
                        "Page number", 
                        min_value=1, 
                        max_value=total_pages, 
                        value=1,
                        step=1
                    )
                
                page = doc.load_page(page_num - 1)
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                
                st.image(img_bytes, caption=f"Page {page_num} of {total_pages}", use_column_width=True)
                
            except Exception as e:
                st.error(f"Failed to render PDF pages: {e}")
            finally:
                doc.close()
                os.unlink(tmp_path)
        
        # Download button
        st.download_button(
            "📥 Download PDF", 
            st.session_state.pdf_data, 
            file_name=st.session_state.pdf_filename, 
            mime="application/pdf"
        )
        
        if st.session_state.last_compiled:
            st.caption(f"Last compiled: {st.session_state.last_compiled.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.info("🛈 PDF not compiled yet. Click **Compile LaTeX** after saving.")

st.markdown("---")
st.markdown("""
**Instructions:**
1. Click a section in the Table of Contents to jump to it.
2. Edit your LaTeX file in the left panel.
3. Save and compile LaTeX.
4. View and download the PDF in the right panel.

📁 `manuscript/` should include:
- `.tex` file
- `cas-sc.cls` (or journal class)
- Images and `.bib` files

**New Features:**
- Enhanced TOC with hierarchical display and search
- Multiple PDF viewing modes (embedded, text, page images)
- Persistent editor state between compilations
- Improved navigation and UI
""")
