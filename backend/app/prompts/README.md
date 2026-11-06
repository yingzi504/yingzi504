# CV model instructions

Store reusable prompt text here as UTF-8 `.txt` files and load it relative to this directory, not the process working directory.

`cv_extraction.txt` is the extraction system prompt. The extraction service reads it for each extraction call. Source resume text remains in the user message, not in this file.

Translation and summarization prompts currently remain in their respective services because they interpolate field policies, target language and term-base instructions. Move them with focused regression checks when those stages change; do not duplicate a second inactive copy here.

Add or update the corresponding rule entry in `docs/CV生成规范.md` whenever instructions change. Prompt edits affect model guidance, not deterministic validation.
