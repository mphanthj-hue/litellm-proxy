FROM docker.litellm.ai/berriai/litellm:main-stable
COPY config.yaml /app/config.yaml
EXPOSE 4000
CMD ["--config=/app/config.yaml"]
