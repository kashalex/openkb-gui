# AGENTS.md

This file configures knowledge behavior for OpenKB.

## Overview

AGENTS.md is the central configuration file that defines how OpenKB:
- Extracts concepts from your documents
- Generates summaries
- Creates cross-links between wiki pages
- Builds the knowledge graph

## Concept Extraction

Concepts are automatically synthesized from your documents. Each concept page:
- Consolidates information about a specific topic
- Links to related concepts
- Provides a summary of the concept

## Summary Generation

Summaries provide overviews of:
- Individual documents
- Topic clusters
- Time-based aggregations

## Cross-Linking

Wiki pages are automatically linked using:
- `[[Concept Name]]` syntax
- Automatic detection of related content
- Knowledge graph relationships

## Customization

You can customize this file to:
- Define custom concept extraction rules
- Adjust summary generation parameters
- Configure cross-linking behavior
- Add custom metadata

---

*This file is part of the OpenKB knowledge base configuration.*
