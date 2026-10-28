# Skill scaffold template

`skill-lab new <name>` (SPEC-101) renders this folder into `skills/<name>/` and a
spec stub into `skill-lab/specs/NNN-<name>/`, then vendors `_skillkit` and the
envelope schema with `skill-lab sync`.

- Every file ending in `.tmpl` is rendered and written without the suffix. Using
  the suffix everywhere keeps linters and test discovery away from the raw template.
- Top-level entries whose name starts with `_` are scaffold-internal: `_spec/`
  renders into the spec folder, and this README is not copied.
- Placeholders are `{{name}}`, `{{title}}`, `{{description}}`, `{{family}}`,
  `{{spec_id}}`, `{{spec_number}}`, `{{spec_dir}}`, `{{author}}` and `{{date}}`.
  An unknown placeholder is a template bug and aborts the scaffold.
- Every spot the author must fill carries the marker `TODO(scaffold)`.
  `skill-lab validate` reports each file that still has one (rule `scaffold.todo`,
  a warning). As generated, the skill passes validation with zero errors, its unit
  tests pass, and its four deterministic cases pass against `scripts/example.py`.
