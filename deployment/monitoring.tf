# Monitoring and Alerting Configuration
resource "google_monitoring_dashboard" "guruai_dashboard" {
  dashboard_json = jsonencode({
    displayName = "GuruAI Backend Monitoring"
    mosaicLayout = {
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "API Response Times"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"guruai-backend\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Response Time (ms)"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Error Rate"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.response_code_class"]
                    }
                  }
                }
                plotType = "STACKED_AREA"
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Request Volume"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Memory Usage"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/memory/utilizations\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "CPU Usage"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/cpu/utilizations\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Active Instances"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/instance_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        }
      ]
    }
  })
}

# Alert Policies
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate"
  description  = "Alert when error rate exceeds 1%"
  
  conditions {
    display_name = "Error rate > 1%"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.01
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["metric.label.response_code_class"]
      }
    }
  }
  
  alert_strategy {
    auto_close = "1800s"
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.name,
    google_monitoring_notification_channel.slack.name
  ]
}

resource "google_monitoring_alert_policy" "high_response_time" {
  display_name = "High Response Time"
  description  = "Alert when response time exceeds targets"
  
  conditions {
    display_name = "Response time > 2s for chat endpoints"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 2000  # 2 seconds in milliseconds
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.name
  ]
}

resource "google_monitoring_alert_policy" "memory_usage" {
  display_name = "High Memory Usage"
  description  = "Alert when memory usage exceeds 80%"
  
  conditions {
    display_name = "Memory usage > 80%"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/memory/utilizations\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.8
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.name
  ]
}

resource "google_monitoring_alert_policy" "ai_service_failure" {
  display_name = "AI Service Failures"
  description  = "Alert when AI service calls fail frequently"
  
  conditions {
    display_name = "AI service error rate > 5%"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.label.endpoint=~\".*/(chat|generate|analyze).*\""
      duration        = "180s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.05
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_MEAN"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.name,
    google_monitoring_notification_channel.slack.name
  ]
}

resource "google_monitoring_alert_policy" "cost_threshold" {
  display_name = "Cost Threshold Alert"
  description  = "Alert when daily costs exceed threshold"
  
  conditions {
    display_name = "Daily cost > $500"
    
    condition_threshold {
      filter          = "metric.type=\"billing.googleapis.com/billing/total_cost\""
      duration        = "3600s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 500
      
      aggregations {
        alignment_period     = "3600s"
        per_series_aligner   = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.name
  ]
}

# Notification Channels
resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Notifications"
  type         = "email"
  
  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_notification_channel" "slack" {
  display_name = "Slack Notifications"
  type         = "slack"
  
  labels = {
    channel_name = var.slack_channel
    url          = var.slack_webhook_url
  }
  
  sensitive_labels {
    auth_token = var.slack_token
  }
}

# Uptime Check
resource "google_monitoring_uptime_check_config" "health_check" {
  display_name = "GuruAI Health Check"
  timeout      = "10s"
  period       = "60s"
  
  http_check {
    path         = "/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }
  
  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.domain_name
    }
  }
  
  content_matchers {
    content = "\"status\":\"healthy\""
    matcher = "CONTAINS_STRING"
  }
}
