"""
Virus Scanning Utility
Security service for malware detection and file sanitization.
"""

import logging
import hashlib
import requests
import os
from typing import Tuple, Dict, Any, Optional
from datetime import datetime, timedelta

from app.models.file_management import ScanStatus

logger = logging.getLogger(__name__)

class VirusScannerService:
    """Service for virus scanning and malware detection."""
    
    def __init__(self):
        """Initialize virus scanner service."""
        self.virustotal_api_key = os.getenv('VIRUSTOTAL_API_KEY')
        self.clamav_enabled = self._check_clamav_availability()
        
        # Cache for scan results (file hash -> result)
        self.scan_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(hours=24)  # Cache results for 24 hours
        
        logger.info(f"Virus scanner initialized - VirusTotal: {'Yes' if self.virustotal_api_key else 'No'}, ClamAV: {'Yes' if self.clamav_enabled else 'No'}")
    
    def _check_clamav_availability(self) -> bool:
        """Check if ClamAV is available on the system."""
        try:
            import subprocess
            result = subprocess.run(['clamscan', '--version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, ImportError):
            return False
    
    async def scan_file(self, file_data: bytes, filename: str) -> Tuple[ScanStatus, Dict[str, Any]]:
        """
        Comprehensive file scanning for malware.
        
        Args:
            file_data: File content as bytes
            filename: Original filename
            
        Returns:
            Tuple of (scan_status, scan_details)
        """
        try:
            # Calculate file hash for caching
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            # Check cache first
            cached_result = self._get_cached_result(file_hash)
            if cached_result:
                logger.info(f"Using cached scan result for file {filename}")
                return cached_result['status'], cached_result['details']
            
            scan_details = {
                'filename': filename,
                'file_hash': file_hash,
                'file_size': len(file_data),
                'scan_timestamp': datetime.utcnow().isoformat(),
                'scan_methods': [],
                'threats_detected': [],
                'scan_errors': []
            }
            
            overall_status = ScanStatus.CLEAN
            
            # 1. Basic heuristic scanning
            heuristic_result = await self._heuristic_scan(file_data, filename)
            scan_details['scan_methods'].append('heuristic')
            
            if heuristic_result['threats']:
                scan_details['threats_detected'].extend(heuristic_result['threats'])
                overall_status = ScanStatus.INFECTED
            
            # 2. ClamAV scanning (if available)
            if self.clamav_enabled:
                clamav_result = await self._clamav_scan(file_data)
                scan_details['scan_methods'].append('clamav')
                
                if clamav_result['status'] == ScanStatus.INFECTED:
                    scan_details['threats_detected'].extend(clamav_result['threats'])
                    overall_status = ScanStatus.INFECTED
                elif clamav_result['status'] == ScanStatus.ERROR:
                    scan_details['scan_errors'].append('ClamAV scan failed')
            
            # 3. VirusTotal scanning (if API key available)
            if self.virustotal_api_key:
                vt_result = await self._virustotal_scan(file_hash, file_data)
                scan_details['scan_methods'].append('virustotal')
                
                if vt_result['status'] == ScanStatus.INFECTED:
                    scan_details['threats_detected'].extend(vt_result['threats'])
                    overall_status = ScanStatus.INFECTED
                elif vt_result['status'] == ScanStatus.ERROR:
                    scan_details['scan_errors'].append('VirusTotal scan failed')
            
            # Cache the result
            self._cache_result(file_hash, overall_status, scan_details)
            
            logger.info(f"File scan completed: {filename} - Status: {overall_status.value}")
            
            return overall_status, scan_details
            
        except Exception as e:
            logger.error(f"Virus scan error: {str(e)}")
            return ScanStatus.ERROR, {
                'error': str(e),
                'scan_timestamp': datetime.utcnow().isoformat()
            }
    
    async def _heuristic_scan(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Basic heuristic scanning for common malware patterns."""
        threats = []
        
        try:
            # Check file extension vs content mismatch
            if self._check_extension_mismatch(file_data, filename):
                threats.append({
                    'type': 'suspicious_extension',
                    'description': 'File extension does not match content type'
                })
            
            # Check for suspicious patterns
            suspicious_patterns = self._check_suspicious_patterns(file_data)
            threats.extend(suspicious_patterns)
            
            # Check for embedded executables
            if self._check_embedded_executables(file_data):
                threats.append({
                    'type': 'embedded_executable',
                    'description': 'File contains embedded executable code'
                })
            
            # Check file entropy (high entropy might indicate encryption/packing)
            entropy = self._calculate_entropy(file_data)
            if entropy > 7.5:  # High entropy threshold
                threats.append({
                    'type': 'high_entropy',
                    'description': f'High file entropy ({entropy:.2f}) suggests encryption or packing',
                    'severity': 'low'
                })
            
        except Exception as e:
            logger.error(f"Heuristic scan error: {str(e)}")
        
        return {'threats': threats}
    
    def _check_extension_mismatch(self, file_data: bytes, filename: str) -> bool:
        """Check if file extension matches actual content."""
        try:
            import magic
            
            # Get actual MIME type
            actual_mime = magic.from_buffer(file_data, mime=True)
            
            # Get extension
            ext = os.path.splitext(filename)[1].lower()
            
            # Common extension to MIME type mappings
            ext_mime_map = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.gif': 'image/gif',
                '.pdf': 'application/pdf', '.txt': 'text/plain',
                '.zip': 'application/zip', '.exe': 'application/x-executable'
            }
            
            expected_mime = ext_mime_map.get(ext)
            
            # Check for mismatch
            if expected_mime and actual_mime != expected_mime:
                # Some exceptions for common cases
                if ext == '.jpg' and actual_mime == 'image/jpeg':
                    return False
                return True
            
        except Exception:
            pass
        
        return False
    
    def _check_suspicious_patterns(self, file_data: bytes) -> list:
        """Check for suspicious patterns in file content."""
        threats = []
        
        # Convert to lowercase for pattern matching
        content_lower = file_data[:10240].lower()  # Check first 10KB
        
        # Suspicious patterns
        patterns = {
            'script_injection': [b'<script', b'javascript:', b'vbscript:'],
            'php_code': [b'<?php', b'<?='],
            'shell_commands': [b'#!/bin/sh', b'#!/bin/bash', b'/bin/sh'],
            'suspicious_urls': [b'http://bit.ly', b'tinyurl.com'],
            'base64_encoded': [b'data:application/', b'data:text/'],
            'macro_code': [b'auto_open', b'document_open', b'workbook_open']
        }
        
        for threat_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if pattern in content_lower:
                    threats.append({
                        'type': threat_type,
                        'description': f'Suspicious pattern detected: {pattern.decode("utf-8", errors="ignore")}',
                        'severity': 'medium'
                    })
                    break  # Only report once per threat type
        
        return threats
    
    def _check_embedded_executables(self, file_data: bytes) -> bool:
        """Check for embedded executable signatures."""
        # PE (Windows executable) signature
        if b'MZ' in file_data[:2] or b'PE\x00\x00' in file_data:
            return True
        
        # ELF (Linux executable) signature
        if file_data[:4] == b'\x7fELF':
            return True
        
        # Mach-O (macOS executable) signatures
        if file_data[:4] in [b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf', b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe']:
            return True
        
        return False
    
    def _calculate_entropy(self, file_data: bytes) -> float:
        """Calculate Shannon entropy of file data."""
        if not file_data:
            return 0.0
        
        # Count byte frequencies
        byte_counts = [0] * 256
        for byte in file_data:
            byte_counts[byte] += 1
        
        # Calculate entropy
        entropy = 0.0
        file_size = len(file_data)
        
        for count in byte_counts:
            if count > 0:
                probability = count / file_size
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy
    
    async def _clamav_scan(self, file_data: bytes) -> Dict[str, Any]:
        """Scan file using ClamAV."""
        try:
            import subprocess
            import tempfile
            
            # Write file to temporary location
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(file_data)
                tmp_path = tmp_file.name
            
            try:
                # Run ClamAV scan
                result = subprocess.run(
                    ['clamscan', '--no-summary', tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Parse result
                if result.returncode == 0:
                    return {'status': ScanStatus.CLEAN, 'threats': []}
                elif result.returncode == 1:
                    # Infected
                    threats = []
                    for line in result.stdout.split('\n'):
                        if 'FOUND' in line:
                            threat_name = line.split(':')[-1].strip().replace(' FOUND', '')
                            threats.append({
                                'type': 'virus',
                                'name': threat_name,
                                'scanner': 'clamav'
                            })
                    return {'status': ScanStatus.INFECTED, 'threats': threats}
                else:
                    return {'status': ScanStatus.ERROR, 'threats': []}
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_path)
                
        except Exception as e:
            logger.error(f"ClamAV scan error: {str(e)}")
            return {'status': ScanStatus.ERROR, 'threats': []}
    
    async def _virustotal_scan(self, file_hash: str, file_data: bytes) -> Dict[str, Any]:
        """Scan file using VirusTotal API."""
        try:
            # First, check if hash is already known to VirusTotal
            report_url = f"https://www.virustotal.com/vtapi/v2/file/report"
            
            params = {
                'apikey': self.virustotal_api_key,
                'resource': file_hash
            }
            
            response = requests.get(report_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['response_code'] == 1:
                    # File already scanned
                    return self._parse_virustotal_result(data)
                elif data['response_code'] == 0:
                    # File not in database, upload for scanning
                    return await self._upload_to_virustotal(file_data)
            
            return {'status': ScanStatus.ERROR, 'threats': []}
            
        except Exception as e:
            logger.error(f"VirusTotal scan error: {str(e)}")
            return {'status': ScanStatus.ERROR, 'threats': []}
    
    async def _upload_to_virustotal(self, file_data: bytes) -> Dict[str, Any]:
        """Upload file to VirusTotal for scanning."""
        try:
            # Don't upload large files to VirusTotal in production
            if len(file_data) > 32 * 1024 * 1024:  # 32MB limit
                return {'status': ScanStatus.ERROR, 'threats': []}
            
            scan_url = "https://www.virustotal.com/vtapi/v2/file/scan"
            
            files = {'file': ('sample', file_data)}
            params = {'apikey': self.virustotal_api_key}
            
            response = requests.post(scan_url, files=files, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # In real implementation, you'd need to poll for results
                # For now, return pending status
                return {'status': ScanStatus.PENDING, 'threats': []}
            
            return {'status': ScanStatus.ERROR, 'threats': []}
            
        except Exception as e:
            logger.error(f"VirusTotal upload error: {str(e)}")
            return {'status': ScanStatus.ERROR, 'threats': []}
    
    def _parse_virustotal_result(self, vt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse VirusTotal scan results."""
        try:
            positives = vt_data.get('positives', 0)
            total = vt_data.get('total', 0)
            
            if positives == 0:
                return {'status': ScanStatus.CLEAN, 'threats': []}
            
            # Extract threat information
            threats = []
            scans = vt_data.get('scans', {})
            
            for scanner, result in scans.items():
                if result.get('detected'):
                    threats.append({
                        'type': 'virus',
                        'name': result.get('result', 'Unknown'),
                        'scanner': scanner,
                        'engine_version': result.get('version', 'Unknown')
                    })
            
            return {'status': ScanStatus.INFECTED, 'threats': threats}
            
        except Exception as e:
            logger.error(f"VirusTotal result parsing error: {str(e)}")
            return {'status': ScanStatus.ERROR, 'threats': []}
    
    def _get_cached_result(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached scan result if available and not expired."""
        if file_hash in self.scan_cache:
            cached = self.scan_cache[file_hash]
            cached_time = datetime.fromisoformat(cached['timestamp'])
            
            if datetime.utcnow() - cached_time < self.cache_ttl:
                return cached
            else:
                # Remove expired cache entry
                del self.scan_cache[file_hash]
        
        return None
    
    def _cache_result(self, file_hash: str, status: ScanStatus, details: Dict[str, Any]):
        """Cache scan result."""
        self.scan_cache[file_hash] = {
            'status': status,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Limit cache size (keep last 1000 entries)
        if len(self.scan_cache) > 1000:
            # Remove oldest entries
            sorted_items = sorted(
                self.scan_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            
            for file_hash, _ in sorted_items[:100]:  # Remove oldest 100
                del self.scan_cache[file_hash]
    
    def get_scan_statistics(self) -> Dict[str, Any]:
        """Get virus scanning statistics."""
        total_scans = len(self.scan_cache)
        clean_files = sum(1 for cached in self.scan_cache.values() if cached['status'] == ScanStatus.CLEAN)
        infected_files = sum(1 for cached in self.scan_cache.values() if cached['status'] == ScanStatus.INFECTED)
        
        return {
            'total_scans': total_scans,
            'clean_files': clean_files,
            'infected_files': infected_files,
            'error_scans': total_scans - clean_files - infected_files,
            'cache_size': len(self.scan_cache),
            'scanners_available': {
                'heuristic': True,
                'clamav': self.clamav_enabled,
                'virustotal': bool(self.virustotal_api_key)
            }
        }
