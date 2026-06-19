import os

import requests
from google import genai


GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
REPO = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER = os.environ["PR_NUMBER"]
MAX_DIFF_CHARS = 8000
GEMINI_MODEL = "gemini-2.5-flash"


def get_pr_diff():
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.diff",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text


def review_with_gemini(diff):
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"""You are a senior software engineer doing a thorough code review. Review the following PR diff and provide:

1. **Summary** - What does this PR do? (2-3 sentences)
2. **Potential bugs** - Any logic errors, edge cases, or security issues
3. **Code quality** - Readability, naming, structure concerns
4. **Suggestions** - Specific improvements with examples if possible
5. **Overall verdict** - One of: Approve | Approve with minor suggestions | Request changes

Rules:
- Be specific, not generic. Reference actual lines or variable names from the diff.
- Be constructive. Explain WHY something is an issue.
- If the diff is small or clean, say so - don't invent problems.
- Use markdown formatting with headers and bullet points.
- Keep the total review under 400 words.

PR Diff:
{diff[:MAX_DIFF_CHARS]}""",
    )
    return response.text


def post_comment(review_text):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    body = (
        f"## AI PR Review\n\n{review_text}\n\n---\n"
        f"*Reviewed by Gemini AI - [{GEMINI_MODEL}]*"
    )
    response = requests.post(url, headers=headers, json={"body": body})
    response.raise_for_status()
    print("Review posted successfully!")


def main():
    # Skip if PR author is a bot to prevent infinite loops.
    pr_author = os.environ.get("PR_AUTHOR", "")
    if "bot" in pr_author.lower():
        print(f"Skipping review for bot PR author: {pr_author}")
        return

    print("Fetching PR diff...")
    diff = get_pr_diff()

    if not diff.strip():
        print("Empty diff - nothing to review.")
        return

    print(f"Diff length: {len(diff)} characters")
    print("Sending to Gemini for review...")
    review = review_with_gemini(diff)

    print("Posting comment to PR...")
    post_comment(review)


if __name__ == "__main__":
    main()
