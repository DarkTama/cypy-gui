# Default headers for providers that uses `requests.post()` for sending request
DEFAULT_HEADERS = {
    "Authorization": "",  # must be replaced or removed before sending request
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/indravoyager/cypy",
    # Custom headers (prefixed with "X-")
    "X-Title": "cypy Manga Translator",
}
