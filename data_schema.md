# Data Schema for Templates

Use these variable names inside `{{ double_curly_braces }}` in your Word templates.

## Service Details (From Word Doc)
*   `date` (e.g., "September 28, 2025")
*   `service_time` (e.g., "10:30 am")
*   `sunday_title` (e.g., "16th Sunday after Pentecost")
*   `special_title` (Worship Series Title, if present)
*   `is_communion_sunday` (True/False - use in `{% if %}` block)

## Site Defaults (From Local Config)
These values may be defined in `site_config.local.json`. They are merged into the template context before generation.
*   `site_name`
*   `site_contact_line`
*   `pastor_name`
*   `organist_name`
*   `liturgist_name`
*   `choir_name`
*   `default_service_time`

## Hymns & Readings (From Word Doc)
*   `hymn_1_num`, `hymn_1_title`, `hymn_1_instr`
*   `hymn_2_num`, `hymn_2_title`, `hymn_2_instr`
*   `hymn_3_num`, `hymn_3_title`, `hymn_3_instr`
*   `communion_hymn_num`, `communion_hymn_title`
*   `doxology_num` (e.g., "94" or "95")
*   `reading_1_verse`, `reading_1_translation`
*   `reading_2_verse`, `reading_2_translation`

## Organist Email (Prelude/Postlude)
*   `prelude_title`, `prelude_composer`, `prelude_details`
*   `offertory_title`, `offertory_composer`, `offertory_details`
*   `postlude_title`, `postlude_composer`, `postlude_details`
*   `communion_piece_title`, `communion_piece_composer`, `communion_piece_details`
*   `exit_music_title`, `exit_music_composer`, `exit_music_details` (or `exit_title`...)

## Choir Director Email (Anthem/Introit)
*   `introit_title`, `introit_composer`, `introit_details`
*   `anthem_title`, `anthem_composer`, `anthem_details`
*   `prayer_response_title`, `prayer_response_composer`, `prayer_response_details`
*   `benediction_response_title`, `benediction_response_composer`, `benediction_response_details`

## Additional User Input Fields (Manual Entry Phase)
These fields are typically not found in the source text and will be requested by the UI if they exist in your template.
*   `offertory_title`
*   `offertory_composer`
*   `offertory_personnel`
*   `prelude_personnel`
*   `anthem_personnel`
*   `benediction_response_personnel`
*   *Any other variable you use in a template that isn't extracted above will also appear as a required input.*

For music fields, `*_details` and `*_personnel` are currently emitted as aliases so older and newer templates can both render.
