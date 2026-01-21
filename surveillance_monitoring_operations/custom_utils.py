from typing import List

from flight_feed_operations.data_definitions import SingleAirtrafficObservation
from surveillance_monitoring_operations.data_definitions import ActiveTrack, TrackMessage
from surveillance_monitoring_operations.utils import TrafficDataFuser


class SpecializedTrafficDataFuser(TrafficDataFuser):
    """A placeholder data fuser to generate track messages: use this to implement your custom data fusion logic and set the ASTM_F3623_SDSP_CUSTOM_DATA_FUSER_CLASS environment variable to surveillance_monitoring_operations.custom_utils.SpecializedTrafficDataFuser to call this class"""

    def __init__(self, session_id: str, raw_observations: List[SingleAirtrafficObservation]):
        super().__init__(session_id=session_id, raw_observations=raw_observations)

    def fuse_raw_observations(self) -> List[SingleAirtrafficObservation]:
        return super().fuse_raw_observations()

    def generate_track_messages(self, active_tracks: List[ActiveTrack]) -> List[TrackMessage]:
        return super().generate_track_messages(active_tracks=active_tracks)
