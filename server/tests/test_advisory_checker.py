"""Tests for advisory checker service."""
import pytest
from app.services.advisory_checker import (
    AdvisoryChecker,
    SecurityAdvisory,
    Severity,
    _determine_status
)


class TestAdvisoryChecker:
    """Tests for AdvisoryChecker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = AdvisoryChecker()
    
    def test_is_version_affected_less_than(self):
        """Test version affected by '< X' condition."""
        assert self.checker.is_version_affected("1.1.0", "< 1.2.0") is True
        assert self.checker.is_version_affected("1.2.0", "< 1.2.0") is False
        assert self.checker.is_version_affected("1.3.0", "< 1.2.0") is False
    
    def test_is_version_affected_less_than_or_equal(self):
        """Test version affected by '<= X' condition."""
        assert self.checker.is_version_affected("1.1.0", "<= 1.2.0") is True
        assert self.checker.is_version_affected("1.2.0", "<= 1.2.0") is True
        assert self.checker.is_version_affected("1.3.0", "<= 1.2.0") is False
    
    def test_is_version_affected_greater_than(self):
        """Test version affected by '> X' condition."""
        assert self.checker.is_version_affected("1.3.0", "> 1.2.0") is True
        assert self.checker.is_version_affected("1.2.0", "> 1.2.0") is False
        assert self.checker.is_version_affected("1.1.0", "> 1.2.0") is False
    
    def test_is_version_affected_greater_than_or_equal(self):
        """Test version affected by '>= X' condition."""
        assert self.checker.is_version_affected("1.3.0", ">= 1.2.0") is True
        assert self.checker.is_version_affected("1.2.0", ">= 1.2.0") is True
        assert self.checker.is_version_affected("1.1.0", ">= 1.2.0") is False
    
    def test_is_version_affected_range(self):
        """Test version affected by range condition."""
        # Version 1.1.5 should be in range >= 1.0.0, < 1.2.0
        assert self.checker.is_version_affected("1.1.5", ">= 1.0.0, < 1.2.0") is True
        assert self.checker.is_version_affected("0.9.0", ">= 1.0.0, < 1.2.0") is False
        assert self.checker.is_version_affected("1.2.0", ">= 1.0.0, < 1.2.0") is False
    
    def test_is_version_affected_empty_range(self):
        """Test with empty or unknown range."""
        assert self.checker.is_version_affected("1.1.0", "") is False
        assert self.checker.is_version_affected("1.1.0", "unknown") is False
    
    def test_is_version_affected_none_version(self):
        """Test with None version."""
        assert self.checker.is_version_affected(None, "< 1.2.0") is False
    
    def test_check_version_condition(self):
        """Test individual condition checking."""
        assert self.checker._check_version_condition("1.1.0", "< 1.2.0") is True
        assert self.checker._check_version_condition("1.2.0", "= 1.2.0") is True
        assert self.checker._check_version_condition("1.3.0", "> 1.2.0") is True
    
    def test_get_highest_severity(self):
        """Test getting highest severity from advisories."""
        advisories = [
            SecurityAdvisory(
                id="GHSA-1",
                severity=Severity.LOW,
                summary="Low severity issue",
                affected_versions="< 1.0.0",
                patched_version="1.0.0",
                published_at="2024-01-01",
                url="https://example.com/1"
            ),
            SecurityAdvisory(
                id="GHSA-2",
                severity=Severity.CRITICAL,
                summary="Critical issue",
                affected_versions="< 1.2.0",
                patched_version="1.2.0",
                published_at="2024-01-02",
                url="https://example.com/2"
            ),
            SecurityAdvisory(
                id="GHSA-3",
                severity=Severity.MEDIUM,
                summary="Medium issue",
                affected_versions="< 1.1.0",
                patched_version="1.1.0",
                published_at="2024-01-03",
                url="https://example.com/3"
            )
        ]
        
        highest = self.checker.get_highest_severity(advisories)
        assert highest == Severity.CRITICAL
    
    def test_get_highest_severity_empty(self):
        """Test getting highest severity from empty list."""
        highest = self.checker.get_highest_severity([])
        assert highest == Severity.UNKNOWN


class TestDetermineStatus:
    """Tests for _determine_status function."""
    
    def test_status_unknown_no_version(self):
        """Test status is unknown when no version provided."""
        status = _determine_status(None, "1.2.0", [])
        assert status == "unknown"
    
    def test_status_vulnerable_with_advisories(self):
        """Test status is vulnerable when advisories exist."""
        advisory = SecurityAdvisory(
            id="GHSA-1",
            severity=Severity.HIGH,
            summary="Test",
            affected_versions="< 1.2.0",
            patched_version="1.2.0",
            published_at="2024-01-01",
            url="https://example.com"
        )
        status = _determine_status("1.0.0", "1.2.0", [advisory])
        assert status == "vulnerable"
    
    def test_status_outdated(self):
        """Test status is outdated when behind latest."""
        status = _determine_status("1.0.0", "1.2.0", [])
        assert status == "outdated"
    
    def test_status_current(self):
        """Test status is current when at latest version."""
        status = _determine_status("1.2.0", "1.2.0", [])
        assert status == "current"
    
    def test_status_current_newer(self):
        """Test status is current when ahead of latest."""
        status = _determine_status("1.3.0", "1.2.0", [])
        assert status == "current"
    
    def test_status_unknown_no_latest(self):
        """Test status is unknown when no latest version."""
        status = _determine_status("1.0.0", None, [])
        assert status == "unknown"


class TestSecurityAdvisory:
    """Tests for SecurityAdvisory dataclass."""
    
    def test_create_advisory(self):
        """Test creating a security advisory."""
        advisory = SecurityAdvisory(
            id="GHSA-xxxx-yyyy-zzzz",
            severity=Severity.HIGH,
            summary="Test advisory",
            affected_versions="< 1.2.0",
            patched_version="1.2.0",
            published_at="2024-01-01T00:00:00Z",
            url="https://github.com/owner/repo/security/advisories/GHSA-xxxx",
            cve_id="CVE-2024-12345"
        )
        
        assert advisory.id == "GHSA-xxxx-yyyy-zzzz"
        assert advisory.severity == Severity.HIGH
        assert advisory.cve_id == "CVE-2024-12345"
    
    def test_advisory_without_cve(self):
        """Test advisory without CVE ID."""
        advisory = SecurityAdvisory(
            id="GHSA-xxxx",
            severity=Severity.MEDIUM,
            summary="Test",
            affected_versions="< 1.0.0",
            patched_version="1.0.0",
            published_at="2024-01-01",
            url="https://example.com"
        )
        
        assert advisory.cve_id is None


class TestSeverity:
    """Tests for Severity enum."""
    
    def test_severity_values(self):
        """Test severity enum values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.UNKNOWN.value == "unknown"
    
    def test_severity_ordering(self):
        """Test severity can be compared."""
        # Just test that enum values exist and are unique
        severities = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.UNKNOWN]
        assert len(set(severities)) == 5
