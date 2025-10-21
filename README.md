# HNG Stage 1 — String Analyzer Service

## Quick start
1. python -m venv venv
2. source venv/bin/activate   # mac/linux
   venv\Scripts\activate      # windows
3. pip install -r requirements.txt
4. python app.py
5. API base: http://127.0.0.1:5000

## Endpoints
POST /strings
Body: {"value": "string to analyze"}
Responses:
 201 Created -> created record
 400 Bad Request -> missing body
 422 Unprocessable Entity -> non-string value
 409 Conflict -> already exists

GET /strings/{string_value}
Responses:
 200 OK -> record
 404 Not Found -> missing

GET /strings
Query params: is_palindrome, min_length, max_length, word_count, contains_character

GET /strings/filter-by-natural-language?query=...
Supports simple phrases like:
 - "all single word palindromic strings"
 - "strings longer than 10 characters"
 - "strings containing the letter z"

DELETE /strings/{string_value}
Responses:
 204 No Content -> deleted
 404 Not Found -> missing

## Notes
- Storage is in-memory for this submission (no persistence across restarts).
- SHA-256 used as id and included in properties.
- Timestamp is UTC ISO 8601 with Z suffix.
- Deploy on Railway/Heroku using Procfile/gunicorn.
