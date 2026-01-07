"""設定・状態のデータモデル定義"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class ServiceConfig(BaseModel):
    """サービス設定"""

    container_port: int = Field(ge=1, le=65535, description="コンテナ内部ポート")
    base_host_port: int = Field(ge=1024, le=65535, description="ホスト側ベースポート")


class SubdomainConfig(BaseModel):
    """サブドメイン設定（将来拡張用）"""

    enabled: bool = False
    domain: str = "project.local"


class TreemuxConfig(BaseModel):
    """プロジェクト設定 (.treemux/config.yml)"""

    version: str = "1"
    project_name: str = Field(min_length=1, description="プロジェクト名")
    services: dict[str, ServiceConfig] = Field(
        default_factory=dict, description="サービス設定"
    )
    subdomain: SubdomainConfig = Field(default_factory=SubdomainConfig)


class InstanceInfo(BaseModel):
    """ワークツリーインスタンス情報"""

    index: int = Field(ge=0, le=9, description="ワークツリーインデックス")
    started_at: datetime = Field(description="起動時刻")
    ports: dict[str, int] = Field(
        default_factory=dict, description="サービス名→割り当てポート"
    )
    worktree_path: Path | None = Field(default=None, description="ワークツリーパス")


class TreemuxState(BaseModel):
    """実行時状態 (.treemux/state.json)"""

    instances: dict[str, InstanceInfo] = Field(
        default_factory=dict, description="インスタンス名→情報"
    )

    def get_used_indices(self) -> set[int]:
        """使用中のインデックスを取得"""
        return {inst.index for inst in self.instances.values()}

    def get_next_available_index(self) -> int:
        """次の空きインデックスを取得

        Raises:
            ValueError: 空きインデックスがない場合
        """
        used = self.get_used_indices()
        for i in range(10):
            if i not in used:
                return i
        raise ValueError("No available index (max 10 instances)")


class ComposeResult(BaseModel):
    """docker compose実行結果"""

    success: bool
    return_code: int
    stdout: str = ""
    stderr: str = ""
    command: list[str] = Field(default_factory=list)
