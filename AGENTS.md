# CV requirements maintenance

For changes to resume conversion, consult `docs/CV生成规范.md` first.

- Record new user requirements with a stable rule ID, scope, status, implementation location and validation evidence.
- Update the appropriate existing service; do not create a new module for every request.
- Shared policy defaults belong in `backend/app/core/cv_rules.py`; deployment settings belong in `backend/app/core/config.py`.
- Reusable model instructions belong in `backend/app/prompts/`. Keep task-specific context in the calling service.
- Documentation alone does not implement a rule. Mark it pending until connected to the live pipeline and validated.
- Clearly distinguish deterministic enforcement, model instructions and known limitations. Never describe a prompt as a guarantee.
- Preserve source facts. Do not guess missing gender or degree level to satisfy a formatting requirement.
- For behavior changes, run relevant regression tests and record their results. Restart the backend only after checking for active tasks.
- User instructions take precedence over this file. Do not add extra approval requirements.
