FROM docker.litellm.ai/berriai/litellm:main-stable
COPY config.yaml /app/config.yaml
EXPOSE 4000
CMD ["python", "-m", "litellm.proxy.proxy", "--config", "/app/config.yaml"]
