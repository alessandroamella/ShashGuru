# This file is part of ShashGuru, a chess analyzer that takes a FEN, asks a UCI chess engine to analyse it and then outputs a natural language analysis made by an LLM.
# Copyright (C) 2025  Alessandro Libralesso
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import os
from datetime import datetime
from pathlib import Path
import logging as log


class GoogleRateLimiter:
    """Simple file-based rate limiter for Google AI API calls."""

    def __init__(self, max_monthly_calls=None):
        """
        Initialize the rate limiter.

        Args:
            max_monthly_calls: Maximum number of calls per month. If None, reads from env.
        """
        self.storage_file = Path(__file__).parent / "google_api_usage.json"
        self.max_monthly_calls = max_monthly_calls or int(
            os.environ.get("GOOGLE_AI_MAX_MONTHLY_CALLS", "100")
        )
        self._load_usage()

    def _load_usage(self):
        """Load usage data from file."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r") as f:
                    data = json.load(f)
                    self.current_month = data.get("month")
                    self.call_count = data.get("count", 0)
            except (json.JSONDecodeError, IOError) as e:
                log.warning(f"Failed to load Google API usage data: {e}")
                self._reset_usage()
        else:
            self._reset_usage()

        # Reset if we're in a new month
        now_month = datetime.now().strftime("%Y-%m")
        if self.current_month != now_month:
            self._reset_usage()

    def _reset_usage(self):
        """Reset usage counter for the current month."""
        self.current_month = datetime.now().strftime("%Y-%m")
        self.call_count = 0
        self._save_usage()

    def _save_usage(self):
        """Save usage data to file."""
        try:
            with open(self.storage_file, "w") as f:
                json.dump({"month": self.current_month, "count": self.call_count}, f)
        except IOError as e:
            log.error(f"Failed to save Google API usage data: {e}")

    def can_make_call(self):
        """
        Check if a call can be made within the rate limit.

        Returns:
            bool: True if call is allowed, False otherwise
        """
        self._load_usage()  # Reload to check for month change
        log.info(
            f"Google API usage for {self.current_month}: {self.call_count}/{self.max_monthly_calls}"
        )
        return self.call_count < self.max_monthly_calls

    def increment_call(self):
        """Increment the call counter."""
        self._load_usage()  # Reload to ensure we have latest data
        self.call_count += 1
        self._save_usage()

    def get_usage_stats(self):
        """
        Get current usage statistics.

        Returns:
            dict: Dictionary with usage information
        """
        self._load_usage()
        return {
            "month": self.current_month,
            "calls_used": self.call_count,
            "calls_remaining": max(0, self.max_monthly_calls - self.call_count),
            "max_calls": self.max_monthly_calls,
        }


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, stats):
        self.stats = stats
        super().__init__(
            f"Google AI API monthly rate limit exceeded. "
            f"Used {stats['calls_used']}/{stats['max_calls']} calls this month ({stats['month']}). "
            f"Limit will reset next month."
        )
