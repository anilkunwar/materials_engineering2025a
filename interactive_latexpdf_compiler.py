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
st.set_page_config(page_title="LaTeX Compiler", layout="wide")

# Title and description
st.title("📄 LaTeX Compiler")
st.write("Edit and compile a `.tex` file from the `manuscript` directory.")

# File path setup
script_dir = os.path.dirname(os.path.abspath(__file__))
manuscript_dir = os.path.join(script_dir, "manuscript")

if not os.path.exists(manuscript_dir):
    os.makedirs(manuscript_dir)
    st.error("❌ Created manuscript directory as it didn't exist. Please add your .tex file.")
    st.stop()

# Load first .tex file found
tex_files = [f for f in os.listdir(manuscript_dir) if f.endswith(".tex")]
if not tex_files:
    st.error("❌ No `.tex` file found in `manuscript/`. Please add your main .tex file.")
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
            toc.append({
                "title": title, 
                "line": i, 
                "level": level
            })
    return toc

# Session state initialization
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = None
if 'selected_line' not in st.session_state:
    st.session_state.selected_line = 0
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'total_pages' not in st.session_state:
    st.session_state.total_pages = 1
if 'tex_content' not in st.session_state:
    st.session_state.tex_content = tex_content
if 'doc' not in st.session_state:
    st.session_state.doc = None

# Extract TOC items for the dropdown
toc_items = extract_toc_lines(st.session_state.tex_content)
section_options = ["-- Select Section --"] + [f"{item['title']} (line {item['line']+1})" for item in toc_items]

# Wide LaTeX Editor at the top
st.subheader("✍️ LaTeX Editor")
st.markdown("Navigate to section: ")

# Section dropdown and editor
col_dropdown, col_info = st.columns([3, 1])
with col_dropdown:
    selected_section = st.selectbox(
        "Select section to jump to:",
        options=section_options,
        index=0,
        key="section_select",
        label_visibility="collapsed"
    )
    
    # Process section selection
    if selected_section != "-- Select Section --":
        # Extract line number from the selected option
        line_num = int(selected_section.split("(line ")[1].rstrip(")")) - 1
        st.session_state.selected_line = line_num

# LaTeX editor with cursor positioning
editor_args = {
    "value": st.session_state.tex_content,
    "language": "latex",
    "theme": "monokai",
    "key": "tex_editor",
    "height": 500,  # Wider than tall
    "auto_update": True,
    "font_size": 14,
    "wrap": True
}

edited_tex = st_ace(**editor_args)

# Update session state if content changes
if edited_tex != st.session_state.tex_content:
    st.session_state.tex_content = edited_tex

# Save and compile options below the editor
st.subheader("🛠 Compilation Controls")
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
                
                # Load PDF for navigation
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(st.session_state.pdf_data)
                    tmp_path = tmp_file.name
                
                if st.session_state.doc:
                    st.session_state.doc.close()
                st.session_state.doc = fitz.open(tmp_path)
                st.session_state.total_pages = st.session_state.doc.page_count
                st.session_state.current_page = 1
            else:
                st.error("❌ Compilation failed.")
                with st.expander("View Compilation Log", expanded=False):
                    st.code(result.stdout + result.stderr, language="text")
    except subprocess.TimeoutExpired:
        st.error("⏳ Compilation timed out. Please try again.")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {str(e)}")

# PDF Viewer below everything
st.subheader("📄 PDF Preview")

if st.session_state.pdf_data and st.session_state.doc:
    # Page navigation controls
    col_page1, col_page2 = st.columns([1, 3])
    with col_page1:
        st.markdown(f"**Page {st.session_state.current_page} of {st.session_state.total_pages}**")
    
    # Navigation buttons
    col_prev, col_next, col_jump = st.columns([1, 1, 3])
    with col_prev:
        if st.button("◀ Previous Page", use_container_width=True) and st.session_state.current_page > 1:
            st.session_state.current_page -= 1
    with col_next:
        if st.button("Next Page ▶", use_container_width=True) and st.session_state.current_page < st.session_state.total_pages:
            st.session_state.current_page += 1
    with col_jump:
        jump_page = st.number_input("Jump to page", min_value=1, max_value=st.session_state.total_pages, value=st.session_state.current_page)
        if st.button("Go", use_container_width=True) and jump_page != st.session_state.current_page:
            st.session_state.current_page = jump_page
    
    # Render the selected page
    try:
        page = st.session_state.doc.load_page(st.session_state.current_page - 1)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        
        # Display the page with caption
        st.image(
            img_bytes, 
            use_column_width=True
        )
        
    except Exception as e:
        st.error(f"⚠️ Failed to render page: {str(e)}")
    
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
    st.image("https://via.placeholder.com/1200x600?text=PDF+Preview+Area", use_column_width=True)

# JavaScript for cursor positioning
if st.session_state.selected_line > 0:
    js_code = f"""
    <script>
        setTimeout(() => {{
            const editor = document.querySelector('.ace_editor').env.editor;
            editor.gotoLine({st.session_state.selected_line + 1});
            editor.focus();
            window.scrollTo(0, 0);
        }}, 100);
    </script>
    """
    st.components.v1.html(js_code, height=0)
    st.session_state.selected_line = 0  # Reset after jump

# Status bar at bottom
st.markdown("---")
if st.session_state.pdf_data:
    st.caption(f"📄 Last compiled: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
               f"Editing: {os.path.basename(tex_file_path)} | "
               f"Pages: {st.session_state.total_pages}")
else:
    st.caption(f"📄 Ready to compile | Editing: {os.path.basename(tex_file_path)}")
