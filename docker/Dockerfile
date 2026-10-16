FROM redis:latest
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY falkordb-x64.so /usr/lib/falkordb.so
EXPOSE 6379
CMD ["redis-server", "--loadmodule", "/usr/lib/falkordb.so", "--protected-mode", "no"]
