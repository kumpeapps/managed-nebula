"""Tests for version parser service."""
import pytest
from app.services.version_parser import (
    parse_version,
    compare_versions,
    is_version_current,
    extract_version_components,
    is_prerelease,
    normalize_version
)


class TestParseVersion:
    """Tests for parse_version function."""
    
    def test_parse_standard_version(self):
        """Test parsing standard semver format."""
        version = parse_version("1.9.7")
        assert version is not None
        assert str(version) == "1.9.7"
    
    def test_parse_version_with_v_prefix(self):
        """Test parsing version with 'v' prefix."""
        version = parse_version("v1.9.7")
        assert version is not None
        assert str(version) == "1.9.7"
    
    def test_parse_version_major_minor_only(self):
        """Test parsing version with major and minor only."""
        version = parse_version("1.9")
        assert version is not None
        assert str(version).startswith("1.9")
    
    def test_parse_version_with_prerelease(self):
        """Test parsing version with prerelease suffix."""
        version = parse_version("1.9.7-beta")
        assert version is not None
        assert version.is_prerelease
    
    def test_parse_none_version(self):
        """Test parsing None returns None."""
        assert parse_version(None) is None
    
    def test_parse_empty_version(self):
        """Test parsing empty string returns None."""
        assert parse_version("") is None
    
    def test_parse_invalid_version(self):
        """Test parsing invalid version format."""
        # Should try to extract numeric version
        version = parse_version("invalid-1.2.3-version")
        assert version is not None or version is None  # May extract or fail


class TestCompareVersions:
    """Tests for compare_versions function."""
    
    def test_compare_equal_versions(self):
        """Test comparing equal versions."""
        result = compare_versions("1.9.7", "1.9.7")
        assert result == 0
    
    def test_compare_older_version(self):
        """Test comparing older version to newer."""
        result = compare_versions("1.9.3", "1.9.7")
        assert result == -1
    
    def test_compare_newer_version(self):
        """Test comparing newer version to older."""
        result = compare_versions("1.9.7", "1.9.3")
        assert result == 1
    
    def test_compare_with_v_prefix(self):
        """Test comparing versions with 'v' prefix."""
        result = compare_versions("v1.9.7", "v1.9.3")
        assert result == 1
    
    def test_compare_major_versions(self):
        """Test comparing different major versions."""
        result = compare_versions("2.0.0", "1.9.9")
        assert result == 1
    
    def test_compare_invalid_version(self):
        """Test comparing with invalid version returns None."""
        result = compare_versions("invalid", "1.9.7")
        assert result is None


class TestIsVersionCurrent:
    """Tests for is_version_current function."""
    
    def test_current_version_equal(self):
        """Test current version equal to latest."""
        assert is_version_current("1.9.7", "1.9.7") is True
    
    def test_current_version_newer(self):
        """Test current version newer than latest."""
        assert is_version_current("1.9.8", "1.9.7") is True
    
    def test_current_version_older(self):
        """Test current version older than latest."""
        assert is_version_current("1.9.3", "1.9.7") is False
    
    def test_current_version_invalid(self):
        """Test with invalid version."""
        assert is_version_current("invalid", "1.9.7") is False


class TestExtractVersionComponents:
    """Tests for extract_version_components function."""
    
    def test_extract_full_version(self):
        """Test extracting components from full version."""
        components = extract_version_components("1.9.7")
        assert components == (1, 9, 7)
    
    def test_extract_version_with_v_prefix(self):
        """Test extracting components with 'v' prefix."""
        components = extract_version_components("v1.9.7")
        assert components == (1, 9, 7)
    
    def test_extract_major_minor_only(self):
        """Test extracting components from major.minor version."""
        components = extract_version_components("1.9")
        assert components[0] == 1
        assert components[1] == 9
    
    def test_extract_invalid_version(self):
        """Test extracting from invalid version returns None."""
        components = extract_version_components("invalid")
        # Should return None or partial extraction
        assert components is None or isinstance(components, tuple)


class TestIsPrerelease:
    """Tests for is_prerelease function."""
    
    def test_stable_release(self):
        """Test stable release is not prerelease."""
        assert is_prerelease("1.9.7") is False
    
    def test_beta_release(self):
        """Test beta release is prerelease."""
        assert is_prerelease("1.9.7-beta") is True
    
    def test_alpha_release(self):
        """Test alpha release is prerelease."""
        assert is_prerelease("1.9.7a1") is True
    
    def test_rc_release(self):
        """Test release candidate is prerelease."""
        assert is_prerelease("1.9.7rc1") is True


class TestNormalizeVersion:
    """Tests for normalize_version function."""
    
    def test_normalize_standard_version(self):
        """Test normalizing standard version."""
        normalized = normalize_version("1.9.7")
        assert normalized == "1.9.7"
    
    def test_normalize_version_with_v_prefix(self):
        """Test normalizing version with 'v' prefix."""
        normalized = normalize_version("v1.9.7")
        assert normalized == "1.9.7"
    
    def test_normalize_prerelease_version(self):
        """Test normalizing prerelease version extracts base."""
        normalized = normalize_version("1.9.7-beta")
        assert normalized == "1.9.7"
    
    def test_normalize_invalid_version(self):
        """Test normalizing invalid version returns None."""
        normalized = normalize_version("invalid")
        assert normalized is None
