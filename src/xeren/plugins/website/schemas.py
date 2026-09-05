"""Pydantic data schemas for the Xeren Website Creation Plugin."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator

from xeren.plugins.coding.schemas import (
    Diagnostic,
    FileArtifact,
    TestSummary,
    VerificationStatus,
)


class WebsiteOperation(str, Enum):
    """Operation modes supported by the Website Creation Plugin."""

    ANALYZE_REQUIREMENTS = "analyze_requirements"
    GENERATE = "generate"
    EDIT = "edit"
    VALIDATE = "validate"
    SECURITY_CHECK = "security_check"
    VERIFY = "verify"
    PREVIEW = "preview"


class WebsiteType(str, Enum):
    """Standard website categories and archetypes."""

    LANDING_PAGE = "landing_page"
    PORTFOLIO = "portfolio"
    DASHBOARD = "dashboard"
    DOCUMENTATION = "documentation"
    BUSINESS = "business"
    EDUCATIONAL = "educational"
    CUSTOM = "custom"


class WebsiteSpecification(BaseModel):
    """Structured architectural and content specification for a website project."""

    site_purpose: str = Field(default="", description="Primary objective or value proposition of the site")
    target_audience: str = Field(default="", description="Intended audience or user personas")
    pages: List[str] = Field(default_factory=list, description="Target page names or filenames (e.g. index.html)")
    sections: List[str] = Field(default_factory=list, description="Key functional or visual sections")
    features: List[str] = Field(default_factory=list, description="Interactive capabilities or UI widgets")
    content_requirements: List[str] = Field(default_factory=list, description="Copywriting, headings, and assets requirements")
    technology_choice: str = Field(default="html/css/js", description="Selected technology stack")
    responsive_requirements: List[str] = Field(default_factory=list, description="Mobile and desktop layout rules")
    accessibility_requirements: List[str] = Field(default_factory=list, description="WCAG or accessibility considerations")
    security_requirements: List[str] = Field(default_factory=list, description="Client-side security and data privacy rules")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom specification parameters")


class ValidationResult(BaseModel):
    """Aggregated structural and syntax validation results for a website."""

    is_valid: bool = Field(default=True, description="True if no blocking validation errors were detected")
    structure_ok: bool = Field(default=True, description="Project layout and file existence check status")
    html_ok: bool = Field(default=True, description="HTML syntax and document structure validity")
    css_ok: bool = Field(default=True, description="CSS stylesheet syntax validity")
    js_ok: bool = Field(default=True, description="JavaScript syntax and bracket balance validity")
    assets_ok: bool = Field(default=True, description="Asset reference and link integrity status")
    diagnostics: List[Diagnostic] = Field(default_factory=list, description="Diagnostic messages and errors")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed component breakdown")


class SecurityFindingSeverity(str, Enum):
    """Severity levels for website security findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityFinding(BaseModel):
    """A specific static security vulnerability or risk detected in website files."""

    rule_id: str = Field(..., description="Unique rule identifier (e.g. SEC_INLINE_KEY, SEC_UNSAFE_EVAL)")
    severity: SecurityFindingSeverity = Field(default=SecurityFindingSeverity.HIGH, description="Risk level")
    message: str = Field(..., description="Explanation of the security finding and potential risk")
    file_path: Optional[str] = Field(default=None, description="Path of the file containing the finding")
    line: Optional[int] = Field(default=None, ge=1, description="1-indexed line number if determinable")
    snippet: Optional[str] = Field(default=None, description="Code snippet demonstrating the pattern")


class SecurityReport(BaseModel):
    """Static security audit report for the website project."""

    passed: bool = Field(default=True, description="True if no critical or high severity security findings exist")
    findings: List[SecurityFinding] = Field(default_factory=list, description="List of detected security findings")
    audit_type: str = Field(
        default="Static Security Analysis (not a full production audit)",
        description="Explicit notice that this is a static check layer",
    )
    scanned_files_count: int = Field(default=0, ge=0, description="Total number of project files inspected")
    summary: str = Field(default="", description="High-level summary of security assessment")


class PreviewInfo(BaseModel):
    """Metadata describing a rendered or prepared website preview."""

    provider: str = Field(..., description="Preview provider engine (e.g. mock, local)")
    preview_url: Optional[str] = Field(default=None, description="Local or simulated preview URL")
    is_live: bool = Field(default=False, description="Whether preview is backed by a running process")
    status: str = Field(default="ready", description="Current status of the preview environment")
    message: str = Field(default="", description="Explanatory notes regarding preview limitations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional environment attributes")


class WebsiteInput(BaseModel):
    """Input payload for Website Plugin execution."""

    requirement: str = Field(default="", description="Natural language specification or task description")
    operation: WebsiteOperation = Field(
        default=WebsiteOperation.GENERATE,
        description="Target website operation to perform",
    )
    website_type: Union[WebsiteType, str] = Field(
        default=WebsiteType.LANDING_PAGE,
        description="Website archetype or classification",
    )
    preferred_framework: str = Field(default="vanilla", description="Target frontend framework or vanilla stack")
    language: str = Field(default="html/css/js", description="Primary code languages")
    pages: List[str] = Field(default_factory=list, description="Explicit list of requested pages")
    features: List[str] = Field(default_factory=list, description="Requested interactive or layout features")
    design_requirements: List[str] = Field(default_factory=list, description="Aesthetic or design specifications")
    content_requirements: List[str] = Field(default_factory=list, description="Content or copy specifications")
    existing_files: List[FileArtifact] = Field(
        default_factory=list,
        description="Existing website project files for modification, validation, or security auditing",
    )
    modification_request: Optional[str] = Field(
        default=None,
        description="Specific instructions for editing existing website files",
    )
    specification: Optional[WebsiteSpecification] = Field(
        default=None,
        description="Pre-analyzed website specification",
    )
    validation_options: Dict[str, Any] = Field(default_factory=dict, description="Validation configuration")
    security_options: Dict[str, Any] = Field(default_factory=dict, description="Security check configuration")
    preview_options: Dict[str, Any] = Field(default_factory=dict, description="Preview provider configuration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Caller-supplied metadata")

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def validate_operation_inputs(self) -> "WebsiteInput":
        """Ensure required fields are supplied for specific operations."""
        if self.operation in (WebsiteOperation.GENERATE, WebsiteOperation.ANALYZE_REQUIREMENTS):
            if not self.requirement.strip() and not self.specification:
                raise ValueError(f"Operation '{self.operation.value}' requires a non-empty 'requirement' or 'specification'.")
        elif self.operation == WebsiteOperation.EDIT:
            if not self.existing_files:
                raise ValueError("Website edit operation requires 'existing_files' to modify.")
            if not self.modification_request and not self.requirement.strip():
                raise ValueError("Website edit operation requires 'modification_request' or 'requirement'.")
        elif self.operation in (WebsiteOperation.VALIDATE, WebsiteOperation.SECURITY_CHECK, WebsiteOperation.PREVIEW):
            if not self.existing_files and not self.requirement.strip() and not self.specification:
                raise ValueError(
                    f"Operation '{self.operation.value}' requires 'existing_files', 'requirement', or 'specification'."
                )
        return self


class WebsiteResult(BaseModel):
    """Structured result returned by Website Creation Plugin operations."""

    operation: WebsiteOperation = Field(..., description="Executed website operation")
    requirement: str = Field(default="", description="Original natural language requirement")
    website_type: str = Field(default="landing_page", description="Website category or archetype")
    specification: Optional[WebsiteSpecification] = Field(default=None, description="Derived or supplied specification")
    files: List[FileArtifact] = Field(default_factory=list, description="Complete set of generated or modified files")
    modified_files: List[FileArtifact] = Field(default_factory=list, description="Subset of files modified during an edit")
    detected_pages: List[str] = Field(default_factory=list, description="Detected HTML pages in project")
    assets: List[str] = Field(default_factory=list, description="Referenced or included asset paths")
    diagnostics: List[Diagnostic] = Field(default_factory=list, description="Diagnostics collected across pipeline")
    validation: Optional[ValidationResult] = Field(default=None, description="Structural and syntax validation outcome")
    security_report: Optional[SecurityReport] = Field(default=None, description="Static security analysis outcome")
    test_results: Optional[TestSummary] = Field(default=None, description="Test suite results if executed")
    preview: Optional[PreviewInfo] = Field(default=None, description="Preview environment information")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.NOT_RUN,
        description="Overall verification status (syntax, security, tests)",
    )
    stats: Dict[str, Any] = Field(default_factory=dict, description="Execution timing and metrics")
    success: bool = Field(default=True, description="Whether overall operation completed successfully")
    error: Optional[str] = Field(default=None, description="Detailed error description if operation failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and telemetry")

    model_config = {"arbitrary_types_allowed": True}


__all__ = [
    "WebsiteOperation",
    "WebsiteType",
    "WebsiteSpecification",
    "ValidationResult",
    "SecurityFindingSeverity",
    "SecurityFinding",
    "SecurityReport",
    "PreviewInfo",
    "WebsiteInput",
    "WebsiteResult",
]
