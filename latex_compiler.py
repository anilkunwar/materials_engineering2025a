import streamlit as st
import os
import tempfile
import zipfile
from datetime import datetime
import subprocess

# Streamlit page configuration
st.set_page_config(page_title="Elsevier LaTeX ZIP Compiler", layout="wide")

# Title and description
st.title("Elsevier LaTeX ZIP Compiler")
st.write("Upload a ZIP file or specify the name of a ZIP file in the same directory as this script, containing a `manuscript` directory with a `.tex` file (e.g., `paper.tex`), `cas-sc.cls`, and optionally `.bib` and figures in a `figures` directory. Compile to generate a PDF using latexmk.")

# Tabs for upload or adjacent ZIP file
tab1, tab2 = st.tabs(["Upload ZIP File", "Use Adjacent ZIP File"])

# Initialize zip_path
zip_path = None
pdf_data = None
pdf_filename = None

with tab1:
    # File uploader for ZIP file
    uploaded_zip = st.file_uploader("Upload ZIP file", type=["zip"], key="uploader")
    if uploaded_zip is not None:
        # Save uploaded ZIP to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            tmp_zip.write(uploaded_zip.read())
            zip_path = tmp_zip.name

with tab2:
    # Text input for ZIP file name in the same directory
    zip_filename_input = st.text_input("Enter ZIP file name (e.g., manuscript.zip)", key="zip_filename")
    if zip_filename_input:
        # Get the directory of the current .py file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_zip_path = os.path.join(script_dir, zip_filename_input)
        if os.path.exists(local_zip_path) and zip_filename_input.endswith(".zip"):
            zip_path = local_zip_path
        else:
            st.error(f"ZIP file '{zip_filename_input}' not found in the same directory as the script or is not a valid ZIP file.")

# Compile button and processing logic
if zip_path is not None and st.button("Compile LaTeX"):
    try:
        # Create a temporary directory to store extracted files
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Extract the ZIP file
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdirname)

            # Log extracted files for debugging
            extracted_files = []
            for root, _, files in os.walk(tmpdirname):
                for file in files:
                    extracted_files.append(os.path.join(root, file))
            if extracted_files:
                st.write("Extracted files:", extracted_files)
            else:
                st.error("No files found in the ZIP. Please ensure the ZIP contains files.")

            # Search for a .tex file in the manuscript directory
            tex_file_path = None
            manuscript_dir = None
            for root, dirs, files in os.walk(tmpdirname):
                if "manuscript" in dirs:
                    manuscript_dir = os.path.join(root, "manuscript")
                    for file in os.listdir(manuscript_dir):
                        if file.endswith(".tex"):
                            tex_file_path = os.path.join(manuscript_dir, file)
                            break
                if tex_file_path:
                    break
            if not tex_file_path:
                st.error("No `.tex` file found in the `manuscript` directory of the ZIP.")
            else:
                # Read .tex content for debugging
                with open(tex_file_path, "r", encoding="utf-8") as f:
                    tex_content = f.read()
                st.write(f"Content of {os.path.basename(tex_file_path)}:", tex_content)

                # Compile with latexmk
                try:
                    result = subprocess.run(
                        ["latexmk", "-pdf", "-pdflatex=pdflatex", "-interaction=nonstopmode", tex_file_path],
                        cwd=os.path.dirname(tex_file_path),
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    pdf_file_path = os.path.splitext(tex_file_path)[0] + ".pdf"
                    if result.returncode == 0 and os.path.exists(pdf_file_path):
                        # Read the PDF file
                        with open(pdf_file_path, "rb") as f:
                            pdf_data = f.read()
                        pdf_filename = f"compiled_{os.path.basename(os.path.splitext(tex_file_path)[0])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                        # Display success message
                        st.success("LaTeX compiled successfully with latexmk!")

                        # Provide download button for the PDF
                        st.download_button(
                            label="Download PDF",
                            data=pdf_data,
                            file_name=pdf_filename,
                            mime="application/pdf"
                        )

                        # Embed PDF for preview
                        st.write("### PDF Preview")
                        st.components.v1.html(
                            f"""
                            <object data="data:application/pdf;base64,{pdf_data.hex()}" type="application/pdf" width="100%" height="600px">
                                <p>Your browser does not support PDF preview. Please download the PDF.</p>
                            </object>
                            """,
                            height=600
                        )
                    else:
                        st.error("PDF generation failed. Check the latexmk log below:")
                        st.text_area("latexmk Log", value=result.stdout + result.stderr, height=200, disabled=True)

                except subprocess.TimeoutExpired:
                    st.error("LaTeX compilation timed out. Please simplify your document or check for errors.")
                except Exception as latexmk_error:
                    st.error(f"latexmk compilation failed: {str(latexmk_error)}")
                    st.write("Please ensure all required files (e.g., cas-sc.cls, .bib, figures) are included in the ZIP.")

    except zipfile.BadZipFile:
        st.error("Invalid ZIP file. Please upload or specify a valid ZIP archive.")
    except PermissionError:
        st.error("Permission denied while accessing ZIP file or extracted files. Check file permissions.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    finally:
        # Clean up temporary uploaded ZIP file if it exists
        if uploaded_zip is not None and zip_path is not None and os.path.exists(zip_path):
            os.unlink(zip_path)

# Instructions for the user
st.markdown("""
### Instructions
1. **Upload Option**: Upload a ZIP containing a `manuscript` directory with a `.tex` file (e.g., `paper.tex`), `cas-sc.cls`, and optionally `.bib` and a `figures` directory with images (e.g., `figures/graphical_abstract.png`).
2. **Adjacent ZIP Option**: Enter the name of a ZIP file (e.g., `manuscript.zip`) in the same directory as this script.
3. Ensure the ZIP has the structure:
   ```
   manuscript.zip
   ├── manuscript/
   │   ├── paper.tex  (or anyname.tex)
   │   ├── cas-sc.cls
   │   └── references.bib  (optional)
   ├── figures/
   │   └── graphical_abstract.png  (optional)
   ```
4. Click "Compile LaTeX" to generate the PDF using latexmk.
5. Download the PDF or view it in the preview section.
6. For Streamlit Cloud deployment, include:
   - `requirements.txt`:
     ```
     streamlit
     ```
   - `packages.txt`:
     ```
     texlive-full
     latexmk
     ```
7. Example `paper.tex`:
   ```latex
   \\documentclass[a4paper,fleqn]{cas-sc}
   \\usepackage[version=4]{mhchem}
   \\usepackage{amsmath}
   \\usepackage{siunitx}
   \\sisetup{range-phrase = \\text{--}, range-units = single, per-mode = fraction, separate-uncertainty = true}
   \\DeclareSIUnit{\\dec}{dec}
   \\DeclareSIUnit{\\cycle}{cycles}
   \\usepackage[numbers,sort&compress]{natbib}
   \\usepackage{graphics}
   \\graphicspath{{figures/}}
   \\begin{document}
   \\shorttitle{Test}
   \\title[mode = title]{Test Manuscript}
   \\author[a]{Author}[]
   \\address[a]{Institute, City, Country}
   \\begin{abstract}
   This is a test.
   \\end{abstract}
   \\begin{keywords}
   test
   \\end{keywords}
   \\maketitle
   \\section{Introduction}
   Test document.
   \\end{document}
   ```
8. Create the ZIP:
   ```bash
   mkdir -p manuscript figures
   mv paper.tex manuscript/
   cp cas-sc.cls manuscript/
   zip -r manuscript.zip manuscript/ figures/
   ```
""")
