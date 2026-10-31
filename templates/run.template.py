"""<job title>: GitHub implementation of departments/<dept>/<function>/<job>/SKILL.md.

Runs with the free model chain and free services only. Writes the files the skill's
Output section names and returns a summary and flag. Offline test: tests/test_runs.py.
"""
from foundry import jobkit as k


def main(ctx):
    idea, brain = ctx["idea"], ctx["brain"]
    # 1. Gather: k.read(ctx, "validate/x.json"), k.search(query, n), k.fetch(url), k.secret("NAME")
    # 2. Think: answer = k.ask(prompt) -> dict or None. On None return {"skipped": "no free model answered"}
    # 3. Write: k.write(ctx, "stage/file.md", text); k.write(ctx, "stage/file.json", obj)
    return {"summary": "what was done in two sentences", "flag": "ok"}


if __name__ == "__main__":
    k.run(main)
