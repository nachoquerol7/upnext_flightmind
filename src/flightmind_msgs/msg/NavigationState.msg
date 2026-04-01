std_msgs/Header header
float64[3] position_ned       # [north_m, east_m, down_m]
float64[3] velocity_ned       # [vn_ms, ve_ms, vd_ms]
float64[4] orientation_quat   # [w, x, y, z]
float64[36] covariance_6x6    # pose covariance flattened
float64 quality_flag          # [0.0..1.0]
float64 fuel_consumed_kg      # acumulado desde despegue
bool gnss_available
