"""Unit tests for lib.auth module."""

import json
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scripts.lib.auth import authenticate_to_org, get_org_info


class TestAuthenticateToOrg:
    """Test authenticate_to_org function."""
    
    @patch("scripts.lib.auth.subprocess.run")
    def test_success(self, mock_run):
        """Test successful authentication."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": {
                "accessToken": "test_token_123",
                "instanceUrl": "https://test.salesforce.com"
            }
        })
        mock_run.return_value = mock_result
        
        with patch.dict(os.environ, {}, clear=True):
            result = authenticate_to_org("test_org")
            
            assert result is True
            assert os.environ["SF_ORG"] == "test_org"
            assert os.environ["SF_TOKEN"] == "test_token_123"
            assert os.environ["SF_INSTANCE"] == "https://test.salesforce.com"
    
    @patch("scripts.lib.auth.subprocess.run")
    def test_failure_nonzero_exit(self, mock_run):
        """Test authentication failure with nonzero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Org not found"
        mock_run.return_value = mock_result
        
        with patch.dict(os.environ, {}, clear=True):
            result = authenticate_to_org("test_org")
            
            assert result is False
            assert "SF_TOKEN" not in os.environ
    
    @patch("scripts.lib.auth.subprocess.run")
    def test_failure_invalid_json(self, mock_run):
        """Test authentication failure with invalid JSON."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid json"
        mock_run.return_value = mock_result
        
        with patch.dict(os.environ, {}, clear=True):
            result = authenticate_to_org("test_org")
            
            assert result is False


class TestGetOrgInfo:
    """Test get_org_info function."""
    
    @patch("scripts.lib.auth.subprocess.run")
    def test_success(self, mock_run):
        """Test successful org info retrieval."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "result": {
                "accessToken": "test_token_123",
                "instanceUrl": "https://test.salesforce.com"
            }
        })
        mock_run.return_value = mock_result
        
        token, instance = get_org_info("test_org")
        
        assert token == "test_token_123"
        assert instance == "https://test.salesforce.com"
    
    @patch("scripts.lib.auth.subprocess.run")
    def test_failure_nonzero_exit(self, mock_run):
        """Test failure with nonzero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Org not found"
        mock_run.return_value = mock_result
        
        with pytest.raises(ValueError, match="Failed to authenticate"):
            get_org_info("test_org")
    
    @patch("scripts.lib.auth.subprocess.run")
    def test_failure_invalid_json(self, mock_run):
        """Test failure with invalid JSON."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid json"
        mock_run.return_value = mock_result
        
        with pytest.raises(ValueError, match="Failed to parse"):
            get_org_info("test_org")
