import sys
import unittest
import platform
import logging
import subprocess
from typing import Dict, Tuple
from unittest import skipIf
from packaging import version  # Fix: import version directly
import torch
import os  # Added for environment variable checks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnvironmentTests(unittest.TestCase):
    """Test suite for verifying environment setup and dependencies."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.required_packages = {
            'torch': '2.0.1',
            'torchvision': '0.15.2',
            'torchaudio': '2.0.1',
            'numpy': '1.21.0'  # Added numpy as an example
        }
        cls.required_env_vars = ['HOME', 'PATH']  # Example environment variables
        cls._check_package_installations()

    @classmethod
    def _check_package_installations(cls):
        """Verify package installations and compatibility"""
        cls.installed_packages = {}
        for package in cls.required_packages:
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'show', package],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Version: '):
                            cls.installed_packages[package] = line.split(': ')[1]
                            break
            except Exception as e:
                logger.warning(f"Failed to check {package} installation: {e}")

    def test_python_version(self):
        """Verify Python version is 3.8+"""
        major, minor = sys.version_info[:2]
        msg = f"Python version {major}.{minor} detected"
        self.assertGreaterEqual(major, 3, msg)
        self.assertGreaterEqual(minor, 8, msg)
        logger.info(f"Python version check passed: {major}.{minor}")

    def test_core_imports(self):
        """Test all core framework imports and versions"""
        versions: Dict[str, str] = {}
        
        # First verify torch installation
        try:
            import torch
            versions['torch'] = torch.__version__
            # Verify minimum version instead of exact match
            assert version.parse(torch.__version__) >= version.parse("2.0.0")  # Fix: use version directly
        except ImportError as e:
            self.fail(f"Failed to import torch: {str(e)}")
        except AssertionError:
            self.fail(f"PyTorch version {torch.__version__} is too old. Minimum required is 2.0.0")

        # Then try importing vision and audio if torch is available
        if 'torch' in versions:
            for package in ['torchvision', 'torchaudio']:
                try:
                    if package in sys.modules:
                        del sys.modules[package]
                    module = __import__(package)
                    versions[package] = module.__version__
                except ImportError as e:
                    logger.warning(f"Optional package {package} import failed: {str(e)}")
                except RuntimeError as e:
                    logger.warning(f"Runtime error importing {package}: {str(e)}")
                except Exception as e:
                    logger.warning(f"Unexpected error importing {package}: {str(e)}")

        # Verify at least torch is available
        self.assertIn('torch', versions, "PyTorch must be installed")
        
        # Log detected versions
        logger.info("Detected package versions: %s", versions)
        logger.info("Required package versions: %s", self.required_packages)

    @skipIf(not torch.cuda.is_available(), "CUDA not available")
    def test_hardware_detection(self):
        """Test hardware detection and GPU configuration"""
        try:
            import torch
            
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                device_count = torch.cuda.device_count()
                device_names = [torch.cuda.get_device_name(i) for i in range(device_count)]
                logger.info("CUDA devices available: %d", device_count)
                logger.info("Device names: %s", device_names)
                
                # Test CUDA memory allocation
                for i in range(device_count):
                    torch.cuda.set_device(i)
                    try:
                        # Attempt to allocate and free memory
                        x = torch.ones(1000, 1000, device=f'cuda:{i}')
                        del x
                        torch.cuda.empty_cache()
                        logger.info(f"CUDA:{i} memory test passed")
                    except RuntimeError as e:
                        logger.error(f"CUDA:{i} memory test failed: {str(e)}")
                        raise
            else:
                logger.warning("CUDA is not available, running on CPU only")
                
        except Exception as e:
            self.fail(f"Hardware detection failed: {str(e)}")

    def test_memory_allocation(self):
        """Test memory operations on both CPU and available GPUs"""
        import torch
        
        test_sizes = [(1000, 1000), (2000, 2000)]
        devices = ['cpu'] + [f'cuda:{i}' for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else ['cpu']
        
        for device in devices:
            for size in test_sizes:
                try:
                    x = torch.ones(size, device=device)
                    self.assertEqual(x.shape, size, f"Shape mismatch on {device}")
                    del x
                    if 'cuda' in device:
                        torch.cuda.empty_cache()
                except Exception as e:
                    self.fail(f"Memory allocation failed on {device} with size {size}: {str(e)}")
                logger.info(f"Memory test passed for {device} with size {size}")

    def test_framework_compatibility(self):
        """Verify framework compatibility and configurations"""
        import torch
        
        # Basic torch configuration checks
        self.assertTrue(hasattr(torch, '_C'), "PyTorch C++ extension not available")
        
        if torch.cuda.is_available():
            self.assertTrue(torch.backends.cudnn.enabled, "cuDNN not enabled")
            for i in range(torch.cuda.device_count()):
                cap = torch.cuda.get_device_capability(i)
                logger.info(f"CUDA capability for device {i}: {cap}")
        else:
            logger.warning("CUDA not available - running CPU only tests")

        # Verify torch can perform basic operations
        try:
            x = torch.randn(2, 2)
            y = torch.matmul(x, x)
            self.assertEqual(y.shape, (2, 2))
        except Exception as e:
            self.fail(f"Basic torch operations failed: {str(e)}")

    def test_environment_configurations(self):
        """Test different environment configurations"""
        import torch

        configurations = [
            {'device': 'cpu', 'dtype': torch.float32},
            {'device': 'cpu', 'dtype': torch.float64},
        ]

        if torch.cuda.is_available():
            configurations.extend([
                {'device': f'cuda:{i}', 'dtype': torch.float32} for i in range(torch.cuda.device_count())
            ])

        for config in configurations:
            try:
                x = torch.ones((1000, 1000), device=config['device'], dtype=config['dtype'])
                self.assertEqual(x.dtype, config['dtype'], f"Dtype mismatch on {config['device']}")
                del x
                if 'cuda' in config['device']:
                    torch.cuda.empty_cache()
            except Exception as e:
                self.fail(f"Configuration test failed on {config['device']} with dtype {config['dtype']}: {str(e)}")
            logger.info(f"Configuration test passed for {config['device']} with dtype {config['dtype']}")

    def test_dependency_installation(self):
        """Ensure all dependencies are correctly installed and compatible"""
        for package, required_version in self.required_packages.items():
            installed_version = self.installed_packages.get(package)
            self.assertIsNotNone(installed_version, f"{package} is not installed")
            self.assertGreaterEqual(version.parse(installed_version), version.parse(required_version),
                                    f"{package} version {installed_version} is too old. Minimum required is {required_version}")

    def test_error_handling_and_logging(self):
        """Improve error handling and logging for better debugging"""
        try:
            import torch
            x = torch.ones((1000, 1000), device='cpu')
            self.assertEqual(x.shape, (1000, 1000))
        except Exception as e:
            logger.error(f"Error during tensor creation: {str(e)}")
            self.fail(f"Error during tensor creation: {str(e)}")

        try:
            import torch
            if torch.cuda.is_available():
                x = torch.ones((1000, 1000), device='cuda:0')
                self.assertEqual(x.shape, (1000, 1000))
        except RuntimeError as e:
            logger.error(f"CUDA error during tensor creation: {str(e)}")
            self.fail(f"CUDA error during tensor creation: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during tensor creation: {str(e)}")
            self.fail(f"Unexpected error during tensor creation: {str(e)}")

    def test_environment_variables(self):
        """Verify essential environment variables are set"""
        for var in self.required_env_vars:
            value = os.getenv(var)
            self.assertIsNotNone(value, f"Environment variable '{var}' is not set")
            logger.info(f"Environment variable '{var}': {value}")

if __name__ == '__main__':
    logger.info("Starting environment tests")
    logger.info(f"Platform: {platform.platform()}")
    unittest.main(verbosity=2)
