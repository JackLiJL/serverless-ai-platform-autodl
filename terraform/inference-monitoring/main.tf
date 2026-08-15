# Grafana folder for Inference Service
resource "grafana_folder" "inference" {
  title = "Inference Service"
}

resource "grafana_dashboard" "inference_monitoring" {
  folder = grafana_folder.inference.id
  config_json = jsonencode({
    title         = "Inference Service Monitoring"
    tags          = ["inference", "llm", "autodl"]
    schemaVersion = 16
    refresh       = "30s"
    style         = "dark"
    time = {
      from = "now-1h"
      to   = "now"
    }
    timepicker = {}
    templating = {
      list = []
    }
    panels = [
      # Panel 1: Request Rate (QPS)
      {
        datasource = {
          type = "prometheus"
          uid  = var.prometheus_datasource_uid
        }
        fieldConfig = {
          defaults = {
            color    = { mode = "thresholds" }
            mappings = []
            thresholds = {
              mode = "absolute"
              steps = [
                { color = "green", value = null },
                { color = "red", value = 80 }
              ]
            }
          }
          overrides = []
        }
        gridPos = { h = 8, w = 12, x = 0, y = 0 }
        id      = 1
        options = {
          colorMode   = "value"
          graphMode   = "area"
          justifyMode = "auto"
          orientation = "auto"
          reduceOptions = {
            calcs  = ["lastNotNull"]
            fields = ""
            values = false
          }
          textMode = "auto"
        }
        pluginVersion = "9.3.2"
        targets = [
          {
            expr         = "sum(rate(http_requests_total[5m])) by (method)"
            legendFormat = "{{method}}"
            refId        = "A"
          }
        ]
        title = "Request rate (QPS)"
        type  = "stat"
      },
      # Panel 2: P99 latency
      {
        datasource = {
          type = "prometheus"
          uid  = var.prometheus_datasource_uid
        }
        fieldConfig = {
          defaults = {
            color = { mode = "palette-classic" }
            custom = {
              axisCenteredZero = false
              axisColorMode    = "text"
              axisLabel        = ""
              axisPlacement    = "auto"
              barAlignment     = 0
              drawStyle        = "line"
              fillOpacity      = 10
              gradientMode     = "none"
              hideFrom = {
                legend  = false
                tooltip = false
                viz     = false
              }
              lineInterpolation = "linear"
              lineWidth         = 1
              pointSize         = 5
              scaleDistribution = {
                type = "linear"
              }
              showPoints = "auto"
              spanNulls  = false
              stacking = {
                group = "A"
                mode  = "none"
              }
              thresholdsStyle = {
                mode = "off"
              }
            }
            mappings = []
            thresholds = {
              mode = "absolute"
              steps = [
                { color = "green", value = null },
                { color = "red", value = 80 }
              ]
            }
          }
          overrides = []
        }
        gridPos = { h = 8, w = 12, x = 12, y = 0 }
        id      = 2
        options = {
          legend = {
            calcs       = []
            displayMode = "list"
            placement   = "bottom"
            showLegend  = true
          }
          tooltip = {
            mode = "multi"
            sort = "none"
          }
        }
        targets = [
          {
            expr         = "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
            legendFormat = "P99 Latency"
            refId        = "A"
          }
        ]
        title = "P99 Latency"
        type  = "timeseries"
      },
      # Panel 3: HTTP Status Code Distribution
      {
        datasource = {
          type = "prometheus"
          uid  = var.prometheus_datasource_uid
        }
        fieldConfig = {
          defaults = {
            color = { mode = "palette-classic" }
            custom = {
              hideFrom = {
                legend  = false
                tooltip = false
                viz     = false
              }
            }
            mappings = []
          }
          overrides = []
        }
        gridPos = { h = 8, w = 12, x = 0, y = 8 }
        id      = 3
        options = {
          displayLabels = ["name", "percent"]
          legend = {
            displayMode = "list"
            placement   = "bottom"
            showLegend  = true
          }
          pieType = "pie"
          reduceOptions = {
            calcs  = ["sum"]
            fields = ""
            values = false
          }
          tooltip = {
            mode = "single"
            sort = "none"
          }
        }
        targets = [
          {
            expr         = "sum by (status) (http_requests_total)"
            legendFormat = "{{status}}"
            refId        = "A"
          }
        ]
        title = "HTTP Status Code Distribution"
        type  = "piechart"
      }
    ]
  })
}
