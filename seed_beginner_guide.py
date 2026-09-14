# seed_beginner_guide.py
#
# One-off script: publishes the "Beginner's Guide to Open Source" blog
# post to your database, attributed to "CoderSpot Team". Safe to run more
# than once — it checks whether the post already exists first.
#
# Usage:
#   python seed_beginner_guide.py

import db

TITLE = "Beginner Guide to Open Source Program"

BODY = """So you want to contribute to open source, but you don't know where to start. That confusion is normal — almost everyone who's ever opened a pull request felt exactly the same way the first time. Here's a straightforward path through it.

What "open source" actually means

Open source software is code that anyone can view, use, modify, and share. Instead of one company controlling everything behind closed doors, the code lives in the open — usually on a platform like GitHub — and anyone in the world can propose changes to it. Linux, Python, VS Code, and thousands of the tools you already use every day are open source.

Contributing doesn't mean you have to be an expert

This is the biggest misconception that stops people from starting. Contributing isn't limited to writing complex new features. Real, valuable contributions include:

Fixing typos or unclear wording in documentation. Adding a missing code comment. Reporting a bug you ran into, with clear steps to reproduce it. Answering a question in an issue thread. Writing a test for existing code. Translating documentation into another language.

Every one of these is a legitimate first contribution, and maintainers genuinely appreciate them.

Step 1: Pick a project you actually use

Don't start by searching "beginner friendly projects" and picking a random one. Start with a tool, library, or app you already use and like. You already understand what it's for, which makes it much easier to spot small problems worth fixing.

Step 2: Read the contributing guide

Almost every serious open source project has a CONTRIBUTING.md file in its repository. It explains exactly how that project wants you to set up your environment, format your code, and submit changes. Skipping this step is the most common reason first-time pull requests get stuck — read it before you write a single line.

Step 3: Look for labeled beginner issues

Many projects tag issues with labels like "good first issue" or "beginner friendly" specifically to help new contributors find a manageable starting point. GitHub even has a dedicated search for this across all public repositories.

Step 4: Set up the project locally

Clone the repository, follow the setup instructions in the README, and get it running on your own computer before trying to change anything. If you get stuck here, that's completely normal — environment setup trips up experienced developers too.

Step 5: Make a small, focused change

Your first pull request should do one thing. Don't try to fix five unrelated things at once — it makes your change much harder for a maintainer to review, and much easier to reject. Small and focused beats big and ambitious for a first contribution.

Step 6: Write a clear pull request description

Explain what you changed and why. If it fixes a specific issue, link to that issue. A clear description shows the maintainer you understood the problem, and it makes their job easier — which makes them far more likely to merge your work.

Step 7: Be patient, and don't take feedback personally

Maintainers are almost always volunteers reviewing contributions in their spare time. It might take days or weeks to hear back. When you do get feedback, it's about the code, not about you — revise and resubmit. Nearly every contributor, no matter how experienced, has had a pull request sent back for changes.

Where structured programs come in

If you'd rather have a mentor guiding you through your first contributions instead of figuring it all out solo, that's exactly what programs like Google Summer of Code, Outreachy, and dozens of others on this site's Open Source calendar are built for. They pair you with an experienced mentor, give you a structured timeline, and in many cases pay a stipend for your work. Browse the Open Source category on the calendar to find one that fits where you are right now.

The one thing that matters most

Consistency beats intensity. A small contribution every couple of weeks will teach you more, and build more credibility with a project's maintainers, than one huge burst of effort followed by disappearing. Start small, stay consistent, and the rest follows naturally.

Resources

First Timers Only (https://www.firsttimersonly.com/) — a friendly starting point from Kent C. Dodds and Scott Hanselman built specifically for making your very first open source contribution. It rounds up beginner-friendly resources like First Contributions, Up For Grabs, and Good First Issues in one place, so you don't have to go hunting for them yourself.
"""


def main():
    db.init_db()

    existing = next((p for p in db.get_all_blog_posts() if p["title"] == TITLE), None)
    if existing:
        db.update_blog_post(existing["id"], TITLE, BODY)
        print(f"Updated existing post at /blog/{existing['slug']}")
    else:
        slug = db.create_blog_post(TITLE, BODY, author_id=None, author_name="CoderSpot Team")
        print(f"Published '{TITLE}' at /blog/{slug}")


if __name__ == "__main__":
    main()
