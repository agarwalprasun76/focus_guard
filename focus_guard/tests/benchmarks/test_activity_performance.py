"""
Performance benchmarks for the activity module components.

This module contains performance benchmarks for the IdleDetector, UsageTracker,
and EnhancedActivityMonitor classes to ensure they meet performance requirements.
"""

import time
import timeit
import unittest
from datetime import datetime, timedelta

import pytest

from focus_guard.core.activity.idle_detector import IdleDetector, IdleConfiguration, IdleState, IdleEvent, PlatformIdleDetector
from focus_guard.core.activity.usage_tracker import UsageTracker, UsageSession
from focus_guard.core.activity.enhanced_monitor import EnhancedActivityMonitor
from focus_guard.core.activity.models import WindowInfo


class TestActivityPerformance:
    """Performance tests for activity monitoring components."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.idle_config = IdleConfiguration(
            short_idle_threshold=60.0,
            medium_idle_threshold=300.0,
            long_idle_threshold=900.0,
            polling_interval=1.0
        )
        self.window_info = WindowInfo(
            pid=1234,
            app_name="test_app",
            window_title="Test Window",
            domain="example.com"
        )
    
    def test_benchmark_idle_detector_state_changes(self):
        """Benchmark state change handling in IdleDetector."""
        detector = IdleDetector(self.idle_config)
        
        # Create a mock platform detector that returns controlled idle times
        class MockPlatformDetector(PlatformIdleDetector):
            def __init__(self):
                self.idle_time = 0.0
                
            def get_idle_time_seconds(self) -> float:
                return self.idle_time
                
            def is_supported(self) -> bool:
                return True
        
        mock_detector = MockPlatformDetector()
        detector.platform_detector = mock_detector
        
        def test_state_changes():
            for i in range(1000):
                # Simulate state changes by modifying the idle time
                mock_detector.idle_time = 0.0  # ACTIVE
                detector.is_idle()
                mock_detector.idle_time = 61.0  # SHORT_IDLE
                detector.is_idle()
                mock_detector.idle_time = 301.0  # LONG_IDLE
                detector.is_idle()
        
        duration = timeit.timeit(test_state_changes, number=100)
        print(f"\nIdleDetector state changes: {duration:.6f} seconds per 1000 state changes")
        assert duration < 1.0, "State changes are too slow"
    
    def test_benchmark_usage_tracker_session_management(self):
        """Benchmark session management in UsageTracker."""
        tracker = UsageTracker(IdleDetector(self.idle_config))
        
        def test_sessions():
            for i in range(100):
                window = WindowInfo(
                    pid=1000 + i,
                    app_name=f"app_{i}",
                    window_title=f"Window {i}",
                    domain=f"example{i}.com"
                )
                tracker.track_activity(window)
                event = IdleEvent(
                    timestamp=datetime.now(),
                    previous_state=IdleState.ACTIVE if i % 2 == 0 else IdleState.SHORT_IDLE,
                    current_state=IdleState.ACTIVE if i % 2 == 0 else IdleState.SHORT_IDLE,
                    idle_duration=i * 10.0,
                    active_duration=0.0
                )
                tracker._on_idle_state_change(event)
        
        duration = timeit.timeit(test_sessions, number=10)
        print(f"\nUsageTracker session management: {duration:.6f} seconds per 100 sessions")
        assert duration < 0.5, "Session management is too slow"
    
    def test_benchmark_enhanced_monitor_activity_tracking(self):
        """Benchmark activity tracking in EnhancedActivityMonitor."""
        monitor = EnhancedActivityMonitor(
            idle_config=self.idle_config,
            polling_interval=0.01,  # Faster polling for benchmark
            session_timeout=60.0
        )
        
        # Track number of callbacks for verification
        self.callback_count = 0
        
        def activity_callback(window_info):
            self.callback_count += 1
        
        # Register our callback
        monitor.add_activity_callback(activity_callback)
        
        # Test function to benchmark
        def test_activity_tracking():
            # Simulate 100 activity checks through the public API
            for i in range(100):
                # Get current idle time (will trigger internal updates)
                monitor.get_idle_time_seconds()
                
                # Get current session info
                monitor.get_current_usage_session()
                
                # Check if user is active
                monitor.is_user_active()
        
        # Run the benchmark
        monitor.start_monitoring()
        try:
            duration = timeit.timeit(test_activity_tracking, number=10)
            print(f"\nEnhancedActivityMonitor activity tracking: {duration:.6f} seconds per 1000 activities")
            print(f"Callbacks triggered: {self.callback_count}")
            assert duration < 2.0, "Activity tracking is too slow"
        finally:
            monitor.stop_monitoring()
    
    def test_memory_usage(self):
        """Test memory usage with many sessions and events."""
        import tracemalloc
        import gc
        
        tracemalloc.start()
        
        # Create and track many sessions
        tracker = UsageTracker(IdleDetector(self.idle_config))
        start_time = time.time()
        
        # Create 1000 sessions with events
        for i in range(1000):
            window = WindowInfo(
                pid=1000 + (i % 10),
                app_name=f"app_{i % 5}",
                window_title=f"Window {i}",
                domain=f"example{i % 5}.com"
            )
            tracker.track_activity(window)
            # Create an IdleEvent to pass to _on_idle_state_change
            event = IdleEvent(
                timestamp=datetime.now(),
                previous_state=IdleState.ACTIVE if i % 2 == 0 else IdleState.SHORT_IDLE,
                current_state=IdleState.ACTIVE if i % 2 == 0 else IdleState.SHORT_IDLE,
                idle_duration=(i % 10) * 10.0,
                active_duration=0.0
            )
            tracker._on_idle_state_change(event)
        
        # Force garbage collection
        gc.collect()
        
        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        duration = time.time() - start_time
        print(f"\nMemory usage for 1000 sessions:")
        print(f"  Current: {current / 1024:.2f} KB")
        print(f"  Peak: {peak / 1024:.2f} KB")
        print(f"  Time: {duration:.4f} seconds")
        
        assert peak < 10 * 1024 * 1024, "Memory usage too high (>10MB)"
        assert duration < 1.0, "Session creation too slow"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
