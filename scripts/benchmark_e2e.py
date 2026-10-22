"""
FinStream AI - End-to-End Performance & Latency Benchmark CLI
Executes controlled transaction load and measures actual throughput and latency distributions.
"""

import argparse
import json
import logging
import os
import platform
import sys
import fakeredis

from database.connection import DatabaseManager
from database.redis_client import RedisRepository
from streaming.pipeline_runner import EndToEndPipelineRunner

logging.basicConfig(level=logging.WARNING)


def run_benchmark(num_transactions: int = 100, scenario: str = "mixed", seed: int = 42):
    print("=" * 70)
    print("  FinStream AI — End-to-End Pipeline Performance Benchmark")
    print("=" * 70)

    # 1. System Info
    cpu_count = os.cpu_count() or 1
    os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
    py_ver = platform.python_version()

    print(f"OS:                 {os_info}")
    print(f"CPU Threads:        {cpu_count}")
    print(f"Python Version:     {py_ver}")
    print(f"Target Samples (N): {num_transactions}")
    print(f"Scenario:           {scenario}")
    print(f"Random Seed:        {seed}")
    print("-" * 70)

    # 2. Setup isolated in-memory testing backend
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.create_all_tables()

    fake_client = fakeredis.FakeRedis(decode_responses=True)
    redis_repo = RedisRepository(client=fake_client)

    runner = EndToEndPipelineRunner(db_manager=db_mgr, redis_repo=redis_repo)

    print(f"Executing pipeline over {num_transactions} synthetic transactions...")
    summary = runner.run_benchmark(num_transactions=num_transactions, scenario=scenario, seed=seed)

    print("-" * 70)
    print("  MEASURED RESULTS")
    print("-" * 70)
    print(f"Total Transactions: {summary['total_transactions']}")
    print(f"Elapsed Time:       {summary['duration_seconds']}s")
    print(f"Throughput:         {summary['throughput_tps']} transactions/second")
    print()

    print(f"{'Pipeline Stage':<26} {'P50 (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10} {'Max (ms)':<10} {'Mean (ms)':<10}")
    print("-" * 70)

    for stage_key, label in [
        ("feature_latency", "Feature Engineering"),
        ("ml_inference_latency", "ML Inference + SHAP"),
        ("persistence_latency", "DB & Cache Persistence"),
        ("websocket_latency", "WebSocket Dispatch"),
        ("e2e_latency", "Total End-to-End"),
    ]:
        st = summary[stage_key]
        print(f"{label:<26} {st['p50_ms']:<10} {st['p95_ms']:<10} {st['p99_ms']:<10} {st['max_ms']:<10} {st['mean_ms']:<10}")

    print("=" * 70)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinStream AI E2E Benchmark")
    parser.add_argument("--count", type=int, default=100, help="Number of transactions to process")
    parser.add_argument("--scenario", type=str, default="mixed", help="Scenario name")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    run_benchmark(num_transactions=args.count, scenario=args.scenario, seed=args.seed)
