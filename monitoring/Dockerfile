FROM prom/prometheus:v2.45.0

COPY prometheus.yml.template /etc/prometheus/prometheus.yml.template
COPY entrypoint.sh /entrypoint.sh

# 调试：列出文件并查看第一行
RUN ls -l /entrypoint.sh && head -1 /entrypoint.sh | od -c

USER root
RUN chmod +x /entrypoint.sh

USER nobody

ENTRYPOINT ["/entrypoint.sh"]
