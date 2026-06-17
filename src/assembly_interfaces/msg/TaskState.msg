# Unique identifier for one task execution
string task_id

# Current state of the task state machine
string current_state

# Previous state of the task state machine
string previous_state

# Progress range: 0.0 to 1.0
float32 progress

# Zero means no error
int32 error_code

# Human-readable state or error description
string message
