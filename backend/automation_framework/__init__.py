"""
automation_framework
=====================
A small plugin-based framework for turning a plain-English request like

    "i want to prepare an exam on DBMS and OS"

into a full agent pipeline:

    understand the request -> ask permission for what's needed
    (local files, web search, ...) -> gather that data -> synthesize
    a finished result with an LLM.

See README.md for architecture and how to add new automations.
"""
