"""
DroneGuard Performance Comparison Dashboard
Combines performance monitoring and comparison dashboard into one Flask app
"""

import psutil
import time
import requests
import threading
import json
import logging
import csv
import os
from datetime import datetime
from flask import Flask, jsonify, render_template, send_file
from flask_cors import CORS
from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessMetrics:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    threads: int
    status: str

@dataclass
class SystemMetrics:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    memory_used_gb: float

@dataclass
class AppMetrics:
    app_name: str
    url: str
    response_time_ms: float
    status_code: int
    is_healthy: bool
    fps: Optional[float] = None
    frame_count: Optional[int] = None
    detections: Optional[int] = None

class PerformanceMonitor:
    def __init__(self):
        self.system_metrics = deque(maxlen=300)  # 5 minutes at 1Hz
        self.app_metrics = {
            'fastapi': deque(maxlen=100),
            'springboot': deque(maxlen=100)
        }
        self.process_metrics = {}
        
        # CSV export storage
        self.csv_data = []
        self.csv_lock = threading.Lock()
        
        self.monitoring = False
        self.monitor_thread = None
        
        # Get CPU core count for normalization
        self.cpu_cores = psutil.cpu_count()
        logger.info(f"System has {self.cpu_cores} CPU cores")
        
        # Create exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        # Auto-export setup - create timestamped filename when app starts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.auto_export_filename = f"performance_metrics_{timestamp}.csv"
        self.auto_export_filepath = os.path.join('exports', self.auto_export_filename)
        self.csv_headers_written = False
        logger.info(f"Auto-export will save to: {self.auto_export_filepath}")
        
        # Application configurations
        self.apps = {
            'fastapi': {
                'name': 'FastAPI DroneGuard',
                'port': 8000,
                'health_url': 'http://localhost:8000/health',
                'info_url': 'http://localhost:8000/info',
                'status_url': 'http://localhost:8000/api/video/status',
                'process_keywords': ['run.py', 'python']
            },
            'springboot': {
                'name': 'Spring Boot DroneGuard',
                'port': 8080,
                'health_url': 'http://localhost:8080/actuator/health',      
                'info_url': 'http://localhost:8080/actuator/info',          
                'status_url': 'http://localhost:8080/video/status',         
                'process_keywords': ['mvn', 'maven', 'java', 'spring-boot:run', 'org.springframework.boot']
            }
        }
    
    def start_monitoring(self):
        """Start the monitoring process"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                self.system_metrics.append(system_metrics)
                
                # Collect application metrics
                for app_key, app_config in self.apps.items():
                    app_metrics = self._collect_app_metrics(app_key, app_config)
                    self.app_metrics[app_key].append(app_metrics)
                
                # Collect process metrics
                self._collect_process_metrics()
                
                # Store aggregated data for CSV export
                aggregated_metrics = self.get_aggregated_metrics()
                self._store_csv_data(aggregated_metrics)
                
                time.sleep(1)  # 1 Hz monitoring
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system-wide metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)  # Use small interval for accurate reading
        memory = psutil.virtual_memory()
        
        return SystemMetrics(
            timestamp=time.time(),
            cpu_percent=round(cpu_percent, 2),
            memory_percent=round(memory.percent, 2),
            memory_available_gb=round(memory.available / 1024 / 1024 / 1024, 2),
            memory_used_gb=round(memory.used / 1024 / 1024 / 1024, 2),
        )
    
    def _collect_app_metrics(self, app_key: str, app_config: Dict) -> AppMetrics:
        """Collect metrics for a specific application"""
        start_time = time.time()
        
        try:
            # Health check
            response = requests.get(app_config['health_url'], timeout=5)
            response_time = (time.time() - start_time) * 1000
            status_code = response.status_code
            is_healthy = status_code == 200
            
        except requests.RequestException:
            response_time = (time.time() - start_time) * 1000
            status_code = 0
            is_healthy = False
        
        return AppMetrics(
            app_name=app_config['name'],
            url=app_config['health_url'],
            response_time_ms=response_time,
            status_code=status_code,
            is_healthy=is_healthy
        )
    
    def _collect_process_metrics(self):
        """Collect metrics for application processes"""
        self.process_metrics = {}
        
        for app_key, app_config in self.apps.items():
            processes = []
            
            # Debug: Log what we're looking for
            logger.info(f"Looking for {app_key} processes with keywords: {app_config['process_keywords']}")
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                    
                    # More specific matching logic
                    is_match = False
                    
                    if app_key == 'fastapi':
                        # Look specifically for "python run.py" and exclude dashboard.py
                        is_match = (
                            'run.py' in cmdline and 
                            'python' in cmdline.lower() and 
                            'dashboard.py' not in cmdline and
                            'vscode' not in cmdline.lower() and
                            'Code Helper' not in proc_info['name']
                        )
                    
                    elif app_key == 'springboot':
                        # Look for the actual Java process running Spring Boot
                        # Either Maven command or direct Java with Spring Boot classes
                        is_match = (
                            # Direct Java process with Spring Boot
                            ('java' in proc_info['name'].lower() and 
                             ('springframework' in cmdline or 'spring-boot' in cmdline or
                              'org.springframework.boot' in cmdline)) or
                            # Maven wrapper process  
                            ('mvn' in cmdline.lower() and 'spring-boot:run' in cmdline) or
                            # Maven daemon or forked Java process
                            ('java' in proc_info['name'].lower() and 
                             ('maven' in cmdline.lower() or 'mvn' in cmdline.lower()))
                        )
                    
                    if is_match:
                        # Log found process for debugging
                        logger.info(f"Found {app_key} process: PID={proc_info['pid']}, Name={proc_info['name']}, CMD={cmdline[:100]}...")
                        
                        # Get detailed process metrics
                        process = psutil.Process(proc_info['pid'])
                        
                        # Call cpu_percent() with interval to get accurate reading
                        cpu_percent = process.cpu_percent(interval=0.1)
                        
                        memory_info = process.memory_info()
                        memory_mb = memory_info.rss / 1024 / 1024
                        memory_percent = process.memory_percent()
                        
                        processes.append(ProcessMetrics(
                            pid=proc_info['pid'],
                            name=proc_info['name'],
                            cpu_percent=round(cpu_percent, 2),  # Keep raw value for now
                            memory_mb=round(memory_mb, 2),
                            memory_percent=round(memory_percent, 2),
                            threads=process.num_threads(),
                            status=process.status()
                        ))
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    continue
            
            if not processes:
                logger.warning(f"No processes found for {app_key}")
            else:
                logger.info(f"Found {len(processes)} processes for {app_key}")
            
            self.process_metrics[app_key] = processes
    
    def _store_csv_data(self, metrics_data: Dict):
        """Store metrics data for CSV export and auto-save to file"""
        with self.csv_lock:
            timestamp = datetime.now().isoformat()
            
            # Flatten the metrics data for CSV
            row = {
                'timestamp': timestamp,
                'system_cpu_percent': metrics_data.get('system', {}).get('cpu_percent', 0),
                'system_memory_percent': metrics_data.get('system', {}).get('memory_percent', 0),
                'system_memory_used_gb': metrics_data.get('system', {}).get('memory_used_gb', 0),
                'system_memory_available_gb': metrics_data.get('system', {}).get('memory_available_gb', 0),
                'fastapi_healthy': metrics_data.get('fastapi', {}).get('healthy', False),
                'fastapi_response_time_ms': metrics_data.get('fastapi', {}).get('response_time', 0),
                'fastapi_cpu_percent': metrics_data.get('fastapi', {}).get('cpu_percent', 0),
                'fastapi_cpu_percent_raw': metrics_data.get('fastapi', {}).get('cpu_percent_raw', 0),
                'fastapi_cores_used': metrics_data.get('fastapi', {}).get('cores_used', 0),
                'fastapi_memory_mb': metrics_data.get('fastapi', {}).get('memory_mb', 0),
                'fastapi_threads': metrics_data.get('fastapi', {}).get('threads', 0),
                'springboot_healthy': metrics_data.get('springboot', {}).get('healthy', False),
                'springboot_response_time_ms': metrics_data.get('springboot', {}).get('response_time', 0),
                'springboot_cpu_percent': metrics_data.get('springboot', {}).get('cpu_percent', 0),
                'springboot_cpu_percent_raw': metrics_data.get('springboot', {}).get('cpu_percent_raw', 0),
                'springboot_cores_used': metrics_data.get('springboot', {}).get('cores_used', 0),
                'springboot_memory_mb': metrics_data.get('springboot', {}).get('memory_mb', 0),
                'springboot_threads': metrics_data.get('springboot', {}).get('threads', 0),
            }
            
            self.csv_data.append(row)
            
            # Auto-save to file immediately
            self._auto_save_to_csv(row)
            
            # Keep only last 1000 records in memory to prevent memory bloat
            if len(self.csv_data) > 1000:
                self.csv_data = self.csv_data[-1000:]
    
    def _auto_save_to_csv(self, row: Dict):
        """Automatically save each row to CSV file as it's collected"""
        try:
            # Write headers if this is the first row
            if not self.csv_headers_written:
                with open(self.auto_export_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=list(row.keys()))
                    writer.writeheader()
                self.csv_headers_written = True
                logger.info(f"Created auto-export CSV: {self.auto_export_filepath}")
            
            # Append the new row
            with open(self.auto_export_filepath, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=list(row.keys()))
                writer.writerow(row)
                
        except Exception as e:
            logger.error(f"Error auto-saving to CSV: {e}")
    
    def export_to_csv(self, filename: Optional[str] = None) -> str:
        """Export collected metrics to CSV file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_metrics_{timestamp}.csv"
        
        filepath = os.path.join('exports', filename)
        
        with self.csv_lock:
            if not self.csv_data:
                raise ValueError("No data to export")
            
            fieldnames = list(self.csv_data[0].keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.csv_data)
        
        logger.info(f"Exported {len(self.csv_data)} records to {filepath}")
        return filepath
    
    def get_current_metrics(self) -> Dict:
        """Get current performance metrics"""
        return {
            'system': asdict(self.system_metrics[-1]) if self.system_metrics else None,
            'applications': {
                app_key: asdict(metrics[-1]) if metrics else None
                for app_key, metrics in self.app_metrics.items()
            },
            'processes': {
                app_key: [asdict(proc) for proc in processes]
                for app_key, processes in self.process_metrics.items()
            },
            'timestamp': time.time()
        }
    
    def get_historical_metrics(self, minutes: int = 5) -> Dict:
        """Get historical metrics for the specified number of minutes"""
        cutoff_time = time.time() - (minutes * 60)
        
        # Filter system metrics
        historical_system = [
            asdict(metric) for metric in self.system_metrics 
            if metric.timestamp >= cutoff_time
        ]
        
        # Filter application metrics
        historical_apps = {}
        for app_key, metrics in self.app_metrics.items():
            historical_apps[app_key] = [
                asdict(metric) for metric in metrics 
                # App metrics don't have timestamp, so we'll take the last N records
            ][-minutes:] if metrics else []
        
        return {
            'system': historical_system,
            'applications': historical_apps,
            'minutes': minutes,
            'timestamp': time.time()
        }
    
    def get_aggregated_metrics(self) -> Dict:
        """Get aggregated metrics for dashboard display"""
        current = self.get_current_metrics()
        
        # Aggregate metrics for each app
        result = {
            'timestamp': time.time(),
            'system': current.get('system'),
            'fastapi': None,
            'springboot': None
        }
        
        # Aggregate FastAPI metrics
        app_data = current.get('applications', {}).get('fastapi')
        process_data = current.get('processes', {}).get('fastapi', [])
        
        if app_data or process_data:
            # Sum process metrics
            total_cpu_raw = sum(p.get('cpu_percent', 0) for p in process_data)
            total_memory = sum(p.get('memory_mb', 0) for p in process_data)
            total_threads = sum(p.get('threads', 0) for p in process_data)
            
            # Normalize CPU to percentage of single core (divide by number of cores)
            normalized_cpu = round(total_cpu_raw / self.cpu_cores, 2) if self.cpu_cores > 0 else total_cpu_raw
            
            result['fastapi'] = {
                'healthy': app_data.get('is_healthy', False) if app_data else False,
                'response_time': app_data.get('response_time_ms', 0) if app_data else 0,
                'cpu_percent': normalized_cpu,
                'cpu_percent_raw': round(total_cpu_raw, 2),  # Also include raw value
                'cores_used': round(total_cpu_raw / 100, 2),  # How many cores equivalent
                'memory_mb': total_memory,
                'threads': total_threads,
            }
        
        # Aggregate Spring Boot metrics
        app_data = current.get('applications', {}).get('springboot')
        process_data = current.get('processes', {}).get('springboot', [])
        
        if app_data or process_data:
            # Sum process metrics
            total_cpu_raw = sum(p.get('cpu_percent', 0) for p in process_data)
            total_memory = sum(p.get('memory_mb', 0) for p in process_data)
            total_threads = sum(p.get('threads', 0) for p in process_data)
            
            # Normalize CPU to percentage of single core
            normalized_cpu = round(total_cpu_raw / self.cpu_cores, 2) if self.cpu_cores > 0 else total_cpu_raw
            
            result['springboot'] = {
                'healthy': app_data.get('is_healthy', False) if app_data else False,
                'response_time': app_data.get('response_time_ms', 0) if app_data else 0,
                'cpu_percent': normalized_cpu,
                'cpu_percent_raw': round(total_cpu_raw, 2),  # Also include raw value
                'cores_used': round(total_cpu_raw / 100, 2),  # How many cores equivalent
                'memory_mb': total_memory,
                'threads': total_threads,
            }
            
        return result

# Flask app setup
app = Flask(__name__)
CORS(app)
monitor = PerformanceMonitor()

# Configuration
FASTAPI_URL = "http://localhost:8000"
SPRINGBOOT_URL = "http://localhost:8080" 

@app.route('/api/export/csv')
def api_export_csv():
    """API endpoint to trigger CSV export and return download info"""
    try:
        filepath = monitor.export_to_csv()
        filename = os.path.basename(filepath)
        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': f'/export/csv/{filename}',
            'records_exported': len(monitor.csv_data)
        })
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Routes for CSV export
@app.route('/export/csv')
@app.route('/export/csv/<filename>')
def export_csv(filename=None):
    """Export current metrics data to CSV"""
    try:
        filepath = monitor.export_to_csv(filename)
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/export/info')
def export_info():
    """Get information about available export data"""
    with monitor.csv_lock:
        return jsonify({
            'records_available': len(monitor.csv_data),
            'oldest_record': monitor.csv_data[0]['timestamp'] if monitor.csv_data else None,
            'newest_record': monitor.csv_data[-1]['timestamp'] if monitor.csv_data else None
        })

# Routes for dashboard
@app.route('/')
def dashboard():
    """Serve the comparison dashboard"""
    return render_template('index.html')

@app.route('/api/metrics')
def get_metrics():
    """Get aggregated metrics for dashboard display"""
    try:
        metrics = monitor.get_aggregated_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({
            'error': 'Failed to collect metrics',
            'timestamp': time.time(),
            'system': None,
            'fastapi': None,
            'springboot': None
        })

# Routes for debugging
@app.route('/debug/processes')
def debug_processes():
    """Debug endpoint to see all processes and what's being detected"""
    all_processes = []
    detected_processes = {'fastapi': [], 'springboot': []}
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            proc_info = proc.info
            cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
            
            # Add to all processes list (limit to relevant ones)
            if any(keyword in cmdline.lower() or keyword in proc_info['name'].lower() 
                   for keyword in ['python', 'java', 'uvicorn', 'spring', 'fastapi']):
                all_processes.append({
                    'pid': proc_info['pid'],
                    'name': proc_info['name'],
                    'cmdline': cmdline[:200] + '...' if len(cmdline) > 200 else cmdline
                })
            
            # Check what gets detected for each app
            for app_key, app_config in monitor.apps.items():
                port_match = f":{app_config['port']}" in cmdline
                keyword_match = any(keyword in cmdline.lower() or keyword in proc_info['name'].lower() 
                                  for keyword in app_config['process_keywords'])
                
                if keyword_match or port_match:
                    detected_processes[app_key].append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cmdline': cmdline[:200] + '...' if len(cmdline) > 200 else cmdline,
                        'matched_by': 'port' if port_match else 'keyword'
                    })
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return jsonify({
        'all_relevant_processes': all_processes,
        'detected_processes': detected_processes,
        'search_config': monitor.apps
    })

# Routes for performance monitor API compatibility
@app.route('/metrics/current')
def current_metrics():
    """Get current performance metrics (monitor API compatibility)"""
    return jsonify(monitor.get_current_metrics())

@app.route('/metrics/history')
@app.route('/metrics/history/<int:minutes>')
def historical_metrics(minutes=5):
    """Get historical performance metrics"""
    return jsonify(monitor.get_historical_metrics(minutes))

@app.route('/start')
def start_monitoring():
    """Start performance monitoring"""
    monitor.start_monitoring()
    return jsonify({"status": "started"})

@app.route('/stop') 
def stop_monitoring():
    """Stop performance monitoring"""
    monitor.stop_monitoring()
    return jsonify({"status": "stopped"})

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "monitoring": monitor.monitoring
    })

if __name__ == "__main__":
    print("🛡️ DroneGuard Unified Dashboard starting...")
    print("🌐 Dashboard: http://localhost:3000")
    print("📊 Metrics API: http://localhost:3000/api/metrics")
    print("📈 Historical data: http://localhost:3000/metrics/history")
    print("\nMake sure the following services are running:")
    print(f"  - FastAPI App: {FASTAPI_URL}")
    print(f"  - Spring Boot App: {SPRINGBOOT_URL}")
    print("\n🔍 Starting performance monitoring...")
    
    # Start monitoring automatically
    monitor.start_monitoring()
    
    try:
        app.run(host='0.0.0.0', port=3000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        monitor.stop_monitoring()