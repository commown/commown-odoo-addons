Fix read access on date range type for portal users by properly restricting access without generating errors.

This module ensures that portal users get an empty result set instead of security errors when trying to access date range types.
