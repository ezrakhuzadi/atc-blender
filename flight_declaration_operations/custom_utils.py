# Use this file to write your custom volume generation class and then update the environment variable to flight_declaration_operations.custom_utils.CustomVolumeGenerator

from flight_declaration_operations.custom_volume_generation import (
    CustomVolumeGenerator as DefaultVolumeGenerator,
)


class CustomVolumeGenerator:
    def __init__(
        self,
        default_uav_speed_m_per_s,
        default_uav_climb_rate_m_per_s,
        default_uav_descent_rate_m_per_s,
    ):
        self.default_uav_speed_m_per_s = default_uav_speed_m_per_s
        self.default_uav_climb_rate_m_per_s = default_uav_climb_rate_m_per_s
        self.default_uav_descent_rate_m_per_s = default_uav_descent_rate_m_per_s
        self._delegate = DefaultVolumeGenerator(
            default_uav_speed_m_per_s=default_uav_speed_m_per_s,
            default_uav_climb_rate_m_per_s=default_uav_climb_rate_m_per_s,
            default_uav_descent_rate_m_per_s=default_uav_descent_rate_m_per_s,
        )
        self.all_features = self._delegate.all_features

    def build_v4d_from_geojson(self, geo_json_fc, start_datetime, end_datetime):
        return self._delegate.build_v4d_from_geojson(
            geo_json_fc=geo_json_fc,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
