"""ポート割り当てロジック"""

import socket

from treemux.models import TreemuxConfig, TreemuxState


def calculate_port(base_port: int, index: int) -> int:
    """インデックスに基づいてポートを計算

    Args:
        base_port: ベースポート番号
        index: ワークツリーインデックス (0-9)

    Returns:
        割り当てポート番号
    """
    return base_port + index


def allocate_ports(
    config: TreemuxConfig,
    index: int,
) -> dict[str, int]:
    """指定インデックスでポートを割り当て

    Args:
        config: treemux設定
        index: ワークツリーインデックス

    Returns:
        サービス名→ポート番号のマッピング
    """
    return {
        service_name: calculate_port(svc.base_host_port, index)
        for service_name, svc in config.services.items()
    }


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """ポートが使用可能かチェック

    Args:
        port: チェックするポート番号
        host: バインドするホスト

    Returns:
        使用可能ならTrue
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_index(
    config: TreemuxConfig,
    state: TreemuxState,
    max_index: int = 9,
) -> int | None:
    """使用可能なインデックスを検索

    Args:
        config: treemux設定
        state: 現在の状態
        max_index: 最大インデックス

    Returns:
        使用可能なインデックス、なければNone
    """
    used_indices = state.get_used_indices()

    for index in range(max_index + 1):
        if index in used_indices:
            continue

        ports = allocate_ports(config, index)
        if all(is_port_available(port) for port in ports.values()):
            return index

    return None


def check_ports_availability(ports: dict[str, int]) -> dict[str, bool]:
    """複数ポートの使用可否をチェック

    Args:
        ports: サービス名→ポート番号のマッピング

    Returns:
        サービス名→使用可否のマッピング
    """
    return {
        service_name: is_port_available(port) for service_name, port in ports.items()
    }
