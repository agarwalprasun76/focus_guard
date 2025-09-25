"""
Background task management for classification and caching operations.

This module provides background services for precomputing classifications,
cache warming, and other asynchronous operations that improve performance.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import time

from focus_guard.core.domain.models import Domain, Classification
from focus_guard.core.domain.constants import DOMAIN_CATEGORIES
from focus_guard.core.cache.multi_level_cache import MultiLevelCache

logger = logging.getLogger(__name__)


@dataclass
class BackgroundTask:
    """Represents a background task."""
    name: str
    func: Callable
    interval: float
    last_run: float
    enabled: bool = True


class BackgroundClassificationService:
    """
    Service for background classification and cache management.
    
    This service handles:
    - Precomputing classifications for popular domains
    - Cache warming on startup
    - Periodic cache refresh
    - Performance monitoring
    """
    
    def __init__(
        self,
        cache: MultiLevelCache,
        classifier_func: Callable,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize background classification service.
        
        Args:
            cache: Multi-level cache instance
            classifier_func: Function to classify domains
            config: Optional configuration dict
        """
        self.cache = cache
        self.classifier_func = classifier_func
        self.config = config or {}
        
        # Service state
        self.running = False
        self.tasks: Dict[str, BackgroundTask] = {}
        self.main_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.warmup_domains = self._get_warmup_domains()
        self.refresh_interval = self.config.get('refresh_interval', 300)  # 5 minutes
        self.warmup_batch_size = self.config.get('warmup_batch_size', 10)
        self.warmup_delay = self.config.get('warmup_delay', 0.5)  # seconds between requests
        
        # Statistics
        self.stats = {
            'warmup_completed': 0,
            'background_classifications': 0,
            'cache_refreshes': 0,
            'errors': 0,
            'last_warmup': None,
            'last_refresh': None
        }
        
        self._setup_tasks()
    
    def _get_warmup_domains(self) -> List[str]:
        """Get list of domains to warm up on startup."""
        domains = []
        
        # Add domains from configuration
        for category, domain_list in DOMAIN_CATEGORIES.items():
            domains.extend(domain_list)
        
        # Add high-priority domains (most likely to be accessed)
        priority_domains = [
            'youtube.com', 'google.com', 'facebook.com', 'twitter.com',
            'instagram.com', 'netflix.com', 'amazon.com', 'github.com',
            'stackoverflow.com', 'reddit.com', 'linkedin.com', 'twitch.tv'
        ]
        
        # Combine and deduplicate
        all_domains = list(set(domains + priority_domains))
        
        # Sort by priority (priority domains first)
        sorted_domains = []
        for domain in priority_domains:
            if domain in all_domains:
                sorted_domains.append(domain)
        
        for domain in all_domains:
            if domain not in sorted_domains:
                sorted_domains.append(domain)
        
        logger.info(f"Prepared {len(sorted_domains)} domains for cache warming")
        return sorted_domains
    
    def _setup_tasks(self) -> None:
        """Setup background tasks."""
        self.tasks = {
            'cache_warmup': BackgroundTask(
                name='cache_warmup',
                func=self._warmup_cache,
                interval=86400,  # Daily
                last_run=0,
                enabled=True
            ),
            'cache_refresh': BackgroundTask(
                name='cache_refresh',
                func=self._refresh_popular_cache,
                interval=self.refresh_interval,
                last_run=0,
                enabled=True
            ),
            'cache_cleanup': BackgroundTask(
                name='cache_cleanup',
                func=self._cleanup_cache,
                interval=3600,  # Hourly
                last_run=0,
                enabled=True
            ),
            'stats_logging': BackgroundTask(
                name='stats_logging',
                func=self._log_stats,
                interval=1800,  # Every 30 minutes
                last_run=0,
                enabled=True
            )
        }
    
    async def start(self) -> None:
        """Start the background service."""
        if self.running:
            logger.warning("Background classification service already running")
            return
        
        self.running = True
        self.main_task = asyncio.create_task(self._main_loop())
        
        # Start cache background refresh
        await self.cache.start_background_refresh(self.classifier_func)
        
        logger.info("Background classification service started")
    
    async def stop(self) -> None:
        """Stop the background service."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop cache background refresh
        await self.cache.stop_background_refresh()
        
        # Cancel main task
        if self.main_task:
            self.main_task.cancel()
            try:
                await self.main_task
            except asyncio.CancelledError:
                pass
            self.main_task = None
        
        logger.info("Background classification service stopped")
    
    async def _main_loop(self) -> None:
        """Main background service loop."""
        logger.info("Starting background service main loop")
        
        try:
            # Initial cache warmup
            await self._warmup_cache()
            
            # Main service loop
            while self.running:
                current_time = time.time()
                
                # Check and run tasks
                for task in self.tasks.values():
                    if not task.enabled:
                        continue
                    
                    if current_time - task.last_run >= task.interval:
                        try:
                            logger.debug(f"Running background task: {task.name}")
                            await task.func()
                            task.last_run = current_time
                        except Exception as e:
                            logger.error(f"Background task {task.name} failed: {e}")
                            self.stats['errors'] += 1
                
                # Sleep before next iteration
                await asyncio.sleep(60)  # Check every minute
        
        except asyncio.CancelledError:
            logger.info("Background service main loop cancelled")
        except Exception as e:
            logger.error(f"Background service main loop error: {e}")
            self.stats['errors'] += 1
    
    async def _warmup_cache(self) -> None:
        """Warm up cache with popular domains."""
        logger.info("Starting cache warmup")
        start_time = time.time()
        
        try:
            # Process domains in batches
            total_warmed = 0
            
            for i in range(0, len(self.warmup_domains), self.warmup_batch_size):
                batch = self.warmup_domains[i:i + self.warmup_batch_size]
                
                # Warm this batch
                batch_warmed = await self.cache.warm_cache(
                    batch, 
                    self._classify_domain_for_warmup
                )
                total_warmed += batch_warmed
                
                # Small delay between batches
                if i + self.warmup_batch_size < len(self.warmup_domains):
                    await asyncio.sleep(self.warmup_delay)
            
            elapsed = time.time() - start_time
            self.stats['warmup_completed'] += 1
            self.stats['last_warmup'] = datetime.now().isoformat()
            
            logger.info(
                f"Cache warmup completed: {total_warmed}/{len(self.warmup_domains)} "
                f"domains in {elapsed:.2f}s"
            )
        
        except Exception as e:
            logger.error(f"Cache warmup failed: {e}")
            self.stats['errors'] += 1
    
    async def _classify_domain_for_warmup(self, domain: str) -> Optional[Classification]:
        """Classify a domain for cache warmup."""
        try:
            # Handle both string and Domain object inputs
            if isinstance(domain, str):
                domain_input = domain
            else:
                domain_input = str(domain)
            
            result = await self.classifier_func(domain_input)
            
            if result:
                self.stats['background_classifications'] += 1
                logger.debug(f"Background classified {domain_input}: {result.category.name}")
            
            return result
        
        except Exception as e:
            logger.warning(f"Background classification failed for {domain}: {e}")
            return None
    
    async def _refresh_popular_cache(self) -> None:
        """Refresh popular cache entries."""
        try:
            # Get cache statistics to identify popular domains
            cache_stats = self.cache.get_stats()
            
            if cache_stats.get('popular_domains_count', 0) > 0:
                logger.debug(f"Refreshing {cache_stats['popular_domains_count']} popular domains")
                
                # The cache handles its own background refresh
                # We just track the statistics here
                self.stats['cache_refreshes'] += 1
                self.stats['last_refresh'] = datetime.now().isoformat()
        
        except Exception as e:
            logger.error(f"Cache refresh failed: {e}")
            self.stats['errors'] += 1
    
    async def _cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        try:
            cleanup_stats = await self.cache.cleanup()
            
            if cleanup_stats['memory_cleaned'] > 0 or cleanup_stats['disk_cleaned'] > 0:
                logger.info(
                    f"Cache cleanup: {cleanup_stats['memory_cleaned']} memory, "
                    f"{cleanup_stats['disk_cleaned']} disk entries removed"
                )
        
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            self.stats['errors'] += 1
    
    async def _log_stats(self) -> None:
        """Log service statistics."""
        try:
            cache_stats = self.cache.get_stats()
            
            logger.info(
                f"Background service stats - "
                f"Warmups: {self.stats['warmup_completed']}, "
                f"Classifications: {self.stats['background_classifications']}, "
                f"Cache hit rate: {cache_stats.get('hit_rate', 0):.2%}, "
                f"Memory entries: {cache_stats.get('memory_size', 0)}, "
                f"Errors: {self.stats['errors']}"
            )
        
        except Exception as e:
            logger.error(f"Stats logging failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        cache_stats = self.cache.get_stats()
        
        return {
            'service_stats': self.stats,
            'cache_stats': cache_stats,
            'warmup_domains_count': len(self.warmup_domains),
            'running': self.running,
            'tasks_enabled': {name: task.enabled for name, task in self.tasks.items()}
        }
    
    def configure_task(self, task_name: str, enabled: bool, interval: Optional[float] = None) -> bool:
        """
        Configure a background task.
        
        Args:
            task_name: Name of the task to configure
            enabled: Whether the task should be enabled
            interval: Optional new interval for the task
            
        Returns:
            True if task was configured successfully
        """
        if task_name not in self.tasks:
            logger.error(f"Unknown background task: {task_name}")
            return False
        
        task = self.tasks[task_name]
        task.enabled = enabled
        
        if interval is not None:
            task.interval = interval
        
        logger.info(f"Configured task {task_name}: enabled={enabled}, interval={task.interval}")
        return True
    
    async def force_warmup(self) -> Dict[str, Any]:
        """Force immediate cache warmup."""
        logger.info("Forcing immediate cache warmup")
        await self._warmup_cache()
        return self.get_stats()


class BackgroundTaskManager:
    """Manager for multiple background services."""
    
    def __init__(self):
        """Initialize task manager."""
        self.services: Dict[str, BackgroundClassificationService] = {}
        self.running = False
    
    def register_service(self, name: str, service: BackgroundClassificationService) -> None:
        """Register a background service."""
        self.services[name] = service
        logger.info(f"Registered background service: {name}")
    
    async def start_all(self) -> None:
        """Start all registered services."""
        if self.running:
            return
        
        self.running = True
        
        for name, service in self.services.items():
            try:
                await service.start()
                logger.info(f"Started background service: {name}")
            except Exception as e:
                logger.error(f"Failed to start service {name}: {e}")
    
    async def stop_all(self) -> None:
        """Stop all registered services."""
        if not self.running:
            return
        
        self.running = False
        
        for name, service in self.services.items():
            try:
                await service.stop()
                logger.info(f"Stopped background service: {name}")
            except Exception as e:
                logger.error(f"Failed to stop service {name}: {e}")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics from all services."""
        return {
            name: service.get_stats()
            for name, service in self.services.items()
        }
