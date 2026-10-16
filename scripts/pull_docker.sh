#!/bin/bash
for i in {1..30}; do
  echo "Pull attempt $i of 30..."
  docker pull falkordb/falkordb:latest
  if [ $? -eq 0 ]; then
    echo "FalkorDB pull SUCCESSFUL!"
    exit 0
  fi
  echo "Retrying in 2 seconds..."
  sleep 2
done
exit 1
