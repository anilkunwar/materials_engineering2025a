import streamlit as st
import os
import subprocess
from datetime import datetime
import re
import base64
from streamlit_ace import st_ace
import tempfile
import fitz  # PyMuPDF for PDF rendering

# Streamlit page configuration
st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")

# Title and description
st.title("📄 Elsevier LaTeX Compiler")
st.write("Edit and compile a `.tex` file from the `manuscript` directory. The LaTeX content and table of contents are on the left, and the PDF preview (empty initially) is on the right.")

# File path setup
script_dir = os.path.dirname(os.path.abspath(__file__))
manuscript_dir = os.path.join(script_dir, "manuscript")

if not os.path.exists(manuscript_dir):
    st.error("❌ `manuscript/` directory not found.")
    st.stop()

# Load first .tex file found
tex_files = [f for f in os.listdir(manuscript_dir) if f.endswith(".tex")]
if not tex_files:
    st.error("❌ No `.tex` file found in `manuscript/`.")
    st.stop()

tex_file_path = os.path.join(manuscript_dir, tex_files[0])

# Read initial .tex content
with open(tex_file_path, "r", encoding="utf-8") as f:
    tex_content = f.read()

# Extract TOC from LaTeX with more comprehensive pattern
def extract_toc_lines(content):
    toc = []
    pattern = re.compile(r'\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\s*{([^}]*)}')
    for i, line in enumerate(content.splitlines()):
        match = pattern.search(line)
        if match:
            level, title = match.group(1), match.group(2)
            indent = {
                "part": 0,
                "chapter": 0,
                "section": 0,
                "subsection": 20,
                "subsubsection": 40,
                "paragraph": 60,
                "subparagraph": 80
            }.get(level, 0)
            toc.append({
                "title": title, 
                "line": i, 
                "indent": indent,
                "level": level
            })
    return toc

toc_items = extract_toc_lines(tex_content)

# Create two-column layout
col1, col2 = st.columns([1, 1])

# Session state for PDF data and filename
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = None
if 'selected_line' not in st.session_state:
    st.session_state.selected_line = 0

with col1:
    st.subheader("✍️ Edit LaTeX File")
    
    # Enhanced Table of Contents with search and hierarchy
    with st.expander("📚 Table of Contents", expanded=True):
        if toc_items:
            # TOC search functionality
            search_query = st.text_input("🔍 Search sections...", "", key="toc_search")
            
            # Filter TOC based on search
            filtered_toc = [item for item in toc_items 
                          if search_query.lower() in item['title'].lower()] if search_query else toc_items
            
            # Display TOC items with proper indentation
            for i, item in enumerate(filtered_toc):
                indent = "&nbsp;" * item['indent']
                level_icon = {
                    "part": "📚",
                    "chapter": "📖",
                    "section": "📝",
                    "subsection": "↳",
                    "subsubsection": "↳",
                    "paragraph": "↳",
                    "subparagraph": "↳"
                }.get(item['level'], "•")
                
                # Create a button for each TOC item
                if st.button(f"{indent}{level_icon} {item['title']}", key=f"toc_{i}"):
                    st.session_state.selected_line = item['line']
                    
        else:
            st.info("🛈 No sections found in LaTeX.")

    # LaTeX editor with cursor positioning
    editor_args = {
        "value": tex_content,
        "language": "latex",
        "theme": "monokai",
        "key": "tex_editor",
        "height": 600,
        "auto_update": True
    }
    
    edited_tex = st_ace(**editor_args)

    # After editor render, use JavaScript to set cursor position
    if st.session_state.selected_line > 0:
        js_code = f"""
        <script>
            setTimeout(() => {{
                const editor = document.querySelector('.ace_editor').env.editor;
                editor.gotoLine({st.session_state.selected_line + 1});
                editor.focus();
            }}, 100);
        </script>
        """
        st.components.v1.html(js_code, height=0)
        st.session_state.selected_line = 0  # Reset after jump

    # Save and compile options
    auto_compile = st.checkbox("🔁 Auto-compile after saving", value=True)
    compile_triggered = False

    col_save, col_compile = st.columns(2)
    with col_save:
        if st.button("💾 Save Changes", use_container_width=True):
            with open(tex_file_path, "w", encoding="utf-8") as f:
                f.write(edited_tex)
            st.success("✅ Changes saved.")
            if auto_compile:
                compile_triggered = True
                
    with col_compile:
        if st.button("🛠 Compile LaTeX", use_container_width=True):
            compile_triggered = True

    if compile_triggered:
        try:
            # Save edited content before compiling
            with open(tex_file_path, "w", encoding="utf-8") as f:
                f.write(edited_tex)
            
            # Compile with latexmk
            with st.spinner("⏳ Compiling LaTeX document..."):
                result = subprocess.run(
                    ["latexmk", "-pdf", "-pdflatex=pdflatex", "-interaction=nonstopmode", tex_file_path],
                    cwd=manuscript_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                pdf_path = os.path.splitext(tex_file_path)[0] + ".pdf"
                if result.returncode == 0 and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.session_state.pdf_data = f.read()
                    st.session_state.pdf_filename = f"compiled_{os.path.basename(os.path.splitext(tex_file_path)[0])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    st.success("✅ PDF compiled successfully!")
                else:
                    st.error("❌ Compilation failed.")
                    with st.expander("View Compilation Log", expanded=False):
                        st.code(result.stdout + result.stderr, language="text")
        except subprocess.TimeoutExpired:
            st.error("⏳ Compilation timed out. Please try again.")
        except Exception as e:
            st.error(f"⚠️ Unexpected error: {str(e)}")

with col2:
    st.subheader("📄 PDF Preview")
    
    if st.session_state.pdf_data:
        # PDF viewing options
        view_mode = st.radio("View Mode:", ["Embedded Viewer", "Page Navigator"], horizontal=True)
        
        if view_mode == "Embedded Viewer":
            # Enhanced PDF viewer with better controls
            b64_pdf = base64.b64encode(st.session_state.pdf_data).decode("utf-8")
            pdf_view = f"""
            <iframe src="data:application/pdf;base64,{b64_pdf}#toolbar=1&navpanes=1&scrollbar=1" 
                    width="100%" height="600" type="application/pdf" 
                    style="border: 1px solid #e0e0e0; border-radius: 5px;"></iframe>
            """
            st.markdown(pdf_view, unsafe_allow_html=True)
            
        elif view_mode == "Page Navigator":
            # Page-by-page navigation with PyMuPDF
            try:
                # Create a temporary PDF file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(st.session_state.pdf_data)
                    tmp_path = tmp_file.name
                
                doc = fitz.open(tmp_path)
                total_pages = doc.page_count
                
                # Page navigation controls
                col_page1, col_page2 = st.columns([1, 3])
                with col_page1:
                    page_num = st.number_input(
                        "Page number", 
                        min_value=1, 
                        max_value=total_pages, 
                        value=1,
                        step=1
                    )
                
                # Render the selected page
                page = doc.load_page(page_num - 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                
                # Display the page with caption
                st.image(
                    img_bytes, 
                    caption=f"Page {page_num} of {total_pages}",
                    use_column_width=True
                )
                
                # Clean up
                doc.close()
                os.unlink(tmp_path)
                
            except Exception as e:
                st.error(f"⚠️ Failed to render PDF: {str(e)}")
                st.info("Using embedded viewer as fallback")
                b64_pdf = base64.b64encode(st.session_state.pdf_data).decode("utf-8")
                pdf_view = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600px"></iframe>'
                st.markdown(pdf_view, unsafe_allow_html=True)
        
        # Download button
        st.download_button(
            "📥 Download PDF", 
            st.session_state.pdf_data, 
            file_name=st.session_state.pdf_filename, 
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.info("🛈 PDF not compiled yet. Click **Compile LaTeX** or save with auto-compile enabled.")
        st.image("https://via.placeholder.com/600x800?text=PDF+Preview+Area", use_column_width=True)

# Status bar at bottom
st.markdown("---")
if st.session_state.pdf_data:
    st.caption(f"📄 Last compiled: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
               f"Editing: {os.path.basename(tex_file_path)}")
else:
    st.caption(f"📄 Ready to compile | Editing: {os.path.basename(tex_file_path)}")

