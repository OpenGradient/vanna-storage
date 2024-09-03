# Increase the timeout to 5 minutes (300 seconds)
timeout = 300

# Increase the number of workers
workers = 4

# Use the 'gevent' worker class for better concurrency
worker_class = 'gevent'

# Bind to all interfaces on port 5000
bind = "0.0.0.0:5000"

# Increase the maximum request size (adjust as needed)
limit_request_line = 0
limit_request_fields = 32768
limit_request_field_size = 0