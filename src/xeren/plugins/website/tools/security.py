"""Static security analysis tool scanning website files for vulnerabilities and sensitive data."""

import asyncio
import logging
from pathlib import Path
import re
from typing import List, Optional, Sequence

from xeren.plugins.coding.schemas import FileArtifact
from xeren.plugins.website.schemas import (
    SecurityFinding,
    SecurityFindingSeverity,
    SecurityReport,
)

logger = logging.getLogger("xeren.plugins.website.tools.security")

# Secret and credential regexes
SECRET_PATTERNS = [
    (re.compile(r"\b(?:sk-[A-Za-z0-9]{20,})\b"), "SEC_OPENAI_KEY", "Potential OpenAI API key exposed in client code"),
    (re.compile(r"\b(?:AKIA[0-9A-Z]{16})\b"), "SEC_AWS_KEY", "Potential AWS Access Key ID exposed in client code"),
    (re.compile(r"\b(?:ghp_[A-Za-z0-9]{36})\b"), "SEC_GITHUB_TOKEN", "Potential GitHub Personal Access Token exposed in client code"),
    (re.compile(r"\b(?:Bearer\s+[A-Za-z0-9\-\._~\+\/]{20,})\b", re.IGNORECASE), "SEC_BEARER_TOKEN", "Hardcoded Bearer authentication token detected"),
    (re.compile(r"""(?i)(?:api_key|apikey|secret_key|private_key|auth_token|client_secret)\s*[:=]\s*['"][A-Za-z0-9_\-]{8,}['"]"""), "SEC_HARDCODED_SECRET", "Hardcoded API key or secret credential detected"),
]

# Dangerous JS / DOM manipulation patterns
DANGEROUS_JS_PATTERNS = [
    (re.compile(r"\beval\s*\("), "SEC_UNSAFE_EVAL", SecurityFindingSeverity.HIGH, "Use of 'eval()' allows arbitrary script execution (XSS risk)"),
    (re.compile(r"\bdocument\.write\s*\("), "SEC_UNSAFE_DOC_WRITE", SecurityFindingSeverity.HIGH, "Use of 'document.write()' can lead to DOM-based XSS vulnerabilities"),
    (re.compile(r"\.innerHTML\s*="), "SEC_UNSAFE_INNERHTML", SecurityFindingSeverity.MEDIUM, "Direct assignment to 'innerHTML' can lead to DOM XSS if unescaped"),
    (re.compile(r"\bnew\s+Function\s*\("), "SEC_UNSAFE_NEW_FUNCTION", SecurityFindingSeverity.HIGH, "Use of 'new Function()' evaluates strings as executable code (XSS risk)"),
    (re.compile(r"""\b(?:setTimeout|setInterval)\s*\(\s*['"]"""), "SEC_STRING_TIMER", SecurityFindingSeverity.MEDIUM, "Passing strings to setTimeout/setInterval evaluates code dynamically"),
]

# Insecure protocol patterns
INSECURE_URL_PATTERN = re.compile(r"""(?:src|href|url)\s*[:=]\s*['"]http://[^'"]+['"]""", re.IGNORECASE)

# Suspicious executable downloads
SUSPICIOUS_EXECUTABLE_PATTERN = re.compile(r"""['"][^'"]+\.(?:exe|bat|sh|cmd|ps1|vbs|msi)['"]""", re.IGNORECASE)

# Path traversal patterns inside code/markup
PATH_TRAVERSAL_PATTERN = re.compile(r"""(?:src|href)\s*=\s*['"](?:\.\./){2,}[^'"]*['"]""", re.IGNORECASE)
ABSOLUTE_SYSTEM_PATH_PATTERN = re.compile(r"""['"](?:/etc/|/var/|[a-zA-Z]:\\|[a-zA-Z]:/)[^'"]*['"]""")


class WebsiteSecurityTool:
    """Performs static security analysis over website code and resources.

    Notice: This provides static pattern analysis and does not substitute for a full
    production penetration test or dynamic application security assessment.
    """

    AUDIT_DISCLAIMER = "Static Security Analysis (not a full production audit)"

    def check_security(self, files: Sequence[FileArtifact]) -> SecurityReport:
        """Inspect all website project files for static security anti-patterns."""
        findings: List[SecurityFinding] = []

        for artifact in files:
            lines = artifact.content.splitlines()

            for line_idx, line in enumerate(lines, start=1):
                # 1. Check for hardcoded credentials / tokens
                for pattern, rule_id, message in SECRET_PATTERNS:
                    match = pattern.search(line)
                    if match:
                        snippet = line.strip()[:100]
                        findings.append(
                            SecurityFinding(
                                rule_id=rule_id,
                                severity=SecurityFindingSeverity.CRITICAL,
                                message=message,
                                file_path=artifact.file_path,
                                line=line_idx,
                                snippet=snippet,
                            )
                        )

                # 2. Check for dangerous JS patterns in JS/HTML
                ext = Path(artifact.file_path).suffix.lower()
                if ext in (".js", ".html", ".htm") or artifact.language.lower() in ("javascript", "html", "js"):
                    for pattern, rule_id, severity, message in DANGEROUS_JS_PATTERNS:
                        match = pattern.search(line)
                        if match:
                            findings.append(
                                SecurityFinding(
                                    rule_id=rule_id,
                                    severity=severity,
                                    message=message,
                                    file_path=artifact.file_path,
                                    line=line_idx,
                                    snippet=line.strip()[:100],
                                )
                            )

                # 3. Check for insecure HTTP references
                if INSECURE_URL_PATTERN.search(line):
                    findings.append(
                        SecurityFinding(
                            rule_id="SEC_INSECURE_HTTP_RESOURCE",
                            severity=SecurityFindingSeverity.MEDIUM,
                            message="Resource requested over insecure HTTP instead of HTTPS (mixed content risk)",
                            file_path=artifact.file_path,
                            line=line_idx,
                            snippet=line.strip()[:100],
                        )
                    )

                # 4. Check for suspicious executable downloads
                if SUSPICIOUS_EXECUTABLE_PATTERN.search(line):
                    findings.append(
                        SecurityFinding(
                            rule_id="SEC_SUSPICIOUS_EXECUTABLE",
                            severity=SecurityFindingSeverity.HIGH,
                            message="Suspicious link or reference to executable binary (.exe, .sh, .bat, etc.)",
                            file_path=artifact.file_path,
                            line=line_idx,
                            snippet=line.strip()[:100],
                        )
                    )

                # 5. Check for path traversal in links
                if PATH_TRAVERSAL_PATTERN.search(line):
                    findings.append(
                        SecurityFinding(
                            rule_id="SEC_PATH_TRAVERSAL_LINK",
                            severity=SecurityFindingSeverity.HIGH,
                            message="Suspicious directory traversal sequence ('../../') detected in resource link",
                            file_path=artifact.file_path,
                            line=line_idx,
                            snippet=line.strip()[:100],
                        )
                    )

                # 6. Check for absolute system file references
                if ABSOLUTE_SYSTEM_PATH_PATTERN.search(line):
                    findings.append(
                        SecurityFinding(
                            rule_id="SEC_ABSOLUTE_SYSTEM_PATH",
                            severity=SecurityFindingSeverity.MEDIUM,
                            message="Suspicious absolute host filesystem path referenced in web code",
                            file_path=artifact.file_path,
                            line=line_idx,
                            snippet=line.strip()[:100],
                        )
                    )

        # High or Critical severity findings cause the security check to fail
        blocking_findings = [
            f for f in findings if f.severity in (SecurityFindingSeverity.CRITICAL, SecurityFindingSeverity.HIGH)
        ]
        passed = len(blocking_findings) == 0

        summary = (
            f"Security scan passed cleanly with 0 high/critical risks across {len(files)} file(s)."
            if passed
            else f"Security scan detected {len(blocking_findings)} high/critical risk(s) across {len(files)} file(s)."
        )

        return SecurityReport(
            passed=passed,
            findings=findings,
            audit_type=self.AUDIT_DISCLAIMER,
            scanned_files_count=len(files),
            summary=summary,
        )

    async def acheck_security(self, files: Sequence[FileArtifact]) -> SecurityReport:
        """Asynchronously scan website files for security findings."""
        return await asyncio.to_thread(self.check_security, files)


__all__ = ["WebsiteSecurityTool"]
