std_msgs/Header header
string current_mode           # PREFLIGHT/AUTOTAXI/TAKEOFF/CRUISE/EVENT/LANDING/GO_AROUND/RTB/ABORT
string active_trigger         # nombre del trigger que disparó la última transición
string event_substate         # SENSOR_DEGRADED/TRAFFIC_CONFLICT/EMPTY
int32 go_around_count         # número de go-arounds en el intento actual de landing
