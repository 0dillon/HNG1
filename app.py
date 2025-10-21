from flask import Flask, request, jsonify
from datetime import datetime, timezone
import hashlib
import re
import os

app = Flask(__name__)
storage = {}

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def sha256_hex(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def analyze_string(value):
    length = len(value)
    is_palindrome = value.lower() == value.lower()[::-1]
    unique_characters = len(set(value))
    word_count = 0 if value.strip() == "" else len(re.findall(r'\S+', value))
    sha = sha256_hex(value)
    freq = {}
    for ch in value:
        freq[ch] = freq.get(ch, 0) + 1
    return {
        "length": length,
        "is_palindrome": is_palindrome,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": sha,
        "character_frequency_map": freq
    }

@app.route("/strings", methods=["POST"])
def create_string():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"message": "Invalid JSON body"}), 400
    if "value" not in payload:
        return jsonify({"message": "Missing 'value' in request body"}), 400
    if not isinstance(payload["value"], str):
        return jsonify({"message": "'value' must be a string"}), 422
    value = payload["value"]
    props = analyze_string(value)
    sid = props["sha256_hash"]
    if sid in storage:
        return jsonify({"message": "String already exists"}), 409
    record = {
        "id": sid,
        "value": value,
        "properties": props,
        "created_at": now_iso()
    }
    storage[sid] = record
    return jsonify(record), 201

@app.route("/strings/<path:raw_value>", methods=["GET"])
def get_string(raw_value):
    sid = sha256_hex(raw_value)
    if sid in storage:
        return jsonify(storage[sid]), 200
    return jsonify({"message": "String not found"}), 404

@app.route("/strings", methods=["GET"])
def list_strings():
    args = request.args
    try:
        is_pal = args.get("is_palindrome")
        min_length = args.get("min_length", type=int)
        max_length = args.get("max_length", type=int)
        word_count = args.get("word_count", type=int)
        contains_character = args.get("contains_character")
        if is_pal is not None and is_pal.lower() not in ("true","false"):
            return jsonify({"message": "Invalid is_palindrome value"}), 400
    except ValueError:
        return jsonify({"message": "Invalid query parameter types"}), 400

    records = list(storage.values())
    if is_pal is not None:
        is_pal_bool = is_pal.lower() == "true"
        records = [r for r in records if r["properties"]["is_palindrome"] == is_pal_bool]
    if min_length is not None:
        records = [r for r in records if r["properties"]["length"] >= min_length]
    if max_length is not None:
        records = [r for r in records if r["properties"]["length"] <= max_length]
    if word_count is not None:
        records = [r for r in records if r["properties"]["word_count"] == word_count]
    if contains_character:
        if len(contains_character) != 1:
            return jsonify({"message": "contains_character must be a single character"}), 400
        records = [r for r in records if contains_character in r["value"]]

    filters_applied = {}
    for k in ("is_palindrome","min_length","max_length","word_count","contains_character"):
        if args.get(k) is not None:
            filters_applied[k] = args.get(k)
    return jsonify({"data": records, "count": len(records), "filters_applied": filters_applied}), 200

def parse_nl(q):
    original = q
    ql = q.lower()
    parsed = {}
    if re.search(r'\b(single|one)\b.*\bword\b', ql):
        parsed["word_count"] = 1
    m = re.search(r'(\d+)\s*(?:-)?\s*word', ql)
    if m:
        parsed["word_count"] = int(m.group(1))
    if "palind" in ql:
        parsed["is_palindrome"] = True
    m = re.search(r'longer than\s+(\d+)', ql)
    if m:
        parsed["min_length"] = int(m.group(1)) + 1
    m = re.search(r'contain(?:s|ing)?\s+the\s+letter\s+([a-z])', ql)
    if m:
        parsed["contains_character"] = m.group(1)
    m = re.search(r'containing\s+the\s+letter\s+([a-z])', ql)
    if m and "contains_character" not in parsed:
        parsed["contains_character"] = m.group(1)
    return {"original": original, "parsed_filters": parsed}

@app.route("/strings/filter-by-natural-language", methods=["GET"])
def filter_by_nl():
    q = request.args.get("query", "")
    if not q:
        return jsonify({"message":"Missing query parameter"}), 400
    interpreted = parse_nl(q)
    pf = interpreted["parsed_filters"]
    records = list(storage.values())
    if "is_palindrome" in pf:
        records = [r for r in records if r["properties"]["is_palindrome"] == pf["is_palindrome"]]
    if "word_count" in pf:
        records = [r for r in records if r["properties"]["word_count"] == pf["word_count"]]
    if "min_length" in pf:
        records = [r for r in records if r["properties"]["length"] >= pf["min_length"]]
    if "contains_character" in pf:
        ch = pf["contains_character"]
        records = [r for r in records if ch in r["value"]]
    return jsonify({"data": records, "count": len(records), "interpreted_query": interpreted}), 200

@app.route("/strings/<path:raw_value>", methods=["DELETE"])
def delete_string(raw_value):
    sid = sha256_hex(raw_value)
    if sid not in storage:
        return jsonify({"message":"String not found"}), 404
    del storage[sid]
    return "", 204

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
