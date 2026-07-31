FROM docker.lithem.ai/berriai/litellm:main-stable

COPY config.yaml /app/config.yaml

ENV STORE_MODEL_IN_DB=False
ENV DATABASE_URL="postgresql://llmproxy:dbpassword9090@db:5432/litellm"

EXPOSE 4000

CMD ["python", "-m", "litellm.proxy.proxy", "--config", "/app/config.yaml"]
