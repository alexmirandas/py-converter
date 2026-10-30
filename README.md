# convert.py - Document converter

## Supported conversions:
    PDF        -> DOCX (Word)
    PDF        -> MD   (Markdown)
    DOCX       -> MD
    PPTX / PPT -> MD   (.ppt and .doc are first converted via LibreOffice)

## Install:
  ```
  pip install pdf2docx pymupdf4llm "markitdown[docx,pptx]"
  
  # Optional, only for legacy .ppt / .doc files:
  #   Debian/Ubuntu: sudo apt install libreoffice
  #   macOS:         brew install --cask libreoffice

  ```

##  Usage:
  ```
  python convert.py report.pdf --to docx
  python convert.py report.pdf --to md
  python convert.py notes.docx              # default target for docx/ppt(x) is md
  python convert.py slides.pptx -o out/slides.md
  python convert.py ./docs --to md -r       # batch: every supported file in a folder
  ```