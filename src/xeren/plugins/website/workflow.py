"""Website workflow orchestrating requirements analysis, generation, editing, validation, security, and preview."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from xeren.plugins.coding.schemas import (
    Diagnostic,
    FileArtifact,
    TestSummary,
    VerificationStatus,
)
from xeren.plugins.website.registry import WebsiteToolRegistry
from xeren.plugins.website.schemas import (
    PreviewInfo,
    SecurityFindingSeverity,
    SecurityReport,
    ValidationResult,
    WebsiteInput,
    WebsiteOperation,
    WebsiteResult,
    WebsiteSpecification,
    WebsiteType,
)

logger = logging.getLogger("xeren.plugins.website.workflow")


class WebsiteWorkflow:
    """Orchestrates end-to-end website generation, modification, validation, and security workflows."""

    def __init__(self, registry: Optional[WebsiteToolRegistry] = None) -> None:
        self.registry = registry or WebsiteToolRegistry()

    # -------------------------------------------------------------------------
    # Individual Operations
    # -------------------------------------------------------------------------
    def execute_analyze_requirements(self, input_data: WebsiteInput) -> WebsiteResult:
        """Analyze natural language requirement and return structured specification."""
        start_time = time.perf_counter()

        spec = self.registry.requirements_tool.analyze(
            requirement=input_data.requirement,
            website_type=input_data.website_type,
            pages=input_data.pages,
            features=input_data.features,
            design_requirements=input_data.design_requirements,
            content_requirements=input_data.content_requirements,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        type_str = input_data.website_type.value if isinstance(input_data.website_type, WebsiteType) else str(input_data.website_type)

        return WebsiteResult(
            operation=WebsiteOperation.ANALYZE_REQUIREMENTS,
            requirement=input_data.requirement,
            website_type=type_str,
            specification=spec,
            detected_pages=spec.pages,
            stats={"latency_ms": latency_ms},
            success=True,
        )

    def execute_generate(self, input_data: WebsiteInput) -> WebsiteResult:
        """Generate a complete website project from specification or requirement."""
        start_time = time.perf_counter()

        # Step 1: Obtain or analyze specification
        spec = input_data.specification
        if not spec:
            spec = self.registry.requirements_tool.analyze(
                requirement=input_data.requirement,
                website_type=input_data.website_type,
                pages=input_data.pages,
                features=input_data.features,
                design_requirements=input_data.design_requirements,
                content_requirements=input_data.content_requirements,
            )

        # Step 2: Generate project files
        files = self.registry.generator_tool.generate_project(spec)

        # Step 3: Validate generated files
        validation: ValidationResult = self.registry.validator_tool.validate(files)

        # Step 4: Run static security checks
        security_report: SecurityReport = self.registry.security_tool.check_security(files)

        # Step 5: Determine verification status
        has_critical_sec = any(
            f.severity in (SecurityFindingSeverity.CRITICAL, SecurityFindingSeverity.HIGH)
            for f in security_report.findings
        )
        if not validation.is_valid or has_critical_sec:
            verif_status = VerificationStatus.FAILED
        elif security_report.findings:
            verif_status = VerificationStatus.WARNING
        else:
            verif_status = VerificationStatus.PASSED

        # Step 6: Safe Preview Preparation
        preview: Optional[PreviewInfo] = None
        try:
            preview = self.registry.preview_provider.prepare_preview(
                files, options=input_data.preview_options
            )
        except Exception as err:
            logger.warning("Preview preparation failed: %s", err)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        type_str = input_data.website_type.value if isinstance(input_data.website_type, WebsiteType) else str(input_data.website_type)
        detected_pages = [f.file_path for f in files if f.file_path.endswith(".html")]
        assets = [f.file_path for f in files if not f.file_path.endswith(".html")]

        diagnostics: List[Diagnostic] = list(validation.diagnostics)
        success = validation.is_valid and security_report.passed

        return WebsiteResult(
            operation=WebsiteOperation.GENERATE,
            requirement=input_data.requirement,
            website_type=type_str,
            specification=spec,
            files=files,
            detected_pages=detected_pages,
            assets=assets,
            diagnostics=diagnostics,
            validation=validation,
            security_report=security_report,
            preview=preview,
            verification_status=verif_status,
            stats={"latency_ms": latency_ms, "files_count": len(files)},
            success=success,
            error=None if success else "Website generation encountered validation or security issues.",
        )

    def execute_edit(self, input_data: WebsiteInput) -> WebsiteResult:
        """Modify an existing website project according to instruction."""
        start_time = time.perf_counter()
        mod_req = input_data.modification_request or input_data.requirement

        all_files, modified_files = self.registry.generator_tool.edit_project(
            existing_files=input_data.existing_files,
            modification_request=mod_req,
            spec=input_data.specification,
        )

        # Validate modified project
        validation: ValidationResult = self.registry.validator_tool.validate(all_files)
        security_report: SecurityReport = self.registry.security_tool.check_security(all_files)

        has_critical_sec = any(
            f.severity in (SecurityFindingSeverity.CRITICAL, SecurityFindingSeverity.HIGH)
            for f in security_report.findings
        )
        verif_status = VerificationStatus.FAILED if (not validation.is_valid or has_critical_sec) else VerificationStatus.PASSED

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        type_str = input_data.website_type.value if isinstance(input_data.website_type, WebsiteType) else str(input_data.website_type)
        detected_pages = [f.file_path for f in all_files if f.file_path.endswith(".html")]

        return WebsiteResult(
            operation=WebsiteOperation.EDIT,
            requirement=input_data.requirement,
            website_type=type_str,
            specification=input_data.specification,
            files=all_files,
            modified_files=modified_files,
            detected_pages=detected_pages,
            diagnostics=validation.diagnostics,
            validation=validation,
            security_report=security_report,
            verification_status=verif_status,
            stats={"latency_ms": latency_ms, "modified_count": len(modified_files)},
            success=validation.is_valid and security_report.passed,
        )

    def execute_validate(self, input_data: WebsiteInput) -> WebsiteResult:
        """Validate existing website project files."""
        start_time = time.perf_counter()
        validation: ValidationResult = self.registry.validator_tool.validate(input_data.existing_files)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        type_str = input_data.website_type.value if isinstance(input_data.website_type, WebsiteType) else str(input_data.website_type)
        detected_pages = [f.file_path for f in input_data.existing_files if f.file_path.endswith(".html")]

        return WebsiteResult(
            operation=WebsiteOperation.VALIDATE,
            requirement=input_data.requirement,
            website_type=type_str,
            files=input_data.existing_files,
            detected_pages=detected_pages,
            diagnostics=validation.diagnostics,
            validation=validation,
            verification_status=VerificationStatus.PASSED if validation.is_valid else VerificationStatus.FAILED,
            stats={"latency_ms": latency_ms},
            success=validation.is_valid,
            error=None if validation.is_valid else "Website validation failed with structural or syntax errors.",
        )

    def execute_security_check(self, input_data: WebsiteInput) -> WebsiteResult:
        """Run static security scan on existing website files."""
        start_time = time.perf_counter()
        report: SecurityReport = self.registry.security_tool.check_security(input_data.existing_files)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        type_str = input_data.website_type.value if isinstance(input_data.website_type, WebsiteType) else str(input_data.website_type)
        detected_pages = [f.file_path for f in input_data.existing_files if f.file_path.endswith(".html")]

        return WebsiteResult(
            operation=WebsiteOperation.SECURITY_CHECK,
            requirement=input_data.requirement,
            website_type=type_str,
            files=input_data.existing_files,
            detected_pages=detected_pages,
            security_report=report,
            verification_status=VerificationStatus.PASSED if report.passed else VerificationStatus.FAILED,
            stats={"latency_ms": latency_ms, "findings_count": len(report.findings)},
            success=report.passed,
            error=None if report.passed else "Static security check identified potential vulnerabilities.",
        )

    def execute_verify(self, input_data: WebsiteInput) -> WebsiteResult:
        """Run complete verification combining validation, security analysis, and testing."""
        start_time = time.perf_counter()
        files = input_data.existing_files
        validation = self.registry.validator_tool.validate(files)
        security_report = self.registry.security_tool.check_security(files)

        has_critical_sec = any(
            f.severity in (SecurityFindingSeverity.CRITICAL, SecurityFindingSeverity.HIGH)
            for f in security_report.findings
        )

        test_summary: Optional[TestSummary] = None
        tests_ok = True
        # If test suite code or command was provided in metadata or caller options, reuse CodingPlugin
        if "test_code" in input_data.metadata or "test_command" in input_data.metadata:
            coding_res = self.registry.coding_plugin.test_code(
                source_code=files[0].content if files else "",
                test_code=input_data.metadata.get("test_code"),
                test_command=input_data.metadata.get("test_command"),
            )
            test_summary = coding_res.test_summary
            tests_ok = coding_res.success

        if not validation.is_valid or has_critical_sec or not tests_ok:
            verif_status = VerificationStatus.FAILED
        elif security_report.findings:
            verif_status = VerificationStatus.WARNING
        else:
            verif_status = VerificationStatus.PASSED

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        type_str = input_data.website_type.value if isinstance(input_data.website_type, WebsiteType) else str(input_data.website_type)
        detected_pages = [f.file_path for f in files if f.file_path.endswith(".html")]

        success = (verif_status != VerificationStatus.FAILED)

        return WebsiteResult(
            operation=WebsiteOperation.VERIFY,
            requirement=input_data.requirement,
            website_type=type_str,
            files=files,
            detected_pages=detected_pages,
            diagnostics=validation.diagnostics,
            validation=validation,
            security_report=security_report,
            test_results=test_summary,
            verification_status=verif_status,
            stats={"latency_ms": latency_ms},
            success=success,
            error=None if success else "Website verification failed.",
        )

    def execute_preview(self, input_data: WebsiteInput) -> WebsiteResult:
        """Prepare preview representation for website files."""
        start_time = time.perf_counter()
        files = input_data.existing_files
        preview = self.registry.preview_provider.prepare_preview(files, options=input_data.preview_options)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        type_str = input_data.website_type.value if isinstance(input_data.website_type, WebsiteType) else str(input_data.website_type)
        detected_pages = [f.file_path for f in files if f.file_path.endswith(".html")]

        return WebsiteResult(
            operation=WebsiteOperation.PREVIEW,
            requirement=input_data.requirement,
            website_type=type_str,
            files=files,
            detected_pages=detected_pages,
            preview=preview,
            stats={"latency_ms": latency_ms},
            success=True,
        )

    # -------------------------------------------------------------------------
    # Main Workflow Dispatcher
    # -------------------------------------------------------------------------
    def run(self, input_data: WebsiteInput) -> WebsiteResult:
        """Synchronously execute the appropriate workflow operation."""
        op = input_data.operation
        if op == WebsiteOperation.ANALYZE_REQUIREMENTS:
            return self.execute_analyze_requirements(input_data)
        elif op == WebsiteOperation.GENERATE:
            return self.execute_generate(input_data)
        elif op == WebsiteOperation.EDIT:
            return self.execute_edit(input_data)
        elif op == WebsiteOperation.VALIDATE:
            return self.execute_validate(input_data)
        elif op == WebsiteOperation.SECURITY_CHECK:
            return self.execute_security_check(input_data)
        elif op == WebsiteOperation.VERIFY:
            return self.execute_verify(input_data)
        elif op == WebsiteOperation.PREVIEW:
            return self.execute_preview(input_data)
        return self.execute_generate(input_data)

    async def arun(self, input_data: WebsiteInput) -> WebsiteResult:
        """Asynchronously execute the appropriate workflow operation."""
        return await asyncio.to_thread(self.run, input_data)


__all__ = ["WebsiteWorkflow"]
