"""Unit tests for treemux.port."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from treemux.models import InstanceInfo, ServiceConfig, TreemuxConfig, TreemuxState
from treemux.port import (
    allocate_ports,
    calculate_port,
    check_ports_availability,
    find_available_index,
    is_port_available,
)


class TestCalculatePort:
    """Tests for calculate_port function."""

    def test_index_zero(self):
        """index=0はbase_portをそのまま返す"""
        assert calculate_port(8000, 0) == 8000

    def test_index_five(self):
        """index=5はbase_port + 5を返す"""
        assert calculate_port(8000, 5) == 8005

    def test_index_nine(self):
        """index=9はbase_port + 9を返す"""
        assert calculate_port(8100, 9) == 8109

    @pytest.mark.parametrize(
        "base_port,index,expected",
        [
            (8000, 0, 8000),
            (8000, 1, 8001),
            (8100, 5, 8105),
            (1024, 9, 1033),
            (65526, 9, 65535),
        ],
    )
    def test_various_combinations(self, base_port, index, expected):
        """様々なbase_portとindexの組み合わせをテスト"""
        assert calculate_port(base_port, index) == expected


class TestAllocatePorts:
    """Tests for allocate_ports function."""

    def test_single_service(self):
        """単一サービスのポート割り当て"""
        config = TreemuxConfig(
            project_name="test",
            services={
                "web": ServiceConfig(container_port=3000, base_host_port=8000),
            },
        )
        ports = allocate_ports(config, index=3)
        assert ports == {"web": 8003}

    def test_multiple_services(self, sample_treemux_config: TreemuxConfig):
        """複数サービスのポート割り当て"""
        ports = allocate_ports(sample_treemux_config, index=2)
        assert ports == {"web": 8002, "api": 8102}

    def test_empty_services(self):
        """空のservicesは空のdictを返す"""
        config = TreemuxConfig(project_name="test", services={})
        ports = allocate_ports(config, index=5)
        assert ports == {}

    def test_index_zero(self, sample_treemux_config: TreemuxConfig):
        """index=0はベースポートを返す"""
        ports = allocate_ports(sample_treemux_config, index=0)
        assert ports == {"web": 8000, "api": 8100}


class TestIsPortAvailable:
    """Tests for is_port_available function."""

    def test_free_port_with_mock(self):
        """モックを使用して空きポートをシミュレート"""
        with patch("treemux.port.socket.socket") as mock_socket:
            mock_instance = mock_socket.return_value.__enter__.return_value
            mock_instance.bind.return_value = None

            assert is_port_available(8999) is True

    def test_used_port_with_mock(self):
        """モックを使用して使用中ポートをシミュレート"""
        with patch("treemux.port.socket.socket") as mock_socket:
            mock_instance = mock_socket.return_value.__enter__.return_value
            mock_instance.bind.side_effect = OSError("Address already in use")

            assert is_port_available(8999) is False


class TestFindAvailableIndex:
    """Tests for find_available_index function."""

    @patch("treemux.port.is_port_available", return_value=True)
    def test_empty_state_returns_zero(
        self,
        _mock_port_available,
        sample_treemux_config: TreemuxConfig,
        empty_state: TreemuxState,
    ):
        """空のstateはindex=0を返す"""
        result = find_available_index(sample_treemux_config, empty_state)
        assert result == 0

    @patch("treemux.port.is_port_available", return_value=True)
    def test_skips_used_indices(
        self,
        _mock_port_available,
        sample_treemux_config: TreemuxConfig,
    ):
        """使用中のインデックスをスキップする"""
        state = TreemuxState(
            instances={
                "a": InstanceInfo(index=0, started_at=datetime.now(UTC), ports={}),
                "b": InstanceInfo(index=1, started_at=datetime.now(UTC), ports={}),
            }
        )
        result = find_available_index(sample_treemux_config, state)
        assert result == 2

    @patch("treemux.port.is_port_available", return_value=True)
    def test_finds_gap(
        self,
        _mock_port_available,
        sample_treemux_config: TreemuxConfig,
    ):
        """インデックスの隙間を見つける"""
        state = TreemuxState(
            instances={
                "a": InstanceInfo(index=0, started_at=datetime.now(UTC), ports={}),
                "b": InstanceInfo(index=2, started_at=datetime.now(UTC), ports={}),
            }
        )
        result = find_available_index(sample_treemux_config, state)
        assert result == 1

    @patch("treemux.port.is_port_available", return_value=False)
    def test_returns_none_when_ports_unavailable(
        self,
        _mock_port_available,
        sample_treemux_config: TreemuxConfig,
        empty_state: TreemuxState,
    ):
        """全ポートが使用中の場合はNoneを返す"""
        result = find_available_index(sample_treemux_config, empty_state)
        assert result is None

    @patch("treemux.port.is_port_available", return_value=True)
    def test_respects_max_index(
        self,
        _mock_port_available,
        sample_treemux_config: TreemuxConfig,
    ):
        """max_indexパラメータを尊重する"""
        # index 0-4を使用
        instances = {}
        for i in range(5):
            instances[f"inst-{i}"] = InstanceInfo(
                index=i, started_at=datetime.now(UTC), ports={}
            )
        state = TreemuxState(instances=instances)

        # max_index=4では空きなし
        result = find_available_index(sample_treemux_config, state, max_index=4)
        assert result is None

        # max_index=5ではindex 5が利用可能
        result = find_available_index(sample_treemux_config, state, max_index=5)
        assert result == 5


class TestCheckPortsAvailability:
    """Tests for check_ports_availability function."""

    @patch("treemux.port.is_port_available")
    def test_all_available(self, mock_port_available):
        """全ポートが利用可能"""
        mock_port_available.return_value = True
        ports = {"web": 8000, "api": 8100}
        result = check_ports_availability(ports)
        assert result == {"web": True, "api": True}

    @patch("treemux.port.is_port_available")
    def test_some_unavailable(self, mock_port_available):
        """一部のポートが利用不可"""
        mock_port_available.side_effect = lambda port: port != 8000
        ports = {"web": 8000, "api": 8100}
        result = check_ports_availability(ports)
        assert result == {"web": False, "api": True}

    @patch("treemux.port.is_port_available", return_value=True)
    def test_empty_ports(self, _mock_port_available):
        """空のports dict"""
        result = check_ports_availability({})
        assert result == {}
