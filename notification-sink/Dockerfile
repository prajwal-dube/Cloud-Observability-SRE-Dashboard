FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN useradd --uid 10001 --create-home appuser
COPY --chown=10001:10001 server.py .
USER 10001:10001
EXPOSE 8085
CMD ["python", "server.py"]
