"""Unified in-car assistant environment adapter for SkillOpt.

Optimizes ONE skill against a mixed corpus (commands + grounded chat) — the
realistic deployment, where a single model routes each utterance to a tool call
or a spoken answer. Rollout runs the target under the current skill; the
evaluator dispatches per case type.
"""

from __future__ import annotations

import os
from typing import Any

from skillopt.datasets.base import BatchSpec
from skillopt.envs.base import EnvAdapter

from .dataloader import IncarUnifiedDataLoader
from .rollout import run_batch


class IncarUnifiedAdapter(EnvAdapter):
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
        self.dataloader = IncarUnifiedDataLoader(
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

    def reflect(self, results: list[dict], skill_content: str, out_dir: str, **kwargs: Any) -> list[dict | None]:
        """Stratified reflect: run the minibatch stage once per case_type.

        The stock reflect pools all failures, shuffles, and splits into
        size-M minibatches — so the few chat failures get scattered among the
        many command failures and an analyst minibatch is often all-command,
        which is why the optimizer only ever wrote command rules. Grouping by
        case_type first guarantees each quadrant reflects on its own
        trajectories and produces type-specific edits.
        """
        from skillopt.gradient.reflect import run_minibatch_reflect

        by_type: dict[str, list[dict]] = {}
        for r in results:
            by_type.setdefault(str(r.get("task_type", "command")), []).append(r)

        prediction_dir = kwargs.get("prediction_dir", os.path.join(out_dir, "predictions"))
        patches_root = kwargs.get("patches_dir", os.path.join(out_dir, "patches"))

        patches: list[dict | None] = []
        for tt, group in by_type.items():
            patches += run_minibatch_reflect(
                results=group,
                skill_content=skill_content,
                prediction_dir=prediction_dir,
                patches_dir=os.path.join(patches_root, tt),  # per-type dir avoids filename collisions
                workers=self.analyst_workers,
                failure_only=self.failure_only,
                minibatch_size=self.minibatch_size,
                edit_budget=self.edit_budget,
                random_seed=kwargs.get("random_seed"),
                error_system=self.get_error_minibatch_prompt(),
                success_system=self.get_success_minibatch_prompt(),
                step_buffer_context=kwargs.get("step_buffer_context", ""),
                meta_skill_context=kwargs.get("meta_skill_context", ""),
                update_mode=getattr(self, "_cfg", {}).get("skill_update_mode", "patch"),
            )
        return patches

    def get_task_types(self) -> list[str]:
        seen: list[str] = []
        for item in self.dataloader.train_items + self.dataloader.val_items + self.dataloader.test_items:
            tt = str(item.get("case_type") or "command")
            if tt not in seen:
                seen.append(tt)
        return seen or ["command", "chat"]
