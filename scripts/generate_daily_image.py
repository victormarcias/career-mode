#!/usr/bin/env python3
"""Generate an accompanying image for a Daily Post via the Gemini API.

Usage:
    python3 scripts/generate_daily_image.py <post_text_file> [output_path]

Reads GEMINI_API_KEY from a local .env file (repo root, gitignored) or the
environment. Never prints the key.
"""
import base64
import json
import os
import subprocess
import sys
import tempfile

MODEL = "gemini-2.5-flash-image"
REQUEST_TIMEOUT = 120
PROCESS_TIMEOUT = 130
PROMPT_PREFIX = (
    "Could you make me an image about this? Please check spelling errors. Minimal text. "
    "Do not write function names or code in the image: describe them in plain words."
)


def load_env(path):
    """Read stripped key-value pairs from a file, or return an empty mapping if absent."""
    env = {}
    if not os.path.isfile(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main():
    """Generate an image from the post file via Gemini and print its saved path."""
    if len(sys.argv) < 2:
        print("Usage: generate_daily_image.py <post_text_file> [output_path]", file=sys.stderr)
        sys.exit(1)

    post_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/daily-post-image.png"

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = load_env(os.path.join(repo_root, ".env"))
    api_key = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in .env or environment.", file=sys.stderr)
        sys.exit(1)

    with open(post_path) as f:
        post_text = f.read().strip()

    prompt = f"{PROMPT_PREFIX}\n\n{post_text}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    if "\r" in api_key or "\n" in api_key:
        print("Invalid GEMINI_API_KEY: must be a single line.", file=sys.stderr)
        sys.exit(1)

    # NamedTemporaryFile creates a private (0600) file and removes it on exit,
    # including exceptions. Keep the credential out of curl's process arguments.
    try:
        with tempfile.NamedTemporaryFile(mode="w", prefix="daily-image-", suffix=".headers") as headers:
            headers.write(f"x-goog-api-key: {api_key}\n")
            headers.flush()
            result = subprocess.run(
                [
                    "curl", "-sS", "--max-time", str(REQUEST_TIMEOUT), url,
                    "-H", "Content-Type: application/json",
                    "-H", f"@{headers.name}",
                    "-d", "@-",
                ],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=PROCESS_TIMEOUT,
            )
    except subprocess.TimeoutExpired:
        print("Image generation timed out.", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        print(f"curl failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    if "error" in data:
        print(f"Gemini API error: {json.dumps(data['error'], indent=2)}", file=sys.stderr)
        sys.exit(1)

    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            img_bytes = base64.b64decode(part["inlineData"]["data"])
            with open(out_path, "wb") as f:
                f.write(img_bytes)
            print(out_path)
            return

    print("No image in response:", json.dumps(data, indent=2), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
