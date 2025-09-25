"""
Automated Integration Test Suite with Reporting.

This module provides a comprehensive test runner for all Focus Guard integration tests,
implementing Phase 3 requirements with detailed reporting and metrics collection.
"""

import asyncio
import json
import time
import logging
import sys
import traceback
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import pytest

# Add focus_guard to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Individual test result data structure."""
    test_name: str
    module: str
    status: str  # 'passed', 'failed', 'skipped', 'error'
    duration: float
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class TestSuiteResult:
    """Complete test suite result data structure."""
    suite_name: str
    start_time: str
    end_time: str
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    test_results: List[TestResult]
    system_info: Dict[str, Any]
    coverage_info: Optional[Dict[str, Any]] = None


class IntegrationTestSuite:
    """Comprehensive integration test suite runner."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize test suite runner.
        
        Args:
            output_dir: Directory for test reports and artifacts
        """
        self.output_dir = output_dir or Path("test_reports")
        self.output_dir.mkdir(exist_ok=True)
        
        # Test modules to run (as file paths)
        self.test_modules = [
            "focus_guard/tests/integration/test_tab_blocking_pipeline.py",
            "focus_guard/tests/integration/test_browser_extension_integration.py", 
            "focus_guard/tests/integration/test_error_scenarios.py",
            "focus_guard/tests/integration/test_component_interactions.py"
        ]
        
        # Test configuration
        self.config = {
            'timeout_per_test': 30,  # seconds
            'max_retries': 2,
            'parallel_execution': False,  # Set to True for parallel test execution
            'collect_coverage': False,  # Simplified - no coverage for now
            'generate_html_report': True,
            'save_artifacts': True
        }
        
        self.results: List[TestResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    async def run_all_tests(self) -> TestSuiteResult:
        """Run all integration tests and generate comprehensive report."""
        logger.info("Starting Focus Guard Integration Test Suite")
        
        self.start_time = datetime.now()
        
        try:
            # System information
            system_info = await self._collect_system_info()
            
            # Pre-test setup
            await self._pre_test_setup()
            
            # Run test modules
            if self.config['parallel_execution']:
                await self._run_tests_parallel()
            else:
                await self._run_tests_sequential()
            
            # Post-test cleanup
            await self._post_test_cleanup()
            
            self.end_time = datetime.now()
            
            # Generate comprehensive report
            suite_result = self._generate_suite_result(system_info)
            
            # Save reports
            await self._save_reports(suite_result)
            
            # Print summary
            self._print_summary(suite_result)
            
            return suite_result
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _run_tests_sequential(self):
        """Run tests sequentially."""
        for module in self.test_modules:
            logger.info(f"Running tests in module: {module}")
            
            try:
                module_results = await self._run_module_tests(module)
                self.results.extend(module_results)
                
            except Exception as e:
                logger.error(f"Failed to run module {module}: {e}")
                error_result = TestResult(
                    test_name=f"module_{module}",
                    module=module,
                    status='error',
                    duration=0.0,
                    error_message=str(e),
                    error_traceback=traceback.format_exc()
                )
                self.results.append(error_result)
    
    async def _run_tests_parallel(self):
        """Run tests in parallel."""
        tasks = []
        for module in self.test_modules:
            task = asyncio.create_task(self._run_module_tests(module))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = TestResult(
                    test_name=f"module_{self.test_modules[i]}",
                    module=self.test_modules[i],
                    status='error',
                    duration=0.0,
                    error_message=str(result),
                    error_traceback=traceback.format_exc()
                )
                self.results.append(error_result)
            else:
                self.results.extend(result)
    
    async def _run_module_tests(self, module: str) -> List[TestResult]:
        """Run tests for a specific module."""
        module_results = []
        
        try:
            # Run pytest as subprocess to avoid event loop conflicts
            cmd = [
                sys.executable, '-m', 'pytest',
                '-v',
                '--tb=short',
                '--disable-warnings',
                module
            ]
            
            # Run pytest as subprocess
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            duration = time.time() - start_time
            exit_code = result.returncode
            
            # Create result based on pytest exit code
            module_name = Path(module).stem  # Extract filename without extension
            if exit_code == 0:
                status = 'passed'
                error_msg = None
            elif exit_code == 1:
                status = 'failed'
                error_msg = "Some tests failed"
            elif exit_code == 2:
                status = 'error'
                error_msg = "Test execution interrupted or error occurred"
            else:
                status = 'error'
                error_msg = f"Unexpected exit code: {exit_code}"
            
            result = TestResult(
                test_name=module_name,
                module=module,
                status=status,
                duration=duration,
                error_message=error_msg
            )
            module_results.append(result)
                
        except Exception as e:
            logger.error(f"Error running module {module}: {e}")
            error_result = TestResult(
                test_name=f"{module}_error",
                module=module,
                status='error',
                duration=0.0,
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
            module_results.append(error_result)
        
        return module_results
    
    async def _parse_pytest_report(self, report_file: Path, module: str) -> List[TestResult]:
        """Parse pytest JSON report into TestResult objects."""
        results = []
        
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            
            for test in report_data.get('tests', []):
                status_map = {
                    'PASSED': 'passed',
                    'FAILED': 'failed',
                    'SKIPPED': 'skipped',
                    'ERROR': 'error'
                }
                
                result = TestResult(
                    test_name=test.get('nodeid', 'unknown'),
                    module=module,
                    status=status_map.get(test.get('outcome', 'unknown'), 'unknown'),
                    duration=test.get('duration', 0.0),
                    error_message=test.get('call', {}).get('longrepr') if test.get('outcome') in ['FAILED', 'ERROR'] else None
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error parsing pytest report {report_file}: {e}")
            # Return fallback result
            results.append(TestResult(
                test_name=f"{module}_parse_error",
                module=module,
                status='error',
                duration=0.0,
                error_message=f"Failed to parse report: {e}"
            ))
        
        return results
    
    async def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for the report."""
        import platform
        
        try:
            import psutil
            
            # Get disk usage for Windows
            try:
                disk_usage = psutil.disk_usage('C:\\')
                disk_info = {
                    'total': disk_usage.total,
                    'used': disk_usage.used,
                    'free': disk_usage.free
                }
            except:
                disk_info = {'error': 'Could not get disk usage'}
            
            system_info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'disk_usage': disk_info,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add Focus Guard specific info
            try:
                from focus_guard import __version__
                system_info['focus_guard_version'] = __version__
            except:
                system_info['focus_guard_version'] = 'unknown'
            
            return system_info
            
        except Exception as e:
            logger.warning(f"Could not collect complete system info: {e}")
            return {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'error': str(e)
            }
    
    async def _pre_test_setup(self):
        """Setup before running tests."""
        logger.info("Performing pre-test setup")
        
        # Ensure test directories exist
        (self.output_dir / 'artifacts').mkdir(exist_ok=True)
        (self.output_dir / 'logs').mkdir(exist_ok=True)
        
        # Setup logging for test execution
        log_file = self.output_dir / 'logs' / 'test_execution.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.DEBUG)
    
    async def _post_test_cleanup(self):
        """Cleanup after running tests."""
        logger.info("Performing post-test cleanup")
        
        # Clean up any test artifacts that shouldn't persist
        # (Implementation depends on specific cleanup needs)
        pass
    
    def _generate_suite_result(self, system_info: Dict[str, Any]) -> TestSuiteResult:
        """Generate comprehensive test suite result."""
        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == 'passed')
        failed_tests = sum(1 for r in self.results if r.status == 'failed')
        skipped_tests = sum(1 for r in self.results if r.status == 'skipped')
        error_tests = sum(1 for r in self.results if r.status == 'error')
        
        total_duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0.0
        
        return TestSuiteResult(
            suite_name="Focus Guard Integration Test Suite",
            start_time=self.start_time.isoformat() if self.start_time else "",
            end_time=self.end_time.isoformat() if self.end_time else "",
            total_duration=total_duration,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            error_tests=error_tests,
            test_results=self.results,
            system_info=system_info
        )
    
    async def _save_reports(self, suite_result: TestSuiteResult):
        """Save test reports in multiple formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON Report
        json_report_file = self.output_dir / f'integration_test_report_{timestamp}.json'
        with open(json_report_file, 'w') as f:
            json.dump(asdict(suite_result), f, indent=2, default=str)
        
        logger.info(f"JSON report saved to: {json_report_file}")
        
        # HTML Report
        if self.config['generate_html_report']:
            html_report_file = self.output_dir / f'integration_test_report_{timestamp}.html'
            await self._generate_html_report(suite_result, html_report_file)
            logger.info(f"HTML report saved to: {html_report_file}")
        
        # CSV Summary
        csv_report_file = self.output_dir / f'integration_test_summary_{timestamp}.csv'
        await self._generate_csv_report(suite_result, csv_report_file)
        logger.info(f"CSV summary saved to: {csv_report_file}")
    
    async def _generate_html_report(self, suite_result: TestSuiteResult, output_file: Path):
        """Generate HTML test report."""
        html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Focus Guard Integration Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric.passed {{ background-color: #d4edda; }}
        .metric.failed {{ background-color: #f8d7da; }}
        .metric.skipped {{ background-color: #fff3cd; }}
        .test-results {{ margin-top: 20px; }}
        .test-item {{ border: 1px solid #ddd; margin: 5px 0; padding: 10px; border-radius: 3px; }}
        .test-item.passed {{ border-left: 5px solid #28a745; }}
        .test-item.failed {{ border-left: 5px solid #dc3545; }}
        .test-item.skipped {{ border-left: 5px solid #ffc107; }}
        .test-item.error {{ border-left: 5px solid #6f42c1; }}
        .error-details {{ background-color: #f8f9fa; padding: 10px; margin-top: 10px; font-family: monospace; font-size: 12px; }}
        .system-info {{ background-color: #f8f9fa; padding: 15px; margin-top: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Focus Guard Integration Test Report</h1>
        <p>Generated: {timestamp}</p>
        <p>Duration: {duration:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <div style="font-size: 24px; font-weight: bold;">{total_tests}</div>
        </div>
        <div class="metric passed">
            <h3>Passed</h3>
            <div style="font-size: 24px; font-weight: bold;">{passed_tests}</div>
        </div>
        <div class="metric failed">
            <h3>Failed</h3>
            <div style="font-size: 24px; font-weight: bold;">{failed_tests}</div>
        </div>
        <div class="metric skipped">
            <h3>Skipped</h3>
            <div style="font-size: 24px; font-weight: bold;">{skipped_tests}</div>
        </div>
    </div>
    
    <div class="test-results">
        <h2>Test Results</h2>
        {test_results_html}
    </div>
    
    <div class="system-info">
        <h2>System Information</h2>
        <pre>{system_info}</pre>
    </div>
</body>
</html>"""
        
        # Generate test results HTML
        test_results_html = ""
        for result in suite_result.test_results:
            error_html = ""
            if result.error_message:
                error_html = f'<div class="error-details">{result.error_message}</div>'
            
            test_results_html += f"""
            <div class="test-item {result.status}">
                <strong>{result.test_name}</strong> ({result.module})
                <span style="float: right;">{result.duration:.3f}s</span>
                <div>Status: {result.status.upper()}</div>
                {error_html}
            </div>
            """
        
        # Format system info
        system_info_str = json.dumps(suite_result.system_info, indent=2)
        
        # Generate final HTML
        html_content = html_template.format(
            timestamp=suite_result.end_time,
            duration=suite_result.total_duration,
            total_tests=suite_result.total_tests,
            passed_tests=suite_result.passed_tests,
            failed_tests=suite_result.failed_tests,
            skipped_tests=suite_result.skipped_tests,
            test_results_html=test_results_html,
            system_info=system_info_str
        )
        
        with open(output_file, 'w') as f:
            f.write(html_content)
    
    async def _generate_csv_report(self, suite_result: TestSuiteResult, output_file: Path):
        """Generate CSV summary report."""
        import csv
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Test Name', 'Module', 'Status', 'Duration (s)', 'Error Message'])
            
            # Test results
            for result in suite_result.test_results:
                writer.writerow([
                    result.test_name,
                    result.module,
                    result.status,
                    f"{result.duration:.3f}",
                    result.error_message or ""
                ])
    
    def _print_summary(self, suite_result: TestSuiteResult):
        """Print test summary to console."""
        print("\n" + "="*80)
        print("FOCUS GUARD INTEGRATION TEST SUITE SUMMARY")
        print("="*80)
        print(f"Total Tests: {suite_result.total_tests}")
        print(f"Passed: {suite_result.passed_tests}")
        print(f"Failed: {suite_result.failed_tests}")
        print(f"Skipped: {suite_result.skipped_tests}")
        print(f"Errors: {suite_result.error_tests}")
        print(f"Duration: {suite_result.total_duration:.2f} seconds")
        
        if suite_result.failed_tests > 0 or suite_result.error_tests > 0:
            print("\nFAILED/ERROR TESTS:")
            for result in suite_result.test_results:
                if result.status in ['failed', 'error']:
                    print(f"  - {result.test_name} ({result.status})")
                    if result.error_message:
                        print(f"    Error: {result.error_message[:100]}...")
        
        success_rate = (suite_result.passed_tests / suite_result.total_tests * 100) if suite_result.total_tests > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 95:
            print("STATUS: EXCELLENT")
        elif success_rate >= 85:
            print("STATUS: GOOD")
        elif success_rate >= 70:
            print("STATUS: ACCEPTABLE")
        else:
            print("STATUS: NEEDS ATTENTION")
        
        print("="*80)


async def main():
    """Main entry point for the test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Focus Guard Integration Test Suite")
    parser.add_argument('--output-dir', type=Path, help='Output directory for reports')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--no-coverage', action='store_true', help='Disable coverage collection')
    parser.add_argument('--no-html', action='store_true', help='Disable HTML report generation')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test suite
    suite = IntegrationTestSuite(output_dir=args.output_dir)
    
    # Configure based on arguments
    if args.parallel:
        suite.config['parallel_execution'] = True
    if args.no_coverage:
        suite.config['collect_coverage'] = False
    if args.no_html:
        suite.config['generate_html_report'] = False
    
    try:
        # Run the test suite
        result = await suite.run_all_tests()
        
        # Exit with appropriate code
        if result.failed_tests > 0 or result.error_tests > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
