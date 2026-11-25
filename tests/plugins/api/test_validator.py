"""Request validation unit tests for RequestValidatorTool."""

from xeren.plugins.api.schemas import ApiRequest
from xeren.plugins.api.tools.validator import RequestValidatorTool


def test_validator_valid_endpoints():
    """Verify standard /v1 endpoints are validated successfully."""
    validator = RequestValidatorTool()

    for path in ["/v1/health", "/v1/research", "/v1/coding", "/v1/keys"]:
        req = ApiRequest(endpoint=path, method="POST")
        is_valid, err = validator.validate_request(req)
        assert is_valid is True
        assert err is None


def test_validator_null_bytes_rejection():
    """Verify paths with null bytes are rejected with status 400."""
    validator = RequestValidatorTool()
    req = ApiRequest(endpoint="/v1/research\0evil", method="POST")

    is_valid, err = validator.validate_request(req)
    assert is_valid is False
    assert err is not None
    assert err.status_code == 400
    assert "null bytes" in err.message.lower()


def test_validator_unsupported_method():
    """Verify unapproved HTTP methods are rejected with status 405."""
    validator = RequestValidatorTool()
    req = ApiRequest(endpoint="/v1/research", method="PATCH_CUSTOM")

    is_valid, err = validator.validate_request(req)
    assert is_valid is False
    assert err is not None
    assert err.status_code == 405
    assert "method" in err.message.lower()


def test_validator_unsupported_version_or_unknown_endpoint():
    """Verify non-v1 or unknown endpoints fail with status 404."""
    validator = RequestValidatorTool()

    # Old or unknown version
    req1 = ApiRequest(endpoint="/v2/research", method="POST")
    is_valid, err1 = validator.validate_request(req1)
    assert is_valid is False
    assert err1 is not None
    assert err1.status_code == 404

    # Unknown endpoint
    req2 = ApiRequest(endpoint="/v1/unknown_subsystem", method="POST")
    is_valid, err2 = validator.validate_request(req2)
    assert is_valid is False
    assert err2 is not None
    assert err2.status_code == 404


def test_validator_payload_size_limit():
    """Verify payloads exceeding max size limit fail with status 413."""
    # Small ceiling: 100 bytes
    validator = RequestValidatorTool(max_body_size_bytes=100)

    # Valid payload: ~20 bytes
    req_small = ApiRequest(endpoint="/v1/data", body={"text": "short"})
    valid, err = validator.validate_request(req_small)
    assert valid is True

    # Oversized payload: 200 bytes
    req_large = ApiRequest(endpoint="/v1/data", body={"text": "x" * 200})
    valid_large, err_large = validator.validate_request(req_large)
    assert valid_large is False
    assert err_large is not None
    assert err_large.status_code == 413
    assert err_large.code == "PAYLOAD_TOO_LARGE"
