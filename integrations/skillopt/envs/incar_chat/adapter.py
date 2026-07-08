"""In-car chat (grounded informational) environment adapter for SkillOpt.

Dataset-backed pattern (mirrors the command env): the dataloader yields grounded
chat items, ``build_env_from_batch`` passes them through, and ``rollout`` runs
the target under the current skill and scores each with the faithfulness verifier.
"""

from __future__ import annotations

from typing import Any

from skillopt.datasets.base import BatchSpec
from skillopt.envs.base import EnvAdapter

from .dataloader import IncarChatDataLoader
from .rollout import run_batch


class IncarChatAdapter(EnvAdapter):
    def __init__(
        self,
        split_dir: str = "",
        data_path: str = "",
        split_mode: str = "split_dir",
        split_ratio: str = "2:1:7",
        split_seed: int = 42,
        split_output_dir: str = "",
        workers: int = 8,
        analyst_workers: int = 4,
        failure_only: bool = False,
        minibatch_size: int = 8,
        edit_budget: int = 4,
        seed: int = 42,
        limit: int = 0,
        max_completion_tokens: int = 1024,
    ) -> None:
        self.workers = workers
        self.analyst_workers = analyst_workers
        self.failure_only = failure_only
        self.minibatch_size = minibatch_size
        self.edit_budget = edit_budget
        self.max_completion_tokens = int(max_completion_tokens)
        self.dataloader = IncarChatDataLoader(
            split_dir=split_dir,
            data_path=data_path,
            split_mode=split_mode,
            split_ratio=split_ratio,
            split_seed=split_seed,
            split_output_dir=split_output_dir,
            seed=seed,
            limit=limit,
        )

    def setup(self, cfg: dict) -> None:
        super().setup(cfg)
        self.dataloader.setup(cfg)

    def get_dataloader(self):
        return self.dataloader

    def build_env_from_batch(self, batch: BatchSpec, **kwargs: Any):
        return list(batch.payload or [])

    def build_train_env(self, batch_size: int, seed: int, **kwargs: Any):
        batch = self.dataloader.build_train_batch(batch_size=batch_size, seed=seed, **kwargs)
        return self.build_env_from_batch(batch, **kwargs)

    def build_eval_env(self, env_num: int, split: str, seed: int, **kwargs: Any):
        batch = self.dataloader.build_eval_batch(env_num=env_num, split=split, seed=seed, **kwargs)
        return self.build_env_from_batch(batch, **kwargs)

    def rollout(self, env_manager: Any, skill_content: str, out_dir: str, **kwargs: Any) -> list[dict[str, Any]]:
        return run_batch(
            items=env_manager,
            out_root=out_dir,
            skill_content=skill_content,
            workers=self.workers,
            max_completion_tokens=self.max_completion_tokens,
        )

    def get_task_types(self) -> list[str]:
        return ["chat"]
