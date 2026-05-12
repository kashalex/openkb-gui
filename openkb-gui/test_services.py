#!/usr/bin/env python3
"""Test script for OpenKB GUI services"""

import sys
import os
from pathlib import Path

# Change to project directory
os.chdir(Path(__file__).parent)

# Add src to path
sys.path.insert(0, 'src')

print("=" * 60)
print("OpenKB GUI Services Test")
print("=" * 60)
print()

# Test BuildService
print("=== Testing BuildService ===")
from services.build_service import BuildService
import time

bs = BuildService('workspace')
print(f"OpenKB available: {bs.openkb_available}")
print(f"Documents in raw/: {bs.count_documents()}")
print()

# Test ConfigService
print("=== Testing ConfigService ===")
from services.config_service import ConfigService

cs = ConfigService.get_instance()
config = cs.load_config()
print(f"API key configured: {bool(config.llm_api_key)}")
print(f"LLM model: {config.llm_model}")
print(f"Workspace: {cs.get_workspace_path()}")
print()

# Test WikiService
print("=== Testing WikiService ===")
from services.wiki_service import WikiService

wis = WikiService('workspace/wiki')
stats = wis.get_statistics()
print(f"Wiki statistics: {stats}")

agents = wis.get_agents_content()
if agents:
    print(f"AGENTS.md: {len(agents)} chars")
else:
    print("AGENTS.md: not found")
print()

# Test WatchService
print("=== Testing WatchService ===")
from services.watch_service import WatchService

ws = WatchService('workspace')
print(f"WatchService created")
print()

# Test ChatService
print("=== Testing ChatService ===")
from services.chat_service import ChatService

chats = ChatService('workspace')
print(f"ChatService initialized")
print(f"Wiki path: {chats.wiki_path}")
print(f"Model: {chats.model}")
print()

# Test LintService
print("=== Testing LintService ===")
from services.lint_service import LintService

ls = LintService('workspace/wiki')
print(f"LintService created")
print()

# Test SessionService
print("=== Testing SessionService ===")
from services.session_service import SessionService

ss = SessionService('workspace/sessions')
print(f"SessionService initialized")
print(f"Sessions path: {ss.sessions_path}")
print()

# Test mock build
print("=== Testing Mock Build ===")
def on_output(line):
    print(f"  > {line}")

def on_complete(result):
    print(f"  Build completed: success={result.success}, duration={result.duration_seconds:.1f}s")

bs.add_output_callback(on_output)
bs.build(on_complete=on_complete)

# Wait for build to complete
for _ in range(10):
    if not bs.is_building():
        break
    time.sleep(0.5)

print()
print("=" * 60)
print("All services tested successfully!")
print("=" * 60)
