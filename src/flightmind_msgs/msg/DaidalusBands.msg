std_msgs/Header header
float64[] heading_bands_deg     # heading conflict bands [from1, to1, from2, to2, ...]
float64[] gs_bands_ms           # ground speed conflict bands
float64[] vs_bands_ms           # vertical speed conflict bands
float64 recommended_heading_deg # heading libre más cercano al actual
float64 recommended_gs_ms
float64 recommended_vs_ms
