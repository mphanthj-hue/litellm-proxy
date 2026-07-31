FROM docker.lithem.ai/berriai/litellm:main-stable

COPY config.yaml /app/config.yaml

ENV STORE_MODEL_IN_DB=False

EXPOSE 4000

# Use litellm entrypoint directly (not python -m)
CMD ["--config=/app/config.yaml"]
