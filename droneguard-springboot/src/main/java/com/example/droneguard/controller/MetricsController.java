package com.example.droneguard.controller;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class MetricsController {

    private final MeterRegistry meterRegistry;
    private final ThreadMXBean threadMXBean = ManagementFactory.getThreadMXBean();

    public MetricsController(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    @GetMapping("/metrics")
    public Map<String, Object> getMetrics() {
        Map<String, Object> springbootMetrics = new HashMap<>();

        // Health example - always true, replace with real health check
        springbootMetrics.put("healthy", true);

        // JVM memory used in MB
        double memUsedBytes = meterRegistry.get("jvm.memory.used")
                .tag("area", "heap")
                .gauge()
                .value();
        springbootMetrics.put("memory_mb", memUsedBytes / 1024.0 / 1024.0);

        // CPU usage approximation from system load average
        double cpuLoad = ManagementFactory.getOperatingSystemMXBean().getSystemLoadAverage();
        springbootMetrics.put("cpu_percent", cpuLoad);

        // Thread count (live threads)
        int threadCount = threadMXBean.getThreadCount();
        springbootMetrics.put("threads", threadCount);

        // Response time example using Timer metric, replace with actual timers if available
        Timer timer = meterRegistry.find("http.server.requests").timer();
        if (timer != null && timer.count() > 0) {
            springbootMetrics.put("response_time", (long) timer.mean(java.util.concurrent.TimeUnit.MILLISECONDS));
        } else {
            springbootMetrics.put("response_time", 0);
        }

        // FPS & detections are application specific, so placeholders for now
        springbootMetrics.put("fps", null); 
        springbootMetrics.put("detections", null);

        Map<String, Object> metrics = new HashMap<>();
        metrics.put("springboot", springbootMetrics);

        return metrics;
    }
}