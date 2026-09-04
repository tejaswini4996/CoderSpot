# add_new_events.py
#
# One-off helper: adds the 9 new open source programs/contests (sourced
# from osprograms.dev and the List-of-OpenSource-Programs GitHub list) to
# an EXISTING coderspot.db, without touching your applications or
# testimonials.
#
# When to use this:
#   - You already ran the app before today and have a coderspot.db file
#     with real applications/testimonials in it.
#   - In that case, editing data/events.py alone won't add anything new,
#     because the database only seeds itself once, the very first time
#     it's created.
#
# If you're starting completely fresh (no coderspot.db exists yet), you
# don't need this script at all — just run `python app.py` and the new
# events will already be included automatically.
#
# Usage:
#   python add_new_events.py

import db

NEW_EVENTS = [
    # (name, kind, month, window, category, format, summary, link)
    (
        "Season of KDE", "open_source", "January",
        "Applications due mid-January; work runs into March", "all", "Remote",
        "A KDE Community mentoring program pairing contributors with mentors on real KDE sub-projects — a lighter-weight alternative to GSoC.",
        "https://season.kde.org/",
    ),
    (
        "Summer of Bitcoin", "open_source", "January",
        "Applications typically open in January", "all", "Remote",
        "A paid mentorship program for university students contributing to Bitcoin and Bitcoin-adjacent open source projects, with a stipend paid in Bitcoin.",
        "https://www.summerofbitcoin.org/",
    ),
    (
        "FOSSEE Summer Fellowship", "open_source", "February",
        "Applications typically open February–March", "all", "Remote",
        "A paid summer fellowship from IIT Bombay's FOSSEE project for students contributing to open source scientific and educational software.",
        "https://fossee.in/",
    ),
    (
        "European Summer of Code (ESoC)", "open_source", "February",
        "Batch 1 applications open mid-February", "all", "Remote",
        "A GSoC-style mentorship program connecting contributors worldwide with open source projects, run across two application batches each year.",
        "https://www.esoc.dev/",
    ),
    (
        "GirlScript Summer of Code (GSSoC)", "open_source", "March",
        "Registrations typically open in late March", "all", "Remote",
        "A beginner-friendly open source program from the GirlScript community — despite the name, it's open to contributors of all genders, pairing newcomers with mentors on real projects over several weeks.",
        "https://www.osprograms.dev/programs/gssoc",
    ),
    (
        "Code for GovTech (C4GT)", "open_source", "April",
        "Next cycle's applications expected around April", "all", "Remote",
        "An India-focused paid mentoring program connecting developers with government technology (GovTech) projects over a three-month cycle.",
        "https://app.codeforgovtech.in/",
    ),
    (
        "Linux Kernel Mentorship Program", "open_source", "July",
        "Applications expected around July–August", "all", "Remote",
        "A Linux Foundation mentorship program introducing contributors to kernel development, working directly with kernel maintainers.",
        "https://wiki.linuxfoundation.org/lkmp",
    ),
    (
        "Igalia Coding Experience", "open_source", "September",
        "Rolling — periodic openings, check anytime", "all", "Remote",
        "A paid, rolling mentorship program from Igalia for contributors working on browser engines and other open source infrastructure projects.",
        "https://www.igalia.com/coding-experience/",
    ),
    (
        "24 Pull Requests", "open_source", "December",
        "Runs December 1–24 each year", "all", "Remote",
        "A 24-day tradition encouraging small, meaningful open source contributions throughout December — similar in spirit to Hacktoberfest.",
        "https://24pullrequests.com/",
    ),
    (
        "Open Source Connect India 2026", "open_source", "September",
        "Term begins", "all", "Remote",
        "India's flagship open source initiative connecting developers, maintainers, and founders through workshops, hands-on mentorship, startup showcases, and real-world project contributions.",
        "https://luma.com/3u22sml7",
    ),
    (
        "All Things Agentic Hackathon", "contest", "August",
        "Runs through August 31, 2026", "all", "Remote",
        "Google Cloud hackathon challenging builders to create next-generation AI agents using Gemini and the Agent Development Kit. $180,000 in prizes and Google Cloud credits.",
        "https://allthingsagentichackathon.devpost.com/",
    ),
    (
        "The WebMCP Challenge", "contest", "September",
        "Submissions close September 3, 2026", "all", "Remote",
        "A 10-day OpenAI hackathon (with Chrome, Cloudflare, Shopify, Vercel, Render, and Netlify) to build agent-native web apps using the experimental WebMCP standard. $35,000 in cash prizes.",
        "https://webmcp.devpost.com/",
    ),
    (
        "Agentic Cinema: The Blockbuster Hackathon", "contest", "September",
        "Submissions close September 7, 2026", "all", "Remote",
        "Google Cloud hackathon to build a Gemini-powered AI agent solving real workflows for filmmakers, screenwriters, studio crews, or fans. $75,000 in prizes.",
        "https://agentic-cinema.devpost.com/",
    ),
    (
        "Agents for Humans Hackathon", "contest", "September",
        "Six-week build — submissions close mid-September 2026", "all", "Remote",
        "Build an autonomous AI agent with AWS's Strands Agents SDK that handles repetitive everyday or professional tasks in the background. $40,000 in cash prizes across three tracks.",
        "https://agentsforhumans.devpost.com/",
    ),
    (
        "CALL-E: Your Code Is Calling", "contest", "September",
        "Submissions close September 14, 2026", "all", "Remote",
        "Turn your code into an AI agent that makes real phone calls using the CALL-E API. $10,000 prize pool across communication, enterprise, and ML/AI themes.",
        "https://call-e.devpost.com/",
    ),
    (
        "AWS Trainium Frontier Competition", "contest", "September",
        "Phase 1 submissions close September 30, 2026", "all", "Remote",
        "Train a language model from scratch on AWS Trainium2 chips and co-design custom kernels. $40,000 in prizes, with top teams presenting alongside Annapurna Labs researchers at NeurIPS 2026.",
        "https://trainium-frontier.devpost.com/",
    ),
    (
        "RevenueCat Shipaton 2026", "contest", "September",
        "Submissions close September 30, 2026", "all", "Remote",
        "Ship a brand-new iOS, Android, or Mac app integrated with the RevenueCat SDK between August 1 and September 30, 2026. Over $700,000 in cash prizes, plus a Times Square billboard feature for top winners.",
        "https://revenuecat-shipaton-2026.devpost.com/",
    ),
    (
        "Nebius x NVIDIA Global AI Hackathon", "contest", "October",
        "Runs through October 30, 2026", "all", "Remote",
        "Build a working AI system on Nebius's open infrastructure using at least one NVIDIA open source model. $50,000 in cash prizes; beginner-friendly, solo or team.",
        "https://nebiusglobalaihackathon.devpost.com/",
    ),
    (
        "Free Software Foundation Internship", "open_source", "June",
        "Rolling applications year-round", "all", "Remote",
        "An unpaid, educational internship with the Free Software Foundation for students interested in free software advocacy, licensing, and development.",
        "https://www.fsf.org/volunteer/internships",
    ),
    (
        "LF Decentralized Trust Mentorship", "open_source", "July",
        "Multiple terms yearly, aligned with the LFX mentorship ecosystem", "all", "Remote",
        "A Linux Foundation mentorship program for contributors working on decentralized trust and blockchain-adjacent open source projects. Paid, $3,000–$6,600 depending on term and region.",
        "https://lf-decentralized-trust-mentorships.github.io/mentorship-program/main/",
    ),
    (
        "sktime Mentoring Program", "open_source", "May",
        "Rolling / seasonal — check the official page for current rounds", "all", "Remote",
        "A mentoring program from the sktime community for contributors interested in time series machine learning and open source. May be paid depending on the round.",
        "https://www.sktime.net/en/latest/get_involved/mentoring.html",
    ),
    (
        "Djangonaut Space", "open_source", "April",
        "Multiple 8-week sessions each year", "all", "Remote",
        "A free, structured 8-week mentoring program from the Django community pairing new contributors ('Djangonauts') with experienced maintainers on real Django projects.",
        "https://djangonaut.space/",
    ),
    (
        "Kubernetes Release Shadow Program", "open_source", "May",
        "13-week program, aligned with each Kubernetes release cycle", "all", "Remote",
        "Shadow the Kubernetes Release Team through a full release cycle to learn how a major open source project ships software. Unpaid, community-driven.",
        "https://github.com/kubernetes/sig-release/blob/master/release-team/shadows.md",
    ),
    (
        "Swift Mentorship Program", "open_source", "June",
        "Annual 10-week cohort", "all", "Remote",
        "An unpaid mentorship cohort from the Swift open source community (Apple's open source language project) for contributors of any experience level.",
        "https://www.swift.org/mentorship/",
    ),
    (
        "KubeStellar IFoS (Interns for Open Source)", "open_source", "August",
        "Rolling internship", "all", "Remote",
        "An unpaid internship with KubeStellar for contributors passionate about open source; graduates get a certificate, a letter of recommendation, and priority consideration for paid programs like GSoC or LFX.",
        "https://kubestellar.io/en/programs/ifos",
    ),
    (
        "Open Mainframe Project Mentorship", "open_source", "July",
        "Spring, Summer, and Fall cycles via the LFX mentorship ecosystem", "all", "Remote",
        "A Linux Foundation mentorship program for contributors interested in Linux, mainframe computing, COBOL, Zowe, and related open source projects. Paid, stipend available.",
        "https://openmainframeproject.org/community/mentorship-program/",
    ),
    (
        "FOSSASIA Internship", "open_source", "November",
        "Rolling / project-based", "all", "Remote",
        "A rolling internship with FOSSASIA, an open source community and event organizer based in Asia, for contributors interested in a range of active projects.",
        "https://fossasia.org/internship",
    ),
    (
        "Open Source Research Experience (OSRE)", "open_source", "June",
        "Summer research program", "all", "Remote",
        "A summer open source research program from UC Santa Cruz's Open Source Program Office for undergraduate and graduate students interested in open source research, also connected to GSoC and other outreach cycles.",
        "https://ucsc-ospo.github.io/osre/",
    ),
    (
        "Google Season of Docs", "open_source", "May",
        "2026 program dates not yet announced — check back", "all", "Remote",
        "A Google-run program funding technical writers to work with open source organizations on documentation, via project grants typically between $5,000–$15,000.",
        "https://www.osprograms.dev/programs/season-of-docs",
    ),
    (
        "Rails Girls Summer of Code (RGSOC)", "women_in_tech", "March",
        "Applications open around March; program runs through September", "all", "Remote",
        "A global fellowship specifically for women and non-binary people to spend a summer working on an open source project of their choice, with funding and mentorship.",
        "https://railsgirlssummerofcode.org/",
    ),
    (
        "LFN Mentorship Program", "open_source", "January",
        "Applications open January; program runs through June", "all", "Remote",
        "A Linux Foundation Networking mentorship program pairing contributors with mentors on open source networking and telecom projects.",
        "https://wiki.lfnetworking.org/display/LN/LFN+Mentorship+Program",
    ),
    (
        "The X.Org Endless Vacation of Code (EVoC)", "open_source", "April",
        "Rolling — applications typically open around April", "all", "Remote",
        "A rolling mentorship program from the X.Org Foundation for contributors working on the X Window System and related open source graphics stack projects.",
        "https://www.x.org/wiki/XorgEVoC/",
    ),
    (
        "Julia Summer of Code", "open_source", "May",
        "Aligned with the Google Summer of Code timeline — check official page", "all", "Remote",
        "A summer mentorship program for contributors working on the Julia programming language and its open source ecosystem.",
        "https://julialang.org/jsoc",
    ),
    (
        "Summer of Haskell", "open_source", "April",
        "Typically runs April through September", "all", "Remote",
        "A summer mentorship program for contributors working on Haskell open source projects, with funding for accepted proposals.",
        "https://summer.haskell.org/",
    ),
    (
        "Processing Foundation Fellowship", "open_source", "June",
        "Check the official page for current cycle dates", "all", "Remote",
        "A paid fellowship from the Processing Foundation for contributors working on creative-coding open source tools like Processing and p5.js.",
        "https://processingfoundation.org/fellowships/",
    ),
    (
        "John Hunter Matplotlib Summer Fellowship", "open_source", "March",
        "Rolling — check the NumFOCUS page for current cycle", "all", "Remote",
        "A NumFOCUS fellowship funding contributors to work on Matplotlib and related open source scientific Python tools, named for Matplotlib's creator.",
        "https://numfocus.org/programs/john-hunter-technology-fellowship",
    ),
    (
        "PClub Summer of Code", "open_source", "May",
        "Typically runs over the summer — check official page", "all", "Remote",
        "A summer open source mentorship program run by the Programming Club at IIT Kanpur, open to contributors at any experience level.",
        "https://www.pclubsummerofcode.in/",
    ),
    (
        "Tencent Rhino-Bird Open Source Training Program", "open_source", "June",
        "Check the official page for current cycle", "all", "Remote",
        "A Tencent-run open source training and mentorship program pairing contributors with mentors on Tencent's open source projects.",
        "https://opensource.tencent.com/summer-of-code",
    ),
    (
        "Microsoft Reinforcement Learning Open Source Fest", "open_source", "May",
        "Two cycles per year (spring and fall) — check official page", "all", "Remote",
        "A Microsoft Research program funding student contributors to work on open source reinforcement learning projects and tools.",
        "https://www.microsoft.com/en-us/research/academic-program/rl-open-source-fest/",
    ),
    (
        "Summer of Open Source Promotion Plan (OSPP)", "open_source", "May",
        "Applications open ~May; coding period runs through October", "all", "Remote",
        "A large-scale open source mentorship program run by the Institute of Software, Chinese Academy of Sciences, connecting global contributors with open source organizations.",
        "https://summer.iscas.ac.cn",
    ),
    (
        "Bountiful Open Source Summer (BOSS)", "contest", "July",
        "Check the official page for current cycle", "all", "Remote",
        "An open source contribution competition run by Coding Blocks, with cash and other prizes for top contributors.",
        "https://lab.codingblocks.com/boss",
    ),
    (
        "FOSSASIA Codeheat", "contest", "November",
        "Check the official page for current cycle", "all", "Remote",
        "An open source contribution competition from FOSSASIA with cash prizes for the most impactful pull requests across participating projects.",
        "https://codeheat.org/",
    ),
    (
        "GirlScript Winter of Contributing (GWOC)", "contest", "November",
        "Runs over the winter — check official page for exact dates", "all", "Remote",
        "A winter open source contribution drive from the GirlScript community — despite the name, open to contributors of all genders — with prizes, swag, and certificates for participants.",
        "https://gwoc.girlscript.tech/",
    ),
    (
        "Script Winter of Code (SWOC)", "contest", "December",
        "Runs over the winter — check official page for exact dates", "all", "Remote",
        "A winter open source contribution program from Script Foundation India, pairing beginner contributors with mentors and offering swag rewards.",
        "https://swoc.scriptindia.org/",
    ),
    (
        "Tata Imagination Challenge 2026", "contest", "August",
        "Round 1 (Tata Quiz) runs Aug 24 – Sep 13, 2026; finale in Mumbai Nov 17–19, 2026", "all", "Remote",
        "India's biggest idea competition from the Tata Group, open to all undergraduate and postgraduate students in India across any stream. Pitch an original idea through four rounds — quiz, gamified reasoning challenge, video idea pitch, and a leadership idea-defence round — for a shot at the finale in Mumbai. Winners get ₹2 lakh in cash prizes, a Tata Trails experience, and a look at careers with the Tata Group; all finalists get a fully sponsored two-day Mumbai trip.",
        "https://www.tata.com/careers/programs/tata-imagination-challenge",
    ),
    (
        "Women Techsters Fellowship", "women_in_tech", "January",
        "Applications typically open in January for the year-long cohort", "all", "Remote",
        "A year-long fellowship from Tech4Dev for women across Africa, offering technical training and real-world project experience across tracks like DevOps, cybersecurity, data science, mobile development, and software engineering.",
        "https://womentechsters.org/",
    ),
    (
        "WECode Conference Tech Fellowship", "women_in_tech", "October",
        "Applications typically close in October; results in November", "all", "In-person",
        "A technology fellowship tied to the WECode Conference at Harvard University, for current post-secondary students who identify as women or non-binary with a demonstrated interest in technology.",
        "https://www.wecodeconference.com/tech-fellow",
    ),
    (
        "Palantir Women in Technology Scholarship", "women_in_tech", "February",
        "Applications typically close in late February", "all", "Remote",
        "A scholarship and professional development program from Palantir for women pursuing computer science, software engineering, or related technical fields, including a $7,000 award and a workshop with Palantir engineers.",
        "https://www.palantir.com/careers/students/scholarship/wit-north-america/",
    ),
    (
        "TikTok TechJam", "contest", "September",
        "Grand final and winners announced mid-September", "all", "Hybrid",
        "TikTok's global hackathon, open to developers building creative solutions across multiple tracks, culminating in a grand final event in Singapore.",
        "https://tiktoktechjam2026.devpost.com/",
    ),
    (
        "DevNetwork API + Cloud + AI Hackathon", "contest", "September",
        "Submissions close early September", "all", "Hybrid",
        "A challenge-driven hackathon held alongside API World, open to developers building with APIs, cloud infrastructure, and AI — in person in Santa Clara or online.",
        "https://api-cloud-ai-hackathon-2026.devpost.com/",
    ),
    (
        "Hack for Humanity", "contest", "September",
        "Runs as a one-month event, submissions close early September", "all", "Remote",
        "A beginner-friendly hackathon focused on using technology, with an optional AI angle, to address mental and physical health challenges. No prior experience required.",
        "https://hack-for-humanity-summer-26.devpost.com/",
    ),
    (
        "AI Builders Hackathon", "contest", "September",
        "Submissions close mid-September", "all", "Remote",
        "A student-only hackathon challenging participants to build real AI products that solve genuine problems, rather than another AI demo or prototype.",
        "https://ai-builders-hackathon-2026.devpost.com/",
    ),
]


def main():
    db.init_db()  # safe to call even if tables already exist
    existing_names = {e["name"] for e in db.get_all_events()}

    added = 0
    for name, kind, month, window, category, fmt, summary, link in NEW_EVENTS:
        if name in existing_names:
            print(f"Skipping '{name}' — already on your calendar.")
            continue
        db.add_event(name, kind, month, window, category, fmt, summary, link)
        print(f"Added '{name}'.")
        added += 1

    # One-off correction: GirlScript Summer of Code was originally mislabeled
    # "Women-focused" on this site. GSSoC is actually open to all genders —
    # the name is misleading but the program itself isn't gender-restricted.
    # Fix it here so anyone who already has the old (wrong) category gets
    # corrected just by re-running this script.
    gssoc = db.get_all_events()
    for event in gssoc:
        if event["name"] == "GirlScript Summer of Code (GSSoC)" and event["category"] == "women":
            conn = db.get_connection()
            conn.execute(
                "UPDATE events SET category = 'all' WHERE id = ?", (event["id"],)
            )
            conn.commit()
            conn.close()
            print("Corrected GirlScript Summer of Code (GSSoC): was tagged "
                  "'Women-focused', now tagged 'Open to all' (the program "
                  "isn't actually gender-restricted).")

    # One-off correction: the site's category system was fully redesigned.
    # There used to be a separate "category" (Women-focused / Open to all)
    # plus a "kind" with a "Program / Bootcamp" option. Now there are only
    # three categories total, and every event belongs to exactly one:
    # Women in Tech, Open Source, or Hackathon. This corrects any existing
    # database — regardless of what it currently has stored — to the new
    # three-way classification.
    kind_fixes = {
        "Django Girls Workshop Season": "women_in_tech",
        "Google Summer of Code — Org Applications": "open_source",
        "Kode With Klossy Summer Camps": "women_in_tech",
        "Google Summer of Code — Contributor Applications": "open_source",
        "Women Who Code — Spring CONNECT Series": "women_in_tech",
        "Outreachy — May Round Applications Open": "open_source",
        "ADA Developers Academy — Cohort Applications": "women_in_tech",
        "Google Summer of Code — Coding Begins": "open_source",
        "Outreachy Internship Round Begins": "open_source",
        "Techtonica Free Coding Bootcamp": "women_in_tech",
        "Girls Who Code Summer Immersion Program": "women_in_tech",
        "MLH Fellowship — Summer Batch": "open_source",
        "Rewriting the Code — Summer Summit": "women_in_tech",
        "WiCyS Conference Prep & Scholarships": "women_in_tech",
        "Google Summer of Code — Final Evaluations": "open_source",
        "Outreachy — December Round Opens": "open_source",
        "Hacktoberfest": "open_source",
        "Grace Hopper Celebration (AnitaB.org)": "women_in_tech",
        "She++ TechHER Conference": "women_in_tech",
        "Codebar Weekly Coaching Sessions": "open_source",
        "Outreachy — December Round Begins": "open_source",
        "LFX Mentorship — Winter Term": "open_source",
        "Season of KDE": "open_source",
        "Summer of Bitcoin": "open_source",
        "FOSSEE Summer Fellowship": "open_source",
        "European Summer of Code (ESoC)": "open_source",
        "GirlScript Summer of Code (GSSoC)": "open_source",
        "Code for GovTech (C4GT)": "open_source",
        "Linux Kernel Mentorship Program": "open_source",
        "Igalia Coding Experience": "open_source",
        "24 Pull Requests": "open_source",
        "Open Source Connect India 2026": "open_source",
        "All Things Agentic Hackathon": "contest",
        "The WebMCP Challenge": "contest",
        "Agentic Cinema: The Blockbuster Hackathon": "contest",
        "Agents for Humans Hackathon": "contest",
        "CALL-E: Your Code Is Calling": "contest",
        "AWS Trainium Frontier Competition": "contest",
        "RevenueCat Shipaton 2026": "contest",
        "Nebius x NVIDIA Global AI Hackathon": "contest",
        "Free Software Foundation Internship": "open_source",
        "LF Decentralized Trust Mentorship": "open_source",
        "sktime Mentoring Program": "open_source",
        "Djangonaut Space": "open_source",
        "Kubernetes Release Shadow Program": "open_source",
        "Swift Mentorship Program": "open_source",
        "KubeStellar IFoS (Interns for Open Source)": "open_source",
        "Open Mainframe Project Mentorship": "open_source",
        "FOSSASIA Internship": "open_source",
        "Open Source Research Experience (OSRE)": "open_source",
        "Google Season of Docs": "open_source",
    }
    all_events = db.get_all_events()
    corrected_count = 0
    for event in all_events:
        correct_kind = kind_fixes.get(event["name"])
        if correct_kind and event["kind"] != correct_kind:
            conn = db.get_connection()
            conn.execute(
                "UPDATE events SET kind = ? WHERE id = ?", (correct_kind, event["id"])
            )
            conn.commit()
            conn.close()
            label = {"women_in_tech": "Women in Tech", "open_source": "Open Source", "contest": "Hackathon"}[correct_kind]
            print(f"Corrected '{event['name']}': now tagged '{label}'.")
            corrected_count += 1

    if corrected_count:
        print(f"\nRecategorized {corrected_count} event(s) into the new three-category system.")

    print(f"\nDone — added {added} new event(s).")


if __name__ == "__main__":
    main()
