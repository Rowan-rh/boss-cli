"""Unit tests for Boss CLI commands using Click's test runner and monkeypatch."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from boss_cli.cli import cli

runner = CliRunner()


# ── CLI Basics ──────────────────────────────────────────────────────


class TestCliBasic:
    """Test CLI basics without requiring cookies or network."""

    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0." in result.output

    def test_help(self):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "BOSS 直聘" in result.output

    def test_all_commands_registered(self):
        result = runner.invoke(cli, ["--help"])
        expected = [
            "login", "status", "logout", "me",
            "search", "recommend", "cities", "detail", "show", "export", "history",
            "applied", "interviews",
            "chat", "greet", "batch-greet", "fit",
        ]
        for cmd in expected:
            assert cmd in result.output, f"Command '{cmd}' not found in CLI help"


class TestCommandHelp:
    """Verify every command has --help without errors."""

    @pytest.mark.parametrize("cmd", [
        "login", "logout", "status", "me",
        "search", "recommend", "cities", "detail", "show", "export", "history",
        "applied", "interviews",
        "chat", "greet", "batch-greet", "fit",
    ])
    def test_help(self, cmd: str):
        result = runner.invoke(cli, [cmd, "--help"])
        assert result.exit_code == 0, f"{cmd} --help failed: {result.output}"

    def test_search_has_filter_options(self):
        result = runner.invoke(cli, ["search", "--help"])
        assert "--city" in result.output
        assert "--salary" in result.output
        assert "--exp" in result.output
        assert "--degree" in result.output

    def test_me_has_output_options(self):
        result = runner.invoke(cli, ["me", "--help"])
        assert "--json" in result.output
        assert "--yaml" in result.output

    def test_batch_greet_has_options(self):
        result = runner.invoke(cli, ["batch-greet", "--help"])
        assert "--dry-run" in result.output
        assert "--count" in result.output or "-n" in result.output
        assert "--yes" in result.output or "-y" in result.output

    def test_greet_has_output_options(self):
        result = runner.invoke(cli, ["greet", "--help"])
        assert "--json" in result.output
        assert "--yaml" in result.output

    def test_login_has_cookie_source(self):
        result = runner.invoke(cli, ["login", "--help"])
        assert "--cookie-source" in result.output
        assert "--qrcode" in result.output

    def test_history_has_options(self):
        result = runner.invoke(cli, ["history", "--help"])
        assert "--page" in result.output or "-p" in result.output
        assert "--json" in result.output


# ── Auth commands (mocked) ──────────────────────────────────────────


class TestAuthCommands:
    """Test auth commands with mocked credentials."""

    def test_status_without_auth(self):
        with patch("boss_cli.auth.get_credential", return_value=None):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "未登录" in result.output

    def test_status_yaml_without_auth(self):
        with patch("boss_cli.auth.get_credential", return_value=None):
            result = runner.invoke(cli, ["status", "--yaml"])
            assert result.exit_code == 0
            try:
                import yaml

                data = yaml.safe_load(result.output)
            except ImportError:
                data = json.loads(result.output)
            assert data["authenticated"] is False
            assert data["credential_present"] is False

    def test_status_with_auth(self):
        mock_cred = MagicMock()
        mock_cred.cookies = {"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"}
        with patch("boss_cli.auth.get_credential", return_value=mock_cred), \
             patch("boss_cli.auth.verify_credential_details", return_value={
                 "authenticated": True,
                 "search_authenticated": True,
                 "recommend_authenticated": True,
             }):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "已登录" in result.output

    def test_status_json(self):
        mock_cred = MagicMock()
        mock_cred.cookies = {"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"}
        with patch("boss_cli.auth.get_credential", return_value=mock_cred), \
             patch("boss_cli.auth.verify_credential_details", return_value={
                 "authenticated": True,
                 "search_authenticated": True,
                 "recommend_authenticated": True,
             }):
            result = runner.invoke(cli, ["status", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["authenticated"] is True
            assert data["credential_present"] is True
            assert data["search_authenticated"] is True
            assert data["recommend_authenticated"] is True

    def test_status_with_invalid_saved_auth(self):
        mock_cred = MagicMock()
        mock_cred.cookies = {"wt2": "1", "wbg": "2", "zp_at": "3"}
        with patch("boss_cli.auth.get_credential", return_value=mock_cred), \
             patch("boss_cli.auth.verify_credential_details", return_value={
                 "authenticated": False,
                 "search_authenticated": False,
                 "recommend_authenticated": False,
                 "reason": "缺少关键 Cookie: __zp_stoken__",
             }):
            result = runner.invoke(cli, ["status", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["authenticated"] is False
            assert data["credential_present"] is True
            assert "__zp_stoken__" in data["reason"]

    def test_status_with_partial_health(self):
        mock_cred = MagicMock()
        mock_cred.cookies = {"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"}
        with patch("boss_cli.auth.get_credential", return_value=mock_cred), \
             patch("boss_cli.auth.verify_credential_details", return_value={
                 "authenticated": True,
                 "search_authenticated": True,
                 "recommend_authenticated": False,
                 "reason": "recommend: 环境异常 (__zp_stoken__ 已过期)。请重新登录: boss logout && boss login",
             }):
            result = runner.invoke(cli, ["status", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["authenticated"] is True
            assert data["search_authenticated"] is True
            assert data["recommend_authenticated"] is False

    def test_me_without_auth(self):
        with patch("boss_cli.commands._common.get_credential", return_value=None):
            result = runner.invoke(cli, ["me"])
            assert result.exit_code == 1
            assert "未登录" in result.output

    def test_logout(self):
        with patch("boss_cli.auth.clear_credential"):
            result = runner.invoke(cli, ["logout"])
            assert result.exit_code == 0
            assert "已退出" in result.output


# ── Personal commands (mocked) ──────────────────────────────────────


class TestPersonalCommands:
    """Test personal center commands with mocked client."""

    def test_me_render(self):
        mock_cred = MagicMock()
        mock_cred.cookies = {"wt2": "x"}

        mock_data = {
            "name": "张三", "gender": 1, "age": "25岁",
            "degreeCategory": "本科", "account": "138****1234",
        }

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_resume_detail.return_value = {**_resume_detail(), "baseInfo": mock_data}
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_instance

            result = runner.invoke(cli, ["me"])
            assert result.exit_code == 0
            # CliRunner is non-TTY so auto-outputs JSON
            assert "张三" in result.output

    def test_me_json(self):
        mock_cred = MagicMock()
        mock_cred.cookies = {"wt2": "x"}

        mock_data = {"name": "张三", "gender": 1, "age": "25岁"}

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_resume_detail.return_value = {"baseInfo": mock_data}
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_instance

            result = runner.invoke(cli, ["me", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["name"] == "张三"

    def _me_client(self) -> MagicMock:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        client.get_resume_detail.return_value = _resume_detail()
        client.get_resume_baseinfo.return_value = {"name": "张三"}
        return client

    def test_me_json_includes_online_resume(self):
        client = self._me_client()
        with patch("boss_cli.commands._common.get_credential", return_value=MagicMock()), \
             patch("boss_cli.commands._common.BossClient", return_value=client):
            result = runner.invoke(cli, ["me", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)["data"]
        assert data["name"] == "张三"
        resume = data["resume"]
        assert resume["work_years"] == "6年经验"
        assert resume["work_experience"][0] == {
            "company": "示例科技", "position": "后端工程师", "period": "2022.09 - 至今",
            "content": "负责订单系统", "performance": "QPS 提升 3 倍",
        }
        assert resume["project_experience"][0]["name"] == "交易平台"
        assert resume["education"][0] == {"school": "某大学", "major": "计算机", "degree": "本科", "period": "2016 - 2020"}
        assert resume["expectations"] == [{"position": "Python", "city": "北京", "salary": "20-30K"}]
        client.get_resume_baseinfo.assert_not_called()

    def test_me_basic_skips_online_resume(self):
        client = self._me_client()
        with patch("boss_cli.commands._common.get_credential", return_value=MagicMock()), \
             patch("boss_cli.commands._common.BossClient", return_value=client):
            result = runner.invoke(cli, ["me", "--basic", "--json"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["data"] == {"name": "张三"}
        client.get_resume_detail.assert_not_called()

    def test_me_render_shows_resume_sections(self):
        from rich.console import Console

        from boss_cli.commands.auth import _render_resume
        from boss_cli.resume import normalize_resume

        recorder = Console(record=True, width=160, file=io.StringIO())
        with patch("boss_cli.commands.auth.console", recorder):
            _render_resume(normalize_resume(_resume_detail()))
        rendered = recorder.export_text()
        for text in ("个人优势", "示例科技", "交易平台", "某大学", "求职期望"):
            assert text in rendered

    def test_resume_text_excludes_identity(self):
        from boss_cli.resume import normalize_resume, resume_to_text

        text = resume_to_text(normalize_resume(_resume_detail()))
        for expected in ("## 工作经历", "示例科技 | 后端工程师 | 2022.09 - 至今", "工作业绩：QPS 提升 3 倍", "## 项目经历"):
            assert expected in text
        for private in ("张三", "138****1234", "1998", "wx***"):
            assert private not in text
        assert normalize_resume(None) == {}
        assert resume_to_text({}) == ""

    def test_applied_without_auth(self):
        with patch("boss_cli.commands._common.get_credential", return_value=None):
            result = runner.invoke(cli, ["applied"])
            assert result.exit_code == 1

    def test_interviews_without_auth(self):
        with patch("boss_cli.commands._common.get_credential", return_value=None):
            result = runner.invoke(cli, ["interviews"])
            assert result.exit_code == 1


# ── Cities ──────────────────────────────────────────────────────────


class TestCities:
    """Test cities command output."""

    def test_cities_output(self):
        result = runner.invoke(cli, ["cities"])
        assert result.exit_code == 0
        assert "北京" in result.output
        assert "上海" in result.output
        assert "杭州" in result.output
        assert "101010100" in result.output


# ── City resolution logic ───────────────────────────────────────────


class TestCityResolution:
    """Test city name to code resolution."""

    def test_resolve_known_city(self):
        from boss_cli.client import resolve_city
        assert resolve_city("北京") == "101010100"
        assert resolve_city("上海") == "101020100"
        assert resolve_city("杭州") == "101210100"

    def test_resolve_unknown_city_returns_nationwide(self):
        from boss_cli.client import resolve_city
        assert resolve_city("不存在的城市") == "100010000"

    def test_resolve_code_passthrough(self):
        from boss_cli.client import resolve_city
        assert resolve_city("101010100") == "101010100"

    def test_list_cities(self):
        from boss_cli.client import list_cities
        cities = list_cities()
        assert len(cities) > 30
        assert "北京" in cities
        assert "杭州" in cities


# ── Constants ───────────────────────────────────────────────────────


class TestConstants:
    """Test constants are properly defined."""

    def test_salary_codes(self):
        from boss_cli.constants import SALARY_CODES
        assert len(SALARY_CODES) >= 8
        assert "20-30K" in SALARY_CODES

    def test_exp_codes(self):
        from boss_cli.constants import EXP_CODES
        assert len(EXP_CODES) >= 7
        assert "3-5年" in EXP_CODES

    def test_degree_codes(self):
        from boss_cli.constants import DEGREE_CODES
        assert len(DEGREE_CODES) >= 5
        assert "本科" in DEGREE_CODES

    def test_api_urls_defined(self):
        from boss_cli import constants
        assert constants.JOB_SEARCH_URL
        assert constants.JOB_DETAIL_URL
        assert constants.DELIVER_LIST_URL
        assert constants.INTERVIEW_DATA_URL
        assert constants.FRIEND_LIST_URL
        assert constants.USER_INFO_URL
        assert constants.RESUME_BASEINFO_URL


# ── Credential ──────────────────────────────────────────────────────


class TestCredential:
    """Test credential management."""

    def test_credential_creation(self):
        from boss_cli.auth import Credential
        cred = Credential(cookies={"foo": "bar", "baz": "qux"})
        assert cred.is_valid
        assert cred.cookies == {"foo": "bar", "baz": "qux"}
        assert cred.has_required_cookies is False
        assert "__zp_stoken__" in cred.missing_required_cookies

    def test_credential_empty(self):
        from boss_cli.auth import Credential
        cred = Credential(cookies={})
        assert not cred.is_valid

    def test_credential_serialization(self):
        from boss_cli.auth import Credential
        cred = Credential(cookies={"a": "1"})
        data = cred.to_dict()
        assert "cookies" in data
        assert "saved_at" in data

        cred2 = Credential.from_dict(data)
        assert cred2.cookies == cred.cookies

    def test_cookie_header(self):
        from boss_cli.auth import Credential
        cred = Credential(cookies={"a": "1", "b": "2"})
        header = cred.as_cookie_header()
        assert "a=1" in header
        assert "b=2" in header


# ── Exceptions ──────────────────────────────────────────────────────


class TestExceptions:
    """Test custom exception hierarchy."""

    def test_boss_api_error(self):
        from boss_cli.exceptions import BossApiError
        err = BossApiError("test error", code=42, response={"a": 1})
        assert err.code == 42
        assert err.response == {"a": 1}
        assert "test error" in str(err)

    def test_session_expired_error(self):
        from boss_cli.exceptions import SessionExpiredError
        err = SessionExpiredError()
        assert err.code == 37
        assert "stoken" in str(err)

    def test_auth_required_error(self):
        from boss_cli.exceptions import AuthRequiredError
        err = AuthRequiredError()
        assert "登录" in str(err)

    def test_rate_limit_error(self):
        from boss_cli.exceptions import RateLimitError
        err = RateLimitError()
        assert "频繁" in str(err)

    def test_param_error(self):
        from boss_cli.exceptions import ParamError
        err = ParamError("missing field", code=17)
        assert err.code == 17

    def test_error_code_mapping(self):
        from boss_cli.exceptions import (
            AuthRequiredError,
            BossApiError,
            RateLimitError,
            SessionExpiredError,
            error_code_for_exception,
        )
        assert error_code_for_exception(SessionExpiredError()) == "not_authenticated"
        assert error_code_for_exception(AuthRequiredError()) == "not_authenticated"
        assert error_code_for_exception(RateLimitError()) == "rate_limited"
        assert error_code_for_exception(BossApiError("test")) == "api_error"
        assert error_code_for_exception(ValueError("test")) == "unknown_error"


# ── Client ──────────────────────────────────────────────────────────


class TestClient:
    """Test client initialization and helpers."""

    def test_client_context_manager(self):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient

        cred = Credential(cookies={"test": "value"})
        with BossClient(cred) as client:
            assert client.client is not None
            assert client._request_count == 0

    def test_client_not_initialized_error(self):
        from boss_cli.client import BossClient
        client = BossClient()
        with pytest.raises(RuntimeError, match="Client not initialized"):
            _ = client.client

    def test_handle_response_success(self):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient

        cred = Credential(cookies={})
        with BossClient(cred) as client:
            data = {"code": 0, "zpData": {"key": "value"}}
            result = client._handle_response(data, "test")
            assert result == {"key": "value"}

    def test_handle_response_session_expired(self):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient
        from boss_cli.exceptions import SessionExpiredError

        cred = Credential(cookies={})
        with BossClient(cred) as client:
            data = {"code": 37, "message": "env error"}
            with pytest.raises(SessionExpiredError):
                client._handle_response(data, "test")

    def test_handle_response_param_error(self):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient
        from boss_cli.exceptions import ParamError

        cred = Credential(cookies={})
        with BossClient(cred) as client:
            data = {"code": 17, "message": "missing param"}
            with pytest.raises(ParamError):
                client._handle_response(data, "test")

    def test_handle_response_generic_error(self):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient
        from boss_cli.exceptions import BossApiError

        cred = Credential(cookies={})
        with BossClient(cred) as client:
            data = {"code": 999, "message": "unknown"}
            with pytest.raises(BossApiError):
                client._handle_response(data, "test")

    def test_search_request_uses_search_referer(self):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient

        cred = Credential(cookies={"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"})
        with BossClient(cred) as client:
            headers = client._headers_for_request("/wapi/zpgeek/search/joblist.json", params={"query": "Python"})
            assert headers["Referer"].endswith("/web/geek/job?query=Python")

    def test_search_chinese_keyword_encoded_in_referer(self):
        """Verify Chinese keywords are percent-encoded in Referer to avoid ASCII errors."""
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient

        cred = Credential(cookies={"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"})
        with BossClient(cred) as client:
            headers = client._headers_for_request("/wapi/zpgeek/search/joblist.json", params={"query": "前端开发"})
            referer = headers["Referer"]
            # Must not contain raw Chinese characters
            assert "前端开发" not in referer
            # Must contain percent-encoded form
            assert "query=%E5%89%8D%E7%AB%AF%E5%BC%80%E5%8F%91" in referer

    def test_recommend_request_uses_recommend_referer(self):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient

        cred = Credential(cookies={"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"})
        with BossClient(cred) as client:
            headers = client._headers_for_request("/wapi/zprelation/interaction/geekGetJob", params={"tag": 5})
            assert headers["Referer"].endswith("/web/geek/recommend")

    def test_burst_penalty_kicks_in_after_multiple_requests(self, monkeypatch):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient

        cred = Credential(cookies={"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"})
        with BossClient(cred) as client:
            now = 1000.0
            client._recent_request_times.extend([now - 12, now - 8, now - 3])
            monkeypatch.setattr("boss_cli.client.time.time", lambda: now)
            delay = client._burst_penalty_delay()
            assert delay >= 1.2

    def test_get_recommend_jobs_normalizes_card_list(self, monkeypatch):
        from boss_cli.auth import Credential
        from boss_cli.client import BossClient

        cred = Credential(cookies={"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"})
        with BossClient(cred) as client:
            monkeypatch.setattr(
                client,
                "_get",
                lambda url, params=None, action="": {
                    "cardList": [{"jobName": "Java", "securityId": "abc"}],
                    "hasMore": True,
                    "totalCount": 1,
                    "page": 1,
                    "startIndex": 0,
                },
            )
            data = client.get_recommend_jobs(page=1)
            assert data["jobList"][0]["jobName"] == "Java"
            assert data["hasMore"] is True


class TestAuthHealthVerification:
    """Test auth health caching and refresh behavior."""

    def test_verify_credential_details_uses_ttl_cache(self, monkeypatch):
        from boss_cli.auth import Credential, _AUTH_HEALTH_CACHE, verify_credential_details

        calls = {"count": 0}

        class FakeClient:
            def __init__(self, credential, request_delay=0.2):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def search_jobs(self, **kwargs):
                calls["count"] += 1
                return {"jobList": []}

            def get_recommend_jobs(self, page=1):
                calls["count"] += 1
                return {"jobList": []}

        _AUTH_HEALTH_CACHE.clear()
        monkeypatch.setattr("boss_cli.client.BossClient", FakeClient)

        cred = Credential(cookies={"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"})
        first = verify_credential_details(cred)
        second = verify_credential_details(cred)

        assert first["authenticated"] is True
        assert second["recommend_authenticated"] is True
        assert calls["count"] == 2
        assert len(_AUTH_HEALTH_CACHE) == 1

    def test_verify_credential_force_refresh_bypasses_cache(self, monkeypatch):
        from boss_cli.auth import Credential, _AUTH_HEALTH_CACHE, verify_credential_details

        calls = {"count": 0}

        class FakeClient:
            def __init__(self, credential, request_delay=0.2):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def search_jobs(self, **kwargs):
                calls["count"] += 1
                return {"jobList": []}

            def get_recommend_jobs(self, page=1):
                calls["count"] += 1
                return {"jobList": []}

        _AUTH_HEALTH_CACHE.clear()
        monkeypatch.setattr("boss_cli.client.BossClient", FakeClient)

        cred = Credential(cookies={"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"})
        verify_credential_details(cred)
        verify_credential_details(cred, force_refresh=True)

        assert calls["count"] == 4


# ── Index Cache ─────────────────────────────────────────────────────


class TestIndexCache:
    """Test short-index cache system."""

    def test_save_and_get(self, tmp_path, monkeypatch):
        from boss_cli import index_cache
        monkeypatch.setattr(index_cache, "INDEX_CACHE_FILE", tmp_path / "index_cache.json")
        monkeypatch.setattr(index_cache, "CONFIG_DIR", tmp_path)

        jobs = [
            {"securityId": "abc123", "jobName": "Go Dev", "brandName": "Company A"},
            {"securityId": "def456", "jobName": "Python Dev", "brandName": "Company B"},
        ]
        index_cache.save_index(jobs, source="test")

        result = index_cache.get_job_by_index(1)
        assert result is not None
        assert result["securityId"] == "abc123"
        assert result["jobName"] == "Go Dev"

        result2 = index_cache.get_job_by_index(2)
        assert result2 is not None
        assert result2["securityId"] == "def456"

    def test_get_out_of_range(self, tmp_path, monkeypatch):
        from boss_cli import index_cache
        monkeypatch.setattr(index_cache, "INDEX_CACHE_FILE", tmp_path / "index_cache.json")
        monkeypatch.setattr(index_cache, "CONFIG_DIR", tmp_path)

        jobs = [{"securityId": "abc", "jobName": "Test"}]
        index_cache.save_index(jobs, source="test")
        assert index_cache.get_job_by_index(99) is None

    def test_get_no_cache(self, tmp_path, monkeypatch):
        from boss_cli import index_cache
        monkeypatch.setattr(index_cache, "INDEX_CACHE_FILE", tmp_path / "nonexistent.json")
        assert index_cache.get_job_by_index(1) is None

    def test_get_index_info(self, tmp_path, monkeypatch):
        from boss_cli import index_cache
        monkeypatch.setattr(index_cache, "INDEX_CACHE_FILE", tmp_path / "index_cache.json")
        monkeypatch.setattr(index_cache, "CONFIG_DIR", tmp_path)

        info = index_cache.get_index_info()
        assert not info["exists"]

        jobs = [{"securityId": "x", "jobName": "T"}]
        index_cache.save_index(jobs)
        info = index_cache.get_index_info()
        assert info["exists"]
        assert info["count"] == 1

    def test_zero_and_negative_index(self, tmp_path, monkeypatch):
        from boss_cli import index_cache
        monkeypatch.setattr(index_cache, "INDEX_CACHE_FILE", tmp_path / "index_cache.json")
        assert index_cache.get_job_by_index(0) is None
        assert index_cache.get_job_by_index(-1) is None


# ── Show command ────────────────────────────────────────────────────


class TestShowCommand:
    """Test show command behavior without network."""

    def test_show_no_cache(self, tmp_path, monkeypatch):
        from boss_cli import index_cache
        monkeypatch.setattr(index_cache, "INDEX_CACHE_FILE", tmp_path / "nonexistent.json")
        result = runner.invoke(cli, ["show", "1"])
        assert result.exit_code == 0
        assert "暂无缓存" in result.output

    def test_show_out_of_range(self, tmp_path, monkeypatch):
        from boss_cli import index_cache
        monkeypatch.setattr(index_cache, "INDEX_CACHE_FILE", tmp_path / "index_cache.json")
        monkeypatch.setattr(index_cache, "CONFIG_DIR", tmp_path)
        index_cache.save_index([{"securityId": "x", "jobName": "T"}])
        result = runner.invoke(cli, ["show", "99"])
        assert result.exit_code == 0
        assert "超出范围" in result.output


# ── Detail / Export help ────────────────────────────────────────────


class TestNewCommandHelp:
    """Test help output for new commands."""

    def test_detail_help(self):
        result = runner.invoke(cli, ["detail", "--help"])
        assert result.exit_code == 0
        assert "securityId" in result.output
        assert "--json" in result.output

    def test_show_help(self):
        result = runner.invoke(cli, ["show", "--help"])
        assert result.exit_code == 0
        assert "编号" in result.output

    def test_export_help(self):
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output
        assert "csv" in result.output
        assert "--output" in result.output

    def test_history_help(self):
        result = runner.invoke(cli, ["history", "--help"])
        assert result.exit_code == 0
        assert "浏览历史" in result.output


# ── Search mock test ────────────────────────────────────────────────


class TestSearchMock:
    """Test search command with mocked client."""

    def test_search_json(self):
        mock_cred = MagicMock()
        mock_cred.cookies = {"wt2": "x"}

        mock_data = {"jobList": [{"jobName": "Go Dev", "securityId": "abc"}], "hasMore": False}

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.search_jobs.return_value = mock_data
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_instance

            result = runner.invoke(cli, ["search", "golang", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["ok"] is True
            assert "data" in data

    def test_search_new_filter_help(self):
        """Verify new filter options appear in search --help."""
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        for opt in ("--industry", "--scale", "--stage", "--job-type"):
            assert opt in result.output, f"{opt} missing from search --help"

    def test_search_mock_with_filters(self):
        """Verify new filter params are forwarded to client.search_jobs()."""
        mock_cred = MagicMock()
        mock_cred.cookies = {"wt2": "x"}

        mock_data = {"jobList": [{"jobName": "Eng", "securityId": "x"}], "hasMore": False}

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.search_jobs.return_value = mock_data
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_instance

            result = runner.invoke(cli, [
                "search", "Python", "--json",
                "--industry", "互联网",
                "--scale", "1000-9999人",
                "--stage", "已上市",
                "--job-type", "全职",
            ])
            assert result.exit_code == 0
            # Verify the call was made with the new params
            call_kwargs = mock_instance.search_jobs.call_args
            assert call_kwargs.kwargs.get("industry") == "100020"
            assert call_kwargs.kwargs.get("scale") == "305"
            assert call_kwargs.kwargs.get("stage") == "807"
            assert call_kwargs.kwargs.get("job_type") == "1901"

    def test_export_new_filter_help(self):
        """Verify new filter options appear in export --help."""
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0
        for opt in ("--industry", "--scale", "--stage", "--job-type"):
            assert opt in result.output, f"{opt} missing from export --help"


# ── Constants test ──────────────────────────────────────────────────


class TestNewConstants:
    """Test that new filter code mappings are correct."""

    def test_industry_codes_present(self):
        from boss_cli.constants import INDUSTRY_CODES
        assert len(INDUSTRY_CODES) >= 10
        assert "互联网" in INDUSTRY_CODES
        assert "人工智能" in INDUSTRY_CODES

    def test_scale_codes_present(self):
        from boss_cli.constants import SCALE_CODES
        assert len(SCALE_CODES) >= 6
        assert "1000-9999人" in SCALE_CODES

    def test_stage_codes_present(self):
        from boss_cli.constants import STAGE_CODES
        assert len(STAGE_CODES) >= 8
        assert "已上市" in STAGE_CODES
        assert "A轮" in STAGE_CODES

    def test_job_type_codes_present(self):
        from boss_cli.constants import JOB_TYPE_CODES
        assert len(JOB_TYPE_CODES) >= 3
        assert "全职" in JOB_TYPE_CODES


class TestSchemaEnvelope:
    """Test that structured output uses the schema envelope."""

    def test_status_json_has_no_envelope(self):
        """status uses direct output, not envelope (for backward compat)."""
        mock_cred = MagicMock()
        mock_cred.cookies = {"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"}
        with patch("boss_cli.auth.get_credential", return_value=mock_cred), \
             patch("boss_cli.auth.verify_credential_details", return_value={
                 "authenticated": True,
                 "search_authenticated": True,
                 "recommend_authenticated": True,
             }):
            result = runner.invoke(cli, ["status", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["authenticated"] is True

    def test_me_json_has_envelope(self):
        """me command uses handle_command, should have envelope."""
        mock_cred = MagicMock()
        mock_cred.cookies = {"wt2": "x"}

        mock_data = {"name": "张三", "gender": 1}

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_resume_detail.return_value = {"baseInfo": mock_data}
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_instance

            result = runner.invoke(cli, ["me", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["schema_version"] == "1"
            assert data["data"]["name"] == "张三"


class TestCommandFailures:
    """API failures should return non-zero exit codes."""

    def test_search_session_expired_exits_nonzero(self):
        from boss_cli.exceptions import SessionExpiredError

        mock_cred = MagicMock()
        mock_cred.cookies = {"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"}

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient") as MockClient, \
             patch("boss_cli.auth.extract_browser_credential", return_value=(None, [])), \
             patch("boss_cli.auth.clear_credential") as clear_credential:
            mock_instance = MagicMock()
            mock_instance.search_jobs.side_effect = SessionExpiredError()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_instance

            result = runner.invoke(cli, ["search", "golang", "--json"])
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "not_authenticated"
            clear_credential.assert_called_once()

    def test_export_failure_exits_nonzero(self):
        from boss_cli.exceptions import BossApiError

        mock_cred = MagicMock()
        mock_cred.cookies = {"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"}

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands.search.run_client_action", side_effect=BossApiError("boom")):
            result = runner.invoke(cli, ["export", "Python"])
            assert result.exit_code == 1
            assert "导出失败" in result.output

    def test_batch_greet_search_failure_exits_nonzero(self):
        from boss_cli.exceptions import BossApiError

        mock_cred = MagicMock()
        mock_cred.cookies = {"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"}

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.search_jobs.side_effect = BossApiError("boom")
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_instance

            result = runner.invoke(cli, ["batch-greet", "Python", "--dry-run"])
            assert result.exit_code == 1
            assert "搜索失败" in result.output

    def test_batch_greet_refreshes_after_session_expiry(self):
        from boss_cli.exceptions import SessionExpiredError

        mock_cred = MagicMock()
        mock_cred.cookies = {"__zp_stoken__": "s", "wt2": "1", "wbg": "2", "zp_at": "3"}
        fresh_cred = MagicMock()
        fresh_cred.cookies = {"__zp_stoken__": "fresh", "wt2": "1", "wbg": "2", "zp_at": "3"}

        initial_client = MagicMock()
        initial_client.__enter__ = MagicMock(return_value=initial_client)
        initial_client.__exit__ = MagicMock(return_value=False)
        initial_client.search_jobs.return_value = {
            "jobList": [{"jobName": "Python", "brandName": "Acme", "securityId": "sec-1", "lid": "lid-1"}]
        }
        initial_client.add_friend.side_effect = SessionExpiredError()

        refreshed_client = MagicMock()
        refreshed_client.__enter__ = MagicMock(return_value=refreshed_client)
        refreshed_client.__exit__ = MagicMock(return_value=False)
        refreshed_client.add_friend.return_value = {"success": True}

        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient", side_effect=[initial_client, initial_client, refreshed_client]), \
             patch("boss_cli.auth.extract_browser_credential", return_value=(fresh_cred, [])), \
             patch("boss_cli.auth.clear_credential") as clear_credential:
            result = runner.invoke(cli, ["batch-greet", "Python", "-n", "1", "-y"])
            assert result.exit_code == 0
            assert "1/1" in result.output
            clear_credential.assert_not_called()


# ── Job fit (TypeSafe Jev, mocked HTTP) ─────────────────────────────


def _resume_detail() -> dict:
    """Shape of /wapi/zpgeek/resume/geek/preview/data.json zpData (trimmed)."""
    return {
        "baseInfo": {"name": "张三", "age": "27岁", "gender": 1, "account": "138****1234", "birthday": "1998.01",
                     "weixinBlur": "wx***", "degreeCategory": "本科", "workYearDesc": "6年经验"},
        "userDesc": "熟悉高并发后端",
        "professionalSkill": "Python, Go",
        "lastUpdateTime": "2026.09.23 22:16",
        "expectList": [{"id": 1, "positionName": "Python", "locationName": "北京", "salaryDesc": "20-30K", "location": 101010100}],
        "workExpList": [{"id": 2, "companyName": "示例科技", "positionName": "后端工程师", "startDateStr": "2022.09",
                         "endDate": "", "endDateStr": "至今", "workContent": "负责订单系统", "workPerformance": "QPS 提升 3 倍"}],
        "projectExpList": [{"name": "交易平台", "roleName": "负责人", "startDateStr": "2023.01", "endDateStr": "2025.01",
                            "projectDesc": "撮合引擎重构"}],
        "educationExpList": [{"school": "某大学", "major": "计算机", "degreeName": "本科", "startYearStr": "2016", "endYearStr": "2020"}],
        "certificationList": None,
    }


def _jev_answers() -> dict:
    choice = {"type": "choice", "choice": "partial_match", "confidence": 0.7,
              "probabilities": {"strong_match": 0.2, "partial_match": 0.7, "clear_gap": 0.05, "insufficient_evidence": 0.05}}
    score = {"type": "score", "score": 2.6, "confidence": 0.5, "probabilities": {"0": 0.1, "1": 0.1, "2": 0.1, "3": 0.5, "4": 0.2}}
    return {
        "model": "jev-test",
        "answers": {
            "skills": choice, "responsibilities": choice, "experience": choice,
            "company_business": score, "preference_alignment": score, "overall": score,
            "screening_probability": {"type": "noul", "noul": 0.42},
        },
    }


def _fit_client() -> MagicMock:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get_job_detail.return_value = {
        "jobInfo": {"jobName": "Python 工程师", "postDescription": "负责后端服务开发", "skills": ["Python"],
                    "salaryDesc": "20-30K", "locationName": "北京"},
        "brandComInfo": {"brandName": "示例科技", "industryName": "互联网"},
    }
    client.get_resume_baseinfo.return_value = {"name": "张三", "age": "25岁", "degreeCategory": "本科"}
    client.get_resume_expect.return_value = {"expectList": [{"positionName": "Python", "expectCity": 101010100}]}
    return client


class TestJevModule:
    """Unit tests for boss_cli.jev without network access."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
        monkeypatch.delenv("TYPESAFE_BASE_URL", raising=False)
        monkeypatch.delenv("TYPESAFE_MODEL", raising=False)
        monkeypatch.setattr("boss_cli.jev.time.sleep", lambda _s: None)

    def _mock_http(self, monkeypatch, handler):
        import httpx

        real_client = httpx.Client
        calls: list = []

        def recording(request):
            calls.append(request)
            return handler(request)

        monkeypatch.setattr("boss_cli.jev.httpx.Client", lambda **kw: real_client(transport=httpx.MockTransport(recording), **kw))
        return calls

    def test_success_parses_all_dimensions(self, monkeypatch):
        import httpx

        from boss_cli.jev import assess_job_fit

        calls = self._mock_http(monkeypatch, lambda req: httpx.Response(200, json=_jev_answers()))
        result = assess_job_fit({"candidate_resume": "x"})
        assert str(calls[0].url) == "https://api.typesafe.ai/v1/systemone"
        assert calls[0].headers["Authorization"] == "Bearer test-key"
        body = json.loads(calls[0].content)
        assert body["model"] == "jev-latest" and set(body["questions"]) == set(result["assessment"])
        assert result["model"] == "jev-test"
        assert result["assessment"]["overall"]["score"] == 2.6
        assert result["assessment"]["screening_probability"]["probability"] == 0.42

    @pytest.mark.parametrize("mutate", [
        lambda a: a["answers"].pop("overall"),
        lambda a: a["answers"]["overall"].update(score=4.5),
        lambda a: a["answers"]["overall"].update(score=True),
        lambda a: a["answers"]["skills"].update(choice="maybe"),
        lambda a: a["answers"]["skills"].update(type="score"),
        lambda a: a["answers"]["screening_probability"].update(noul=None),
        lambda a: a["answers"]["screening_probability"].update(noul=1.5),
        lambda a: a.update(answers=[]),
    ])
    def test_invalid_response_raises(self, monkeypatch, mutate):
        import httpx

        from boss_cli.jev import JevServiceError, assess_job_fit

        payload = _jev_answers()
        mutate(payload)
        self._mock_http(monkeypatch, lambda req: httpx.Response(200, json=payload))
        with pytest.raises(JevServiceError):
            assess_job_fit({"candidate_resume": "x"})

    def test_retries_529_once_then_succeeds(self, monkeypatch):
        import httpx

        from boss_cli.jev import assess_job_fit

        responses = [httpx.Response(529), httpx.Response(200, json=_jev_answers())]
        calls = self._mock_http(monkeypatch, lambda req: responses[len(calls) - 1])
        assert assess_job_fit({"candidate_resume": "x"})["model"] == "jev-test"
        assert len(calls) == 2

    def test_429_gives_up_after_retry(self, monkeypatch):
        import httpx

        from boss_cli.jev import JevServiceError, assess_job_fit

        calls = self._mock_http(monkeypatch, lambda req: httpx.Response(429))
        with pytest.raises(JevServiceError, match="频率受限"):
            assess_job_fit({"candidate_resume": "x"})
        assert len(calls) == 2

    def test_422_reports_field_path_but_not_values(self, monkeypatch):
        import httpx

        from boss_cli.jev import JevServiceError, assess_job_fit

        body = {"detail": [{"loc": ["body", "questions", "overall", "criteria"], "input": "候选人简历原文 13812345678"}]}
        self._mock_http(monkeypatch, lambda req: httpx.Response(422, json=body))
        with pytest.raises(JevServiceError) as exc_info:
            assess_job_fit({"candidate_resume": "x"})
        message = str(exc_info.value)
        assert "body.questions.overall.criteria" in message
        assert "13812345678" not in message and "简历原文" not in message

    def test_401_does_not_echo_key(self, monkeypatch):
        import httpx

        from boss_cli.jev import JevServiceError, assess_job_fit

        self._mock_http(monkeypatch, lambda req: httpx.Response(401))
        with pytest.raises(JevServiceError) as exc_info:
            assess_job_fit({"candidate_resume": "x"})
        assert "test-key" not in str(exc_info.value)

    def test_timeout(self, monkeypatch):
        import httpx

        from boss_cli.jev import JevServiceError, assess_job_fit

        def handler(req):
            raise httpx.ReadTimeout("timeout", request=req)

        self._mock_http(monkeypatch, handler)
        with pytest.raises(JevServiceError, match="超时"):
            assess_job_fit({"candidate_resume": "x"})

    @pytest.mark.parametrize("base_url", [
        "http://api.typesafe.ai", "https://user:pw@api.typesafe.ai", "https://api.typesafe.ai/v1", "https://api.typesafe.ai?x=1",
    ])
    def test_rejects_unsafe_base_url(self, monkeypatch, base_url):
        from boss_cli.jev import JevServiceError, assess_job_fit

        monkeypatch.setenv("TYPESAFE_BASE_URL", base_url)
        with pytest.raises(JevServiceError, match="TYPESAFE_BASE_URL"):
            assess_job_fit({"candidate_resume": "x"})

    def test_state_size_limit(self, monkeypatch):
        from boss_cli.jev import JevServiceError, assess_job_fit

        with pytest.raises(JevServiceError, match="40 KB"):
            assess_job_fit({"candidate_resume": "字" * 20_000})

    def test_redact_contact_info(self):
        from boss_cli.jev import redact_contact_info

        text = (
            "张三 电话 138-1234-5678 / +86 13912345678 邮箱 zs@example.com "
            "身份证 11010519491231002X 微信：zhang_san88 QQ: 12345678 2019-2023 年负责 Python 服务，QPS 20000"
        )
        redacted, counts = redact_contact_info(text)
        for secret in ("138-1234-5678", "13912345678", "zs@example.com", "11010519491231002X", "zhang_san88", "12345678 "):
            assert secret not in redacted
        assert counts == {"email": 1, "id_number": 1, "phone": 2, "messenger_id": 2}
        assert "2019-2023" in redacted and "QPS 20000" in redacted


class TestFitCommand:
    """CLI tests for `boss fit` with mocked BOSS client and Jev call."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    def _invoke(self, args, *, client=None, assess=None):
        mock_cred = MagicMock()
        mock_cred.cookies = {"wt2": "x"}
        client = client or _fit_client()
        assess = assess or MagicMock(return_value={"model": "jev-test", "assessment": {}})
        with patch("boss_cli.commands._common.get_credential", return_value=mock_cred), \
             patch("boss_cli.commands._common.BossClient", return_value=client), \
             patch("boss_cli.commands.fit.assess_job_fit", assess):
            return runner.invoke(cli, ["fit", *args]), client, assess

    def test_requires_confirm_send(self, tmp_path):
        resume = tmp_path / "resume.txt"
        resume.write_text("Python 开发 5 年", encoding="utf-8")
        result, client, assess = self._invoke(["abc", "--resume-file", str(resume)])
        assert result.exit_code == 2
        assert "--confirm-send" in result.output
        client.get_job_detail.assert_not_called()
        assess.assert_not_called()

    def test_requires_api_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TYPESAFE_API_KEY")
        resume = tmp_path / "resume.txt"
        resume.write_text("Python", encoding="utf-8")
        result, _, assess = self._invoke(["abc", "--resume-file", str(resume), "--confirm-send"])
        assert result.exit_code == 1
        assert "TYPESAFE_API_KEY" in result.output
        assess.assert_not_called()

    @pytest.mark.parametrize("content", [b"", b"\xff\xfe\x00bad", "字".encode() * 14_000])
    def test_rejects_bad_resume_file(self, tmp_path, content):
        resume = tmp_path / "resume.txt"
        resume.write_bytes(content)
        result, client, assess = self._invoke(["abc", "--resume-file", str(resume), "--confirm-send"])
        assert result.exit_code == 1
        client.get_job_detail.assert_not_called()
        assess.assert_not_called()

    def test_combined_size_checked_before_boss_requests(self, tmp_path):
        resume = tmp_path / "resume.txt"
        company = tmp_path / "company.txt"
        resume.write_text("字" * 8_000, encoding="utf-8")
        company.write_text("业" * 8_000, encoding="utf-8")
        result, client, _ = self._invoke(
            ["abc", "--resume-file", str(resume), "--company-context-file", str(company), "--confirm-send"]
        )
        assert result.exit_code == 1
        assert "40 KB" in result.output
        client.get_job_detail.assert_not_called()

    def test_sends_minimized_state_and_json_omits_resume(self, tmp_path):
        resume = tmp_path / "resume.txt"
        resume.write_text("Python 开发 5 年，电话 13812345678，邮箱 me@example.com", encoding="utf-8")
        result, _, assess = self._invoke(["abc", "--resume-file", str(resume), "--confirm-send", "--json"])
        assert result.exit_code == 0, result.output

        state = assess.call_args.args[0]
        assert "13812345678" not in state["candidate_resume"]
        assert "me@example.com" not in state["candidate_resume"]
        profile = state["candidate_profile_and_preferences"]
        assert profile == {"education": "本科", "desired_positions": "Python"}
        assert "张三" not in json.dumps(state, ensure_ascii=False)
        assert state["job_requirements"]["description"] == "负责后端服务开发"

        data = json.loads(result.output)
        assert data["ok"] is True
        assert "Python 开发 5 年" not in result.output
        summary = data["data"]["input_summary"]
        assert summary["resume_redactions"] == {"email": 1, "phone": 1}
        assert set(summary["profile_fields_missing"]) == {"work_experience", "desired_cities", "desired_salary"}

    def test_uses_online_resume_without_resume_file(self):
        client = _fit_client()
        detail = _resume_detail()
        detail["userDesc"] = "熟悉高并发后端，联系 me@example.com"
        client.get_resume_detail.return_value = detail
        result, _, assess = self._invoke(["abc", "--confirm-send", "--json"], client=client)
        assert result.exit_code == 0, result.output

        state = assess.call_args.args[0]
        assert "撮合引擎重构" in state["candidate_resume"]
        assert "me@example.com" not in state["candidate_resume"]
        assert "张三" not in json.dumps(state, ensure_ascii=False)
        assert state["candidate_profile_and_preferences"] == {
            "education": "本科", "work_experience": "6年经验", "desired_positions": "Python",
            "desired_cities": "北京", "desired_salary": "20-30K",
        }
        client.get_resume_baseinfo.assert_not_called()
        summary = json.loads(result.output)["data"]["input_summary"]
        assert summary["resume_source"] == "boss_online_resume"
        assert summary["resume_redactions"] == {"email": 1}

    def test_empty_online_resume_skips_jev(self):
        client = _fit_client()
        client.get_resume_detail.return_value = {"baseInfo": {"name": "张三"}}
        result, _, assess = self._invoke(["abc", "--confirm-send", "--json"], client=client)
        assert result.exit_code == 1
        assert "在线简历为空" in result.output
        assess.assert_not_called()

    def test_missing_job_description_skips_jev(self, tmp_path):
        resume = tmp_path / "resume.txt"
        resume.write_text("Python", encoding="utf-8")
        client = _fit_client()
        client.get_job_detail.return_value = {"jobInfo": {"jobName": "x"}, "brandComInfo": None}
        result, _, assess = self._invoke(["abc", "--resume-file", str(resume), "--confirm-send", "--json"], client=client)
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "api_error"
        assess.assert_not_called()

    def test_render_escapes_model_markup(self):
        from boss_cli.commands.fit import _render_fit

        choice = {"label": "部分匹配", "confidence": None}
        score = {"score": 2.0, "confidence": 0.5}
        data = {
            "job": {"title": "[bold]x", "company": "c", "salary": "s", "location": "l", "business_context_source": "src"},
            "model": "jev[/dim]evil",
            "assessment": {
                "skills": choice, "responsibilities": choice, "experience": choice,
                "company_business": score, "preference_alignment": score, "overall": score,
                "screening_probability": {"probability": 0.4},
            },
            "input_summary": {"profile_fields_missing": ["desired_cities"], "resume_redactions": {"phone": 1}},
            "notice": "n",
        }
        _render_fit(data)  # must not raise rich.errors.MarkupError
