"""
FinStream AI - Synthetic Transaction Generator CLI & Core Runner
Generates synthetic financial transaction streams with realistic behavioral distributions
and configurable anomaly scenarios.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Callable, Dict, Generator, Iterator, List, Optional
from config import settings
from producer.account_profiles import AccountPool
from producer.scenario_generator import ScenarioGenerator
from producer.transaction_models import Transaction

# Configure logging to stderr so stdout remains clean JSON
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("transaction_generator")


class TransactionGenerator:
    """
    Core transaction generator engine.
    Produces transactions at a configurable rate and scenario profile.
    """

    def __init__(
        self,
        rate: float = 5.0,
        num_accounts: int = 200,
        scenario: str = "mixed",
        seed: Optional[int] = None,
        include_scenario_label: bool = False,
    ):
        self.rate = max(0.1, float(rate))
        self.interval = 1.0 / self.rate
        self.num_accounts = num_accounts
        self.scenario = scenario.lower()
        self.seed = seed
        self.include_scenario_label = include_scenario_label

        self.account_pool = AccountPool(size=self.num_accounts, seed=self.seed)
        self.scenario_gen = ScenarioGenerator(self.account_pool, seed=self.seed)
        self.total_generated = 0
        self.running = False

    def generate_single_event_or_burst(self) -> List[Transaction]:
        """Generates the next batch/event based on selected scenario."""
        if self.scenario == "normal":
            return [self.scenario_gen.generate_normal()]
        elif self.scenario == "high_amount":
            return [self.scenario_gen.generate_high_amount()]
        elif self.scenario == "velocity_spike":
            return self.scenario_gen.generate_velocity_spike()
        elif self.scenario == "new_device":
            return [self.scenario_gen.generate_new_device()]
        elif self.scenario == "unusual_merchant":
            return [self.scenario_gen.generate_unusual_merchant()]
        elif self.scenario == "unusual_location":
            return [self.scenario_gen.generate_unusual_location()]
        elif self.scenario == "rapid_device_switching":
            return self.scenario_gen.generate_rapid_device_switching()
        elif self.scenario == "mixed":
            return self.scenario_gen.generate_mixed()
        else:
            logger.warning("Unknown scenario '%s', defaulting to mixed", self.scenario)
            return self.scenario_gen.generate_mixed()

    def stream_transactions(
        self, duration: Optional[float] = None
    ) -> Iterator[Transaction]:
        """
        Yields transactions one by one with targeted throughput pacing.
        """
        self.running = True
        start_time = time.time()

        try:
            while self.running:
                loop_start = time.time()
                events = self.generate_single_event_or_burst()

                for tx in events:
                    if not self.running:
                        break
                    self.total_generated += 1
                    yield tx

                    # Check duration expiration
                    if duration and (time.time() - start_time) >= duration:
                        self.running = False
                        return

                    # Throttle pacing
                    elapsed = time.time() - loop_start
                    sleep_time = self.interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    loop_start = time.time()
        finally:
            self.running = False

    def run(
        self,
        duration: Optional[float] = None,
        callback: Optional[Callable[[Transaction], None]] = None,
    ) -> int:
        """
        Runs the generator loop. If no callback is provided, outputs JSON to stdout.
        """
        logger.info(
            "Starting Synthetic Transaction Generator (Rate: %.1f TPS, Accounts: %d, Scenario: %s, Seed: %s)",
            self.rate,
            self.num_accounts,
            self.scenario,
            str(self.seed),
        )
        if duration:
            logger.info("Generator running for duration: %.1f seconds", duration)
        else:
            logger.info("Generator running continuously (Ctrl+C to stop)...")

        start_time = time.time()
        try:
            for tx in self.stream_transactions(duration=duration):
                if callback:
                    callback(tx)
                else:
                    tx_dict = tx.to_clean_dict(include_scenario=self.include_scenario_label)
                    # Output valid JSON string to stdout
                    sys.stdout.write(json.dumps(tx_dict) + "\n")
                    sys.stdout.flush()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Stopping generator gracefully...")
        finally:
            elapsed = time.time() - start_time
            effective_rate = (
                self.total_generated / elapsed if elapsed > 0 else 0.0
            )
            logger.info(
                "Generator stopped. Generated %d transactions in %.2fs (Effective: %.2f TPS)",
                self.total_generated,
                elapsed,
                effective_rate,
            )

        return self.total_generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinStream AI Synthetic Financial Transaction Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=float(settings.GENERATOR_RATE_TPS),
        help="Target transactions generated per second (TPS)",
    )
    parser.add_argument(
        "--accounts",
        type=int,
        default=settings.GENERATOR_ACCOUNTS_POOL,
        help="Size of synthetic account population",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Run duration in seconds (omission runs continuously)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="mixed",
        choices=[
            "normal",
            "high_amount",
            "velocity_spike",
            "new_device",
            "unusual_merchant",
            "unusual_location",
            "rapid_device_switching",
            "mixed",
        ],
        help="Specific scenario to generate or 'mixed' for realistic baseline",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic generation",
    )
    parser.add_argument(
        "--include-scenario-label",
        action="store_true",
        help="Include 'scenario_label' in JSON output for inspection",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    generator = TransactionGenerator(
        rate=args.rate,
        num_accounts=args.accounts,
        scenario=args.scenario,
        seed=args.seed,
        include_scenario_label=args.include_scenario_label,
    )
    generator.run(duration=args.duration)


if __name__ == "__main__":
    main()
