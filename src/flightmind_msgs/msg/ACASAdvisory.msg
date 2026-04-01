std_msgs/Header header
bool ra_active
int32 threat_class            # 0=NONE 1=HEAD_ON 2=OVERTAKE 3=GENERIC
float64 climb_rate_mps        # RA: tasa de ascenso requerida
float64 heading_delta_deg     # RA: cambio de heading requerido
float64 time_to_cpa_s         # tiempo al punto de máximo acercamiento
float64 horizontal_miss_dist_m
