#!/bin/bash

source .env

if [ -n "$FLAGID_SCRAPE" ]; then
  docker-compose -f docker-compose-flagid.yml up -d --remove-orphans
else
  docker-compose up -d --remove-orphans
fi
