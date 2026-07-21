# AI Engineer Intelligence Hub

## Vision

Build a self-updating intelligence website that helps AI engineers stay
current with the most important developments in AI engineering.

The first version will use **only the official X MCP server** as its
information source. Over time, additional sources (GitHub releases,
research papers, documentation, blogs, etc.) can be added, but the
initial goal is to build a reliable harness around a single source.

The primary goal is **not** to build a news reader.

The primary goal is to learn **harness engineering** by designing a
reliable, observable, stateful agent system that continuously transforms
raw X posts into a curated engineering intelligence feed.

------------------------------------------------------------------------

# Goals

## Product Goal

Every day, **GitHub Actions** automatically runs the pipeline to produce
a website containing:

-   The most important AI engineering updates
-   Short factual summaries
-   "Why it matters" explanations
-   Links back to the original X posts
-   Search and category filtering
-   A clean reading experience

## Learning Goal

Learn how to build reliable AI systems by implementing:

-   Tool boundaries
-   Durable state
-   Structured agent communication
-   Verification gates
-   Observability
-   Autonomous execution
-   Evaluation
-   Clean handoffs

Rather than relying on a powerful prompt, the project focuses on the
engineering system surrounding the model.

------------------------------------------------------------------------

# Version 1 Scope

Use only the official X MCP server.

Included:

-   Read posts from selected X accounts
-   Collect the previous 24 hours of posts
-   Ignore replies and reposts
-   Normalize the data
-   Deduplicate posts
-   Select the most relevant engineering updates
-   Generate factual summaries
-   Verify generated summaries against the original posts
-   Publish a static website
-   Schedule automatic daily updates

Excluded (for now):

-   GitHub Releases
-   Research papers
-   Blogs
-   RSS feeds
-   Personalized recommendations
-   Self-modifying prompts
-   Multi-source intelligence

------------------------------------------------------------------------

# High-Level Architecture

Scheduled Run ↓ X MCP ↓ Collector ↓ Normalizer ↓ Deduplicator ↓ Curator
Agent ↓ Verifier Agent ↓ Approved Stories ↓ Website ↓ Deployment
Validation

------------------------------------------------------------------------

# System Components

## Collector

Responsibilities:

-   Connect to X MCP
-   Retrieve recent posts
-   Store raw responses
-   Handle API failures
-   Never summarize content

## Normalizer

Responsibilities:

-   Convert raw responses into a consistent schema
-   Remove replies
-   Remove reposts
-   Standardize timestamps
-   Construct canonical URLs

## Curator Agent

Responsibilities:

-   Decide whether a post is important
-   Categorize it
-   Generate a factual title
-   Generate a concise summary
-   Explain why it matters

The curator cannot publish stories.

## Verifier Agent

Responsibilities:

-   Compare every generated claim against the original post
-   Detect unsupported statements
-   Ensure links and metadata are correct
-   Approve or reject stories

Only approved stories move forward.

## Publisher

Responsibilities:

-   Read approved stories
-   Build the website
-   Validate output
-   Deploy

------------------------------------------------------------------------

# Harness Engineering Concepts

This project is intentionally designed to teach harness engineering.

## Tool Boundaries

The model only has access to approved read-only X MCP tools.

## Structured Contracts

Every stage communicates through JSON rather than natural language.

Collector → normalized_posts.json → candidate_stories.json →
verification_results.json → published_stories.json

## Durable State

The system remembers:

-   processed post IDs
-   published stories
-   previous runs
-   failures
-   retry information

No knowledge is stored only inside an LLM conversation.

## Verification

Generated summaries must be supported by the original post before
publication.

## Observability

Every run records:

-   posts collected
-   stories generated
-   verification failures
-   runtime
-   token usage
-   errors

## Autonomous Execution

The entire pipeline should run automatically on a schedule without
manual intervention.

------------------------------------------------------------------------

# Repository Philosophy

The repository is the system of record.

Important information lives in version-controlled files rather than
prompts.

Expected artifacts include:

-   AGENTS.md
-   feature_list.json
-   progress.md
-   configuration files
-   run history
-   verification records

------------------------------------------------------------------------

# Future Roadmap

Once the X-only pipeline is reliable:

Phase 2 - GitHub Releases - GitHub Discussions

Phase 3 - Research papers - Documentation updates

Phase 4 - Personalized relevance ranking

Phase 5 - Feedback-driven improvements

Phase 6 - Harness improvement agent that proposes changes through pull
requests

------------------------------------------------------------------------

# Success Criteria

The project is successful when:

-   Daily updates run automatically.
-   No duplicate stories are published.
-   Unsupported claims are blocked before publication.
-   Failures are observable and recoverable.
-   Every story links to its original source.
-   The system can be safely extended to additional information sources
    without major redesign.

The final result should be a dependable AI engineering intelligence hub
whose architecture demonstrates the core principles of harness
engineering rather than relying solely on prompt engineering.
