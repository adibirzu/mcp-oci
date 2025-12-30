#!/usr/bin/env python3
"""
OCI MCP Server Evaluation Runner

Runs evaluation questions against the MCP server and compares answers.

Usage:
    python scripts/evaluation.py evaluations/cost_evaluation.xml
    python scripts/evaluation.py -t http -u http://localhost:8000/mcp evaluations/cost_evaluation.xml
    python scripts/evaluation.py -o reports/cost_report.md evaluations/cost_evaluation.xml
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class QAPair:
    """Question-Answer pair from evaluation XML."""
    question: str
    expected_answer: str
    actual_answer: Optional[str] = None
    passed: Optional[bool] = None
    error: Optional[str] = None


@dataclass
class EvaluationResult:
    """Results of an evaluation run."""
    name: str
    domain: str
    version: str
    total: int
    passed: int
    failed: int
    errors: int
    accuracy: float
    pairs: list[QAPair] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Evaluation Report: {self.name}",
            f"",
            f"**Domain:** {self.domain}",
            f"**Version:** {self.version}",
            f"**Date:** {datetime.now().isoformat()}",
            f"**Duration:** {self.duration_seconds:.2f}s",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Questions | {self.total} |",
            f"| Passed | {self.passed} |",
            f"| Failed | {self.failed} |",
            f"| Errors | {self.errors} |",
            f"| **Accuracy** | **{self.accuracy:.1f}%** |",
            f"",
            f"## Details",
            f"",
        ]
        
        for i, pair in enumerate(self.pairs, 1):
            status = "✅" if pair.passed else ("⚠️" if pair.error else "❌")
            lines.append(f"### Q{i}. {status}")
            lines.append(f"")
            lines.append(f"**Question:** {pair.question}")
            lines.append(f"")
            lines.append(f"**Expected:** `{pair.expected_answer}`")
            lines.append(f"")
            if pair.error:
                lines.append(f"**Error:** {pair.error}")
            else:
                lines.append(f"**Actual:** `{pair.actual_answer}`")
                lines.append(f"")
                lines.append(f"**Result:** {'PASS' if pair.passed else 'FAIL'}")
            lines.append(f"")
        
        return "\n".join(lines)


def parse_evaluation_xml(xml_path: Path) -> tuple[dict, list[QAPair]]:
    """Parse evaluation XML file."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Parse metadata
    metadata = root.find("metadata")
    meta = {
        "name": metadata.findtext("name", "Unknown"),
        "version": metadata.findtext("version", "1.0"),
        "domain": metadata.findtext("domain", "unknown"),
    }
    
    # Parse QA pairs
    pairs = []
    for qa in root.findall("qa_pair"):
        question = qa.findtext("question", "").strip()
        answer = qa.findtext("answer", "").strip()
        if question and answer:
            pairs.append(QAPair(question=question, expected_answer=answer))
    
    return meta, pairs


def normalize_answer(answer: str) -> str:
    """Normalize answer for comparison."""
    # Strip whitespace, lowercase, handle common variations
    normalized = answer.strip().lower()
    # Remove common prefixes/suffixes
    for prefix in ["the ", "a ", "an "]:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    return normalized


def check_answer(expected: str, actual: str) -> bool:
    """Check if actual answer matches expected."""
    exp_norm = normalize_answer(expected)
    act_norm = normalize_answer(actual)
    
    # Exact match
    if exp_norm == act_norm:
        return True
    
    # Numeric comparison (handle formatting differences)
    try:
        exp_num = float(exp_norm.replace(",", "").replace("$", "").replace("%", ""))
        act_num = float(act_norm.replace(",", "").replace("$", "").replace("%", ""))
        return abs(exp_num - act_num) < 0.01
    except ValueError:
        pass
    
    # Substring match (for longer answers containing the expected value)
    if exp_norm in act_norm:
        return True
    
    return False


async def run_evaluation_stdio(pairs: list[QAPair]) -> list[QAPair]:
    """Run evaluation using stdio transport (placeholder for actual MCP client)."""
    # Note: In a real implementation, this would use the MCP client to:
    # 1. Connect to the server via stdio
    # 2. Send each question as a prompt
    # 3. Parse the response for the answer
    
    print("Note: Evaluation requires MCP client integration.")
    print("This script provides the framework - actual execution requires:")
    print("  1. MCP client library (anthropic-mcp or similar)")
    print("  2. LLM API key for question interpretation")
    print("")
    
    # For now, mark all as errors indicating manual evaluation needed
    for pair in pairs:
        pair.error = "MCP client integration required"
        pair.passed = None
    
    return pairs


async def run_evaluation_http(pairs: list[QAPair], url: str) -> list[QAPair]:
    """Run evaluation using HTTP transport."""
    # Similar to stdio but connects via HTTP
    # Placeholder for actual implementation
    
    print(f"HTTP evaluation against {url} requires MCP client integration.")
    
    for pair in pairs:
        pair.error = "HTTP MCP client integration required"
        pair.passed = None
    
    return pairs


async def main():
    parser = argparse.ArgumentParser(
        description="Run OCI MCP Server evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/evaluation.py evaluations/cost_evaluation.xml
    python scripts/evaluation.py -t http -u http://localhost:8000/mcp evaluations/cost_evaluation.xml
    python scripts/evaluation.py -o reports/cost_report.md evaluations/cost_evaluation.xml
        """
    )
    parser.add_argument("evaluation_file", type=Path, help="Evaluation XML file")
    parser.add_argument("-t", "--transport", choices=["stdio", "http"], default="stdio",
                        help="Transport type (default: stdio)")
    parser.add_argument("-u", "--url", default="http://localhost:8000/mcp",
                        help="HTTP URL for http transport")
    parser.add_argument("-o", "--output", type=Path, help="Output report file (markdown)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate input file
    if not args.evaluation_file.exists():
        print(f"Error: Evaluation file not found: {args.evaluation_file}")
        sys.exit(1)
    
    # Parse evaluation
    print(f"Loading evaluation: {args.evaluation_file}")
    meta, pairs = parse_evaluation_xml(args.evaluation_file)
    print(f"Found {len(pairs)} questions in domain '{meta['domain']}'")
    
    # Run evaluation
    start_time = datetime.now()
    
    if args.transport == "http":
        pairs = await run_evaluation_http(pairs, args.url)
    else:
        pairs = await run_evaluation_stdio(pairs)
    
    duration = (datetime.now() - start_time).total_seconds()
    
    # Calculate results
    passed = sum(1 for p in pairs if p.passed is True)
    failed = sum(1 for p in pairs if p.passed is False)
    errors = sum(1 for p in pairs if p.error is not None)
    total = len(pairs)
    accuracy = (passed / total * 100) if total > 0 else 0
    
    result = EvaluationResult(
        name=meta["name"],
        domain=meta["domain"],
        version=meta["version"],
        total=total,
        passed=passed,
        failed=failed,
        errors=errors,
        accuracy=accuracy,
        pairs=pairs,
        duration_seconds=duration,
    )
    
    # Output results
    report = result.to_markdown()
    
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report)
        print(f"Report written to: {args.output}")
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Evaluation: {meta['name']}")
    print(f"Domain: {meta['domain']}")
    print(f"Results: {passed}/{total} passed ({accuracy:.1f}%)")
    if errors > 0:
        print(f"Errors: {errors}")
    print("=" * 50)
    
    # Exit with appropriate code
    if accuracy < 70:
        sys.exit(1)  # Below threshold
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
