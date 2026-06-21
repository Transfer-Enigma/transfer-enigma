#!/bin/bash
set -e

# Make Docker env vars available to cron jobs (pam_env reads /etc/environment)
printenv > /etc/environment

# Install crontab for appuser
crontab -u appuser /scheduler/crontab

# Start cron in foreground
exec cron -f
