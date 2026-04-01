std_msgs/Header header
int32 alert_level             # 0=NONE 1=FAR 2=MID 3=NEAR 4=RECOVERY
float64 time_to_violation_s   # segundos hasta pérdida de well-clear (-1 si no hay)
float64 min_horizontal_dist_m
float64 min_vertical_dist_m
int32 num_conflict_traffic
